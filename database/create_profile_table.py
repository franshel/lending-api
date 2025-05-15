import sys
import os
import logging

# Use absolute imports since we're running from the root directory
from database.database import Base, engine, WalletProfile, SessionLocal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_profile_table():
    """Create the wallet_profiles table in the database"""
    try:
        # Create the table
        logger.info("Creating wallet_profiles table...")
        Base.metadata.create_all(bind=engine, tables=[WalletProfile.__table__])
        logger.info("wallet_profiles table created successfully!")

        # Validate the table was created
        db = SessionLocal()
        try:
            # Try to count records in the new table
            count = db.query(WalletProfile).count()
            logger.info(f"Table created. Found {count} records.")
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error creating wallet_profiles table: {str(e)}")
        raise


if __name__ == "__main__":
    create_profile_table()
