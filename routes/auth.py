from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from pydantic import BaseModel, validator
from typing import Dict, Any, Optional
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
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
            raise ValueError('Invalid Ethereum wallet address format')
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

        # Check if this wallet has been analyzed before - use direct SQL to avoid ORM issues
        existing_analysis_query = db.execute(
            text("SELECT id FROM wallet_analyses WHERE wallet_address = :address"),
            {"address": wallet_address}).fetchone()
        existing_analysis = existing_analysis_query is not None

        # Default flags
        background_analysis_initiated = False
        profile_created = False

        # If first time authentication, schedule a background analysis
        if not existing_analysis:
            try:
                logger.info(
                    f"First-time authentication for {wallet_address}. Scheduling background wallet analysis.")
                background_tasks.add_task(
                    background_wallet_analysis, wallet_address, db)
                logger.info(
                    f"Background wallet analysis scheduled for {wallet_address}")
                background_analysis_initiated = True
                # Also check if a profile exists, and if not, create a minimal one
                try:
                    # Use a direct SQL query to check if the wallet profile exists
                    # Use parameterized queries to avoid SQL injection
                    existing_profile = db.execute(
                        text(
                            "SELECT wallet_address FROM wallet_profiles WHERE wallet_address = :address"),
                        {"address": wallet_address}
                    ).fetchone()

                    if not existing_profile:
                        # Create a minimal profile for the wallet with direct SQL
                        # Use parameterized query to avoid SQL injection
                        db.execute(
                            text("INSERT INTO wallet_profiles (wallet_address, profile_completed, email_verified, kyc_verified, created_at, updated_at) VALUES (:address, false, false, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"),
                            {"address": wallet_address}
                        )
                        db.commit()
                        logger.info(
                            f"Created initial profile for {wallet_address} using direct SQL")
                        profile_created = True
                except Exception as profile_error:
                    # Log but don't fail authentication if profile creation fails
                    logger.error(
                        f"Error creating profile for {wallet_address}: {str(profile_error)}")
                    db.rollback()

            except Exception as e:
                # Log the error but don't fail the authentication
                logger.error(
                    f"Error scheduling background analysis for {wallet_address}: {str(e)}")
                # Authentication should still succeed even if background task scheduling fails        # Generate JWT token
        # Include information about background analysis and profile creation in response
        access_token = create_access_token(wallet_address)
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "wallet_address": wallet_address,
            "background_analysis_started": background_analysis_initiated,
            "profile_created": profile_created
        }

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

    Args:
        wallet_address: The authenticated wallet address (from the token)
        db: Database session

    Returns:
        Information about the authenticated wallet including profile status
    """
    # Check if user has a profile - using direct SQL to avoid ORM relationship issues
    try:
        profile_query = db.execute(
            text(
                f"SELECT wallet_address, profile_completed, display_name, email, company_name FROM wallet_profiles WHERE wallet_address = '{wallet_address}'")
        ).fetchone()

        has_profile = profile_query is not None

        # If profile doesn't exist, create one
        if not has_profile:
            logger.info(
                f"Creating profile for wallet {wallet_address} during /me endpoint call")
            db.execute(
                text(
                    f"INSERT INTO wallet_profiles (wallet_address, profile_completed, email_verified, kyc_verified) VALUES ('{wallet_address}', false, false, false)")
            )
            db.commit()

            # Fetch the newly created profile
            profile_query = db.execute(
                text(
                    f"SELECT wallet_address, profile_completed, display_name, email, company_name FROM wallet_profiles WHERE wallet_address = '{wallet_address}'")
            ).fetchone()
            has_profile = True

        profile_completed = profile_query.profile_completed if has_profile else False

        # Prepare the response
        response = {
            "wallet_address": wallet_address,
            "is_authenticated": True,
            "has_profile": has_profile,
            "profile_completed": profile_completed,
            "display_name": profile_query.display_name if has_profile else None,
            "email": profile_query.email if has_profile else None,
            "company_name": profile_query.company_name if has_profile else None
        }

        return response
    except Exception as e:
        logger.error(
            f"Error in get_current_user_info for {wallet_address}: {str(e)}")
        # Return basic info if there's an error
        return {
            "wallet_address": wallet_address,
            "is_authenticated": True,
            "has_profile": False,
            "profile_completed": False,
            "display_name": None,
            "email": None,
            "company_name": None
        }
