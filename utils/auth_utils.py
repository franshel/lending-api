import os
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from eth_account.messages import encode_defunct
from web3 import Web3
from pydantic import BaseModel

# Configure logging
logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()

# Get JWT settings from environment variables or use defaults
SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY", "your-secret-key-for-jwt-please-change-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "525600"))

# Web3 provider setup - can be configured via environment variables
WEB3_PROVIDER = os.getenv(
    "WEB3_PROVIDER_URL", "https://mainnet.infura.io/v3/your-infura-project-id")
web3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))

# Create a nonce cache to prevent replay attacks
# In a production environment, this should be stored in Redis or a database
# This is a simple in-memory cache for demonstration purposes
nonce_cache: Dict[str, Dict[str, datetime]] = {}


class TokenData(BaseModel): 
    """Token data model for JWT claims"""
    wallet_address: str
    exp: Optional[datetime] = None


class AuthMessage(BaseModel):
    """Model for wallet authentication message"""
    message: str
    signature: str
    wallet_address: str


def generate_nonce(wallet_address: str) -> str:
    """
    Generate a unique nonce for wallet address authentication

    Args:
        wallet_address: The Ethereum wallet address requesting authentication

    Returns:
        A nonce string
    """
    # Generate a timestamp-based nonce
    timestamp = datetime.utcnow().isoformat()
    nonce = f"{wallet_address.lower()}:{timestamp}"

    # Store in the nonce cache with expiry time
    nonce_cache[wallet_address.lower()] = {
        "nonce": nonce,
        "expires_at": datetime.utcnow() + timedelta(minutes=5)  # 5-minute expiry
    }

    return nonce


def get_auth_message(wallet_address: str) -> str:
    """
    Get the message that needs to be signed by the wallet for authentication

    Args:
        wallet_address: The Ethereum wallet address requesting authentication

    Returns:
        Message string to be signed
    """
    nonce = generate_nonce(wallet_address)
    return f"Sign this message to authenticate with the Lending API: {nonce}"


def verify_signature(wallet_address: str, signature: str, message: str) -> bool:
    """
    Verify the signature against the provided message and wallet address

    Args:
        wallet_address: The claiming Ethereum wallet address
        signature: The signature produced by the wallet
        message: The message that was signed

    Returns:
        True if signature is valid, False otherwise
    """
    try:
        # Clean the addresses for comparison
        wallet_address = wallet_address.lower()

        # Check if nonce is valid and not expired
        if wallet_address not in nonce_cache:
            logger.warning(f"No nonce found for wallet: {wallet_address}")
            return False

        nonce_data = nonce_cache[wallet_address]
        if nonce_data["expires_at"] < datetime.utcnow():
            logger.warning(f"Expired nonce for wallet: {wallet_address}")
            # Clean up expired nonce
            del nonce_cache[wallet_address]
            return False

        # Verify the signature
        message_hash = encode_defunct(text=message)
        recovered_address = web3.eth.account.recover_message(
            message_hash, signature=signature)

        # Compare recovered address with claimed address
        is_valid = recovered_address.lower() == wallet_address

        # Remove nonce after successful verification to prevent replay
        if is_valid:
            del nonce_cache[wallet_address]
        else:
            logger.warning(
                f"Signature verification failed for wallet: {wallet_address}")

        return is_valid
    except Exception as e:
        logger.error(f"Error verifying signature: {str(e)}")
        return False


def create_access_token(wallet_address: str) -> str:
    """
    Create a JWT access token for the authenticated wallet

    Args:
        wallet_address: The authenticated Ethereum wallet address

    Returns:
        JWT token string
    """
    # Set expiration time
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Create JWT payload
    to_encode = {
        "sub": wallet_address.lower(),
        "exp": expire,
        "wallet_address": wallet_address.lower()
    }

    # Encode and return the token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_wallet(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Dependency to get the current authenticated wallet address from a JWT token

    Args:
        credentials: The HTTP Authorization credentials

    Returns:
        The authenticated wallet address

    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode the JWT token
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Extract wallet address
        wallet_address: str = payload.get("wallet_address")
        if wallet_address is None:
            raise credentials_exception

        # Return the authenticated wallet address
        return wallet_address
    except JWTError:
        raise credentials_exception
