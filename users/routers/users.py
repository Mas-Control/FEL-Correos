"""Accountant router module.
This module defines the API endpoints for managing accountants.
It includes routes for registering, activating, and managing accountants.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models.models import Accountants, Subscriptions, Companies, AccountantCompanies, InvoiceRequests
from schemas.accountant import AccountantCreate
from schemas.company import CompanyCreate
from core.security import get_password_hash, get_api_key
import secrets
from users.helper import _send_credentials, _get_subscription_by_name
from logging import getLogger
from uuid import UUID

logger = getLogger(__name__)

router = APIRouter(prefix="/v1/users", tags=["users"])


@router.post(
    "/accountant/register",
    status_code=status.HTTP_201_CREATED,
)
async def register_accountant(
    accountant: AccountantCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
) -> None:
    """
    Register a new accountant in the system.

    This endpoint creates a new accountant record with the provided information and sets up
    their initial invoice request tracking. The accountant will be created in an inactive state
    and will need to be activated separately.

    Args:
        accountant (AccountantCreate): The accountant information including:
            - email: The accountant's email address
            - first_name: The accountant's first name
            - last_name: The accountant's last name
            - subscription_name: The name of the subscription plan
        db (Session): Database session for database operations
        api_key (str): API key for authentication

    Raises:
        HTTPException (404): If the specified subscription is not found or is inactive
        HTTPException (500): If there's an error during the registration process

    Returns:
        None: The function returns nothing on success
    """

    try:
        # Check if the accountant already exists
        existing_accountant = (
            db.query(Accountants)
            .filter(Accountants.email == accountant.email.lower().strip())
            .first()
        )
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

        # Create initial invoice request record
        invoice_request = InvoiceRequests(
            accountant_id=new_accountant.id,
            request_count=0
        )
        db.add(invoice_request)
        db.commit()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while registering the accountant. {e}",
        ) from e


@router.patch("/accountant/{email}/status", status_code=status.HTTP_200_OK)
async def activate_accountant(
    email: str,
    status: bool,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
) -> None:
    """
    Activate or deactivate an accountant and manage their relationships.

    This endpoint handles the activation/deactivation of an accountant and their relationships
    with companies. When activating an accountant:
    - Generates a new password
    - Sets the accountant as active
    - Activates all their company relationships
    - Sends credentials to the accountant's email

    When deactivating an accountant:
    - Sets the accountant as inactive
    - Deactivates all their company relationships

    Args:
        email (str): The email address of the accountant to activate/deactivate
        status (bool): True to activate, False to deactivate
        db (Session): Database session for database operations
        api_key (str): API key for authentication

    Raises:
        HTTPException (404): If the accountant is not found
        HTTPException (500): If there's an error during the activation/deactivation process

    Returns:
        None: The function returns nothing on success
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
        if accountant.is_active == status:
            return

        if accountant.is_active and not status:
            # Deactivate the accountant
            accountant.is_active = status
            db.commit()
            db.refresh(accountant)
            # Deactivate the accountant's relation with the company
            accountant_company = (
                db.query(AccountantCompanies)
                .filter(AccountantCompanies.accountant_id == accountant.id)
                .all()
            )
            for company in accountant_company:
                company.is_active = False
                db.commit()
                db.refresh(company)
            return

        password = secrets.token_urlsafe(13)
        accountant.password = get_password_hash(password)
        # Activate the accountant
        accountant.is_active = True
        db.commit()
        db.refresh(accountant)

        # Uppdate the accountant's relation with the company
        accountant_company = (
            db.query(AccountantCompanies)
            .filter(AccountantCompanies.accountant_id == accountant.id)
            .all()
        )
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


