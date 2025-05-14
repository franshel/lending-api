from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from fastapi import HTTPException

from database.database import WalletAnalysis
from utils.holdings import get_token_holdings_data
from utils.transactions import get_tx_data
from ai_gen_analysis import generate
from utils.utils import serialize_pydantic_model
import logging

# Configure logging
logger = logging.getLogger(__name__)


async def analyze_wallet_address(wallet_address: str, db: Session) -> Dict[str, Any]:
    """
    Analyze a wallet address and store the results in the database.
    If the wallet has been analyzed before, the analysis will be updated.

    Args:
        wallet_address: Ethereum wallet address to analyze
        db: Database session

    Returns:
        Dict containing the wallet analysis results

    Raises:
        HTTPException: If there's an error during the analysis process
    """
    try:
        # Check if wallet already exists in database
        existing = db.query(WalletAnalysis).filter(
            WalletAnalysis.wallet_address == wallet_address).first()

        try:
            # Get wallet data
            token_holdings = get_token_holdings_data(wallet_address)
        except Exception as e:
            token_holdings = []
            logger.error(f"Error fetching token holdings: {str(e)}")

        try:
            # Get transaction data
            transactions = get_tx_data(wallet_address)
        except Exception as e:
            transactions = []
            logger.error(f"Error fetching transactions: {str(e)}")

        # If no data is available for the wallet, create minimal data for storage
        if not transactions and not token_holdings:
            # Return a response for wallets with no data
            return {
                "wallet_address": wallet_address,
                "status": "no_data",
                "message": "No transaction or token holding data found for this wallet address",
                "timestamp": datetime.utcnow().isoformat()
            }

        # Generate analysis using AI
        analysis_result = generate(
            wallet_address, token_holdings, transactions)

        # Process the analysis result with proper datetime handling
        processed_analysis = serialize_pydantic_model(analysis_result)

        # Process transactions with proper datetime handling
        processed_transactions = None
        if isinstance(transactions, list):
            processed_transactions = [
                serialize_pydantic_model(tx) for tx in transactions]

        # Prepare data for storage with proper datetime serialization
        wallet_data = {
            "wallet_address": wallet_address,
            "network": processed_analysis["network"],
            "analysis_timestamp": processed_analysis["analysis_timestamp"],
            "final_score": processed_analysis["final_score"],
            "risk_level": processed_analysis["risk_level"],
            "wallet_metadata": processed_analysis["wallet_metadata"],
            "scoring_breakdown": processed_analysis["scoring_breakdown"],
            "behavioral_patterns": processed_analysis["behavioral_patterns"],
            "transactions": processed_transactions,
            "token_holdings": token_holdings,
            "comments": processed_analysis["comments"]
        }

        if existing:
            # Update existing record
            for key, value in wallet_data.items():
                setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing.to_dict()
        else:
            # Create new record
            new_analysis = WalletAnalysis(**wallet_data)
            db.add(new_analysis)
            db.commit()
            db.refresh(new_analysis)
            return new_analysis.to_dict()

    except Exception as e:
        logger.error(f"Error analyzing wallet {wallet_address}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error analyzing wallet: {str(e)}")


async def get_or_create_wallet_analysis(wallet_address: str, db: Session) -> Optional[Dict[str, Any]]:
    """
    Gets existing wallet analysis or creates one if it doesn't exist.

    Args:
        wallet_address: Ethereum wallet address to analyze
        db: Database session

    Returns:
        Dict containing the wallet analysis results or None if analysis failed

    Note: This function catches exceptions internally and returns None on failure,
    making it safer to use in workflows where analysis failure should not stop the main process.
    """
    try:
        # Check if wallet already has an analysis
        existing = db.query(WalletAnalysis).filter(
            WalletAnalysis.wallet_address == wallet_address).first()

        if existing:
            # If analysis exists and is recent (less than 24 hours old), return it
            analysis_time = existing.analysis_timestamp
            now = datetime.utcnow()

            # If analysis is less than 24 hours old, return existing analysis
            if (now - analysis_time).total_seconds() < 86400:  # 24 hours in seconds
                logger.info(
                    f"Using existing wallet analysis for {wallet_address}, created at {analysis_time}")
                return existing.to_dict()
            else:
                logger.info(
                    f"Existing wallet analysis for {wallet_address} is outdated, creating new analysis")
        else:
            logger.info(
                f"No existing wallet analysis found for {wallet_address}, creating new analysis")

        # Perform new analysis
        return await analyze_wallet_address(wallet_address, db)

    except Exception as e:
        logger.error(
            f"Error getting or creating wallet analysis for {wallet_address}: {str(e)}",
            exc_info=True)
        return None
