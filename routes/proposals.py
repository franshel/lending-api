from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError
from typing import List, Optional
import uuid
import logging

from database.database import get_db, WalletAnalysis, BusinessProposal, ProposalDocument, Tag, WalletProfile
from schemas.schemas import (
    BusinessProposalCreate, BusinessProposalUpdate,
    BusinessProposalResponse, DocumentCreate
)
from utils.auth_utils import get_current_wallet
from utils.wallet_utils import analyze_wallet_address, get_or_create_wallet_analysis

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/proposals",
    tags=["proposals"],
)


@router.post("/", response_model=BusinessProposalResponse, status_code=status.HTTP_201_CREATED)
async def create_business_proposal(
    proposal: BusinessProposalCreate,
    db: Session = Depends(get_db),
    wallet_address: str = Depends(get_current_wallet)
):
    """
    Create a new business proposal from an authenticated wallet.
    Requires a completed profile before allowing proposal creation.
    Only one active proposal per wallet is allowed.
    """
    try:
        # Check if wallet already has an active proposal
        existing_proposal = db.query(BusinessProposal).filter(
            BusinessProposal.proposer_wallet == wallet_address
        ).first()

        if existing_proposal:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You already have an active proposal. Only one proposal per wallet is allowed."
            )

        # Check if user has a completed profile - using direct SQL to avoid ORM issues
        profile_query = db.execute(
            text(
                "SELECT wallet_address, profile_completed FROM wallet_profiles WHERE wallet_address = :address"
            ),
            {"address": wallet_address}
        ).fetchone()

        logger.debug(
            f"Profile query result for {wallet_address}: {profile_query}")

        if not profile_query:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You must create a profile before creating a business proposal"
            )

        if not profile_query.profile_completed:
            logger.debug(f"Profile not completed for wallet {wallet_address}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You must complete your profile before creating a business proposal"
            )

        # Always do fresh wallet analysis when creating a proposal
        try:
            wallet_analysis_result = await analyze_wallet_address(wallet_address, db)
            logger.info(
                f"Wallet {wallet_address} analyzed successfully with risk level: {wallet_analysis_result.get('risk_level', 'unknown')}")
        except Exception as e:
            logger.warning(
                f"Could not analyze wallet {wallet_address}, but will continue with proposal creation: {str(e)}")
            wallet_analysis_result = None

        # Get the wallet analysis from the database (after analysis) - using direct SQL
        wallet_analysis_query = db.execute(
            text("SELECT id FROM wallet_analyses WHERE wallet_address = :address"),
            {"address": wallet_address}
        ).fetchone()

        wallet_analysis_id = wallet_analysis_query.id if wallet_analysis_query else None

        # Generate proposal ID
        proposal_id = f"prop-{uuid.uuid4().hex[:6]}"

        # Prepare data for business proposal
        try:
            proposal_data = proposal.model_dump()
            proposal_data.pop("documents")  # Handle documents separately
            proposal_data.pop("tags")  # Handle tags separately
        except ValidationError as ve:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(ve)
            )

        # Create the business proposal
        proposal_data["proposer_wallet"] = wallet_address
        try:
            new_proposal = BusinessProposal(
                id=proposal_id,
                **proposal_data,
                wallet_analysis_id=wallet_analysis_id
            )
            db.add(new_proposal)

            # Add documents
            for doc in proposal.documents:
                doc_id = f"doc-{uuid.uuid4().hex[:6]}"
                document = ProposalDocument(
                    id=doc_id,
                    proposal_id=proposal_id,
                    **doc.model_dump()
                )
                db.add(document)

            # Add tags
            for tag_name in proposal.tags:
                tag = db.query(Tag).filter(Tag.name == tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.add(tag)
                new_proposal.tags.append(tag)

            db.commit()
            db.refresh(new_proposal)
            return new_proposal.to_dict()

        except SQLAlchemyError as e:
            db.rollback()
            logger.error(
                f"Database error creating business proposal: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Database error while creating business proposal"
            )
        except ValidationError as ve:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(ve)
            )
    except HTTPException as he:
        # Re-raise HTTP exceptions with their original status codes
        raise he
    except Exception as e:
        # For unknown errors, log them but return a generic message
        logger.error(
            f"Unexpected error creating business proposal: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the business proposal"
        )


@router.get("/by-wallet/{wallet_address}")
async def get_wallet_proposals(
    wallet_address: str,
    db: Session = Depends(get_db)
):
    """
    Get all business proposals submitted by a specific wallet address
    """
    try:
        proposals = db.query(BusinessProposal).filter(
            BusinessProposal.proposer_wallet == wallet_address
        ).all()

        return {
            "total": len(proposals),
            "wallet_address": wallet_address,
            "proposals": [proposal.to_dict() for proposal in proposals]
        }
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching proposals: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Error retrieving proposals from database"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching proposals: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving proposals"
        )


@router.get("/me", response_model=dict)
async def get_my_proposals(
    db: Session = Depends(get_db),
    wallet_address: str = Depends(get_current_wallet)
):
    """
    Get all business proposals submitted by the authenticated wallet
    """
    try:
        proposals = db.query(BusinessProposal).filter(
            BusinessProposal.proposer_wallet == wallet_address
        ).all()

        return {
            "total": len(proposals),
            "wallet_address": wallet_address,
            "proposals": [proposal.to_dict() for proposal in proposals]
        }
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching proposals: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Error retrieving proposals from database"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching proposals: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving proposals"
        )


