import math
from web3 import Web3
import json
import asyncio
import httpx
from functools import partial
from fastapi import BackgroundTasks
from pathlib import Path

# Configuration constants
RPC_URL = "https://rpc.sepolia-api.lisk.com"
# CONTRACT_ADDRESS = "0x14Fa23DEf3832dD489F08D7ad618928b3B237Cb8"
CONFIG_PATH = Path(__file__).parent.parent / 'configs' / 'owner_wallet.json'

# Minimal ABI for the contract
PRICEFEED_ABI = json.loads("""[
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


async def get_idr_to_usd() -> int | None:
    """Fetch USD to IDR exchange rate asynchronously"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("https://open.er-api.com/v6/latest/USD",
                                        timeout=10.0)
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


async def get_btc_to_usd() -> int | None:
    """Fetch USD to IDR exchange rate asynchronously"""
    """Fetch BTC to USD exchange rate asynchronously"""
    async with httpx.AsyncClient() as client:
        try:
            # Using CoinGecko public API
            api_url = "https://api.coinlore.net/api/ticker/?id=90"
            response = await client.get(api_url, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            # CoinGecko returns the direct price, multiply by 1e8 for fixed-point representation
            price_usd = float(data[0]["price_usd"])
            btc_price = int(math.ceil(price_usd * 10) / 10 * 1e8)
            print(f"BTC/USD rate: {btc_price}")
            return btc_price
        except Exception as e:
            print(f"Error fetching BTC rate: {str(e)}")
            return None


async def get_eth_to_usd() -> int | None:
    """Fetch ETH to USD exchange rate asynchronously"""
    async with httpx.AsyncClient() as client:
        try:
            # Using CoinGecko public API
            api_url = "https://api.coinlore.net/api/ticker/?id=80"
            response = await client.get(api_url, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            # CoinGecko returns the direct price, multiply by 1e8 for fixed-point representation
            price_usd = float(data[0]["price_usd"])
            eth_price = int(math.ceil(price_usd * 10) / 10 * 1e8)
            print(f"ETH/USD rate: {eth_price}")
            return eth_price
        except Exception as e:
            print(f"Error fetching ETH rate: {str(e)}")
            return None


async def update_blockchain_price(contract_address: str, rate: int, private_key: str) -> bool:
    """Handle blockchain operations asynchronously with better timeout handling"""
    try:
        # Initialize Web3 and contract
        web3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={'timeout': 30}))
        contract = web3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=PRICEFEED_ABI
        )

        # Get account address from private key
        account = web3.eth.account.from_key(private_key)
        account_address = Web3.to_checksum_address(account.address)

        # Build transaction with proper timeouts
        loop = asyncio.get_event_loop()
        
        # Run each web3 operation with a timeout to prevent hanging
        try:
            nonce = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: web3.eth.get_transaction_count(account_address)),
                timeout=30
            )
        except asyncio.TimeoutError:
            print(f"Timeout getting nonce for {contract_address}")
            return False

        # Estimate gas with safety margin
        try:
            estimated_gas = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: contract.functions.updateAnswer(rate).estimate_gas({
                    'from': account_address
                })),
                timeout=30
            )
            gas_limit = int(estimated_gas * 1.2)  # Add 20% buffer
        except asyncio.TimeoutError:
            print(f"Timeout estimating gas for {contract_address}")
            return False
        except Exception as e:
            print(f"Error estimating gas: {str(e)}")
            # Use a default gas limit as fallback
            gas_limit = 200000

        # Get gas price
        try:
            gas_price = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: web3.eth.gas_price),
                timeout=30
            )
        except asyncio.TimeoutError:
            print(f"Timeout getting gas price for {contract_address}")
            return False

        # Prepare transaction
        tx = contract.functions.updateAnswer(rate).build_transaction({
            'from': account_address,
            'nonce': nonce,
            'gas': gas_limit,
            'gasPrice': gas_price
        })

        # Sign and send transaction
        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        try:
            tx_hash = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: web3.eth.send_raw_transaction(signed_tx.raw_transaction)),
                timeout=30
            )
        except asyncio.TimeoutError:
            print(f"Timeout sending transaction for {contract_address}")
            return False

        # Wait for transaction receipt asynchronously with a generous but finite timeout
        try:
            receipt = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)),
                timeout=150  # Slightly longer than the internal web3 timeout
            )
            print(f"Price update success. TX hash: {receipt['transactionHash'].hex()}")
            return True
        except asyncio.TimeoutError:
            print(f"Transaction sent but confirmation timed out for {contract_address}. TX hash: {tx_hash.hex()}")
            # We return True since the transaction was sent but just not confirmed yet
            return True

    except Exception as e:
        print(f"Price update failed: {str(e)}")
        return False


