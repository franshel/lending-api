from web3 import Web3
import json
import asyncio
from functools import partial
from fastapi import BackgroundTasks
from pathlib import Path

# Configuration constants
RPC_URL = "https://rpc.sepolia-api.lisk.com"
CONTRACT_ADDRESS = "0x1C5025C66FC6d8F36f48cac97Ea5120A61ba8EA5"
CONFIG_PATH = Path(__file__).parent.parent / 'configs' / 'owner_wallet.json'

# Minimal ABI for the contract
LENDING_ABI = json.loads("""[
    {
        "constant": true,
        "inputs": [],
        "name": "getCollateralTokens",
        "outputs": [{"name": "", "type": "address[]"}],
        "payable": false,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": false,
        "inputs": [
            {"name": "_user", "type": "address"},
            {"name": "_token", "type": "address"}
        ],
        "name": "liquidate",
        "outputs": [],
        "payable": false,
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "anonymous": false,
        "inputs": [
            {"indexed": true, "name": "user", "type": "address"},
            {"indexed": false, "name": "amount", "type": "uint256"},
            {"indexed": false, "name": "totalDebt", "type": "uint256"}
        ],
        "name": "Borrowed",
        "type": "event"
    }
]""")


async def load_wallet_config() -> dict:
    """Load wallet configuration"""
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load wallet config: {e}")
        raise


def get_active_loan_users(web3: Web3, contract) -> list:
    """Get list of users with active loans"""
    try:
        event_signature_hash = web3.keccak(
            text="Borrowed(address,uint256,uint256)")
        logs = web3.eth.get_logs({
            "fromBlock": 0,
            "toBlock": "latest",
            "address": Web3.to_checksum_address(CONTRACT_ADDRESS),
            "topics": [event_signature_hash]
        })

        users = set()
        for log in logs:
            decoded = contract.events.Borrowed().process_log(log)
            users.add(Web3.to_checksum_address(decoded["args"]["user"]))

        print(f"Found {len(users)} users with active loans")
        return list(users)
    except Exception as e:
        print(f"Error fetching active loans: {str(e)}")
        return []


def perform_liquidation(web3: Web3, contract, user: str, token: str, account_address: str, private_key: str) -> bool:
    """Execute liquidation for a single user and token"""
    try:
        # Estimate gas with safety margin
        estimated_gas = contract.functions.liquidate(user, token).estimate_gas({
            "from": account_address
        })
        gas_limit = int(estimated_gas * 1.1)        # Build transaction
        nonce = web3.eth.get_transaction_count(
            Web3.to_checksum_address(account_address))
        txn = contract.functions.liquidate(user, token).build_transaction({
            "from": account_address,
            "nonce": nonce,
            "gas": gas_limit,
            "gasPrice": web3.to_wei('20', 'gwei')
        })

        # Sign and send transaction
        signed_txn = web3.eth.account.sign_transaction(
            txn, private_key=private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        print(
            f"Liquidation success for user {user}. TX hash: {receipt['transactionHash'].hex()}")
        return True

    except Exception as e:
        print(f"Liquidation failed for user {user}: {str(e)}")
        return False


async def liquidate_task():
    """Main liquidation task"""
    try:
        # Load configuration
        wallets = await load_wallet_config()
        private_key = wallets[0].get('private_key')
        if not private_key:
            raise ValueError("Private key not found in wallet config")

        # Initialize Web3
        web3 = Web3(Web3.HTTPProvider(RPC_URL))
        contract = web3.eth.contract(
            address=Web3.to_checksum_address(CONTRACT_ADDRESS),
            abi=LENDING_ABI
        )

        account = web3.eth.account.from_key(private_key)
        account_address = Web3.to_checksum_address(account.address)

        # Run Web3 operations in thread pool
        loop = asyncio.get_event_loop()

        # Get collateral tokens
        collaterals = await loop.run_in_executor(
            None,
            contract.functions.getCollateralTokens().call
        )
        print(f"Checking {len(collaterals)} collateral tokens")

        # Get active users
        users = await loop.run_in_executor(
            None,
            partial(get_active_loan_users, web3, contract)
        )

        # Try liquidation for each user and token
        for user in users:
            for token in collaterals:
                await loop.run_in_executor(
                    None,
                    partial(perform_liquidation,
                            web3,
                            contract,
                            Web3.to_checksum_address(user),
                            Web3.to_checksum_address(token),
                            account_address,
                            private_key)
                )

    except Exception as e:
        print(f"Liquidation task error: {str(e)}")


def schedule_liquidation(background_tasks: BackgroundTasks):
    """Schedule a liquidation check"""
    background_tasks.add_task(liquidate_task)
    return {"status": "Liquidation check scheduled"}


async def start_periodic_liquidations(interval_seconds: int = 300):
    """Start periodic liquidation checks"""
    while True:
        await liquidate_task()
        await asyncio.sleep(interval_seconds)


# For manual testing
if __name__ == "__main__":
    async def test_liquidation():
        await liquidate_task()

    asyncio.run(test_liquidation())
