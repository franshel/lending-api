from database.database import Base, engine, BusinessProposal, ProposalDocument, Tag
from sqlalchemy import inspect, MetaData
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_tables():
    """Create database tables if they don't exist"""
    # Get existing tables
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    # Get all table names defined in the models
    model_tables = [table for table in Base.metadata.tables.keys()]

    # Create only the tables that don't exist yet
    tables_to_create = [
        table for table in model_tables if table not in existing_tables]

    if tables_to_create:
        logger.info(f"Creating tables: {', '.join(tables_to_create)}")
        try:
            # This will create tables that don't exist yet without touching existing ones
            Base.metadata.create_all(bind=engine)
            logger.info("Tables created successfully")
        except Exception as e:
            logger.error(f"Error creating tables: {str(e)}")
    else:
        logger.info("All tables already exist")


if __name__ == "__main__":
    create_tables()
