"""Auth dependency contract tests (no network)."""
import asyncio
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import JWTError

import backend.utils.auth as auth_utils
from backend.utils.auth import require_auth


def _run(coro):
    return asyncio.run(coro)


def test_require_auth_no_credentials_returns_401():
    db = MagicMock()
    with pytest.raises(HTTPException) as exc:
        _run(require_auth(credentials=None, db=db))
    assert exc.value.status_code == 401


def test_require_auth_missing_cognito_returns_503(monkeypatch):
    monkeypatch.setattr(auth_utils, "COGNITO_USER_POOL_ID", "")
    monkeypatch.setattr(auth_utils, "COGNITO_CLIENT_ID", "")
    cred = HTTPAuthorizationCredentials(scheme="Bearer", credentials="dummy.jwt.here")
    db = MagicMock()
    with pytest.raises(HTTPException) as exc:
        _run(require_auth(credentials=cred, db=db))
    assert exc.value.status_code == 503


def test_require_auth_invalid_token_returns_401(monkeypatch):
    monkeypatch.setattr(auth_utils, "COGNITO_USER_POOL_ID", "us-east-1_fake")
    monkeypatch.setattr(auth_utils, "COGNITO_CLIENT_ID", "fakeclient")

    def bad_decode(_token):
        raise JWTError("invalid")

    monkeypatch.setattr(auth_utils, "_decode_token", bad_decode)
    cred = HTTPAuthorizationCredentials(scheme="Bearer", credentials="x.y.z")
    db = MagicMock()
    with pytest.raises(HTTPException) as exc:
        _run(require_auth(credentials=cred, db=db))
    assert exc.value.status_code == 401
