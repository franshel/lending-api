from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import logging

from database.database import get_db, WalletProfile
from schemas.schemas import WalletProfileCreate, WalletProfileUpdate, WalletProfileResponse
from utils.auth_utils import get_current_wallet

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/profiles",
    tags=["profiles"],
    responses={
        401: {"description": "Authentication failed"},
        400: {"description": "Bad request"},
        404: {"description": "Profile not found"},
        500: {"description": "Internal server error"},
    },
)


@router.get("/me", response_model=WalletProfileResponse)
async def get_my_profile(
    wallet_address: str = Depends(get_current_wallet),
    db: Session = Depends(get_db)
):
    """
    Get the profile of the currently authenticated wallet.
    If the profile doesn't exist, it creates a minimal profile.
    """    # Use direct SQL to check if the profile exists with parameterized query for security
    profile_result = db.execute(text(
        "SELECT * FROM wallet_profiles WHERE wallet_address = :address"),
        {"address": wallet_address}
    ).fetchone()

    # If profile doesn't exist, create a minimal one with direct SQL
    if not profile_result:
        try:
            db.execute(
                text("INSERT INTO wallet_profiles (wallet_address, profile_completed, email_verified, kyc_verified, created_at, updated_at) VALUES (:address, false, false, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"),
                {"address": wallet_address}
            )
            db.commit()
            logger.info(f"Created initial profile for {wallet_address}")

            # Fetch the newly created profile
            profile_result = db.execute(text(
                "SELECT * FROM wallet_profiles WHERE wallet_address = :address"),
                {"address": wallet_address}
            ).fetchone()
        except Exception as e:
            logger.error(f"Error creating wallet profile: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating wallet profile"
            )

    # Convert the result to a dictionary
    profile = {
        "wallet_address": profile_result.wallet_address,
        "display_name": profile_result.display_name,
        "email": profile_result.email,
        "bio": profile_result.bio,
        "avatar_url": profile_result.avatar_url,
        "profile_completed": profile_result.profile_completed,
        "phone": profile_result.phone,
        "website": profile_result.website,
        "social_media": profile_result.social_media,
        "company_name": profile_result.company_name,
        "company_position": profile_result.company_position,
        "company_website": profile_result.company_website,
        "company_description": profile_result.company_description,
        "email_verified": profile_result.email_verified,
        "kyc_verified": profile_result.kyc_verified,
        "created_at": profile_result.created_at,
        "updated_at": profile_result.updated_at
    }

    return profile


@router.put("/me", response_model=WalletProfileResponse)
async def update_my_profile(
    profile_update: WalletProfileUpdate,
    wallet_address: str = Depends(get_current_wallet),
    db: Session = Depends(get_db)
):
    """
    Update the profile of the currently authenticated wallet.
    """
    try:
        # First check if profile exists using direct SQL
        profile_exists = db.execute(
            text(
                f"SELECT 1 FROM wallet_profiles WHERE wallet_address = '{wallet_address}'")
        ).fetchone() is not None

        # Extract profile data from update payload
        profile_data = profile_update.dict(exclude_unset=True)

        # Convert profile_data to SQL update parts
        update_parts = []
        for key, value in profile_data.items():
            if value is None:
                update_parts.append(f"{key} = NULL")
            elif isinstance(value, str):
                # Properly escape single quotes in strings
                safe_value = value.replace("'", "''")
                update_parts.append(f"{key} = '{safe_value}'")
            elif isinstance(value, dict):
                # Handle JSON data
                import json
                json_value = json.dumps(value)
                update_parts.append(f"{key} = '{json_value}'::jsonb")
            else:
                update_parts.append(f"{key} = {value}")

        # If profile doesn't exist, create it
        if not profile_exists:
            logger.info(f"Creating new profile for {wallet_address}")
            # Insert the basic record first
            db.execute(
                text(
                    f"INSERT INTO wallet_profiles (wallet_address) VALUES ('{wallet_address}')")
            )

        # If we have fields to update
        if update_parts:
            update_sql = f"UPDATE wallet_profiles SET {', '.join(update_parts)}"

            # Check required fields for profile completion
            profile_completion_sql = text(f"""
                UPDATE wallet_profiles SET profile_completed = (
                    display_name IS NOT NULL AND 
                    email IS NOT NULL AND 
                    company_name IS NOT NULL
                )
                WHERE wallet_address = '{wallet_address}'
            """)

            # Execute the updates
            db.execute(
                text(f"{update_sql} WHERE wallet_address = '{wallet_address}'"))
            db.execute(profile_completion_sql)

        db.commit()

        # Fetch the updated profile
        updated_profile = db.execute(text(
            f"SELECT * FROM wallet_profiles WHERE wallet_address = '{wallet_address}'")
        ).fetchone()

        # Convert row to dictionary
        result = {
            "wallet_address": updated_profile.wallet_address,
            "display_name": updated_profile.display_name,
            "email": updated_profile.email,
            "bio": updated_profile.bio,
            "avatar_url": updated_profile.avatar_url,
            "profile_completed": updated_profile.profile_completed,
            "phone": updated_profile.phone,
            "website": updated_profile.website,
            "social_media": updated_profile.social_media,
            "company_name": updated_profile.company_name,
            "company_position": updated_profile.company_position,
            "company_website": updated_profile.company_website,
            "company_description": updated_profile.company_description,
            "email_verified": updated_profile.email_verified,
            "kyc_verified": updated_profile.kyc_verified,
            "created_at": updated_profile.created_at,
            "updated_at": updated_profile.updated_at
        }

        return result
    except Exception as e:
        logger.error(f"Error updating profile: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating profile: {str(e)}"
        )


@router.get("/{wallet_address}", response_model=WalletProfileResponse)
async def get_wallet_profile(
    wallet_address: str,
    db: Session = Depends(get_db)
):
    """
    Get a wallet profile by its address.
    """
    try:        # Use direct SQL to get the profile with parameterized query
        profile_result = db.execute(text(
            "SELECT * FROM wallet_profiles WHERE wallet_address = :address"),
            {"address": wallet_address}
        ).fetchone()

        if not profile_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found"
            )

        # Convert row to dictionary
        profile = {
            "wallet_address": profile_result.wallet_address,
            "display_name": profile_result.display_name,
            "email": profile_result.email,
            "bio": profile_result.bio,
            "avatar_url": profile_result.avatar_url,
            "profile_completed": profile_result.profile_completed,
            "phone": profile_result.phone,
            "website": profile_result.website,
            "social_media": profile_result.social_media,
            "company_name": profile_result.company_name,
            "company_position": profile_result.company_position,
            "company_website": profile_result.company_website,
            "company_description": profile_result.company_description,
            "email_verified": profile_result.email_verified,
            "kyc_verified": profile_result.kyc_verified,
            "created_at": profile_result.created_at,
            "updated_at": profile_result.updated_at
        }

        return profile
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching profile"
        )


@router.get("/", response_model=List[WalletProfileResponse])
async def get_all_profiles(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    wallet_address: str = Depends(get_current_wallet)  # For auth only
):
    """
    Get all wallet profiles with pagination.
    Requires authentication.
    """
    profiles = db.query(WalletProfile).offset(skip).limit(limit).all()
    return profiles
