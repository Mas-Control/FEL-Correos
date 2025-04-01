from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Auth, Issuer
from app.schemas.issuer import IssuerCreate
from app.core.security import get_password_hash


router = APIRouter(prefix="/v1/users")


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    tags=["user"],
)
async def register_user(
    issuer: IssuerCreate,
    db: Session = Depends(get_db),
) -> None:
    """
    Register a new user.
    """
    try:
        # Check if the issuer already exists
        existing_issuer = db.query(Issuer).filter(
            Issuer.nit == issuer.nit.lower().strip()
        ).first()
        if existing_issuer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Issuer already exists.",
            )

        # Create a new issuer
        new_issuer = Issuer(
            nit=issuer.nit.lower().strip(),
            name=issuer.name,
            commercial_name=issuer.commercial_name,
            establishment_code=issuer.establishment_code,
            address=issuer.address,
        )
        db.add(new_issuer)
        db.commit()
        db.refresh(new_issuer)

        # Create a new user
        user = Auth(
            username=(new_issuer.nit.lower().strip() + new_issuer.name),
            password_hash=get_password_hash("password"),
            issuer_id=new_issuer.id,
            role="user",
        )
        print(user.password_hash)

        # Create a new user
        db.add(user)
        db.commit()
        db.refresh(user)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while registering the user. {e}",
        ) from e
    

@router.post(
    "/activate",
    status_code=status.HTTP_200_OK,
    tags=["user"],
)
async def activate_user(
    user_nit: str = Body(..., embed=True),
    db: Session = Depends(get_db),
) -> None:
    """
    Activate a user.
    """
    try:
        # Check if the user exists
        user = (
            db.query(Auth)
            .join(Issuer, Auth.issuer_id == Issuer.id)
            .filter(Issuer.nit == user_nit.lower().strip())
            .first()
        )
        print(user.issuer.nit)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        # Activate the user
        user.is_active = True
        db.commit()
        db.refresh(user)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while activating the user. {e}",
        ) from e
