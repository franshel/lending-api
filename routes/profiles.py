from datetime import datetime
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
                )        # Convert SQLAlchemy Row to dict safely with explicit mapping
        try:
            profile_dict = dict(profile_result)
            return profile_dict
        except Exception as e:
            logger.error(f"Error converting profile to dict: {str(e)}")
            # Manually create dictionary from row attributes
            return {
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
                "created_at": profile_result.created_at.isoformat() if profile_result.created_at else None,
                "updated_at": profile_result.updated_at.isoformat() if profile_result.updated_at else None
            }

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
    Sets profile_completed to true when all required fields are present.
    """
    try:
        # First check if profile exists using direct SQL
        profile_exists = db.execute(
            text("SELECT 1 FROM wallet_profiles WHERE wallet_address = :address"),
            {"address": wallet_address}
        ).fetchone() is not None

        # Extract profile data from update payload
        try:
            profile_data = profile_update.model_dump(exclude_unset=True)
        except ValidationError as ve:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(ve)
            )

        # Check if all required fields are present for a complete profile
        required_fields = [
            "display_name", "email", "company_name",
            "company_position", "company_website", "company_description"
        ]

        # Get existing profile data if it exists
        existing_data = {}
        if profile_exists:
            existing_profile = db.execute(
                text("SELECT * FROM wallet_profiles WHERE wallet_address = :address"),
                {"address": wallet_address}
            ).fetchone()
            if existing_profile:
                try:
                    existing_data = dict(existing_profile)
                except Exception as e:
                    # Log the error and create a safe dictionary from profile attributes
                    logger.error(f"Error converting profile to dict: {str(e)}")
                    # Manually create dictionary from column names and values
                    existing_data = {
                        "wallet_address": existing_profile.wallet_address,
                        "display_name": existing_profile.display_name,
                        "email": existing_profile.email,
                        "bio": existing_profile.bio,
                        "avatar_url": existing_profile.avatar_url,
                        "profile_completed": existing_profile.profile_completed,
                        "phone": existing_profile.phone,
                        "website": existing_profile.website,
                        "social_media": existing_profile.social_media,
                        "company_name": existing_profile.company_name,
                        "company_position": existing_profile.company_position,
                        "company_website": existing_profile.company_website,
                        "company_description": existing_profile.company_description,
                        "email_verified": existing_profile.email_verified,
                        "kyc_verified": existing_profile.kyc_verified
                    }

        # Combine existing data with updates to check completeness
        combined_data = {**existing_data, **profile_data}
        is_complete = all(combined_data.get(field)
                          for field in required_fields)

        logger.debug(
            f"Profile completion check for {wallet_address}: {is_complete}")
        logger.debug(f"Required fields: {required_fields}")
        logger.debug(f"Combined data: {combined_data}")

        # Convert profile_data to SQL update parts
        update_parts = []
        update_values = {"address": wallet_address}

        for key, value in profile_data.items():
            update_parts.append(f"{key} = :{key}")
            update_values[key] = value

        # Always include profile_completed, email_verified, and kyc_verified in the update
        # Ensure profile_completed, email_verified, and kyc_verified are included in the update
        update_parts.append("profile_completed = :profile_completed")
        update_values["profile_completed"] = is_complete

        update_parts.append("email_verified = :email_verified")
        update_values["email_verified"] = True

        update_parts.append("kyc_verified = :kyc_verified")
        update_values["kyc_verified"] = True

        # Ensure updated_at is set to the current timestamp
        update_parts.append("updated_at = :updated_at")
        # Handle the case where the profile does not exist
        update_values["updated_at"] = datetime.now(datetime.timezone.utc)
        if not profile_exists:
            # Set created_at for a new profile
            update_values["created_at"] = datetime.now(datetime.timezone.utc)

            # Insert a new profile with all required fields
            columns = ["wallet_address", "profile_completed", "email_verified", "kyc_verified", "created_at"] + \
                list(profile_data.keys())
            placeholders = [":address", ":profile_completed", ":email_verified", ":kyc_verified", ":created_at"] + \
                [f":{key}" for key in profile_data.keys()]

            create_query = text(f"""
            INSERT INTO wallet_profiles ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            """)

            db.execute(create_query, update_values)
        else:
            # Ensure created_at remains unchanged for existing profiles
            update_parts.append("created_at = :created_at")
            update_values["created_at"] = existing_data.get("created_at")

            # If we have fields to update and the profile exists
            if update_parts:
                update_query = text(f"""
                UPDATE wallet_profiles
                SET {', '.join(update_parts)}
                WHERE wallet_address = :address
                """)

                db.execute(update_query, update_values)

        # If we have fields to update
        if update_parts:
            update_query = text(f"""
            UPDATE wallet_profiles
            SET {', '.join(update_parts)}
            WHERE wallet_address = :address
            """)

            db.execute(update_query, update_values)

        db.commit()
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
            )        # Convert to dictionary with explicit field mapping - safer than dict()
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
            # Always include created_at and updated_at as they're required by WalletProfileResponse
            "created_at": updated_profile.created_at.isoformat() if updated_profile.created_at else datetime.now(datetime.timezone.utc).isoformat(),
            "updated_at": updated_profile.updated_at.isoformat() if updated_profile.updated_at else datetime.now(datetime.timezone.utc).isoformat(),
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
        result = []
        for profile in profiles:
            try:
                result.append(dict(profile))
            except Exception as e:
                logger.error(f"Error converting profile to dict: {str(e)}")
                # Use the model's to_dict method or fallback to manual mapping
                if hasattr(profile, 'to_dict'):
                    result.append(profile.to_dict())
                else:
                    result.append({
                        "wallet_address": profile.wallet_address,
                        "display_name": profile.display_name,
                        "email": profile.email,
                        "bio": profile.bio,
                        "avatar_url": profile.avatar_url,
                        "profile_completed": profile.profile_completed,
                        "phone": profile.phone,
                        "website": profile.website,
                        "social_media": profile.social_media,
                        "company_name": profile.company_name,
                        "company_position": profile.company_position,
                        "company_website": profile.company_website,
                        "company_description": profile.company_description,
                        "email_verified": profile.email_verified,
                        "kyc_verified": profile.kyc_verified,
                        "created_at": profile.created_at.isoformat() if profile.created_at else None,
                        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None
                    })
        return result
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

        try:
            return dict(profile_result)
        except Exception as e:
            logger.error(f"Error converting profile to dict: {str(e)}")
            # Manually create dictionary from row attributes
            return {
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
                "created_at": profile_result.created_at.isoformat() if profile_result.created_at else None,
                "updated_at": profile_result.updated_at.isoformat() if profile_result.updated_at else None
            }

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
