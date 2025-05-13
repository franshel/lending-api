import json
import os
from sqlalchemy.orm import Session
from database import SessionLocal, WalletAnalysis
from datetime import datetime
import json


def insert_sample_data():
    """Insert sample data into the database"""
    db = SessionLocal()
    try:
        # Sample data for a low-risk wallet
        low_risk_wallet = WalletAnalysis(
            wallet_address="0x473269f9F2D3B8e99134A4b37CB2E30c10AE31c2",
            network="Lisk",
            analysis_timestamp=datetime.now(),
            final_score=85.0,
            risk_level="Low Risk",
            wallet_metadata={
                "first_seen": datetime(2025, 1, 15).isoformat(),
                "last_seen": datetime(2025, 5, 11).isoformat(),
                "age_days": 116,
                "total_transactions": 9,
                "inbound_count": 1,
                "outbound_count": 8,
                "unique_tokens_used": 1,
                "unique_contracts_interacted": 1,
                "uses_only_transfers": True,
                "all_contracts_verified": True,
                "funded_by_established_wallet": True,
                "linked_to_flagged_entity": False
            },
            scoring_breakdown=[
                {
                    "criteria": "Transaction Direction",
                    "score_delta": 15.0,
                    "reason": "Wallet has both inbound and outbound transactions"
                },
                {
                    "criteria": "Transaction Variability",
                    "score_delta": 10.0,
                    "reason": "Transaction amounts show logical variation"
                },
                {
                    "criteria": "Contract Interaction Diversity",
                    "score_delta": -10.0,
                    "reason": "Wallet interacts with only one contract"
                }
            ],
            behavioral_patterns={
                "outbound_only": False,
                "transaction_anomalies": [],
                "contract_usage": {
                    "single_contract_usage": True,
                    "unverified_contract_usage": False
                }
            },
            token_holdings=[
                "Token: Nuzo KSH (KSH)\nType: ERC-20\nAmount: 127.8200 KSH\nCirculating Market Cap: $1,500,000\nTotal Supply: 1000000 KSH\nExchange Rate: $0.85"
            ],
            comments=["Normal usage pattern",
                      "Regular transfers to verified contract"]
        )

        # Sample data for a high-risk wallet
        high_risk_wallet = WalletAnalysis(
            wallet_address="0xA76D02E3B083179804088b1D4A5B5367D28c69B6",
            network="Lisk",
            analysis_timestamp=datetime.now(),
            final_score=35.0,
            risk_level="High Risk",
            wallet_metadata={
                "first_seen": datetime(2025, 5, 1).isoformat(),
                "last_seen": datetime(2025, 5, 11).isoformat(),
                "age_days": 10,
                "total_transactions": 15,
                "inbound_count": 0,
                "outbound_count": 15,
                "unique_tokens_used": 1,
                "unique_contracts_interacted": 3,
                "uses_only_transfers": True,
                "all_contracts_verified": False,
                "funded_by_established_wallet": False,
                "linked_to_flagged_entity": True
            },
            scoring_breakdown=[
                {
                    "criteria": "Transaction Direction",
                    "score_delta": -15.0,
                    "reason": "Wallet has only outbound transactions"
                },
                {
                    "criteria": "Transaction Variability",
                    "score_delta": -10.0,
                    "reason": "Transaction amounts are erratic"
                },
                {
                    "criteria": "Contract Verification",
                    "score_delta": -10.0,
                    "reason": "Wallet interacts with unverified contracts"
                }
            ],
            behavioral_patterns={
                "outbound_only": True,
                "transaction_anomalies": ["Rapid fund drainage", "Identical transaction amounts"],
                "contract_usage": {
                    "single_contract_usage": False,
                    "unverified_contract_usage": True
                }
            },
            token_holdings=[
                "Token: Ethereum (ETH)\nType: Native\nAmount: 0.0025 ETH\nExchange Rate: $2529.79"
            ],
            comments=["Suspicious outbound-only pattern",
                      "Linked to known scam addresses"]
        )

        # Add the sample wallets to the database
        db.add(low_risk_wallet)
        db.add(high_risk_wallet)
        db.commit()

        print("Sample data inserted successfully!")

    except Exception as e:
        db.rollback()
        print(f"Error inserting sample data: {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    insert_sample_data()