async def update_price_task():
    """Main price update task that runs as a background task"""
    contract_addresses = []
    try:
        # Load configuration
        wallets = await load_wallet_config()
        private_key = wallets[0].get('private_key')
        if not private_key:
            raise ValueError("Private key not found in wallet config")

        # Get latest rates
        idr_rate = await get_idr_to_usd()
        btc_rate = await get_btc_to_usd()
        eth_rate = await get_eth_to_usd()
        usdt_rate = 100000000

        if not idr_rate or not btc_rate:
            print("Failed to get one or more exchange rates")
            return

        # Define contract addresses and corresponding rates
        contract_addresses = [
            {"symbol": "IDRX", "address": "0x14fa23def3832dd489f08d7ad618928b3b237cb8",
                "rate": idr_rate},
            {"symbol": "BTC", "address": "0xF4Dd86C807D2D14cFbc366371D852aA14fFE1661",
                "rate": btc_rate},
            {"symbol": "ETH", "address": "0x9A3C4F432B698b0026fA85bE44BD6d94426959B9",
                "rate": eth_rate},
            {"symbol": "USDT", "address": "0x900c82d4d336b036c614f55b921de25c3bdd88e4",
                "rate": usdt_rate}
        ]
        # 10665700000000

        # Run blockchain operations concurrently in thread pool
        # Execute blockchain operations one by one
        for contract in contract_addresses:
            symbol = contract["symbol"]
            address = contract["address"]
            rate = contract["rate"]

            print(f"Updating price for {symbol}...")
            success = await update_blockchain_price(address, rate, private_key)

            if success:
                print(f"Update for contract {symbol} succeeded")
            else:
                print(f"Update for contract {symbol} failed, retrying after 2 seconds...")
                # Wait for 2 seconds before retry
                await asyncio.sleep(2)
                # Retry the transaction once
                print(f"Retrying update for {symbol}...")
                success = await update_blockchain_price(address, rate, private_key)
                if success:
                    print(f"Retry for contract {symbol} succeeded")
                else:
                    print(f"Retry for contract {symbol} failed")

            # Add a short delay between transactions to avoid nonce conflicts
            await asyncio.sleep(2)

    except Exception as e:
        print(f"Error in update_price task: {str(e)}")


# FastAPI integration functions
def schedule_price_updates(background_tasks: BackgroundTasks):
    """Schedule a single price update as a background task with improved handling"""
    # Create a wrapper function that properly handles exceptions
    async def safe_update_task():
        try:
            # Set a timeout for the task
            await asyncio.wait_for(update_price_task(), timeout=300)  # 5-minute timeout
        except asyncio.TimeoutError:
            print("Manual price update timed out after 5 minutes")
        except Exception as e:
            print(f"Error in manual price update: {str(e)}")
    
    # Add the wrapped task
    background_tasks.add_task(safe_update_task)
    return {"status": "Price update scheduled"}


async def start_periodic_updates(interval_seconds: int = 3600):
    """Start periodic price updates - can be called from FastAPI on_startup"""
    while True:
        try:
            # Run the price update task with a timeout
            await asyncio.wait_for(update_price_task(), timeout=300)  # 5-minute timeout
        except asyncio.TimeoutError:
            print("Price update task timed out after 5 minutes - continuing to next cycle")
        except Exception as e:
            print(f"Error in periodic price update: {str(e)}")
        
        # Always sleep before next iteration regardless of success/failure
        await asyncio.sleep(interval_seconds)  # Default: 1 hour


# For manual testing
if __name__ == "__main__":
    async def test_price_update():
        await update_price_task()

    asyncio.run(test_price_update())
