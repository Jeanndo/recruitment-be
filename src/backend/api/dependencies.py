"""Shared FastAPI dependencies.

The most important one is authentication. A dependency is just a function
that FastAPI calls before the route; if it raises, the route never runs. That
is why every admin endpoint can be protected with a single line instead of a
manual check at the top of each function.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.user import User, UserRole

# Only these roles may use the admin area. Candidates are not users at all -
# they apply through the public form.
STAFF_ROLES = {UserRole.ADMIN, UserRole.RECRUITER}


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Return the staff member behind the signed session cookie.

    Raises 401 when there is no session, when the user was deleted, or when
    the account has been deactivated. A deactivated account is treated as
    logged out and its session is cleared.
    """
    user_id = request.session.get("user_id")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )

    user = db.get(User, user_id)

    if user is None or not user.is_active:
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )

    return user


def require_staff(current_user: User = Depends(get_current_user)) -> User:
    """Allow only administrators and recruiters through.

    401 means "we don't know who you are"; 403 means "we know, but you are
    not allowed". Keeping them separate makes the frontend's behaviour clear.
    """
    if current_user.role not in STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action.",
        )
    return current_user
