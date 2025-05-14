from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from typing import List, Optional
import json
from datetime import datetime

from database.database import get_db, WalletAnalysis
from schemas.schemas import FraudRiskAnalysis, ProcessedTransaction
from utils.holdings import get_token_holdings_data, get_token_holdings_summary
from utils.transactions import get_tx_data  # type: ignore
from ai_gen_analysis import generate
from utils.utils import json_serial, serialize_pydantic_model

# Create a custom JSON encoder class

load_dotenv()


class CustomJSONResponse(JSONResponse):
    def render(self, content):
        return json.dumps(
            content,
            default=json_serial,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":")
        ).encode("utf-8")


app = FastAPI(
    title="Wallet Analysis API",
    description="API for storing and retrieving wallet analysis data",
    version="1.0.0",
    default_response_class=CustomJSONResponse
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint, returns API status"""
    return {"status": "active", "message": "Wallet Analysis API is running"}


@app.post("/analyze/{wallet_address}")
async def analyze_wallet(wallet_address: str, db: Session = Depends(get_db)):
    """
    Analyze a wallet address and store the results in the database.
    If the wallet has been analyzed before, the analysis will be updated.
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
            print(f"Error fetching token holdings: {str(e)}")

        try:
            # Get transaction data
            transactions = get_tx_data(wallet_address)
        except Exception as e:
            transactions = []
            print(f"Error fetching transactions: {str(e)}")

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
            wallet_address, token_holdings, transactions)        # Import the utility function for serializing Pydantic models
        from utils.utils import serialize_pydantic_model

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
        raise HTTPException(
            status_code=500, detail=f"Error analyzing wallet: {str(e)}")


@app.get("/wallets/{wallet_address}")
async def get_wallet_analysis(wallet_address: str, db: Session = Depends(get_db)):
    """
    Get analysis results for a specific wallet address
    """
    wallet = db.query(WalletAnalysis).filter(
        WalletAnalysis.wallet_address == wallet_address).first()
    if not wallet:
        raise HTTPException(
            status_code=404, detail="Wallet analysis not found")
    return wallet.to_dict()


@app.get("/wallets")
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
    query = db.query(WalletAnalysis)

    # Apply filters if provided
    if risk_level:
        query = query.filter(WalletAnalysis.risk_level == risk_level)
    if min_score is not None:
        query = query.filter(WalletAnalysis.final_score >= min_score)
    if max_score is not None:
        query = query.filter(WalletAnalysis.final_score <= max_score)

    # Apply pagination
    total = query.count()
    wallets = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "wallets": [wallet.to_dict() for wallet in wallets]
    }


@app.delete("/wallets/{wallet_address}")
async def delete_wallet_analysis(wallet_address: str, db: Session = Depends(get_db)):
    """
    Delete analysis results for a specific wallet address
    """
    wallet = db.query(WalletAnalysis).filter(
        WalletAnalysis.wallet_address == wallet_address).first()
    if not wallet:
        raise HTTPException(
            status_code=404, detail="Wallet analysis not found")

    db.delete(wallet)
    db.commit()
    return {"message": f"Wallet analysis for {wallet_address} has been deleted"}
