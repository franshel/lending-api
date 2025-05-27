import os
from alembic.config import Config
from alembic import command

from dotenv import load_dotenv

load_dotenv()


def setup_alembic():
    """Set up Alembic for database migrations"""
    # Create a new Alembic configuration
    alembic_cfg = Config("alembic.ini")

    # Set the path to the migration scripts
    script_location = os.path.join(os.path.dirname(__file__), "alembic")
    alembic_cfg.set_main_option("script_location", script_location)

    # Set the SQLAlchemy URL
    database_url = os.environ.get(
        "DATABASE_URL", "")
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)

    # Create the migration environment
    command.init(alembic_cfg, "alembic")

    # Create a new migration
    command.revision(
        alembic_cfg, "Create wallet analyses table", autogenerate=True)

    # Apply the migration
    command.upgrade(alembic_cfg, "head")


if __name__ == "__main__":
    print("Setting up Alembic...")
    setup_alembic()
    print("Alembic setup complete!")
