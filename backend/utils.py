# backend/utils.py
import bcrypt
from datetime import datetime, timedelta
from typing import Union

from jose import jwt
from passlib.context import CryptContext

SECRET_KEY = "YOUR_SECRET_KEY"  # Replace with a strong, random secret key
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hashes the password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verifies the password against the hashed password."""
    return pwd_context.verify(password, hashed_password)


def create_access_token(subject: Union[str, any], expires_delta: timedelta = None) -> str:
    """Creates a JWT access token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)  # Default: 15 minutes
    to_encode = {"exp": expire, "sub": str(subject)}  # Subject must be a string
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_password_hash(password):
    return pwd_context.hash(password)
