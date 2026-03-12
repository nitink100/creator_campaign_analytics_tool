from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.deps.db import get_db_session
from app.deps.auth import get_current_user
from app.models.user import User
from app.schemas.auth import SignupRequest, LoginRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_access_token(user_id: str, *, stay_signed_in: bool = False) -> str:
    settings = get_settings()
    minutes = (
        settings.STAY_SIGNED_IN_EXPIRE_MINUTES
        if stay_signed_in
        else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


@router.post("/signup", response_model=TokenResponse)
async def signup(
    body: SignupRequest,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )
    settings = get_settings()
    role = "user"
    if settings.ADMIN_EMAIL and body.email.lower() == settings.ADMIN_EMAIL.lower():
        role = "admin"
    user = User(
        email=body.email.lower(),
        hashed_password=_hash_password(body.password),
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    access_token = _create_access_token(user.id, stay_signed_in=body.stay_signed_in)
    return TokenResponse(access_token=access_token)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()
    if not user or not _verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    access_token = _create_access_token(user.id, stay_signed_in=body.stay_signed_in)
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(id=current_user.id, email=current_user.email, role=current_user.role)
