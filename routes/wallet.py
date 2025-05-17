from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional
from datetime import datetime
import logging

from database.database import get_db, WalletAnalysis
from utils.wallet_utils import analyze_wallet_address

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/wallets",
    tags=["wallet"],
)


@router.post("/analyze/{wallet_address}", tags=["analysis"])
async def analyze_wallet(wallet_address: str, db: Session = Depends(get_db)):
    """
    Analyze a wallet address and store the results in the database.
    If the wallet has been analyzed before, the analysis will be updated.
    """
    try:
        return await analyze_wallet_address(wallet_address, db)
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error during wallet analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Error storing wallet analysis results"
        )
    except Exception as e:
        logger.error(f"Error analyzing wallet {wallet_address}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during wallet analysis"
        )


@router.get("/{wallet_address}")
async def get_wallet_analysis(wallet_address: str, db: Session = Depends(get_db)):
    """
    Get analysis results for a specific wallet address
    """
    try:
        # Use direct SQL with explicit column selection
        wallet_query = db.execute(
            text("""
                SELECT wallet_address, network, analysis_timestamp, final_score,
                       risk_level, wallet_metadata, scoring_breakdown,
                       behavioral_patterns, transactions, token_holdings,
                       comments, created_at, updated_at
                FROM wallet_analyses 
                WHERE wallet_address = :address
            """),
            {"address": wallet_address}
        ).fetchone()

        if not wallet_query:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet analysis not found"
            )

        # Convert to dictionary with explicit field mapping
        result = {
            "wallet_address": wallet_query.wallet_address,
            "network": wallet_query.network,
            "analysis_timestamp": wallet_query.analysis_timestamp.isoformat() if wallet_query.analysis_timestamp else None,
            "final_score": wallet_query.final_score,
            "risk_level": wallet_query.risk_level,
            "wallet_metadata": wallet_query.wallet_metadata,
            "scoring_breakdown": wallet_query.scoring_breakdown,
            "behavioral_patterns": wallet_query.behavioral_patterns,
            "transactions": wallet_query.transactions,
            "token_holdings": wallet_query.token_holdings,
            "comments": wallet_query.comments,
            "created_at": wallet_query.created_at.isoformat() if wallet_query.created_at else None,
            "updated_at": wallet_query.updated_at.isoformat() if wallet_query.updated_at else None
        }

        return result

    except HTTPException as he:
        raise he
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching wallet analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Error retrieving wallet analysis from database"
        )
    except Exception as e:
        logger.error(f"Error fetching wallet analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving the wallet analysis"
        )


@router.get("/")
async def get_all_wallets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    risk_level: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """
    Get all analyzed wallets with optional filtering
    """
    try:
        columns = """
            wallet_address, network, analysis_timestamp, final_score,
            risk_level, wallet_metadata, scoring_breakdown,
            behavioral_patterns, transactions, token_holdings,
            comments, created_at, updated_at
        """
        base_query = f"SELECT {columns} FROM wallet_analyses WHERE 1=1"
        params = {}

        # Build query with filters
        if risk_level:
            base_query += " AND risk_level = :risk_level"
            params["risk_level"] = risk_level
        if min_score is not None:
            base_query += " AND final_score >= :min_score"
            params["min_score"] = min_score
        if max_score is not None:
            base_query += " AND final_score <= :max_score"
            params["max_score"] = max_score

        # Add pagination
        base_query += " LIMIT :limit OFFSET :skip"
        params.update({"limit": limit, "skip": skip})

        # Get total count (without pagination)
        count_query = "SELECT COUNT(*) FROM wallet_analyses WHERE 1=1"
        if risk_level:
            count_query += " AND risk_level = :risk_level"
        if min_score is not None:
            count_query += " AND final_score >= :min_score"
        if max_score is not None:
            count_query += " AND final_score <= :max_score"
        total = db.execute(text(count_query), params).scalar()

        # Get paginated results
        wallets = db.execute(text(base_query), params).fetchall()

        # Convert results to dictionaries with proper handling
        wallet_list = []
        for wallet in wallets:
            wallet_dict = {
                "wallet_address": wallet.wallet_address,
                "network": wallet.network,
                "analysis_timestamp": wallet.analysis_timestamp.isoformat() if wallet.analysis_timestamp else None,
                "final_score": wallet.final_score,
                "risk_level": wallet.risk_level,
                "wallet_metadata": wallet.wallet_metadata,
                "scoring_breakdown": wallet.scoring_breakdown,
                "behavioral_patterns": wallet.behavioral_patterns,
                "transactions": wallet.transactions,
                "token_holdings": wallet.token_holdings,
                "comments": wallet.comments,
                "created_at": wallet.created_at.isoformat() if wallet.created_at else None,
                "updated_at": wallet.updated_at.isoformat() if wallet.updated_at else None
            }
            wallet_list.append(wallet_dict)

        return {
            "total": total,
            "wallets": wallet_list
        }

    except SQLAlchemyError as e:
        logger.error(f"Database error fetching wallets: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Error retrieving wallet data from database"
        )
    except Exception as e:
        logger.error(f"Error fetching wallets: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving wallet data"
        )


@router.delete("/{wallet_address}")
async def delete_wallet_analysis(wallet_address: str, db: Session = Depends(get_db)):
    """
    Delete analysis results for a specific wallet address
    """
    try:        # First check if wallet exists
        wallet = db.execute(
            text("SELECT id FROM wallet_analyses WHERE wallet_address = :address"),
            {"address": wallet_address}
        ).fetchone()

        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet analysis not found"
            )

        # Then delete it
        db.execute(
            text("DELETE FROM wallet_analyses WHERE wallet_address = :address"),
            {"address": wallet_address}
        )
        db.commit()

        return {"message": f"Wallet analysis for {wallet_address} has been deleted"}

    except HTTPException as he:
        raise he
    except SQLAlchemyError as e:
        logger.error(f"Database error deleting wallet analysis: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Error deleting wallet analysis from database"
        )
    except Exception as e:
        logger.error(f"Error deleting wallet analysis: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting the wallet analysis"
        )
