from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from uuid import uuid4
from datetime import datetime, timedelta, timezone
import secrets
from typing import Optional
from db import get_db
from crypto import encrypt_payload, decrypt_payload
from scanner import scan_payload
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="AgentDrop", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

class DropPayload(BaseModel):
    payload: str = Field(..., max_length=102400, description="The string data to securely transfer.")
    ttl_seconds: int = Field(default=3600, ge=60, le=86400)

@app.post("/drop")
@limiter.limit("5/minute")
def create_drop(request: Request, data: DropPayload):
    # 1. Scan for injection
    scan_result = scan_payload(data.payload)
    if scan_result["status"] == "blocked":
        raise HTTPException(status_code=400, detail=scan_result["reason"])

    # 2. Encrypt payload
    ciphertext, key_b64 = encrypt_payload(data.payload)

    # 3. Generate IDs
    drop_id = str(uuid4())
    revoke_token = secrets.token_urlsafe(16)
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=data.ttl_seconds)).isoformat()
    created_at = datetime.now(timezone.utc).isoformat()

    # 4. Store in DB
    conn = get_db()
    conn.execute(
        "INSERT INTO drops (id, ciphertext, created_at, expires_at, status, revoke_token) VALUES (?, ?, ?, ?, 'active', ?)",
        (drop_id, ciphertext, created_at, expires_at, revoke_token)
    )
    conn.execute(
        "INSERT INTO receipts (drop_id, action, timestamp) VALUES (?, 'created', ?)",
        (drop_id, created_at)
    )
    conn.commit()
    conn.close()

    # 5. Return URL with key in fragment
    url = f"/x/{drop_id}#{key_b64}"
    return {
        "id": drop_id,
        "url": url,
        "revoke_token": revoke_token,
        "expires_at": expires_at,
        "scan_status": scan_result["status"]
    }

@app.get("/x/{drop_id}")
def read_drop(drop_id: str, key: str):
    conn = get_db()
    drop = conn.execute("SELECT * FROM drops WHERE id = ?", (drop_id,)).fetchone()

    if not drop:
        raise HTTPException(status_code=404, detail="Drop not found.")
    if drop["status"] != "active":
        conn.execute("INSERT INTO receipts (drop_id, action, timestamp) VALUES (?, 'failed_access', ?)", (drop_id, datetime.now(timezone.utc).isoformat()))
        conn.commit()
        raise HTTPException(status_code=403, detail=f"Drop is {drop['status']}.")
    if datetime.now(timezone.utc) > datetime.fromisoformat(drop["expires_at"]):
        conn.execute("UPDATE drops SET status = 'expired' WHERE id = ?", (drop_id,))
        conn.execute("INSERT INTO receipts (drop_id, action, timestamp) VALUES (?, 'expired', ?)", (drop_id, datetime.now(timezone.utc).isoformat()))
        conn.commit()
        raise HTTPException(status_code=410, detail="Drop expired.")

    # Decrypt FIRST to prevent Denial of Service via invalid keys
    try:
        plaintext = decrypt_payload(drop["ciphertext"], key)
    except Exception:
        # Record failed attempt
        conn.execute("UPDATE drops SET failed_attempts = failed_attempts + 1 WHERE id = ?", (drop_id,))
        failed = conn.execute("SELECT failed_attempts FROM drops WHERE id = ?", (drop_id,)).fetchone()["failed_attempts"]
        
        if failed >= 3:
            conn.execute("UPDATE drops SET status = 'revoked' WHERE id = ?", (drop_id,))
            conn.execute("INSERT INTO receipts (drop_id, action, timestamp) VALUES (?, 'revoked_brute_force', ?)", (drop_id, datetime.now(timezone.utc).isoformat()))
            conn.commit()
            conn.close()
            raise HTTPException(status_code=403, detail="Too many failed attempts. Drop destroyed.")
            
        conn.commit()
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid decryption key or corrupt payload.")
        
    # Atomic update to prevent race conditions on successful reads
    cursor = conn.execute("UPDATE drops SET status = 'used' WHERE id = ? AND status = 'active'", (drop_id,))
    if cursor.rowcount == 0:
        # Another request beat us to it
        conn.close()
        raise HTTPException(status_code=409, detail="Drop was just consumed.")

    conn.execute("INSERT INTO receipts (drop_id, action, timestamp) VALUES (?, 'served', ?)", (drop_id, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    conn.close()
    return {"payload": plaintext, "status": "used"}

@app.post("/revoke/{drop_id}")
def revoke_drop(drop_id: str, revoke_token: str):
    conn = get_db()
    drop = conn.execute("SELECT * FROM drops WHERE id = ?", (drop_id,)).fetchone()
    if not drop:
        raise HTTPException(status_code=404, detail="Drop not found.")
    if drop["revoke_token"] != revoke_token:
        raise HTTPException(status_code=403, detail="Invalid revoke token.")
    if drop["status"] != "active":
        raise HTTPException(status_code=400, detail=f"Cannot revoke, drop is already {drop['status']}.")

    cursor = conn.execute("UPDATE drops SET status = 'revoked' WHERE id = ? AND status = 'active'", (drop_id,))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=400, detail="Cannot revoke, drop was just modified.")
    
    conn.execute("INSERT INTO receipts (drop_id, action, timestamp) VALUES (?, 'revoked', ?)", (drop_id, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    conn.close()
    return {"status": "revoked"}

@app.get("/receipt/{drop_id}")
def get_receipt(drop_id: str, key: Optional[str] = None, revoke_token: Optional[str] = None):
    conn = get_db()
    
    drop = conn.execute("SELECT ciphertext, revoke_token FROM drops WHERE id = ?", (drop_id,)).fetchone()
    if not drop:
        raise HTTPException(status_code=404, detail="No receipt found.")
        
    if not key and not revoke_token:
        raise HTTPException(status_code=401, detail="Authentication required (provide key or revoke_token).")
        
    if revoke_token:
        if drop["revoke_token"] != revoke_token:
            raise HTTPException(status_code=403, detail="Invalid revoke token.")
    elif key:
        try:
            decrypt_payload(drop["ciphertext"], key)
        except Exception:
            raise HTTPException(status_code=403, detail="Invalid decryption key.")
            
    receipts = conn.execute("SELECT action, timestamp FROM receipts WHERE drop_id = ? ORDER BY timestamp ASC", (drop_id,)).fetchall()
    return {"drop_id": drop_id, "events": [dict(r) for r in receipts]}

@app.get("/health")
def health():
    return {"status": "ok"}
