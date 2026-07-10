import pytest
from crypto import encrypt_payload, decrypt_payload
from cryptography.fernet import InvalidToken

def test_encryption_decryption_cycle():
    payload = "Super secret message"
    ciphertext, key_b64 = encrypt_payload(payload)
    assert ciphertext != payload
    assert key_b64 is not None
    
    plaintext = decrypt_payload(ciphertext, key_b64)
    assert plaintext == payload

def test_decryption_with_invalid_key():
    payload = "Another secret"
    ciphertext, _ = encrypt_payload(payload)
    _, wrong_key_b64 = encrypt_payload("dummy")
    
    with pytest.raises(InvalidToken):
        decrypt_payload(ciphertext, wrong_key_b64)

def test_decryption_tampered_ciphertext():
    payload = "Tamper me"
    ciphertext, key_b64 = encrypt_payload(payload)
    # Alter the last character
    tampered = ciphertext[:-1] + ("A" if ciphertext[-1] != "A" else "B")
    
    with pytest.raises(InvalidToken):
        decrypt_payload(tampered, key_b64)

def test_encryption_randomness():
    payload = "Identical payload"
    c1, _ = encrypt_payload(payload)
    c2, _ = encrypt_payload(payload)
    assert c1 != c2

def test_empty_payload():
    ciphertext, key_b64 = encrypt_payload("")
    plaintext = decrypt_payload(ciphertext, key_b64)
    assert plaintext == ""

def test_large_payload():
    payload = "A" * 1000000  # 1MB string
    ciphertext, key_b64 = encrypt_payload(payload)
    plaintext = decrypt_payload(ciphertext, key_b64)
    assert plaintext == payload
