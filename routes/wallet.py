from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from database.database import get_db, WalletAnalysis
from utils.wallet_utils import analyze_wallet_address

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
    return await analyze_wallet_address(wallet_address, db)


@router.get("/{wallet_address}")
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


@router.delete("/{wallet_address}")
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