@router.post("/company/register", status_code=status.HTTP_201_CREATED)
async def register_companies(
    companies: list[CompanyCreate],
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
) -> dict:
    """
    Register multiple companies in bulk with optional accountant relationships.

    This endpoint handles the registration of multiple companies in a single request. For each company:
    - Creates a new company record
    - Sets up initial invoice request tracking
    - Optionally links the company to an accountant
    - Handles subscription assignment

    The endpoint also handles special cases:
    - Updates existing inactive companies with new subscriptions
    - Checks accountant NIT limits before creating relationships
    - Creates accountant-company relationships if specified

    Args:
        companies (list[CompanyCreate]): List of companies to register, each containing:
            - email: Company's email address
            - name: Company's name
            - nit: Company's NIT number
            - subscription_name: Optional subscription plan name
            - accountant_email: Optional accountant's email for relationship
        db (Session): Database session for database operations
        api_key (str): API key for authentication

    Returns:
        dict: A summary of the registration results containing:
            - successful: List of successfully registered companies
            - failed: List of failed registrations with reasons

    Raises:
        HTTPException (404): If an accountant is not found
        HTTPException (400): If an accountant has reached their NIT limit
        HTTPException (500): If there's an error during the registration process
    """
    results = {
        "successful": [],
        "failed": []
    }

    for company in companies:
        try:
            # Check if the company already exists
            existing_company = (
                db.query(Companies)
                .filter(Companies.email == company.email.lower().strip())
                .first()
            )
            if existing_company:
                if not existing_company.is_active and not existing_company.subscription_id and company.subscription_name:
                    # Update existing company with new subscription
                    logger.info("Updating inactive company with subscription: %s", company.email)
                    subscription = _get_subscription_by_name(
                        subscription_name=company.subscription_name,
                        db=db,
                    )
                    if subscription and subscription.is_active:
                        existing_company.subscription_id = subscription.id
                        existing_company.name = company.name
                        existing_company.nit = company.nit
                        db.commit()
                        db.refresh(existing_company)
                        
                        # Handle accountant relation if provided
                        if company.accountant_email:
                            logger.info("Linking company to accountant: %s", company.accountant_email)
                            accountant = (
                                db.query(Accountants)
                                .filter(Accountants.email == company.accountant_email.lower().strip())
                                .first()
                            )
                            if not accountant:
                                raise HTTPException(
                                    status_code=status.HTTP_404_NOT_FOUND,
                                    detail=f"Accountant not found for company {company.email}."
                                )
                            
                            # Check NIT limit before creating relationship
                            if accountant.is_active:
                                _check_accountant_nit_limit(accountant.id, db)
                            
                            company_relation_status = False
                            if accountant.is_active:
                                company_relation_status = True

                            # Create new AccountantCompany
                            accountant_company = AccountantCompanies()
                            accountant_company.accountant_id = accountant.id
                            accountant_company.company_id = existing_company.id
                            accountant_company.is_active = company_relation_status

                            db.add(accountant_company)
                            db.commit()
                        
                        results["successful"].append({
                            "email": company.email,
                            "name": company.name,
                            "status": "updated"
                        })
                        continue
                    else:
                        results["failed"].append({
                            "email": company.email,
                            "reason": "Invalid or inactive subscription"
                        })
                        continue
                else:
                    logger.info("Company already exists: %s", company.email)
                    results["failed"].append({
                        "email": company.email,
                        "reason": "Company already exists"
                    })
                    continue

            # If there's an accountant, check NIT limit before creating the company
            if company.accountant_email:
                accountant = (
                    db.query(Accountants)
                    .filter(Accountants.email == company.accountant_email.lower().strip())
                    .first()
                )
                if not accountant:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Accountant not found for company {company.email}."
                    )
                
                # Check NIT limit before creating company
                if accountant.is_active:
                    _check_accountant_nit_limit(accountant.id, db)

            subscription: Subscriptions | None = None
            if company.subscription_name:
                subscription = _get_subscription_by_name(
                    subscription_name=company.subscription_name,
                    db=db,
                )
                if subscription or subscription.is_active is False:
                    logger.info("Subscription found: %s", subscription.name)

            logger.info("Registering company: %s", company.email)
            # Create new Company
            new_company = Companies()
            new_company.email = company.email.lower().strip()
            new_company.name = company.name
            new_company.nit = company.nit
            new_company.is_active = False
            new_company.subscription_id = subscription.id if subscription else None

            db.add(new_company)
            db.commit()
            db.refresh(new_company)

            # Create initial invoice request record
            invoice_request = InvoiceRequests(
                company_id=new_company.id,
                request_count=0
            )
            db.add(invoice_request)
            db.commit()

            if company.accountant_email:
                logger.info("Linking company to accountant: %s", company.accountant_email)
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

            results["successful"].append({
                "email": company.email,
                "name": company.name
            })

        except Exception as e:
            logger.error("Error registering company %s: %s", company.email, str(e))
            results["failed"].append({
                "email": company.email,
                "reason": str(e)
            })
            db.rollback()

    return results


