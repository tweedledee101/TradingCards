"""
Auth API endpoints

Cognito handles signup/login directly (hosted UI or Amplify).
These endpoints handle post-auth operations: user info, account management.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from backend.utils.database import get_db
from backend.utils.auth import require_auth
from backend.models import User, Account

router = APIRouter()


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    account_type: Optional[str] = None


class InviteMember(BaseModel):
    email: str
    role: str = "member"


@router.get("/auth/me")
def get_me(current_user: User = Depends(require_auth)):
    """Return current user + account info."""
    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "display_name": current_user.display_name,
            "role": current_user.role,
        },
        "account": {
            "id": current_user.account_id,
            "name": current_user.account.name,
            "account_type": current_user.account.account_type,
        },
    }


@router.put("/auth/account")
def update_account(
    data: AccountUpdate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Update account settings (owner/admin only)."""
    if current_user.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Owner or admin required")

    account = db.get(Account, current_user.account_id)
    if data.name:
        account.name = data.name
    if data.account_type and data.account_type in ("individual", "business"):
        account.account_type = data.account_type
    db.commit()
    return {"message": "Account updated", "account_type": account.account_type}


@router.post("/auth/invite")
def invite_member(
    data: InviteMember,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Invite a team member to a business account (owner/admin only)."""
    if current_user.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Owner or admin required")

    account = db.get(Account, current_user.account_id)
    if account.account_type != "business":
        raise HTTPException(status_code=400, detail="Upgrade to business account first")

    if data.role not in ("admin", "member"):
        raise HTTPException(status_code=400, detail="Role must be admin or member")

    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="User already exists")

    user = User(
        account_id=current_user.account_id,
        email=data.email,
        role=data.role,
    )
    db.add(user)
    db.commit()
    return {"message": f"Invited {data.email} as {data.role}", "user_id": user.id}


@router.get("/auth/team")
def get_team(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """List team members for the account."""
    members = db.query(User).filter(User.account_id == current_user.account_id).all()
    return {
        "members": [
            {
                "id": m.id,
                "email": m.email,
                "display_name": m.display_name,
                "role": m.role,
                "is_active": m.is_active,
                "last_login": m.last_login_at.isoformat() if m.last_login_at else None,
            }
            for m in members
        ]
    }
