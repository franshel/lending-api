import os
import json
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging

# Get the database URL from environment variable or use a default
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@157.230.244.71:9999/postgres")

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a base class for models
Base = declarative_base()


class WalletAnalysis(Base):
    """SQLAlchemy model for the wallet_analyses table"""
    __tablename__ = "wallet_analyses"

    id = Column(Integer, primary_key=True, index=True)
    wallet_address = Column(String(42), unique=True,
                            nullable=False, index=True)
    network = Column(String(50), nullable=False)
    analysis_timestamp = Column(DateTime, nullable=False)
    final_score = Column(Float, nullable=False, index=True)
    risk_level = Column(String(20), nullable=False, index=True)
    # Changed from 'metadata' as it's reserved
    wallet_metadata = Column(JSONB, nullable=False)
    scoring_breakdown = Column(JSONB, nullable=False)
    behavioral_patterns = Column(JSONB, nullable=False)
    transactions = Column(JSONB, nullable=True)
    token_holdings = Column(JSONB, nullable=True)
    comments = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert model to dictionary"""
        from utils.utils import json_serial
        return {
            "id": self.id,
            "wallet_address": self.wallet_address,
            "network": self.network,
            "analysis_timestamp": self.analysis_timestamp.isoformat() if self.analysis_timestamp else None,
            "final_score": self.final_score,
            "risk_level": self.risk_level,
            # Changed from 'metadata' to match column name
            "wallet_metadata": self.wallet_metadata,
            "scoring_breakdown": self.scoring_breakdown,
            "behavioral_patterns": self.behavioral_patterns,
            "transactions": self.transactions,
            "token_holdings": self.token_holdings,
            "comments": self.comments,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


# Helper functions for database operations
def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
