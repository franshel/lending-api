from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError
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
    """
    try:
        # Use direct SQL to check if the profile exists with parameterized query
        profile_result = db.execute(
            text("SELECT * FROM wallet_profiles WHERE wallet_address = :address"),
            {"address": wallet_address}
        ).fetchone()

        # If profile doesn't exist, create a minimal one with direct SQL
        if not profile_result:
            try:
                db.execute(
                    text("""
                        INSERT INTO wallet_profiles (wallet_address, profile_completed)
                        VALUES (:address, false)
                    """),
                    {"address": wallet_address}
                )
                db.commit()

                profile_result = db.execute(
                    text("SELECT * FROM wallet_profiles WHERE wallet_address = :address"),
                    {"address": wallet_address}
                ).fetchone()

                if not profile_result:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Profile could not be created"
                    )
            except SQLAlchemyError as e:
                logger.error(f"Error creating profile: {str(e)}")
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Error creating wallet profile"
                )

        # Convert SQLAlchemy Row to dict safely
        profile_dict = dict(profile_result)
        return profile_dict

    except HTTPException as he:
        raise he
    except SQLAlchemyError as e:
        logger.error(f"Database error getting profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Error accessing profile data"
        )
    except Exception as e:
        logger.error(f"Error getting profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving the profile"
        )


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
            text("SELECT 1 FROM wallet_profiles WHERE wallet_address = :address"),
            {"address": wallet_address}
        ).fetchone() is not None

        # Extract profile data from update payload
        try:
            profile_data = profile_update.dict(exclude_unset=True)
        except ValidationError as ve:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(ve)
            )

        # Convert profile_data to SQL update parts
        update_parts = []
        update_values = {"address": wallet_address}

        for key, value in profile_data.items():
            update_parts.append(f"{key} = :{key}")
            update_values[key] = value

        # If profile doesn't exist, create it
        if not profile_exists:
            columns = ["wallet_address"] + list(profile_data.keys())
            placeholders = [":address"] + \
                [f":{k}" for k in profile_data.keys()]

            create_query = text(f"""
                INSERT INTO wallet_profiles ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
            """)

            db.execute(create_query, update_values)

        # If we have fields to update
        elif update_parts:
            update_query = text(f"""
                UPDATE wallet_profiles
                SET {', '.join(update_parts)}
                WHERE wallet_address = :address
            """)

            db.execute(update_query, update_values)

        db.commit()

        # Fetch the updated profile
        updated_profile = db.execute(
            text("""
                SELECT wallet_address, display_name, email, bio, avatar_url, 
                       profile_completed, phone, website, social_media, 
                       company_name, company_position, company_website, 
                       company_description, email_verified, kyc_verified, 
                       created_at, updated_at 
                FROM wallet_profiles 
                WHERE wallet_address = :address
            """),
            {"address": wallet_address}
        ).fetchone()

        if not updated_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found after update"
            )        # Convert row to dictionary
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
            "created_at": updated_profile.created_at.isoformat() if updated_profile.created_at else None,
            "updated_at": updated_profile.updated_at.isoformat() if updated_profile.updated_at else None
        }

        return result

    except HTTPException:
        raise
    except ValidationError as ve:
        logger.error(f"Validation error: {str(ve)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve)
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error updating profile: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Error updating profile in database"
        )
    except Exception as e:
        logger.error(f"Error updating profile: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating the profile"
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
    try:
        profiles = db.query(WalletProfile).offset(skip).limit(limit).all()
        return [dict(profile) for profile in profiles]
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching profiles: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Error retrieving profiles from database"
        )
    except Exception as e:
        logger.error(f"Error fetching profiles: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving profiles"
        )


@router.get("/{wallet_address}", response_model=WalletProfileResponse)
async def get_wallet_profile(
    wallet_address: str,
    db: Session = Depends(get_db)
):
    """
    Get a wallet profile by its address.
    """
    try:
        profile_result = db.execute(
            text("SELECT * FROM wallet_profiles WHERE wallet_address = :address"),
            {"address": wallet_address}
        ).fetchone()

        if not profile_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile not found for wallet address {wallet_address}"
            )

        return dict(profile_result)

    except HTTPException as he:
        raise he
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Error retrieving profile from database"
        )
    except Exception as e:
        logger.error(f"Error fetching profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving the profile"
        )
