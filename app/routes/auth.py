from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.schemas.auth import TokenResponse, UserCreate, UserLogin, UserResponse
from app.security import create_access_token, decode_access_token, hash_password, verify_password


router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

DbSession = Annotated[Session, Depends(get_db)]
BearerToken = Annotated[str, Depends(oauth2_scheme)]


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def get_current_user(token: BearerToken, db: DbSession) -> User:
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please log in again. Your session is missing or invalid.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please log in again. This token does not include a user.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account no longer exists. Please register or log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(user_data: UserCreate, db: DbSession) -> User:
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists. Please log in instead.",
        )

    user = User(
        full_name=user_data.full_name,
        email=user_data.email,
        phone=user_data.phone,
        password_hash=hash_password(user_data.password),
        role=user_data.role,
    )

    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="We could not create this account because the email is already in use.",
        ) from None

    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login_user(login_data: UserLogin, db: DbSession) -> TokenResponse:
    user = get_user_by_email(db, login_data.email)
    if user is None or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please check your details and try again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={
            "user_id": user.id,
            "role": user.role,
            "email": user.email,
        },
    )
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user
