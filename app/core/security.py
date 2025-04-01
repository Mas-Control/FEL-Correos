from fastapi import HTTPException, Depends
from app.database import Session
from app.schemas.token import Token
from app.models.models import Auth
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from app.config import get_settings
from datetime import timedelta, datetime, timezone
from jose import jwt, JWTError, ExpiredSignatureError
from app.database import get_db

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
        print(user.id)

        if not user:
            raise HTTPException(status_code=400, detail="User does not exist.")
        if not verify_password(password, user.password_hash):
            raise HTTPException(status_code=400, detail="Invalid credentials.")
        _verify_user_access(user=user)
        return await get_user_token(user=user, refresh=True)

    except HTTPException as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid login credentials. {e}",
        ) from e


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify if the provided plain password matches the hashed password.
    """
    print(plain_password)
    print(hashed_password)
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
    user: Auth,
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


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db=None
) -> Auth:
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
                detail="Could not validate credentials 1",
            )

        user_id = payload.get("id")
        if not user_id:
            print("user_id is none")
            raise HTTPException(
                status_code=401,
                detail="Could not validate credentials 2",
            )

        # user_id = UUID(user_id)

    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=401,
            detail="Token has expired",
        ) from exc
    except (JWTError, ValueError) as exc:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials 3",
        ) from exc

    # Initialize db if not provided
    if not db:
        db = next(get_db())

    user = db.query(Auth).filter(Auth.id == user_id).first()
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