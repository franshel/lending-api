from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, validator
from typing import Dict, Any, Optional
import logging
from utils.auth_utils import (
    AuthMessage,
    get_auth_message,
    verify_signature,
    create_access_token,
    get_current_wallet
)

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


class WalletInfo(BaseModel):
    """Model for wallet information"""
    wallet_address: str
    is_authenticated: bool


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
async def verify_wallet_signature(auth_message: AuthMessage) -> Dict[str, Any]:
    """
    Verify a wallet signature and issue a JWT token if valid

    Args:
        auth_message: The authentication message with signature

    Returns:
        Access token information

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

        # Generate JWT token
        access_token = create_access_token(wallet_address)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "wallet_address": wallet_address
        }
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error verifying wallet signature: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error verifying wallet signature"
        )


@router.get("/me", response_model=WalletInfo)
async def get_current_user_info(wallet_address: str = Depends(get_current_wallet)) -> Dict[str, Any]:
    """
    Get information about the currently authenticated wallet

    Args:
        wallet_address: The authenticated wallet address (from the token)

    Returns:
        Information about the authenticated wallet
    """
    return {
        "wallet_address": wallet_address,
        "is_authenticated": True
    }
