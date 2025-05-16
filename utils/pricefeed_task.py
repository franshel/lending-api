from web3 import Web3
import json
import asyncio
import httpx
from functools import partial
from fastapi import BackgroundTasks
from pathlib import Path

# Configuration constants
RPC_URL = "https://rpc.sepolia-api.lisk.com"
EXCHANGE_API_URL = "https://open.er-api.com/v6/latest/USD"
CONTRACT_ADDRESS = "0x14Fa23DEf3832dD489F08D7ad618928b3B237Cb8"
CONFIG_PATH = Path(__file__).parent.parent / 'configs' / 'owner_wallet.json'

# Minimal ABI for the contract
LENDING_ABI = json.loads("""[
    {
        "inputs": [
            {
                "internalType": "int256",
                "name": "_answer",
                "type": "int256"
            }
        ],
        "name": "updateAnswer",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]""")


async def load_wallet_config() -> dict:
    """Load wallet configuration asynchronously"""
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load wallet config: {e}")
        raise


async def get_usd_to_idr() -> int | None:
    """Fetch USD to IDR exchange rate asynchronously"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(EXCHANGE_API_URL, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            rate = data.get("rates", {}).get("IDR")

            if rate is None:
                raise ValueError("IDR rate not found in response")

            idrtousd = int(1e8 * (1 / rate))
            print(f"IDR/USD rate: {idrtousd}")
            return idrtousd
        except Exception as e:
            print(f"Error fetching rate: {str(e)}")
            return None


def update_blockchain_price(rate: int, private_key: str) -> bool:
    """Handle synchronous blockchain operations in a separate thread"""
    try:
        # Initialize Web3 and contract
        web3 = Web3(Web3.HTTPProvider(RPC_URL))
        contract = web3.eth.contract(
            address=Web3.to_checksum_address(CONTRACT_ADDRESS),
            abi=LENDING_ABI
        )

        # Get account address from private key
        account = web3.eth.account.from_key(private_key)
        account_address = Web3.to_checksum_address(account.address)

        # Build transaction
        nonce = web3.eth.get_transaction_count(account_address)

        # Estimate gas with safety margin
        estimated_gas = contract.functions.updateAnswer(rate).estimate_gas({
            'from': account_address
        })
        gas_limit = int(estimated_gas * 1.1)  # Add 10% buffer

        # Prepare transaction
        tx = contract.functions.updateAnswer(rate).build_transaction({
            'from': account_address,
            'nonce': nonce,
            'gas': gas_limit,
            'gasPrice': web3.eth.gas_price
        })

        # Sign and send transaction
        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

        # Wait for transaction receipt
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        print(
            f"Price update success. TX hash: {receipt['transactionHash'].hex()}")
        return True

    except Exception as e:
        print(f"Price update failed: {str(e)}")
        return False


async def update_price_task():
    """Main price update task that runs as a background task"""
    try:
        # Load configuration
        wallets = await load_wallet_config()
        private_key = wallets[0].get('private_key')
        if not private_key:
            raise ValueError("Private key not found in wallet config")

        # Get latest rate
        rate = await get_usd_to_idr()
        if not rate:
            print("Failed to get USD/IDR rate")
            return

        # Run blockchain operations in a thread pool
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            partial(update_blockchain_price, rate, private_key)
        )

    except Exception as e:
        print(f"Error in update_price task: {str(e)}")


# FastAPI integration functions
def schedule_price_updates(background_tasks: BackgroundTasks):
    """Schedule a single price update as a background task"""
    background_tasks.add_task(update_price_task)
    return {"status": "Price update scheduled"}


async def start_periodic_updates(interval_seconds: int = 3600):
    """Start periodic price updates - can be called from FastAPI on_startup"""
    while True:
        await update_price_task()
        await asyncio.sleep(interval_seconds)  # Default: 1 hour


# For manual testing
if __name__ == "__main__":
    async def test_price_update():
        await update_price_task()

    asyncio.run(test_price_update())
