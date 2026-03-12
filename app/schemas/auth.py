from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    stay_signed_in: bool = False


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    stay_signed_in: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    role: str

    class Config:
        from_attributes = True
