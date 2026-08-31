import uuid

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.repositories import user_repo
from app.security import decode_access_token

# Name of the cookie the JWT rides in. Defined once here so the login route
# and this dependency can never disagree about it.
COOKIE_NAME = "attache_session"


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Resolve the caller's identity from the session cookie.

    Identity comes ONLY from the verified JWT (design doc §3.2, enforcement
    layer 1). Nothing here reads a user id from the path, query string, or
    body — a caller cannot ask to be someone else.
    """
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )

    token = request.cookies.get(COOKIE_NAME)
    if token is None:
        raise credentials_error

    # Returns None on a bad signature, a malformed token, or an expired one.
    subject = decode_access_token(token)
    if subject is None:
        raise credentials_error

    # The token is valid, but the id inside it still has to be a real UUID.
    try:
        user_id = uuid.UUID(subject)
    except ValueError:
        raise credentials_error

    # A signed token for a since-deleted user must not authenticate anyone.
    user = user_repo.get_by_id(db, user_id)
    if user is None:
        raise credentials_error

    return user
