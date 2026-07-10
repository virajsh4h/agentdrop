import pytest
import sqlite3
import os
from datetime import datetime, timedelta, timezone

def test_create_drop_default_ttl(client):
    res = client.post("/drop", json={"payload": "secret"})
    assert res.status_code == 200
    assert "url" in res.json()

def test_create_drop_min_ttl(client):
    res = client.post("/drop", json={"payload": "secret", "ttl_seconds": 60})
    assert res.status_code == 200

def test_create_drop_max_ttl(client):
    res = client.post("/drop", json={"payload": "secret", "ttl_seconds": 86400})
    assert res.status_code == 200

def test_create_drop_invalid_ttl_low(client):
    res = client.post("/drop", json={"payload": "secret", "ttl_seconds": 59})
    assert res.status_code == 422

def test_create_drop_invalid_ttl_high(client):
    res = client.post("/drop", json={"payload": "secret", "ttl_seconds": 86401})
    assert res.status_code == 422

def test_create_drop_missing_payload(client):
    res = client.post("/drop", json={"ttl_seconds": 3600})
    assert res.status_code == 422

def test_create_drop_large_payload(client):
    large_payload = "A" * 1000000
    res = client.post("/drop", json={"payload": large_payload})
    assert res.status_code == 200

def test_read_drop_success(client):
    res = client.post("/drop", json={"payload": "secret_code"})
    data = res.json()
    drop_id = data["id"]
    key = data["url"].split("#")[1]

    read_res = client.get(f"/x/{drop_id}", params={"key": key})
    assert read_res.status_code == 200
    assert read_res.json()["payload"] == "secret_code"

def test_read_drop_incorrect_key(client):
    res = client.post("/drop", json={"payload": "secret_code"})
    drop_id = res.json()["id"]
    wrong_key = "invalidkeybase64format="
    read_res = client.get(f"/x/{drop_id}", params={"key": wrong_key})
    assert read_res.status_code == 400
    assert "Invalid decryption key" in read_res.json()["detail"]

def test_read_drop_not_found(client):
    read_res = client.get("/x/nonexistent-id", params={"key": "dummy"})
    assert read_res.status_code == 404

def test_read_drop_already_used(client):
    res = client.post("/drop", json={"payload": "secret_code"})
    data = res.json()
    drop_id = data["id"]
    key = data["url"].split("#")[1]

    client.get(f"/x/{drop_id}", params={"key": key}) # First read
    read_res_2 = client.get(f"/x/{drop_id}", params={"key": key}) # Second read
    assert read_res_2.status_code == 403

def test_read_drop_revoked(client):
    res = client.post("/drop", json={"payload": "temp_data"})
    data = res.json()
    drop_id = data["id"]
    key = data["url"].split("#")[1]
    
    client.post(f"/revoke/{drop_id}", params={"revoke_token": data["revoke_token"]})
    read_res = client.get(f"/x/{drop_id}", params={"key": key})
    assert read_res.status_code == 403

def test_read_drop_expired(client):
    res = client.post("/drop", json={"payload": "secret", "ttl_seconds": 60})
    data = res.json()
    drop_id = data["id"]
    key = data["url"].split("#")[1]
    
    # Manually update expiration time in DB to simulate expiry
    db_path = os.environ.get("TESTING_DB")
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE drops SET expires_at = ? WHERE id = ?", (datetime.now(timezone.utc) - timedelta(seconds=1), drop_id))
    conn.commit()
    conn.close()

    read_res = client.get(f"/x/{drop_id}", params={"key": key})
    assert read_res.status_code == 410

def test_revoke_drop_success(client):
    res = client.post("/drop", json={"payload": "secret"})
    data = res.json()
    rev_res = client.post(f"/revoke/{data['id']}", params={"revoke_token": data["revoke_token"]})
    assert rev_res.status_code == 200

def test_revoke_drop_invalid_token(client):
    res = client.post("/drop", json={"payload": "secret"})
    data = res.json()
    rev_res = client.post(f"/revoke/{data['id']}", params={"revoke_token": "wrong_token"})
    assert rev_res.status_code == 403

def test_revoke_drop_not_found(client):
    rev_res = client.post("/revoke/nonexistent-id", params={"revoke_token": "token"})
    assert rev_res.status_code == 404

def test_revoke_already_used_drop(client):
    res = client.post("/drop", json={"payload": "secret"})
    data = res.json()
    client.get(f"/x/{data['id']}", params={"key": data["url"].split("#")[1]})
    
    rev_res = client.post(f"/revoke/{data['id']}", params={"revoke_token": data["revoke_token"]})
    assert rev_res.status_code == 400
    assert "already used" in rev_res.json()["detail"]

def test_double_revoke(client):
    res = client.post("/drop", json={"payload": "secret"})
    data = res.json()
    client.post(f"/revoke/{data['id']}", params={"revoke_token": data["revoke_token"]})
    rev_res_2 = client.post(f"/revoke/{data['id']}", params={"revoke_token": data["revoke_token"]})
    assert rev_res_2.status_code == 400

def test_receipt_not_found(client):
    res = client.get("/receipt/nonexistent")
    assert res.status_code == 404

def test_receipt_flow(client):
    res = client.post("/drop", json={"payload": "secret"})
    data = res.json()
    drop_id = data["id"]
    key = data["url"].split("#")[1]
    
    # 1. Created receipt
    rec = client.get(f"/receipt/{drop_id}").json()["events"]
    assert len(rec) == 1
    assert rec[0]["action"] == "created"
    
    # 2. Read receipt
    client.get(f"/x/{drop_id}", params={"key": key})
    rec = client.get(f"/receipt/{drop_id}").json()["events"]
    assert len(rec) == 2
    assert rec[1]["action"] == "served"
    
    # 3. Failed read receipt
    client.get(f"/x/{drop_id}", params={"key": key})
    rec = client.get(f"/receipt/{drop_id}").json()["events"]
    assert len(rec) == 3
    assert rec[2]["action"] == "failed_access"

def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
