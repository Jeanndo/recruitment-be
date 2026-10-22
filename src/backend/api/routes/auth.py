"""Login, logout and "who am I".

The session is kept in a signed, HttpOnly cookie created by Starlette's
SessionMiddleware. "HttpOnly" means JavaScript cannot read it, so a cross-site
scripting bug cannot steal the session the way it could steal a token from
localStorage. The cookie only contains the user id; it is signed, so a client
cannot change that id without the server's secret key.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.dependencies import get_current_user
from backend.core.security import password_needs_rehash, hash_password, verify_password
from backend.database import get_db
from backend.models.user import User
from backend.schemas.auth import LoginRequest, LoginResponse, LogoutResponse
from backend.schemas.user import UserResponse

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Log in as a staff member",
)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """Check the credentials and start a session.

    The same 401 message is used for an unknown email and a wrong password.
    Saying "no such account" would let an attacker discover which addresses
    have accounts.
    """
    # Emails are stored lowercase, so the lookup is lowercase too.
    email = payload.email.lower()
    user = db.scalar(select(User).where(User.email == email))

    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # If the stored hash was made with older parameters, upgrade it now that
    # we know the password is correct. The user never notices.
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
        db.commit()

    # Clear first so a previous session cannot survive a login as another user.
    request.session.clear()
    request.session["user_id"] = user.id

    return LoginResponse(
        user=UserResponse.model_validate(user),
        message="Logged in successfully.",
    )


@router.post("/logout", response_model=LogoutResponse, summary="End the current session")
def logout(request: Request) -> LogoutResponse:
    """Forget the session cookie.

    This is deliberately allowed without being logged in: logging out twice
    should be harmless, not an error.
    """
    request.session.clear()
    return LogoutResponse(message="Logged out successfully.")


@router.get("/me", response_model=UserResponse, summary="Get the logged-in user")
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    """Return the account behind the current session (used by the frontend on load)."""
    return current_user
