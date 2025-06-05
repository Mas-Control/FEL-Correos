from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from schemas.token import Token
from database import get_db
from core.security import (
    get_accountant_token,
    get_refresh_token,
    get_company_token,
)

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post(
    "/accountant/token",
    response_model=Token,
    status_code=status.HTTP_200_OK,
)
async def accountant_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    """
    Authenticate a user and return an access token.
    """
    try:
        token = await get_accountant_token(
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


@router.post(
    "/accountant/refresh",
    response_model=Token,
    status_code=status.HTTP_200_OK,
)
async def refresh(
    refresh_token: str = Header(...),
    db: Session = Depends(get_db),
) -> Token:
    """
    Refresh the access token using the refresh token.
    """
    try:
        new_token = await get_refresh_token(
            token=refresh_token,
            db=db,
        )
        return new_token
    except HTTPException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid credentials {e}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


@router.post(
    "/company/token",
    response_model=Token,
    status_code=status.HTTP_200_OK,
)
async def company_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    """
    Authenticate a user and return an access token.
    """
    try:
        token = await get_company_token(
            nit=form_data.username,
            api_key=form_data.password,
            db=db,
        )
        return token
    except HTTPException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login failed, {e}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