@router.get("/{proposal_id}", response_model=BusinessProposalResponse)
async def get_business_proposal(proposal_id: str, db: Session = Depends(get_db)):
    """
    Get a specific business proposal by ID
    """
    try:
        proposal = db.query(BusinessProposal).filter(
            BusinessProposal.id == proposal_id).first()

        if not proposal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Business proposal with id {proposal_id} not found"
            )

        return proposal.to_dict()
    except HTTPException as he:
        raise he
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching proposal: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Error retrieving proposal from database"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching proposal: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving the proposal"
        )


@router.get("/", response_model=dict)
async def get_all_proposals(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    token: Optional[str] = None,
    min_funding: Optional[float] = None,
    tags: Optional[List[str]] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get all business proposals with optional filtering
    """
    query = db.query(BusinessProposal)

    # Apply filters if provided
    if status:
        query = query.filter(BusinessProposal.status == status)
    if token:
        query = query.filter(BusinessProposal.accepted_token == token)
    if min_funding is not None:
        # This is a simplified filter for strings representing numeric values
        query = query.filter(
            BusinessProposal.current_funding >= str(min_funding))
    if tags:
        for tag in tags:
            query = query.filter(BusinessProposal.tags.any(name=tag))

    # Apply pagination
    total = query.count()
    proposals = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "proposals": [proposal.to_dict() for proposal in proposals]
    }


@router.put("/{proposal_id}", response_model=BusinessProposalResponse)
async def update_business_proposal(
    proposal_id: str,
    proposal_update: BusinessProposalUpdate,
    db: Session = Depends(get_db),
    wallet_address: str = Depends(get_current_wallet)
):
    """
    Update a business proposal (must be the original proposer)
    """
    db_proposal = db.query(BusinessProposal).filter(
        BusinessProposal.id == proposal_id).first()
    if not db_proposal:
        raise HTTPException(
            status_code=404, detail="Business proposal not found")

    # Verify that the authenticated wallet is the original proposer
    if db_proposal.proposer_wallet.lower() != wallet_address.lower():
        raise HTTPException(
            status_code=403, detail="You can only update your own proposals")

    # Update proposal fields
    proposal_data = proposal_update.dict(exclude_unset=True)

    # Handle tags separately
    if "tags" in proposal_data:
        tags = proposal_data.pop("tags")

        # Clear existing tags
        db_proposal.tags = []

        # Add new tags
        for tag_name in tags:
            tag = db.query(Tag).filter(Tag.name == tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                db.add(tag)
            db_proposal.tags.append(tag)

    # Update other fields
    for key, value in proposal_data.items():
        setattr(db_proposal, key, value)

    db.commit()
    db.refresh(db_proposal)

    return db_proposal.to_dict()


@router.delete("/{proposal_id}")
async def delete_business_proposal(
    proposal_id: str,
    db: Session = Depends(get_db),
    wallet_address: str = Depends(get_current_wallet)
):
    """
    Delete a business proposal (must be the original proposer)
    """
    db_proposal = db.query(BusinessProposal).filter(
        BusinessProposal.id == proposal_id).first()
    if not db_proposal:
        raise HTTPException(
            status_code=404, detail="Business proposal not found")

    # Verify that the authenticated wallet is the original proposer
    if db_proposal.proposer_wallet.lower() != wallet_address.lower():
        raise HTTPException(
            status_code=403, detail="You can only delete your own proposals")

    db.delete(db_proposal)
    db.commit()

    return {"message": f"Business proposal {proposal_id} has been deleted"}


@router.post("/{proposal_id}/documents", response_model=dict)
async def add_document_to_proposal(
    proposal_id: str,
    document: DocumentCreate,
    db: Session = Depends(get_db),
    wallet_address: str = Depends(get_current_wallet)
):
    """
    Add a document to a business proposal (must be the original proposer)
    """
    # Check if proposal exists
    db_proposal = db.query(BusinessProposal).filter(
        BusinessProposal.id == proposal_id).first()
    if not db_proposal:
        raise HTTPException(
            status_code=404, detail="Business proposal not found")

    # Verify that the authenticated wallet is the original proposer
    if db_proposal.proposer_wallet.lower() != wallet_address.lower():
        raise HTTPException(
            status_code=403, detail="You can only add documents to your own proposals")

    # Create document
    doc_id = f"doc-{uuid.uuid4().hex[:6]}"
    new_document = ProposalDocument(
        id=doc_id,
        proposal_id=proposal_id,
        **document.dict()
    )

    db.add(new_document)
    db.commit()
    db.refresh(new_document)

    return new_document.to_dict()


@router.delete("/{proposal_id}/documents/{document_id}")
async def delete_proposal_document(
    proposal_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    wallet_address: str = Depends(get_current_wallet)
):
    """
    Delete a document from a business proposal (must be the original proposer)
    """
    # First get the proposal to check ownership
    db_proposal = db.query(BusinessProposal).filter(
        BusinessProposal.id == proposal_id).first()
    if not db_proposal:
        raise HTTPException(
            status_code=404, detail="Business proposal not found")

    # Verify that the authenticated wallet is the original proposer
    if db_proposal.proposer_wallet.lower() != wallet_address.lower():
        raise HTTPException(
            status_code=403, detail="You can only delete documents from your own proposals")

    # Now check if the document exists
    db_document = db.query(ProposalDocument).filter(
        ProposalDocument.id == document_id,
        ProposalDocument.proposal_id == proposal_id
    ).first()

    if not db_document:
        raise HTTPException(
            status_code=404, detail="Document not found")

    db.delete(db_document)
    db.commit()

    return {"message": f"Document {document_id} has been deleted from proposal {proposal_id}"}
