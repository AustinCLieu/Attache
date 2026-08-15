import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

class SignupIn(BaseModel):
    """POST /auth/signup request body."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class LoginIn(BaseModel):
    """POST /auth/login request body"""

    email: EmailStr
    password: str

class UserOut(BaseModel):
    """Public shape of a user, never includes password_hash"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    display_name: str | None
    created_at: datetime

    