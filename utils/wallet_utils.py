from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime, timezone
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
    For new wallets with no activity, uses a template instead of AI analysis.

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

        print("REACHED FUCKING HERE")
        print(transactions, token_holdings)
        # Template for new wallets with no activity
        if not transactions and not token_holdings:
            print("no tx and no holdings")
            wallet_data = {
                "wallet_address": wallet_address,
                "network": "ethereum",
                "analysis_timestamp": datetime.now(timezone.utc),
                "final_score": 0,
                "risk_level": "unknown",
                "wallet_metadata": {
                    "age": "new",
                    "activity_level": "none",
                    "transaction_count": 0,
                    "unique_interactions": 0
                },
                "scoring_breakdown": {
                    "age_score": 0,
                    "activity_score": 0,
                    "balance_score": 0,
                    "diversity_score": 0
                },
                "behavioral_patterns": [],
                "transactions": [],
                "token_holdings": [],
                "comments": ["New wallet with no transaction history or token holdings."]
            }
        else:
            print("have tx and hv holdings")

            # Only use AI analysis if there is activity
            analysis_result = generate(
                wallet_address, token_holdings, transactions)
            print("analysis result", analysis_result)
            processed_analysis = serialize_pydantic_model(analysis_result)
            print("processed analysis", processed_analysis)
            processed_transactions = [tx.model_dump_json()
                                      for tx in transactions]
            print("processed transactions", processed_transactions)
            wallet_data = {
                "wallet_address": wallet_address,
                "network": processed_analysis.get('network', 'ethereum'),
                "analysis_timestamp": processed_analysis.get('analysis_timestamp', datetime.now(timezone.utc)),
                "final_score": processed_analysis.get('final_score', 0),
                "risk_level": processed_analysis.get('risk_level', 'unknown'),
                "wallet_metadata": processed_analysis.get('wallet_metadata', {}),
                "scoring_breakdown": processed_analysis.get('scoring_breakdown', {}),
                "behavioral_patterns": processed_analysis.get('behavioral_patterns', []),
                "transactions": processed_transactions,
                "token_holdings": token_holdings,
                "comments": processed_analysis.get('comments', [])
            }
            print("wallet data", wallet_data)

        if existing:
            print("existing wallet found")
            # Update existing record
            for key, value in wallet_data.items():
                setattr(existing, key, value)
            existing.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(existing)
            return existing.to_dict()
        else:
            print("no existing wallet found")
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


async def background_wallet_analysis(wallet_address: str, db: Session) -> None:
    """
    Dedicated function for running wallet analysis in the background.
    This function properly handles errors and ensures the database session is used correctly.

    Args:
        wallet_address: Ethereum wallet address to analyze
        db: Database session from the request scope
    """
    from database.database import SessionLocal

    # Create a new database session specifically for this background task
    # This is important because the request's session might be closed by the time this runs
    background_db = SessionLocal()

    logger.info(f"Starting background wallet analysis for {wallet_address}")
    try:
        # Check if wallet already has an analysis (double check in case it was created between scheduling and execution)
        # Using direct SQL instead of ORM to avoid relationship issues
        existing_query = background_db.execute(
            text(
                f"SELECT id FROM wallet_analyses WHERE wallet_address = '{wallet_address}'")).fetchone()

        if existing_query:
            logger.info(
                f"Analysis for wallet {wallet_address} already exists, skipping background analysis")
            return

        print('reached here.......')
        # Perform the wallet analysis
        result = await analyze_wallet_address(wallet_address, background_db)
        logger.info(
            f"Successfully completed background wallet analysis for {wallet_address}. Score: {result.get('final_score', 'N/A')}")

    except Exception as e:
        # Log but don't raise - this is a background task
        logger.error(
            f"Error in background wallet analysis for {wallet_address}: {str(e)}", exc_info=True)
    finally:
        # Always close the background database session when done
        background_db.close()
        logger.info(
            f"Background database session closed for wallet analysis of {wallet_address}")
