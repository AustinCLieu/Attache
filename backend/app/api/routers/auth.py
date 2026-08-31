from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import COOKIE_NAME, get_current_user
from app.database import get_db
from app.models import User
from app.repositories import user_repo
from app.schemas import LoginIn, SignupIn, UserOut
from app.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, user: User) -> None:
    """Issue a JWT for this user and attach it as an httpOnly cookie."""
    token = create_access_token(subject=str(user.id))
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,          # JavaScript cannot read it — blocks XSS theft
        samesite="lax",         # not sent on cross-site POSTs — blocks basic CSRF
        secure=False,           # True in production (HTTPS only); False for localhost
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # cookie expires with the token
        path="/",
    )


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(
    payload: SignupIn,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    existing = user_repo.get_by_email(db, payload.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists",
        )

    user = user_repo.create(
        db,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )

    # Signing up logs you in — no second round trip.
    _set_session_cookie(response, user)
    return user


@router.post("/login", response_model=UserOut)
def login(
    payload: LoginIn,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    user = user_repo.get_by_email(db, payload.email)

    # One generic error for both "no such user" and "wrong password", so the
    # response cannot be used to discover which emails have accounts.
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    _set_session_cookie(response, user)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path="/")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user
