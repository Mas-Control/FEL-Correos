from fastapi import HTTPException
from app.database import Session
from app.schemas.token import Token
from app.models.models import Auth
from app.main import logger
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from app.config import get_settings
from datetime import timedelta


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
        user = db.query(Auth).filter(Auth.username == username).first()

        if not user:
            raise HTTPException(status_code=400, detail="User does not exist.")
        if not verify_password(password, user.password_hash):
            raise HTTPException(status_code=400, detail="Invalid credentials.")
        _verify_user_access(user=user)
        return await get_user_token(user=user, refresh=True, db=db)
    except HTTPException as e:
        logger.error(f"Error getting token: {e}")
        raise HTTPException(
            status_code=400,
            detail="Invalid login credentials.",
        )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify if the provided plain password matches the hashed password.
    """
    return pwd_context.verify(plain_password, hashed_password)


def _verify_user_access(user: Auth) -> None:
    """
    Verify the user's access to the system.

    Args:
        user (User): The user object to verify.

    Raises:
        HTTPException: If the user's account is inactive or has been deleted.
    """
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Inactive user. Please contact support.",
        )


async def get_user_token(
    user: Auth, db: Session,
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
    print(user.id)

    payload = {
        "id": str(user.id)
    }

    if settings.ACCESS_TOKEN_EXPIRE_MINUTES is None:
        raise HTTPException(
            status_code=500,
            detail="Access token expiration time is not set in the configuration.",
        )
    access_token_expiry = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = await create_access_token(payload, access_token_expiry)
    if not refresh_token or refresh:
        refresh_token_expiry = timedelta(
            minutes=settings.REFRESH_ACCESS_TOKEN_EXPIRE_DAYS or 4320
        )
        refresh_token = await create_refresh_token(payload, refresh_token_expiry)

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