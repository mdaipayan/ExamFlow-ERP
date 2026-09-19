import pytest

from app.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_round_trip():
    password = "A-secure-password-123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong-password", hashed)


def test_short_password_rejected():
    with pytest.raises(ValueError):
        hash_password("short")


def test_access_token_round_trip(monkeypatch):
    monkeypatch.setattr("app.settings.settings.jwt_secret", "x" * 40)
    token = create_access_token("user-1", "institution-1", ["TC"])
    claims = decode_access_token(token)
    assert claims["sub"] == "user-1"
    assert claims["institution_id"] == "institution-1"
    assert claims["roles"] == ["TC"]
