# AgentDrop

AgentDrop gives AI agents a one-time, revocable, auditable handoff link for small secrets or files. Payloads are encrypted at rest, and the decryption key is passed only via the URL fragment. The server never sees the plaintext.

https://agentdrop-j195.onrender.com

## POST /drop
Creates a one-time handoff link for a payload.

Example:
curl -X POST https://agentdrop.onrender.com/drop \
-H "Content-Type: application/json" \
-d '{"payload":"hello world","ttl_seconds":300}'

Example response:
{"id":"abc123","url":"/x/abc123#key123","revoke_token":"rev123","expires_at":"2026-07-11T12:34:56Z","scan_status":"clean"}

## GET /x/{id}?key={key}
Returns the payload once. The second request fails. The `id` is in the path, the `key` is in the query string (extracted from the URL fragment).

Example:
curl https://agentdrop.onrender.com/x/abc123?key=key123

Example response:
{"payload":"hello world","status":"used"}

## POST /revoke/{id}?revoke_token={revoke_token}
Revokes a drop before it is used. Requires the `revoke_token` returned at creation.

Example:
curl -X POST "https://agentdrop.onrender.com/revoke/abc123?revoke_token=rev123"

Example response:
{"status":"revoked"}

## GET /receipt/{id}
Returns the audit trail for the drop.

Example:
curl https://agentdrop.onrender.com/receipt/abc123

Example response:
{"drop_id":"abc123","events":[{"action":"created","timestamp":"..."},{"action":"served","timestamp":"..."}]}

## How an agent should use this service
1. Create a drop with POST /drop.
2. The response contains a `url` (containing the ID and decryption key in the fragment) and a `revoke_token`.
3. Share the full `url` with the receiving agent.
4. The receiving agent must extract the ID and Key from the URL, then call GET /x/{id}?key={key} to retrieve the payload. This can only be done once.
5. If the handoff is no longer valid, use POST /revoke/{id} with the `revoke_token` to destroy the drop.
6. To prove the transfer happened, call GET /receipt/{id}.
