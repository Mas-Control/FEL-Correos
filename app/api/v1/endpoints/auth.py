from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.schemas.token import Token
from app.database import get_db
from app.core.security import get_token, create_refresh_token

router = APIRouter(prefix="/v1/auth")


@router.post(
    "/token",
    response_model=Token,
    status_code=status.HTTP_200_OK,
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    """
    Authenticate a user and return an access token.
    """
    try:
        token = await get_token(
            username=form_data.username,
            password=form_data.password,
            db=db,
        )
        return token
    except HTTPException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid credentials {e}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e