@router.patch("/company/{nit}/status", status_code=status.HTTP_200_OK)
async def activate_company(
    nit: str,
    status: bool,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
) -> None:
    """
    Activate or deactivate a company and manage their API access.

    This endpoint handles the activation/deactivation of a company. When activating a company:
    - Generates a new API key
    - Sets the company as active
    - Sends credentials to the company's email

    When deactivating a company:
    - Sets the company as inactive
    - Maintains existing relationships but marks them as inactive

    Args:
        nit (str): The NIT number of the company to activate/deactivate
        status (bool): True to activate, False to deactivate
        db (Session): Database session for database operations
        api_key (str): API key for authentication

    Raises:
        HTTPException (404): If the company is not found
        HTTPException (500): If there's an error during the activation/deactivation process

    Returns:
        None: The function returns nothing on success
    """
    try:
        # Check if the accountant exists
        company = db.query(Companies).filter(Companies.nit == nit).first()
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found.",
            )
        if company.is_active == status:
            return

        if company.is_active and not status:
            # Deactivate the company
            company.is_active = status
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
        _send_credentials(email=company.email, password=api_key, is_company=True)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while activating the company. {e}",
        ) from e


@router.patch("/company/{nit}/subscription", status_code=status.HTTP_200_OK)
async def update_company_subscription(
    nit: str,
    subscription_name: str,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
) -> dict:
    """
    Update a company's subscription plan.

    This endpoint allows updating a company's subscription to a new plan. It:
    - Validates the new subscription exists and is active
    - Updates the company's subscription reference
    - Maintains all existing relationships and settings

    Args:
        nit (str): The NIT number of the company to update
        subscription_name (str): The name of the new subscription plan
        db (Session): Database session for database operations
        api_key (str): API key for authentication

    Returns:
        dict: Updated company information including:
            - email: Company's email
            - name: Company's name
            - subscription: New subscription name
            - status: Update status

    Raises:
        HTTPException (404): If the company is not found
        HTTPException (400): If the subscription is invalid or inactive
        HTTPException (500): If there's an error during the update process
    """
    try:
        # Check if the company exists
        company = (
            db.query(Companies)
            .filter(Companies.nit == nit)
            .first()
        )
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found."
            )

        # Get the new subscription
        subscription = _get_subscription_by_name(
            subscription_name=subscription_name,
            db=db,
        )
        if not subscription or not subscription.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or inactive subscription."
            )

        # Update the company's subscription
        company.subscription_id = subscription.id
        db.commit()
        db.refresh(company)

        return {
            "email": company.email,
            "name": company.name,
            "subscription": subscription.name,
            "status": "updated"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating company subscription: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while updating the subscription. {e}"
        ) from e


