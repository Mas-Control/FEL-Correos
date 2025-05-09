"""Accountant router module.
This module defines the API endpoints for managing accountants.
It includes routes for registering, activating, and managing accountants.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models.models import (
    Accountants,
    Subscriptions,
    Companies,
    AccountantCompanies
)
from schemas.accountant import AccountantCreate, AccountantUpdate
from schemas.company import CompanyCreate, CompanyUpdate
from core.security import get_password_hash
import secrets
from users.helper import (
    _send_credentials, _get_subscription_by_name
)
from logging import getLogger

logger = getLogger(__name__)

router = APIRouter(prefix="/v1/users", tags=["users"])


@router.post(
    "/accountant/register",
    status_code=status.HTTP_201_CREATED,
)
async def register_accountant(
    accountant: AccountantCreate,
    db: Session = Depends(get_db),
) -> None:
    """
    Register a new user.
    """

    try:
        # Check if the accountant already exists
        existing_accountant = db.query(Accountants).filter(
            Accountants.email == accountant.email.lower().strip()
        ).first()
        if existing_accountant:
            logger.info("Accountant already exists: %s", accountant.email)
            return

        logger.info("Registering accountant: %s", accountant.email)
        subscription: Subscriptions = _get_subscription_by_name(
            subscription_name=accountant.subscription_name,
            db=db,
        )
        if not subscription or subscription.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found. Please contact support.",
            )
        logger.info("Subscription found: %s", subscription.name)
        # Create new Accountant
        new_accountant = Accountants()
        new_accountant.email = accountant.email.lower().strip()
        new_accountant.subscription_id = subscription.id
        new_accountant.first_name = accountant.first_name
        new_accountant.last_name = accountant.last_name

        db.add(new_accountant)
        db.commit()
        db.refresh(new_accountant)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while registering the accountant. {e}",
        ) from e


@router.patch(
    "/accountant/{email}/status",
    status_code=status.HTTP_200_OK
)
async def activate_accountant(
    email: str,
    accountant_upt: AccountantUpdate,
    db: Session = Depends(get_db),
) -> None:
    """
    Activate a accountant and send credentials.
    """
    try:
        # Check if the accountant exists
        accountant = (
            db.query(Accountants)
            .filter(Accountants.email == email.lower().strip())
            .first()
        )
        if not accountant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Accountant not found.",
            )
        if accountant.is_active == accountant_upt.is_active:
            return

        if accountant.is_active and not accountant_upt.is_active:
            # Deactivate the accountant
            accountant.is_active = False
            db.commit()
            db.refresh(accountant)
            return

        password = secrets.token_urlsafe(13)
        accountant.password = get_password_hash(password)
        # Activate the accountant
        accountant.is_active = True
        db.commit()
        db.refresh(accountant)

        # Uppdate the accountant's relation with the company
        accountant_company = db.query(AccountantCompanies).filter(
            AccountantCompanies.accountant_id == accountant.id
        ).all()
        for company in accountant_company:
            company.is_active = True
            db.commit()
            db.refresh(company)

        # Send credentials to the accountant
        _send_credentials(email=accountant.email, password=password)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while activating the accountant. {e}",
        ) from e


@router.post(
    "/company/register",
    status_code=status.HTTP_201_CREATED
)
async def register_company(
    company: CompanyCreate,
    db: Session = Depends(get_db),
) -> None:
    """
    Register a new user.
    """

    try:
        # Check if the accountant already exists
        existing_company = db.query(Companies).filter(
            Companies.email == company.email.lower().strip()
        ).first()
        if existing_company:
            logger.info("Company already exists: %s", company.email)
            return

        logger.info("Registering company: %s", company.email)
        # Create new Company
        new_company = Companies()
        new_company.email = company.email.lower().strip()
        new_company.name = company.name
        new_company.nit = company.nit

        db.add(new_company)
        db.commit()
        db.refresh(new_company)

        if company.accountant_email:
            logger.info(
                "Linking company to accountant: %s", company.accountant_email
            )
            accountant = db.query(Accountants).filter(
                Accountants.email == company.accountant_email.lower().strip()
            ).first()
            if not accountant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Accountant not found.",
                )
            company_relation_status = False
            if accountant.is_active:
                company_relation_status = True

            # Create new AccountantCompany
            accountant_company = AccountantCompanies()
            accountant_company.accountant_id = accountant.id
            accountant_company.company_id = new_company.id
            accountant_company.is_active = company_relation_status
            db.add(accountant_company)
            db.commit()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while registering the company. {e}",
        ) from e


@router.patch(
    "/company/{nit}/status",
    status_code=status.HTTP_200_OK
)
async def activate_company(
    nit: str,
    company_upt: CompanyUpdate,
    db: Session = Depends(get_db),
) -> None:
    """
    Activate a company and send credentials.
    """
    try:
        # Check if the accountant exists
        company = (
            db.query(Companies)
            .filter(Companies.nit == nit)
            .first()
        )
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found.",
            )
        if company.is_active == company_upt.is_active:
            return

        if company.is_active and not company_upt.is_active:
            # Deactivate the company
            company.is_active = False
            db.commit()
            db.refresh(company)
            return

        api_key = secrets.token_urlsafe(13)
        company.api_key = get_password_hash(api_key)
        # Activate the company
        company.is_active = True
        db.commit()
        db.refresh(company)

        # Send credentials to the company
        _send_credentials(
            email=company.email, password=api_key, is_company=True
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while activating the company. {e}",
        ) from e