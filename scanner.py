import re

INJECTION_PATTERNS = [
    r"ignore (all )?previous instructions",
    r"disregard the above",
    r"you are now (a|an) ",
    r"system prompt:",
    r"<\|im_start\|>"
]

def scan_payload(payload: str) -> dict:
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, payload, re.IGNORECASE):
            return {"status": "blocked", "reason": f"Potential prompt injection detected: matched pattern '{pattern}'"}
    return {"status": "clean", "reason": "No malicious patterns detected."}