@router.patch("/accountant/{email}/subscription", status_code=status.HTTP_200_OK)
async def update_accountant_subscription(
    email: str,
    subscription_name: str,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
) -> dict:
    """
    Update an accountant's subscription plan.

    This endpoint allows updating an accountant's subscription to a new plan. It:
    - Validates the new subscription exists and is active
    - Updates the accountant's subscription reference
    - Maintains all existing relationships and settings
    - Does not affect existing company relationships

    Args:
        email (str): The email address of the accountant to update
        subscription_name (str): The name of the new subscription plan
        db (Session): Database session for database operations
        api_key (str): API key for authentication

    Returns:
        dict: Updated accountant information including:
            - email: Accountant's email
            - first_name: Accountant's first name
            - last_name: Accountant's last name
            - subscription: New subscription name
            - status: Update status

    Raises:
        HTTPException (404): If the accountant is not found
        HTTPException (400): If the subscription is invalid or inactive
        HTTPException (500): If there's an error during the update process
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
                detail="Accountant not found."
            )

        # Get the new subscription
        subscription = _get_subscription_by_name(
            subscription_name=subscription_name,
            db=db,
        )
        if not subscription or not subscription.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or inactive subscription."
            )

        # Update the accountant's subscription
        accountant.subscription_id = subscription.id
        db.commit()
        db.refresh(accountant)

        return {
            "email": accountant.email,
            "first_name": accountant.first_name,
            "last_name": accountant.last_name,
            "subscription": subscription.name,
            "status": "updated"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating accountant subscription: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while updating the subscription. {e}"
        ) from e


def _check_accountant_nit_limit(accountant_id: UUID, db: Session) -> None:
    """
    Check if an accountant has reached their NIT limit.

    This helper function verifies if an accountant has reached their subscription's NIT limit
    by counting their active company relationships. If the limit is reached, it raises an
    exception to prevent further company associations.

    Args:
        accountant_id (UUID): The ID of the accountant to check
        db (Session): Database session for database operations

    Raises:
        HTTPException (404): If the accountant is not found
        HTTPException (400): If the accountant has reached their NIT limit

    Returns:
        None: The function returns nothing if the check passes
    """
    accountant: Accountants | None = db.query(Accountants).filter(Accountants.id == accountant_id).first()
    if not accountant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accountant not found."
        )

    subscription: Subscriptions | None = accountant.subscription
    if not subscription or not subscription.nit_limit:
        return

    # Count active company relationships
    active_companies = (
        db.query(AccountantCompanies)
        .filter(
            AccountantCompanies.accountant_id == accountant_id,
            AccountantCompanies.is_active == True
        )
        .count()
    )

    if active_companies >= subscription.nit_limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"NIT limit reached ({subscription.nit_limit}). Please upgrade your subscription."
        )


@router.patch("/company/{nit}/accountant", status_code=status.HTTP_200_OK)
async def update_company_accountant(
    nit: str,
    accountant_email: str,
    status: bool = True,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
) -> dict:
    """
    Update the relationship between a company and an accountant.

    This endpoint manages the relationship between a company and an accountant. It can:
    - Create a new relationship
    - Activate/deactivate an existing relationship
    - Check NIT limits before activating relationships
    - Handle relationship status based on accountant's active status

    Args:
        nit (str): The NIT number of the company
        accountant_email (str): The email address of the accountant
        status (bool, optional): True to activate, False to deactivate. Defaults to True
        db (Session): Database session for database operations
        api_key (str): API key for authentication

    Returns:
        dict: Updated relationship information including:
            - company: Company details (nit, name, email)
            - accountant: Accountant details (email, first_name, last_name)
            - is_active: Current relationship status
            - status: Update status ("created" or "updated")

    Raises:
        HTTPException (404): If the company or accountant is not found
        HTTPException (400): If the accountant has reached their NIT limit
        HTTPException (500): If there's an error during the update process
    """
    try:
        # Check if the company exists
        company = (
            db.query(Companies)
            .filter(Companies.nit == nit)
            .first()
        )
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found."
            )

        # Check if the accountant exists
        accountant = (
            db.query(Accountants)
            .filter(Accountants.email == accountant_email.lower().strip())
            .first()
        )
        if not accountant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Accountant not found."
            )

        # Check if relationship already exists
        existing_relation = (
            db.query(AccountantCompanies)
            .filter(
                AccountantCompanies.company_id == company.id,
                AccountantCompanies.accountant_id == accountant.id
            )
            .first()
        )

        if existing_relation:
            # If activating a relationship, check the NIT limit
            if status and not existing_relation.is_active:
                _check_accountant_nit_limit(accountant.id, db)
            # Update existing relationship
            existing_relation.is_active = status
            db.commit()
            db.refresh(existing_relation)
        else:
            # If creating a new relationship, check the NIT limit
            if status:
                _check_accountant_nit_limit(accountant.id, db)
            # Create new relationship, relation is active if accountant is active
            new_relation = AccountantCompanies()
            new_relation.company_id = company.id
            new_relation.accountant_id = accountant.id
            new_relation.is_active = accountant.is_active and status
            db.add(new_relation)
            db.commit()
            db.refresh(new_relation)

        return {
            "company": {
                "nit": company.nit,
                "name": company.name,
                "email": company.email
            },
            "accountant": {
                "email": accountant.email,
                "first_name": accountant.first_name,
                "last_name": accountant.last_name
            },
            "is_active": new_relation.is_active if not existing_relation else existing_relation.is_active,
            "status": "updated" if existing_relation else "created"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating company-accountant relation: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while updating the relationship. {e}"
        ) from e
