from sqlalchemy import text
from database.database import SessionLocal
import sys
import os
import logging

# Add parent directory to path to make imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_profile_for_all_wallets():
    """Create wallet profile for all existing wallets in wallet_analyses table"""
    db = SessionLocal()
    try:
        # Get all wallet addresses from wallet_analyses table
        wallet_addresses = db.execute(
            text("SELECT wallet_address FROM wallet_analyses")
        ).fetchall()

        wallets_count = len(wallet_addresses)
        logger.info(f"Found {wallets_count} wallets in wallet_analyses table")

        created_count = 0
        existing_count = 0

        # For each wallet, check if a profile exists and create one if it doesn't
        for wallet_row in wallet_addresses:
            # Extract the wallet address from the row tuple
            wallet_address = wallet_row[0]

            # Check if profile exists
            existing_profile = db.execute(
                text(
                    f"SELECT wallet_address FROM wallet_profiles WHERE wallet_address = '{wallet_address}'")
            ).fetchone()

            if not existing_profile:
                # Create a profile
                db.execute(
                    text(
                        f"INSERT INTO wallet_profiles (wallet_address, profile_completed, email_verified, kyc_verified) VALUES ('{wallet_address}', false, false, false)")
                )
                created_count += 1
                logger.info(f"Created profile for wallet {wallet_address}")
            else:
                existing_count += 1

        # Commit all changes
        db.commit()
        logger.info(
            f"Created {created_count} new profiles, {existing_count} already existed")

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating profiles: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_profile_for_all_wallets()
