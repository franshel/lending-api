import json
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import requests
from functools import lru_cache

from schemas.schemas import ProcessedTransaction, Transaction  # Adjusted import path

# A dictionary to store the wallet address to generated alias mapping

WALLET_ALIAS_MAP: Dict[str, str] = {}
wallet_counter = 1  # Counter for dynamically creating wallet names

# Token address to name mapping (should be expanded or fetched from external source)
TOKEN_ADDRESS_MAP: Dict[str, str] = {}


@lru_cache(maxsize=128)
def get_token_name(address: str) -> Optional[str]:
    """
    Get token name from address using the mapping or fetching from Blockscout API
    Uses local cache for better performance and to reduce API calls
    """
    # First check local mapping
    if address in TOKEN_ADDRESS_MAP:
        return TOKEN_ADDRESS_MAP[address]

    # If not found, try to fetch from API
    try:
        response = requests.get(
            f"https://sepolia-blockscout.lisk.com/api/v2/tokens/{address}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Return token name or symbol if available
            return data.get("name") or data.get("symbol")
    except Exception as e:
        print(f"Error fetching token info for {address}: {str(e)}")

    return None


def get_wallet_alias(address: str, is_contract: bool) -> str:
    """
    Return 'contract' for contracts, else assign and return a wallet alias like 'wallet-1'.
    """
    global wallet_counter
    if is_contract:
        return "contract"
    if address not in WALLET_ALIAS_MAP:
        alias = f"wallet-{wallet_counter}"
        WALLET_ALIAS_MAP[address] = alias
        wallet_counter += 1
    return WALLET_ALIAS_MAP[address]


def extract_transaction_info(tx: Transaction) -> ProcessedTransaction:
    exchange_rate = float(tx.exchange_rate or tx.historic_exchange_rate or 0)
    value_wei = int(tx.value)
    fee_wei = int(tx.fee.value) if tx.fee else 0
    gas_used = int(tx.gas_used)
    gas_limit = int(tx.gas_limit)
    gas_efficiency = round(gas_used / gas_limit, 4) if gas_limit else 0.0

    token_amount = None
    if tx.decoded_input:
        for param in tx.decoded_input.parameters:
            if param.name == "amount":
                token_amount = int(param.value)
                break

    # Handle contract creation transactions where 'to' is None
    if tx.to is None:
        # Check if we have created_contract info
        to_address = tx.created_contract.hash if tx.created_contract else ""
        to_is_contract = True  # New contracts are always contracts
        to_is_verified = tx.created_contract.is_verified if tx.created_contract else False
        to_alias = get_wallet_alias(
            to_address, True) if to_address else "created-contract"
        token_name = tx.token_name or get_token_name(
            to_address) if to_address else None
    else:
        # Regular transaction with 'to' address
        to_address = tx.to.hash
        to_is_contract = tx.to.is_contract
        to_is_verified = tx.to.is_verified or False
        to_alias = get_wallet_alias(to_address, to_is_contract)
        token_name = tx.token_name or get_token_name(to_address)

    # Get names for addresses (using alias system)
    from_alias = get_wallet_alias(tx.from_.hash, tx.from_.is_contract)

    return ProcessedTransaction(
        tx_hash=tx.hash,
        timestamp=tx.timestamp,
        block_number=tx.block_number,
        status=tx.status,
        tx_type=tx.transaction_types,
        from_address=tx.from_.hash,
        to_address=to_address,
        from_is_contract=tx.from_.is_contract,
        to_is_contract=to_is_contract,
        to_is_verified=to_is_verified,
        from_name=from_alias,
        to_name=to_alias,
        token_name=token_name,
        method=tx.method,
        token_amount=token_amount / 1000000 if token_amount else token_amount,
        value_wei=value_wei,
        value_usd=(value_wei / 1e18) * exchange_rate,
        fee_wei=fee_wei,
        fee_usd=(fee_wei / 1e18) * exchange_rate,
        gas_used=gas_used,
        gas_limit=gas_limit,
        gas_price=int(tx.gas_price),
        gas_efficiency=gas_efficiency
    )


def process_transactions(raw_data: dict) -> List[ProcessedTransaction]:
    # print("TESTING", raw_data.get("items"))
    transactions = [Transaction(**tx) for tx in raw_data.get("items", [])]
    return [extract_transaction_info(tx) for tx in transactions]


def tx_verbose_string(tx: ProcessedTransaction) -> str:
    from_alias = get_wallet_alias(tx.from_address, tx.from_is_contract)
    to_alias = get_wallet_alias(tx.to_address, tx.to_is_contract)

    from_name_str = f" ({tx.from_name})" if tx.from_name else ""
    to_name_str = f" ({tx.to_name})" if tx.to_name else ""
    token_name_str = f" ({tx.token_name})" if tx.token_name else ""

    verification_type = "Contract" if tx.to_is_contract else "Wallet"
    verification_str = f"{verification_type} Verified: {tx.to_is_verified}"

    return (
        f"TX[{tx.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] Status: {tx.status} Type: {', '.join(tx.tx_type)}\n"
        f"From: {from_alias}{from_name_str} (Contract: {tx.from_is_contract})\n"
        f"To: {to_alias}{to_name_str} (Contract: {tx.to_is_contract}, {verification_str})\n"
        f"Method: {tx.method or 'N/A'} TokenAmount: {tx.token_amount if tx.token_amount is not None else 'N/A'}{token_name_str}"
    )


def get_tx_data(wallet_address: str) -> List[ProcessedTransaction]:
    """
    Get transaction summary for a wallet address.
    Returns an empty list if no transactions found.
    """
    WALLET_ALIAS_MAP[wallet_address] = wallet_address
    url = f"https://sepolia-blockscout.lisk.com/api/v2/addresses/{wallet_address}/transactions"

    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            print(f"Failed to fetch transactions: {response.status_code}")
            return []

        data = response.json()
        # print(data)
        if "items" not in data:
            print(
                f"Invalid response format: 'items' key not found for {wallet_address}")
            return []

        if not data["items"]:
            print(
                f"No transactions found for wallet address: {wallet_address}")
            return []

        # Process transactions
        processed = process_transactions(data)
        print(f"Processed {len(processed)} transactions for {wallet_address}")
        return processed

    except Exception as e:
        print(f"Error processing transactions for {wallet_address}: {str(e)}")
        return []

