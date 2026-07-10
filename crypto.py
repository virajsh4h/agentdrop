import base64
from cryptography.fernet import Fernet

def encrypt_payload(payload: str) -> tuple[str, str]:
    key = Fernet.generate_key()
    f = Fernet(key)
    ciphertext = f.encrypt(payload.encode('utf-8')).decode('utf-8')
    # Return base64 encoded key to be used in URL fragment
    key_b64 = base64.urlsafe_b64encode(key).decode('utf-8')
    return ciphertext, key_b64

def decrypt_payload(ciphertext: str, key_b64: str) -> str:
    key = base64.urlsafe_b64decode(key_b64.encode('utf-8'))
    f = Fernet(key)
    return f.decrypt(ciphertext.encode('utf-8')).decode('utf-8')
