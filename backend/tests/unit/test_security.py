import pytest
import jwt
from backend.app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from backend.app.core.config import settings

def test_password_hashing():
    password = "SuperSecretPassword123"
    hashed = hash_password(password)
    
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_token_creation_and_decoding():
    user_id = 42
    token = create_access_token(data={"sub": str(user_id)})
    
    decoded = decode_access_token(token)
    assert decoded.get("sub") == str(user_id)
    assert "exp" in decoded

def test_invalid_token_decoding():
    invalid_token = "invalid.jwt.token"
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(invalid_token)
