"""
Security module for handling authentication and authorization.
This module provides functions for user authentication, password hashing,
token generation, and user access verification.
"""
from fastapi import HTTPException, Depends, Request
from database import Session, get_db
from schemas.token import Token
from models.models import Accountants
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from typing import Optional, Callable
from config import get_settings
from datetime import timedelta, datetime, timezone
from jose import jwt, JWTError, ExpiredSignatureError
from functools import wraps
from uuid import UUID

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
settings = get_settings()


async def get_token(
    username: str, password: str, db: Session
) -> Token:
    """
    Authenticate a user based on their email and password and generate an 
    access and refresh token.

    Args:
        email (str): The user's email address.
        password (str): The user's plain text password.
        db (Session): The SQLAlchemy database session dependency.

    Returns:
        dict: A dictionary containing access token, refresh token, expiration
        time, and token type.

    Raises:
        HTTPException: If the email is not registered, password is incorrect,
        or user access is not verified.
    """
    try:
        username = username.lower().strip()
        user = (
            db.query(Accountants)
            .filter(Accountants.email == username, Accountants.is_active)
            .first()
        )

        if not user or not user.password:
            raise HTTPException(status_code=400, detail="User does not exist.")
        if not verify_password(password, user.password):
            raise HTTPException(status_code=400, detail="Invalid credentials.")
        return await get_user_token(user=user, refresh=True)

    except HTTPException as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid login credentials. {e}",
        ) from e


async def get_refresh_token(token: str, db: Session) -> Token:
    """
    Generate a new access token using a valid refresh token.

    Args:
        token (str): The JWT refresh token.
        db (Session): The SQLAlchemy database session dependency.

    Returns:
        dict: A dictionary containing a new access token, refresh token,
        expiration time, and token type.

    Raises:
        HTTPException: If the refresh token is invalid or the user is not
        found.
    """
    payload = get_token_payload(token=token)
    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token.",
        )
    user_id = payload.get("id", None)
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token.",
        )
    user = db.query(Accountants).filter(Accountants.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token.",
        )
    return await get_user_token(user=user, refresh_token=token, refresh=True)


def verify_password(plain_password: str, password: str) -> bool:
    """
    Verify if the provided plain password matches the hashed password.
    """
    return pwd_context.verify(plain_password, password)


async def get_user_token(
    user: Accountants,
    refresh_token: Optional[str] = None,
    refresh: bool = False
) -> Token:
    """
    Generate access and refresh tokens for the user.

    Args:
        user (User): The user object for whom the tokens are being generated.
        refresh_token (Optional[str]): An existing refresh token, if available.

    Returns:
        dict: A dictionary containing the access token, refresh token, 
        expiration
        time, and token type.
    """

    payload = {
        "id": str(user.id)
    }

    if settings.ACCESS_TOKEN_EXPIRE_MINUTES is None:
        raise HTTPException(
            status_code=500,
            detail=(
                """Access token expiration time is not set in the
                configuration."""
            ),
        )
    access_token_expiry = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    access_token = await create_access_token(payload, access_token_expiry)
    if not refresh_token or refresh:
        refresh_token_expiry = timedelta(
            minutes=settings.REFRESH_ACCESS_TOKEN_EXPIRE_MINUTES or 4320
        )
        refresh_token = await create_refresh_token(
            payload, refresh_token_expiry
        )

    expires_in = access_token_expiry.total_seconds()

    token = Token(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(expires_in),
        token_type="bearer",
    )
    return token


async def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None
) -> str:
    """
    Creates a new JWT access token.
    """
    if not settings.JWT_SECRET:
        raise ValueError("JWT_SECRET is not set in settings.")

    if not settings.ALGORITHM:
        raise ValueError("ALGORITHM is not set in settings.")
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


async def create_refresh_token(
    data: dict, expires_delta: Optional[timedelta] = None
) -> str:
    """
    Creates a new JWT refresh token.
    """
    if not settings.JWT_SECRET:
        raise ValueError("JWT_SECRET is not set in settings.")

    if not settings.ALGORITHM:
        raise ValueError("ALGORITHM is not set in settings.")

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=4320)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def get_password_hash(password: str) -> str:
    """
    Hashes the given password using passlib.
    """
    try:
        if not password:
            raise ValueError("Password cannot be empty.")
        return pwd_context.hash(password)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail="Password cannot be empty.",
        ) from e


async def get_current_accountant(
        token: str = Depends(oauth2_scheme),
        db=None
) -> Accountants:
    """
    Retrieves the current user based on the provided JWT token.
    """
    if not settings.JWT_SECRET:
        raise ValueError("JWT_SECRET is not set in settings.")

    if not settings.ALGORITHM:
        raise ValueError("ALGORITHM is not set in settings.")
    try:
        payload = get_token_payload(token)
        if not payload:
            print("payload is none")
            raise HTTPException(
                status_code=401,
                detail="Could not validate credentials",
            )

        user_id = payload.get("id")
        if not user_id:
            print("user_id is none")
            raise HTTPException(
                status_code=401,
                detail="Could not validate credentials",
            )

        user_id = UUID(user_id)

    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=401,
            detail="Token has expired",
        ) from exc
    except (JWTError, ValueError) as exc:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
        ) from exc

    # Initialize db if not provided
    if not db:
        db = next(get_db())

    user = db.query(Accountants).filter(Accountants.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
        )
    return user


def get_token_payload(token: str) -> Optional[dict]:
    """
    Decodes the given JWT token to extract its payload.
    """
    if not settings.JWT_SECRET:
        raise ValueError("JWT_SECRET is not set in settings.")

    if not settings.ALGORITHM:
        raise ValueError("ALGORITHM is not set in settings.")

    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM]
        )
    except JWTError:
        print("JWTError", token)
        return None
    return payload


def api_key_auth(api_key_name: str = "X-API-Key"):
    """
    Decorator to implement API key authentication.
    
    Args:
        api_key_name (str): The name of the header field containing the API
        key.
            Defaults to "X-API-Key".
    
    Returns:
        Callable: The decorated function.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            api_key = request.headers.get(api_key_name)
            if not api_key:
                raise HTTPException(
                    status_code=401,
                    detail=f"Missing {api_key_name} header"
                )
            if api_key != settings.SCHEDULER_API_KEY:
                raise HTTPException(
                    status_code=403,
                    detail="Invalid API key"
                )
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


async def get_api_key(
        request: Request, api_key_name: str = "X-API-Key"
) -> str:
    """
    Dependency to get and validate the API key from request headers.
    
    Args:
        request (Request): The FastAPI request object.
        api_key_name (str): The name of the header field containing the API
        key.
    
    Returns:
        str: The validated API key.
    
    Raises:
        HTTPException: If the API key is missing or invalid.
    """
    api_key = request.headers.get(api_key_name)
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail=f"Missing {api_key_name} header"
        )
    if api_key != settings.SCHEDULER_API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    return api_key

def verify_api_key(plain_api_key: str, hashed_api_key: str) -> bool:
    return pwd_context.verify(plain_api_key, hashed_api_key)