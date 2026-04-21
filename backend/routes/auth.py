"""
Authentication Route — Dainik-Vidya
Handles Signup and Login with JWT and bcrypt.
Sets is_subscribed_email=True on signup; backfills on login.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
import jwt
import os
from datetime import datetime, timedelta, timezone
from database import get_collection

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("JWT_SECRET", "super-secret-dainik-vidya-key-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

class AuthRequest(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@router.post("/signup")
async def signup(request: AuthRequest):
    users_col = get_collection("users")
    existing_user = await users_col.find_one({"email": request.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = pwd_context.hash(request.password)
    user_doc = {
        "email": request.email,
        "name": request.name or "",
        "password": hashed_password,
        "is_subscribed_email": True,
        "preferred_topics": [],
        "top_n_preference": 10,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    await users_col.insert_one(user_doc)

    access_token = create_access_token(
        data={"sub": request.email}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "email": request.email,
            "name": request.name,
            "is_subscribed_email": True,
        },
    }


@router.post("/login")
async def login(request: AuthRequest):
    users_col = get_collection("users")
    user = await users_col.find_one({"email": request.email})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or password")
    
    if not pwd_context.verify(request.password, user["password"]):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    # Backfill personalization fields for legacy users
    updates = {}
    if "is_subscribed_email" not in user:
        updates["is_subscribed_email"] = True
    if "preferred_topics" not in user:
        updates["preferred_topics"] = []
    if "top_n_preference" not in user:
        updates["top_n_preference"] = 10
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)
        await users_col.update_one({"_id": user["_id"]}, {"$set": updates})
        user.update(updates)

    access_token = create_access_token(
        data={"sub": request.email}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "email": user["email"],
            "name": user.get("name", ""),
            "is_subscribed_email": user.get("is_subscribed_email", True),
        },
    }
