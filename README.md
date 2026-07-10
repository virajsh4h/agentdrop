<div align="center">
  <h1>🛡️ AgentDrop</h1>
  <p><strong>The Secure, Ephemeral Handoff Protocol for the Agentic Web</strong></p>
</div>

---

## 🌌 The Future of Agentic Architecture

As we transition into the era of the **Internet of AI Agents**, autonomous systems will continuously negotiate, collaborate, and transact. But how do two independent, mutually distrusting AI agents securely exchange sensitive data—API keys, access tokens, encrypted payloads, or private datasets—without relying on centralized, persistent storage that is vulnerable to data breaches?

**AgentDrop** is the answer. It is a stateless-by-design, cryptographic dead-drop service built specifically for multi-agent systems. It ensures that data is passed exactly once, securely, and with a mathematically verifiable audit trail. 

AgentDrop introduces the **Zero-Trust URL Fragment Protocol**. Payloads are encrypted at rest on the server. The decryption key is never seen, stored, or logged by the server; it is passed exclusively through the URL fragment (`#key`), which is processed entirely client-side by the receiving agent. Even if the AgentDrop database is completely compromised, the payloads remain mathematically unreadable.

---

## ✨ Core Innovations

1. **Zero-Trust Encryption Model:** The payload is encrypted server-side using AES (via Fernet). The decryption key is generated dynamically and appended to the URL as a `#` fragment. Because browsers and HTTP clients do not send URL fragments to the server, the decryption key never touches our logs. 
2. **True Ephemerality (Burn-After-Reading):** Data is read exactly once. The moment a payload is successfully decrypted, it is mathematically obliterated from active status via atomic database transactions, preventing race-condition replay attacks.
3. **Agentic Prompt Injection Firewall:** AI agents are highly vulnerable to prompt injection attacks embedded within data payloads. AgentDrop features a pre-flight firewall (`scanner.py`) that actively scans and blocks payloads attempting to hijack the receiving agent's context window.
4. **Verifiable Audit Receipts:** Every action (creation, consumption, revocation, expiration) is logged in an immutable receipt ledger, providing verifiable proof of handoff for escrow and arbitration services.

---

## 🏗️ System Architecture

```text
agentdrop/
├── main.py             # FastAPI routing and orchestration
├── db.py               # SQLite schema and transactional logic
├── crypto.py           # Fernet symmetric encryption 
├── scanner.py          # Pre-flight prompt injection firewall
├── requirements.txt    # Minimal, pinned dependencies
├── Dockerfile          # OCI-compliant container definition
└── tests/              # Rigorous QA and invariant testing
```

---

## 🚀 Quickstart & Deployment

AgentDrop is designed to run anywhere—from a local Jupyter notebook to a globally distributed Kubernetes cluster. It requires zero external dependencies, utilizing a local SQLite file for lightning-fast, portable persistence.

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
pytest tests/test_api.py

# 4. Start the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker Deployment (Render, Railway, Fly.io)
AgentDrop includes a production-ready `Dockerfile`. To deploy, simply connect your GitHub repository to a PaaS provider (like Render or Railway) and select Docker as the runtime environment.

```bash
docker build -t agentdrop .
docker run -p 80:80 agentdrop
```

---

## 📖 API Reference

### 1. Create a Drop
`POST /drop`
Encrypts a payload and generates a secure handoff link.
- **Request:** `{"payload": "super_secret_token", "ttl_seconds": 3600}`
- **Response:** Returns the `id`, the `revoke_token`, and the `url` containing the key in the fragment.

### 2. Consume a Drop
`GET /x/{id}?key={key}`
Retrieves and decrypts the payload exactly once. 
*Note: AI agents must parse the URL fragment from the creation response to extract the `key` parameter.*
- **Response:** `{"payload": "super_secret_token", "status": "used"}`

### 3. Revoke a Drop
`POST /revoke/{id}?revoke_token={revoke_token}`
Destroys a payload before it can be consumed. Essential for agents aborting a transaction.

### 4. Audit Trail
`GET /receipt/{id}`
Returns a chronological ledger of the drop's lifecycle for dispute resolution.

---

## 🤖 The `SKILL.md`

AgentDrop is fully compatible with the NANDA Town ecosystem. A complete `SKILL.md` is provided in the repository, instructing external LLM agents exactly how to format payloads, parse fragments, and utilize the API autonomously.

---
*Built for the future. Built for the Internet of Agents.*
