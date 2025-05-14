import sys
import os
import traceback
from datetime import datetime
import uuid
from database.database import get_db, BusinessProposal, ProposalDocument, Tag, WalletAnalysis


def insert_test_proposal():
    """Insert a test business proposal"""
    # Get database session
    db = next(get_db())

    try:
        # Check if wallet exists
        proposer_wallet = "lsk7823459abcdefghijklmnopqrstuvwxyz"
        wallet_analysis = db.query(WalletAnalysis).filter(
            WalletAnalysis.wallet_address == proposer_wallet
        ).first()

        # If wallet doesn't exist, create a placeholder wallet analysis
        if not wallet_analysis:
            print("Creating placeholder wallet analysis...")
            wallet_analysis = WalletAnalysis(
                wallet_address=proposer_wallet,
                network="LSK",
                analysis_timestamp=datetime.utcnow(),
                final_score=75.5,
                risk_level="medium",
                wallet_metadata={
                    "first_seen": datetime.utcnow().isoformat(),
                    "last_seen": datetime.utcnow().isoformat(),
                    "age_days": 365,
                    "total_transactions": 120,
                    "inbound_count": 45,
                    "outbound_count": 75,
                    "unique_tokens_used": 5,
                    "unique_contracts_interacted": 10,
                    "uses_only_transfers": False,
                    "all_contracts_verified": True,
                    "funded_by_established_wallet": True,
                    "linked_to_flagged_entity": False
                },
                scoring_breakdown=[
                    {
                        "criteria": "Wallet Age",
                        "score_delta": 15.0,
                        "reason": "Wallet has been active for over 1 year"
                    },
                    {
                        "criteria": "Transaction Volume",
                        "score_delta": 8.5,
                        "reason": "Moderate transaction volume with steady activity"
                    }
                ],
                behavioral_patterns={
                    "outbound_only": False,
                    "transaction_anomalies": [],
                    "contract_usage": {
                        "single_contract_usage": False,
                        "unverified_contract_usage": False
                    }
                }
            )
            db.add(wallet_analysis)
            db.commit()
            db.refresh(wallet_analysis)

        # Check if the proposal already exists
        existing_proposal = db.query(BusinessProposal).filter(
            BusinessProposal.id == "prop-001"
        ).first()

        if existing_proposal:
            print("Proposal 'prop-001' already exists, skipping creation.")
            return

        # Create business proposal
        print("Creating test business proposal...")
        proposal = BusinessProposal(
            id="prop-001",
            company_name="TechNova Solutions",
            logo="/placeholder.svg?height=100&width=100",
            accepted_token="BTC",
            total_pooled="5.8 BTC",
            short_description="AI-powered supply chain optimization platform for manufacturing",
            full_description="TechNova Solutions is developing an AI-powered supply chain optimization platform that helps manufacturing companies reduce costs, minimize delays, and improve efficiency. Our solution uses machine learning algorithms to analyze historical data, predict potential disruptions, and recommend optimal inventory levels and supplier selections.",
            business_plan="Our business model is based on a SaaS subscription with tiered pricing based on company size and usage. We've already secured pilot programs with three mid-sized manufacturing companies and are seeking funding to expand our development team and accelerate our go-to-market strategy.",
            expected_return="18-22% APY",
            duration="24 months",
            minimum_investment="0.1 BTC",
            maximum_investment="1.0 BTC",
            proposer_wallet=proposer_wallet,
            proposed_at=datetime.fromisoformat("2023-12-15T00:00:00"),
            deadline=datetime.fromisoformat("2023-06-30T00:00:00"),
            status="active",
            current_funding="3.2 BTC",
            target_funding="10 BTC",
            investor_count=12,
            wallet_analysis_id=wallet_analysis.id,
            website="https://technova.example.com",
            social_media={
                "twitter": "https://twitter.com/technova",
                "linkedin": "https://linkedin.com/company/technova"
            }
        )
        db.add(proposal)

        # Create documents
        documents = [
            {
                "id": "doc-001",
                "title": "Business Plan",
                "type": "pdf",
                "url": "#",
                "uploaded_at": datetime.fromisoformat("2023-12-15T00:00:00"),
                "size": "2.4 MB"
            },
            {
                "id": "doc-002",
                "title": "Financial Projections",
                "type": "spreadsheet",
                "url": "#",
                "uploaded_at": datetime.fromisoformat("2023-12-15T00:00:00"),
                "size": "1.8 MB"
            },
            {
                "id": "doc-003",
                "title": "Technical Whitepaper",
                "type": "pdf",
                "url": "#",
                "uploaded_at": datetime.fromisoformat("2023-12-16T00:00:00"),
                "size": "3.5 MB"
            },
            {
                "id": "doc-004",
                "title": "Team Credentials",
                "type": "pdf",
                "url": "#",
                "uploaded_at": datetime.fromisoformat("2023-12-17T00:00:00"),
                "size": "1.2 MB"
            }
        ]

        for doc_data in documents:
            doc = ProposalDocument(
                proposal_id="prop-001",
                **doc_data
            )
            db.add(doc)

        # Create tags
        tags = ["AI", "Supply Chain", "SaaS", "Manufacturing"]
        for tag_name in tags:
            tag = db.query(Tag).filter(Tag.name == tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                db.add(tag)

            proposal.tags.append(tag)
          # Commit the transaction
        db.commit()
        print("Test proposal created successfully!")

    except Exception as e:
        db.rollback()
        print(f"Error creating test proposal: {str(e)}")
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    insert_test_proposal()
