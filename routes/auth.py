from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from pydantic import BaseModel, validator, ValidationError
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
import logging

from database.database import get_db, WalletAnalysis, WalletProfile
from utils.wallet_utils import get_or_create_wallet_analysis
from utils.auth_utils import (
    AuthMessage,
    get_auth_message,
    verify_signature,
    create_access_token,
    get_current_wallet
)
from utils.wallet_utils import background_wallet_analysis

# Configure logging
logger = logging.getLogger(__name__)

# Create a router for authentication endpoints
router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={
        401: {"description": "Authentication failed"},
        400: {"description": "Bad request"},
        500: {"description": "Internal server error"},
    },
)


class NonceRequest(BaseModel):
    """Request model for nonce generation"""
    wallet_address: str

    @validator('wallet_address')
    def validate_wallet_address(cls, v):
        """Validate wallet address format"""
        v = v.lower()
        if not v.startswith('0x') or len(v) != 42:
            raise ValueError("Invalid wallet address format")
        return v


class NonceResponse(BaseModel):
    """Response model for nonce generation"""
    message: str
    wallet_address: str


class AuthResponse(BaseModel):
    """Response model for successful authentication"""
    access_token: str
    token_type: str
    wallet_address: str
    background_analysis_started: Optional[bool] = False
    profile_created: Optional[bool] = False


class WalletInfo(BaseModel):
    """Model for wallet information"""
    wallet_address: str
    is_authenticated: bool
    has_profile: Optional[bool] = False
    profile_completed: Optional[bool] = False
    display_name: Optional[str] = None
    email: Optional[str] = None
    company_name: Optional[str] = None


@router.post("/request-message", response_model=NonceResponse)
async def request_auth_message(request: NonceRequest) -> Dict[str, Any]:
    """
    Generate an authentication message that needs to be signed by the wallet

    Args:
        request: The nonce request containing the wallet address

    Returns:
        A message to be signed
    """
    try:
        wallet_address = request.wallet_address
        message = get_auth_message(wallet_address)

        return {
            "message": message,
            "wallet_address": wallet_address
        }
    except ValidationError as ve:
        logger.error(f"Validation error: {str(ve)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Error generating authentication message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating authentication message"
        )


@router.post("/verify", response_model=AuthResponse)
async def verify_wallet_signature(
    auth_message: AuthMessage,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Verify a wallet signature and issue a JWT token if valid.
    If this is the first time the wallet is authenticating, it initiates
    the wallet AI analysis in the background while still returning a successful
    authentication response immediately.

    Args:
        auth_message: The authentication message with signature
        background_tasks: FastAPI background tasks for running the AI analysis
        db: Database session

    Returns:
        Access token information with a flag indicating if background analysis was started

    Raises:
        HTTPException: If signature verification fails
    """
    try:
        wallet_address = auth_message.wallet_address
        signature = auth_message.signature
        message = auth_message.message

        # Verify the signature
        is_valid = verify_signature(wallet_address, signature, message)

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature"
            )

        # Check if this wallet has been analyzed before
        try:
            existing_analysis_query = db.execute(
                text("SELECT id FROM wallet_analyses WHERE wallet_address = :address"),
                {"address": wallet_address}).fetchone()
            existing_analysis = existing_analysis_query is not None
        except SQLAlchemyError as e:
            logger.error(f"Database error checking wallet analysis: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Error checking wallet analysis status"
            )

        # Default flags
        background_analysis_initiated = False
        profile_created = False

        # If first time authentication, schedule background analysis
        if not existing_analysis:
            background_tasks.add_task(
                background_wallet_analysis, wallet_address, db)
            background_analysis_initiated = True

        # Generate access token
        try:
            access_token = create_access_token(wallet_address)
        except Exception as e:
            logger.error(f"Error creating access token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating access token"
            )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "wallet_address": wallet_address,
            "background_analysis_started": background_analysis_initiated,
            "profile_created": profile_created
        }

    except HTTPException as he:
        raise he
    except ValidationError as ve:
        logger.error(f"Validation error: {str(ve)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Error verifying wallet signature: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error verifying wallet signature"
        )


@router.get("/me", response_model=WalletInfo)
async def get_current_user_info(
    wallet_address: str = Depends(get_current_wallet),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get information about the currently authenticated wallet including profile status
    """
    try:
        # Check if user has a profile
        profile_query = db.execute(
            text("""
                SELECT wallet_address, profile_completed, display_name, 
                       email, company_name 
                FROM wallet_profiles 
                WHERE wallet_address = :address
            """),
            {"address": wallet_address}
        ).fetchone()

        has_profile = profile_query is not None

        # If profile doesn't exist, create one
        if not has_profile:
            try:
                db.execute(
                    text("""
                        INSERT INTO wallet_profiles (wallet_address, profile_completed)
                        VALUES (:address, false)
                    """),
                    {"address": wallet_address}
                )
                db.commit()

                # Fetch the newly created profile
                profile_query = db.execute(
                    text("""
                        SELECT wallet_address, profile_completed, display_name, 
                               email, company_name 
                        FROM wallet_profiles 
                        WHERE wallet_address = :address
                    """),
                    {"address": wallet_address}
                ).fetchone()
                has_profile = True
            except SQLAlchemyError as e:
                logger.error(f"Error creating profile: {str(e)}")
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Error creating wallet profile"
                )

        # Prepare the response with safe access to attributes
        response = {
            "wallet_address": wallet_address,
            "is_authenticated": True,
            "has_profile": has_profile,
            "profile_completed": profile_query.profile_completed if profile_query else False,
            "display_name": profile_query.display_name if profile_query else None,
            "email": profile_query.email if profile_query else None,
            "company_name": profile_query.company_name if profile_query else None
        }

        return response
    except HTTPException as he:
        raise he
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_current_user_info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Error accessing user profile data"
        )
    except Exception as e:
        logger.error(
            f"Error in get_current_user_info for {wallet_address}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving user info"
        )
