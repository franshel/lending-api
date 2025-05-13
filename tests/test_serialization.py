from datetime import datetime, timedelta
import json
from schemas.schemas import FraudRiskAnalysis, WalletMetadata, BehavioralPatterns, ContractUsage, ScoringBreakdown
from utils.utils import json_serial, serialize_pydantic_model


def test_serialization():
    """Test JSON serialization of Pydantic models with datetime objects"""

    # Create sample data with datetime objects
    current_time = datetime.now()
    # Create a test FraudRiskAnalysis object
    analysis = FraudRiskAnalysis(
        wallet_address="0x123456789abcdef",
        network="Lisk",
        analysis_timestamp=current_time,
        final_score=75.5,
        risk_level="Medium",        wallet_metadata=WalletMetadata(
            first_seen=current_time - timedelta(days=30),
            last_seen=current_time,
            age_days=30,
            total_transactions=50,
            inbound_count=20,
            outbound_count=30,
            unique_tokens_used=5,
            unique_contracts_interacted=10,
            uses_only_transfers=False,
            all_contracts_verified=True,
            funded_by_established_wallet=True,
            linked_to_flagged_entity=False
        ),
        scoring_breakdown=[
            ScoringBreakdown(
                criteria="Age",
                score_delta=10.0,
                reason="Wallet is more than 7 days old"
            ),
            ScoringBreakdown(
                criteria="Transaction Pattern",
                score_delta=15.0,
                reason="Wallet has both inbound and outbound transactions"
            )
        ],
        behavioral_patterns=BehavioralPatterns(
            outbound_only=False,
            transaction_anomalies=["None detected"],
            contract_usage=ContractUsage(
                single_contract_usage=False,
                unverified_contract_usage=False
            )
        ),
        comments=["Normal usage pattern", "Multiple tokens used"]
    )

    print("=== Testing serialization of Pydantic model with datetime objects ===")

    try:
        # Try standard JSON serialization (should fail)
        json_str = json.dumps(analysis.dict())
        print("Standard JSON serialization succeeded (unexpected!)")
    except TypeError as e:
        print(f"Standard JSON serialization failed as expected: {str(e)}")

    try:
        # Try with our custom serializer
        serialized = serialize_pydantic_model(analysis)
        json_str = json.dumps(serialized)
        print("Custom serialization succeeded!")
        print(f"JSON output: {json_str[:200]}...")  # Print first 200 chars
    except Exception as e:
        print(f"Custom serialization failed: {str(e)}")

    # Test serialization of a list of models
    try:
        model_list = [analysis, analysis]
        serialized_list = [serialize_pydantic_model(
            item) for item in model_list]
        json_list_str = json.dumps(serialized_list)
        print("List serialization succeeded!")
    except Exception as e:
        print(f"List serialization failed: {str(e)}")

    print("=== Serialization test completed ===")


if __name__ == "__main__":
    test_serialization()
