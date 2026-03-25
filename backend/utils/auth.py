"""
Cognito JWT Authentication

Validates access tokens from AWS Cognito User Pool.
Resolves user -> account for tenant-scoped queries.

Set COGNITO_USER_POOL_ID and COGNITO_CLIENT_ID (env or backend/.env) when using JWT.
If unset, /api/auth/* strict routes return 503; get_current_user still falls back to
default account user for backward compatibility when no Bearer token is sent.

Usage:
    @router.get("/protected")
    def endpoint(current_user: User = Depends(get_current_user)):
        account_id = current_user.account_id
"""
import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError, jwk
from sqlalchemy.orm import Session

from backend.utils.database import get_db
from backend.models import User, Account

security = HTTPBearer(auto_error=False)

COGNITO_REGION = os.getenv("COGNITO_REGION", "us-east-1").strip()
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "").strip()
COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID", "").strip()


def _cognito_configured() -> bool:
    return bool(COGNITO_USER_POOL_ID and COGNITO_CLIENT_ID)


def _jwks_url() -> Optional[str]:
    if not _cognito_configured():
        return None
    return (
        f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/"
        f"{COGNITO_USER_POOL_ID}/.well-known/jwks.json"
    )


def _issuer() -> Optional[str]:
    if not _cognito_configured():
        return None
    return (
        f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/"
        f"{COGNITO_USER_POOL_ID}"
    )


@lru_cache(maxsize=1)
def _get_jwks():
    """Fetch and cache Cognito JWKS (public keys for token verification)."""
    url = _jwks_url()
    if not url:
        raise RuntimeError("Cognito JWKS URL not configured")
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.URLError as e:
        raise RuntimeError(f"Failed to fetch JWKS: {e}") from e


def _decode_token(token: str) -> dict:
    """Decode and validate a Cognito JWT access token."""
    if not _cognito_configured():
        raise JWTError("Cognito not configured")

    jwks = _get_jwks()
    headers = jwt.get_unverified_headers(token)
    kid = headers.get("kid")

    key = None
    for k in jwks["keys"]:
        if k["kid"] == kid:
            key = k
            break
    if not key:
        raise JWTError("Key not found")

    return jwt.decode(
        token,
        key,
        algorithms=["RS256"],
        audience=COGNITO_CLIENT_ID,
        issuer=_issuer(),
        options={"verify_at_hash": False},
    )


def _get_or_create_user(db: Session, claims: dict) -> User:
    """Find user by cognito_sub, or auto-provision on first login."""
    sub = claims["sub"]
    user = db.query(User).filter(User.cognito_sub == sub).first()
    if user:
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)
        return user

    # First login -- create account + user
    email = claims.get("email", f"{sub}@unknown")
    display_name = claims.get("name") or claims.get("email", "").split("@")[0]

    account = Account(name=display_name, account_type="individual")
    db.add(account)
    db.flush()

    user = User(
        account_id=account.id,
        cognito_sub=sub,
        email=email,
        display_name=display_name,
        role="owner",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency: extract and validate JWT, return User.

    Returns default account user (id=1) when no token is provided,
    so existing unauthenticated flows keep working during migration.
    """
    if not credentials:
        # No token -- fall back to default account for backward compat
        user = db.query(User).filter(User.account_id == 1).first()
        if user:
            return user
        # No default user yet -- create one for the default account
        user = User(account_id=1, email="default@ragnarokgamez.com", display_name="Default", role="owner")
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    if not _cognito_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured (set COGNITO_USER_POOL_ID and COGNITO_CLIENT_ID)",
        )

    try:
        claims = _decode_token(credentials.credentials)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _get_or_create_user(db, claims)


async def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Strict auth -- no fallback to default account."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not _cognito_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured (set COGNITO_USER_POOL_ID and COGNITO_CLIENT_ID)",
        )

    try:
        claims = _decode_token(credentials.credentials)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _get_or_create_user(db, claims)
