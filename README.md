<div align="center">

# AgentDrop

**A Secure, Ephemeral Handoff Protocol for AI Agents**

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/SQLite-07405E?style=for-the-badge&logo=sqlite)](https://www.sqlite.org/)
[![pytest](https://img.shields.io/badge/pytest-passing-success?style=for-the-badge&logo=pytest)](https://docs.pytest.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

*Built for the next 20 years of agentic architectures.*

</div>

---

## Overview

AgentDrop is a stateless, ephemeral data-transfer microservice designed specifically for multi-agent systems. It allows autonomous AI agents to securely exchange sensitive data—such as API keys, access tokens, or private datasets—using one-time, revocable handoff links. 

To maintain strict API simplicity for LLMs and autonomous agents, AgentDrop handles encryption and decryption server-side. This removes the need for client agents to bundle, execute, or understand complex cryptography libraries.

---

## Architecture & Security Implementation

AgentDrop is engineered to mitigate specific vulnerabilities common in multi-agent environments.

- **Server-Side Encryption (AES-Fernet):** Payloads are encrypted at rest in the database. The decryption key is generated dynamically, appended to the drop URL as a fragment, and must be provided back to the server to decrypt and consume the payload.
- **Race Condition Prevention:** True ephemerality is enforced at the database level. Upon successful decryption, payloads are marked as consumed via atomic SQLite transactions combined with Write-Ahead Logging (WAL) mode. This strictly prevents race-condition replay attacks where concurrent agents attempt to consume the same drop simultaneously.
- **Prompt Injection Firewall:** A pre-flight firewall (`scanner.py`) actively scans payloads using regex patterns to block known LLM prompt injection vectors (e.g., system prompt overrides, `<|im_start|>` tokens) before they reach the database.
- **Brute-Force & Denial of Service Protection:**
  - **3-Strike Lockout:** Drops are only consumed upon successful decryption. If a caller fails decryption 3 times using an invalid key, the drop is permanently locked.
  - **Rate Limiting:** The creation endpoint is rate-limited to 5 requests per minute per IP using `slowapi` to prevent infrastructure exhaustion.
  - **Payload Limits:** Strict 100KB size limits prevent database storage exhaustion.
- **Authenticated Audit Receipts:** Every action in a drop's lifecycle is logged in an immutable ledger. The receipt endpoint requires either the decryption key or the revocation token to view the audit trail, preventing public metadata leakage.

---

## Testing & Quality Assurance

The system is backed by a rigorous suite of 37 isolated tests covering:
- Concurrency and race-condition attempts
- Cryptographic failure states (tampered ciphertext, invalid keys)
- Brute-force lockout and rate-limiting validation
- Prompt injection bypass attempts and edge-cases
- API lifecycle routing (creation, consumption, revocation, and audit)

---

## System Architecture

```text
agentdrop/
├── main.py             # FastAPI routing, rate limiting, and endpoints
├── db.py               # SQLite schema, WAL mode, and atomic transactions
├── crypto.py           # Fernet symmetric encryption 
├── scanner.py          # Pre-flight prompt injection firewall
├── requirements.txt    # Pinned dependencies (fastapi, slowapi, cryptography)
├── Dockerfile          # OCI-compliant container definition
└── tests/              # 37 comprehensive tests with isolated databases
```

---

## Quickstart & Deployment

AgentDrop requires no external services (like Redis or Postgres), utilizing a local SQLite database for maximum portability.

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

AgentDrop includes a production-ready `Dockerfile` intended for deployment to container-as-a-service providers like Render, Fly.io, or Railway.

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
