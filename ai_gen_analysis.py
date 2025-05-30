from utils.holdings import format_token_holding, get_token_holdings_data  # type: ignore
from utils.transactions import get_tx_data, tx_verbose_string  # type: ignore
from schemas.schemas import FraudRiskAnalysis, WalletMetadata, BehavioralPatterns, ContractUsage, ScoringBreakdown
from dotenv import load_dotenv

import base64
import os
from google import genai
from google.genai import types
from datetime import datetime, timedelta


INSTRUCTION_PROMPT = """
You are an expert at analyzing blockchain transactions on a layer-2 Ethereum-based network called Lisk. Your job is to assess the risk and legitimacy of wallet activity by examining transaction patterns, contract interactions, token usage, and funding behavior. You apply a strict scoring rubric to evaluate how closely a wallet’s behavior aligns with legitimate, natural usage versus suspicious, synthetic, or potentially fraudulent patterns.

You must:

* Rely solely on on-chain data such as transaction direction, amounts, contract verification status, timing patterns, and usage diversity.
* Assume anonymity is normal; unverified wallets are not inherently suspicious.
* Apply the scoring rubric as follows (maximum 100%, higher score = safer behavior):

  * +15% if wallet has both inbound and outbound transactions (0% if outbound only)
  * +10% if transaction amounts are consistent or logically variable (0% if arbitrary or erratic)
  * +10% if wallet interacts with multiple contracts/addresses (0% if single recipient or contract)
  * +5% if there is a ≥10-minute delay before spending after funding (0% if transfers are immediate)
  * +10% if all interacted contracts are verified (0% if unverified contracts are involved)
  * +5% if contracts are publicly known or widely used (0% if obscure or low-usage)
  * +5% if only standard methods like `transfer`, `stake`, or `swap` are used (0% for custom/obfuscated methods)
  * +10% if funded by established or active wallets (0% if funded by fresh or suspicious wallets)
  * +10% if the wallet is at least 7 days old (0% if newly created)
  * +5% if wallet uses multiple tokens (0% if only one token is involved)
  * +5% if wallet uses smart contract functions beyond transfers (0% if only transfers)
  * +10% if wallet has no known scam/mixer/flagged connections (0% if linked to flagged addresses)

Do not generate a subjective opinion. Only return the final score, the contributing deductions or additions, and a brief justification for each. The analysis must be objective, audit-friendly, and transparent. Always assume your output may be used as input to a larger fraud detection system.

"""


def generate(wallet_address, token_holdings, tx_summary):
    """
    Generate a fraud risk analysis for a wallet address using AI.

    Args:
        wallet_address (str): The wallet address to analyze
        token_holdings (list): List of token holdings
        tx_summary (list): List of transactions

    Returns:
        FraudRiskAnalysis: The generated fraud risk analysis
    """
    # Handle empty transaction data
    if not tx_summary and not token_holdings:
        # Create a default analysis for wallets with no data
        current_time = datetime.now()

        # Create a minimal FraudRiskAnalysis object

        analysis = FraudRiskAnalysis(
            wallet_address=wallet_address,
            network="Lisk",
            analysis_timestamp=current_time,
            final_score=50.0,  # Neutral score
            risk_level="Indeterminate",
            wallet_metadata=WalletMetadata(
                first_seen=current_time,
                last_seen=current_time,
                age_days=0,
                total_transactions=0,
                inbound_count=0,
                outbound_count=0,
                unique_tokens_used=0,
                unique_contracts_interacted=0,
                uses_only_transfers=False,
                all_contracts_verified=True,
                funded_by_established_wallet=False,
                linked_to_flagged_entity=False
            ),
            scoring_breakdown=[
                ScoringBreakdown(
                    criteria="Data Availability",
                    score_delta=0.0,
                    reason="No transaction or token data available for analysis"
                )
            ],
            behavioral_patterns=BehavioralPatterns(
                outbound_only=False,
                transaction_anomalies=[],
                contract_usage=ContractUsage(
                    single_contract_usage=False,
                    unverified_contract_usage=False
                )
            ),
            comments=[
                "No transaction or token holding data available for this wallet address"]
        )
        return analysis

    # Format input text for AI
    token_holdings_text = "\n".join([format_token_holding(
        holding) for holding in token_holdings]) if token_holdings else "No token holdings found"
    tx_summary_text = "\n".join([tx_verbose_string(
        tx) for tx in tx_summary]) if tx_summary else "No transactions found"

    TEXT_INPUT = f"""
Wallet Address: {wallet_address}

Here are the token holdings and transaction summaries for a wallet. Please analyze the data and provide a risk score based on the provided rubric.
Token Holdings:
{token_holdings_text}

Transaction Summary:
{tx_summary_text}
    """

    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    # model = "gemini-2.5-flash-preview-04-17"
    model = "gemini-2.0-flash"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=TEXT_INPUT),
            ],
        ),
    ]

    # thinking_config = types.ThinkingConfig(
    #     include_thoughts=True,
    # )
    generate_content_config = types.GenerateContentConfig(
        temperature=0.1,
        response_mime_type="application/json",
        response_schema=FraudRiskAnalysis,
        system_instruction=INSTRUCTION_PROMPT,
        # thinking_config=thinking_config,
    )

    print("Generating analysis")
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=generate_content_config,
    )

    # Get the parsed response
    analysis_result: FraudRiskAnalysis = response.parsed

    # Override the timestamp to ensure it's current
    analysis_result.analysis_timestamp = datetime.now()

    final_score = 0.0
    for i in analysis_result.scoring_breakdown:
        final_score += i.score_delta

    analysis_result.final_score = final_score

    # Set the network if not already set
    if not hasattr(analysis_result, 'network') or not analysis_result.network:
        analysis_result.network = "Lisk"

    with open('analysis_result.json', 'w') as f:
        f.write(analysis_result.model_dump_json(indent=2))
    return analysis_result


if __name__ == "__main__":
    wallet_address = "0xeBe5f532F357D053aAd4Ca5E95d2ac1cb308091E"
    token_holdings = get_token_holdings_data(wallet_address)
    tx_data = get_tx_data(wallet_address)
    analysis = generate(wallet_address, token_holdings, tx_data)
    # print(analysis)
