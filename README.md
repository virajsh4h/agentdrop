<div align="center">
  <h1>🛡️ AgentDrop</h1>
  <p><strong>A Secure, Ephemeral Handoff Protocol for AI Agents</strong></p>
  
  [![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
  [![SQLite](https://img.shields.io/badge/SQLite-07405E?style=flat&logo=sqlite)](https://www.sqlite.org/)
  [![pytest](https://img.shields.io/badge/pytest-passing-success?style=flat&logo=pytest)](https://docs.pytest.org/)
</div>

---

## Overview

**AgentDrop** is a stateless, ephemeral data-transfer microservice designed for multi-agent systems. It allows autonomous AI agents to securely exchange sensitive data—such as API keys, access tokens, or private datasets—using one-time, revocable handoff links. 

To maintain strict API simplicity for LLMs and autonomous agents, AgentDrop handles encryption and decryption **server-side**, removing the need for client agents to bundle or execute complex cryptography libraries.

---

## Security & Architecture Features

1. **Server-Side Encryption (AES-Fernet):** 
   Payloads are encrypted at rest in the database. The decryption key is generated dynamically, appended to the drop URL, and must be provided back to the server to decrypt and consume the payload.
2. **True Ephemerality (Burn-After-Reading):** 
   Payloads can be read exactly once. Upon successful decryption, the payload is permanently marked as consumed via atomic SQLite database transactions, mitigating race-condition replay attacks.
3. **Brute-Force & Denial of Service Protection:** 
   - **3-Strike Lockout:** To prevent attackers from invalidating drops with incorrect keys, drops are only consumed upon successful decryption. If a caller fails decryption 3 times, the drop is permanently locked.
   - **Rate Limiting:** The creation endpoint is rate-limited (5 requests per minute, per IP) using `slowapi` to prevent resource exhaustion.
   - **Payload Limits:** Strict 100KB size limits prevent database storage exhaustion.
4. **Authenticated Audit Receipts:** 
   Every action in a drop's lifecycle is logged. The receipt endpoint requires either the decryption key or the revocation token to view the audit trail, preventing public metadata leakage.
5. **Prompt Injection Firewall:** 
   A pre-flight firewall (`scanner.py`) actively scans and blocks payloads containing known LLM prompt injection vectors before they are stored.

---

## System Architecture

```text
agentdrop/
├── main.py             # FastAPI routing, rate limiting, and endpoints
├── db.py               # SQLite schema, WAL mode, and migrations
├── crypto.py           # Fernet symmetric encryption 
├── scanner.py          # Pre-flight prompt injection firewall
├── requirements.txt    # Pinned dependencies (fastapi, slowapi, cryptography)
├── Dockerfile          # OCI-compliant container definition
└── tests/              # Comprehensive test suite with isolated databases
```

---

## Quickstart & Deployment

AgentDrop uses a local SQLite database configured with Write-Ahead Logging (WAL) for high concurrency. It requires no external services (like Redis or Postgres).

### Local Development
```bash
# 1. Clone and enter the repository
git clone https://github.com/your-username/agentdrop.git
cd agentdrop

# 2. Set up the virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Run the test suite
pytest tests/ -v

# 4. Start the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker Deployment
AgentDrop includes a production-ready `Dockerfile`. It is ready to be deployed to container-as-a-service providers like Render, Fly.io, or Railway.

```bash
docker build -t agentdrop .
docker run -p 80:80 agentdrop
```

---

## API Reference

### 1. Create a Drop
`POST /drop`
Encrypts a payload (max 100KB) and generates a secure handoff link. Rate-limited to 5 requests per minute.
- **Request:** `{"payload": "secret_token", "ttl_seconds": 3600}`
- **Response:** Returns the `id`, the `revoke_token`, and the `url`.

### 2. Consume a Drop
`GET /x/{id}?key={key}`
Retrieves and decrypts the payload exactly once. 
- **Response:** `{"payload": "secret_token", "status": "used"}`

### 3. Revoke a Drop
`POST /revoke/{id}?revoke_token={revoke_token}`
Permanently destroys a payload before it can be consumed.
- **Response:** `{"status": "revoked"}`

### 4. Audit Trail
`GET /receipt/{id}?key={key}` or `?revoke_token={revoke_token}`
Returns a chronological ledger of the drop's lifecycle. Requires authentication.
- **Response:** `{"drop_id": "abc123", "events": [{"action": "created", "timestamp": "..."}]}`

---

## Autonomous Agent Integration

AgentDrop provides a [`SKILL.md`](./SKILL.md) file detailing how external LLMs and AI agents can autonomously format requests, handle authentication, and parse API responses. Providing this skill file in an agent's context window allows it to use AgentDrop without human intervention.
