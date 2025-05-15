import os
import json
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey, Table, Boolean
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
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

    # Relationship to business proposals
    proposals = relationship(
        "BusinessProposal", back_populates="wallet_analysis")

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


# Association table for many-to-many relationship between proposals and tags
proposal_tags = Table(
    'proposal_tags',
    Base.metadata,
    Column('proposal_id', String(20), ForeignKey('business_proposals.id')),
    Column('tag_name', String(50), ForeignKey('tags.name'))
)


class BusinessProposal(Base):
    """SQLAlchemy model for business proposals"""
    __tablename__ = "business_proposals"

    id = Column(String(20), primary_key=True, index=True)
    company_name = Column(String(100), nullable=False, index=True)
    logo = Column(String(255), nullable=True)
    accepted_token = Column(String(10), nullable=False)
    total_pooled = Column(String(50), nullable=False)
    short_description = Column(String(200), nullable=False)
    full_description = Column(Text, nullable=False)
    business_plan = Column(Text, nullable=False)
    expected_return = Column(String(20), nullable=False)
    duration = Column(String(20), nullable=False)
    minimum_investment = Column(String(20), nullable=False)
    maximum_investment = Column(String(20), nullable=False)
    proposer_wallet = Column(String(100), nullable=False, index=True)
    proposed_at = Column(DateTime, nullable=False)
    deadline = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False, default='active', index=True)
    current_funding = Column(String(20), nullable=False, default='0')
    target_funding = Column(String(20), nullable=False)
    investor_count = Column(Integer, nullable=False, default=0)
    website = Column(String(255), nullable=True)
    social_media = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    # Foreign key to wallet_analysis
    wallet_analysis_id = Column(Integer, ForeignKey(
        'wallet_analyses.id'), nullable=True)

    # Relationships
    wallet_analysis = relationship(
        "WalletAnalysis", back_populates="proposals")
    documents = relationship(
        "ProposalDocument", back_populates="proposal", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary=proposal_tags, backref="proposals")

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "company_name": self.company_name,
            "logo": self.logo,
            "accepted_token": self.accepted_token,
            "total_pooled": self.total_pooled,
            "short_description": self.short_description,
            "full_description": self.full_description,
            "business_plan": self.business_plan,
            "expected_return": self.expected_return,
            "duration": self.duration,
            "minimum_investment": self.minimum_investment,
            "maximum_investment": self.maximum_investment,
            "proposer_wallet": self.proposer_wallet,
            "proposed_at": self.proposed_at.isoformat() if self.proposed_at else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "status": self.status,
            "current_funding": self.current_funding,
            "target_funding": self.target_funding,
            "investor_count": self.investor_count,
            "wallet_analysis": self.wallet_analysis.to_dict() if self.wallet_analysis else None,
            "documents": [doc.to_dict() for doc in self.documents],
            "tags": [tag.name for tag in self.tags],
            "website": self.website,
            "social_media": self.social_media,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class ProposalDocument(Base):
    """SQLAlchemy model for proposal documents"""
    __tablename__ = "proposal_documents"

    id = Column(String(20), primary_key=True, index=True)
    proposal_id = Column(String(20), ForeignKey(
        "business_proposals.id"), nullable=False)
    title = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)
    url = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, nullable=False)
    size = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    # Relationship
    proposal = relationship("BusinessProposal", back_populates="documents")

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "proposal_id": self.proposal_id,
            "title": self.title,
            "type": self.type,
            "url": self.url,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "size": self.size,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Tag(Base):
    """SQLAlchemy model for tags"""
    __tablename__ = "tags"

    name = Column(String(50), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class WalletProfile(Base):
    """SQLAlchemy model for user profiles linked to wallets"""
    __tablename__ = "wallet_profiles"

    # Wallet address is the primary key
    wallet_address = Column(String(42), primary_key=True, index=True)

    # Basic profile information
    display_name = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(255), nullable=True)
    profile_completed = Column(Boolean, default=False, nullable=False)

    # Contact information
    phone = Column(String(20), nullable=True)
    website = Column(String(255), nullable=True)
    social_media = Column(JSONB, nullable=True)

    # Business information (for proposal creators)
    company_name = Column(String(100), nullable=True)
    company_position = Column(String(100), nullable=True)
    company_website = Column(String(255), nullable=True)
    company_description = Column(Text, nullable=True)

    # Verification status
    email_verified = Column(Boolean, default=False, nullable=False)
    kyc_verified = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)
    # Foreign relationships
    # Add relationship to wallet analysis using foreign() annotation
    wallet_analysis = relationship(
        "WalletAnalysis",
        primaryjoin="foreign(WalletProfile.wallet_address) == remote(WalletAnalysis.wallet_address)",
        backref="profile",
        uselist=False,
        viewonly=True  # Make it read-only to prevent cascading issues
    )

    # Add relationship to business proposals using foreign() annotation
    proposals = relationship(
        "BusinessProposal",
        primaryjoin="foreign(WalletProfile.wallet_address) == remote(BusinessProposal.proposer_wallet)",
        backref="profile",
        uselist=True,
        viewonly=True  # Make it read-only to prevent cascading issues
    )

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "wallet_address": self.wallet_address,
            "display_name": self.display_name,
            "email": self.email,
            "bio": self.bio,
            "avatar_url": self.avatar_url,
            "profile_completed": self.profile_completed,
            "phone": self.phone,
            "website": self.website,
            "social_media": self.social_media,
            "company_name": self.company_name,
            "company_position": self.company_position,
            "company_website": self.company_website,
            "company_description": self.company_description,
            "email_verified": self.email_verified,
            "kyc_verified": self.kyc_verified,
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
