import os
import asyncio
import json
import time
import requests
from pprint import pprint
from datetime import datetime, timedelta
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
from eth_account.signers.local import LocalAccount

# Define the API base URL
API_BASE_URL = "https://api.dingdong.loans"

# Set up Web3 connection (just for signing, we don't need a working provider)
w3 = Web3()


class Web3WalletSimulator:
    """
    Simulates an Ethereum wallet for testing the authentication system
    """

    def __init__(self, private_key=None):
        """
        Initialize with a private key or generate a new one
        """
        if private_key:
            self.account = Account.from_key(private_key)
        else:
            # Generate a new random account
            self.account = Account.create()

        self.address = self.account.address
        self.private_key = self.account.key.hex()
        self.auth_token = None

    def sign_message(self, message: str) -> str:
        """
        Sign a message with the private key

        Args:
            message: The message to sign

        Returns:
            Signature as a hex string
        """
        message_encoded = encode_defunct(text=message)
        signed_message = w3.eth.account.sign_message(
            message_encoded, private_key=self.private_key
        )
        return signed_message.signature.hex()

    def authenticate(self) -> bool:
        """
        Authenticate with the API using web3 wallet

        Returns:
            True if authentication is successful, False otherwise
        """
        try:
            # Step 1: Request a message to sign
            response = requests.post(
                f"{API_BASE_URL}/auth/request-message",
                json={"wallet_address": self.address}
            )
            print("\nRequest message response:")
            print(f"Status: {response.status_code}")
            print("Response data:", json.dumps(response.json(), indent=2))
            response.raise_for_status()

            message_data = response.json()
            message = message_data["message"]
            print(f"✓ Received auth message: {message}")

            # Step 2: Sign the message
            signature = self.sign_message(message)
            print(f"✓ Generated signature for wallet {self.address}")

            # Step 3: Send the signed message for verification
            response = requests.post(
                f"{API_BASE_URL}/auth/verify",
                json={
                    "wallet_address": self.address,
                    "message": message,
                    "signature": signature
                }
            )
            print("\nVerification response:")
            print(f"Status: {response.status_code}")
            print("Response data:", json.dumps(response.json(), indent=2))
            response.raise_for_status()

            auth_data = response.json()
            self.auth_token = auth_data["access_token"]
            print(f"✓ Authentication successful! Token received.")
            return True

        except Exception as e:
            print(f"× Authentication failed: {str(e)}")
            if hasattr(e, 'response'):
                print(f"Status: {e.response.status_code}")
                try:
                    error_data = e.response.json()
                    print("Error response:", json.dumps(error_data, indent=2))
                except:
                    print("Raw response:", e.response.text)
            return False

    def get_auth_headers(self) -> dict:
        """
        Get the authorization headers for API requests

        Returns:
            Headers dict with Authorization token
        """
        if not self.auth_token:
            raise ValueError("Not authenticated. Call authenticate() first.")
        return {"Authorization": f"Bearer {self.auth_token}"}

    def create_business_proposal(self) -> dict:
        """
        Create a sample business proposal

        Returns:
            Created proposal data or None if failed
        """
        try:
            proposal_data = {
                "company_name": f"Test Company {int(time.time())}",
                "accepted_token": "ETH",
                "total_pooled": "100",
                "short_description": "A test proposal created by script",
                "full_description": "This is a test proposal created by the web3 integration test script.",
                "business_plan": "Our business plan is to test the API integration.",
                "expected_return": "10%",
                "duration": "12 months",
                "minimum_investment": "1",
                "maximum_investment": "10",
                "deadline": (datetime.now() + timedelta(days=30)).isoformat(),
                "target_funding": "1000",
                "website": "https://example.com",
                "social_media": {
                    "twitter": "https://twitter.com/example",
                    "linkedin": "https://linkedin.com/company/example"
                },
                "tags": ["test", "integration"],
                "documents": [
                    {
                        "title": "Test Document",
                        "type": "pdf",
                        "url": "https://example.com/test.pdf",
                        "size": "1MB"
                    }
                ]
            }

            response = requests.post(
                f"{API_BASE_URL}/proposals/",
                json=proposal_data,
                headers=self.get_auth_headers()
            )
            response.raise_for_status()

            proposal = response.json()
            print(
                f"✓ Proposal created successfully with ID: {proposal.get('id')}")
            return proposal

        except Exception as e:
            print(f"× Failed to create proposal: {str(e)}")
            if hasattr(e, 'response') and e.response:
                print(f"× Response: {e.response.text}")
            return None

    def get_my_proposals(self) -> list:
        """
        Get all proposals created by this wallet

        Returns:
            List of proposals or empty list if failed
        """
        try:
            response = requests.get(
                f"{API_BASE_URL}/proposals/me",
                headers=self.get_auth_headers()
            )
            response.raise_for_status()

            proposals_data = response.json()
            print(f"✓ Retrieved {proposals_data.get('total', 0)} proposals")
            return proposals_data.get("proposals", [])

        except Exception as e:
            print(f"× Failed to get proposals: {str(e)}")
            if hasattr(e, 'response') and e.response:
                print(f"× Response: {e.response.text}")
            return []

    def verify_wallet_analysis(self) -> dict:
        """
        Check if wallet analysis was created

        Returns:
            Wallet analysis data or None if failed
        """
        try:
            response = requests.get(
                f"{API_BASE_URL}/wallets/{self.address}",
                headers=self.get_auth_headers()
            )
            response.raise_for_status()

            analysis = response.json()
            print(
                f"✓ Wallet analysis found with risk level: {analysis.get('risk_level')}")
            return analysis

        except Exception as e:
            print(f"× Failed to get wallet analysis: {str(e)}")
            if hasattr(e, 'response') and e.response:
                print(f"× Response: {e.response.text}")
            return None

    def update_wallet_profile(self) -> dict:
        """
        Update wallet profile with required fields to allow proposal creation.

        Returns:
            Updated profile data or None if failed
        """
        try:
            profile_data = {
                "display_name": f"Test User {int(time.time())}",
                "email": f"testuser{int(time.time())}@example.com",
                "company_name": f"Test Company {int(time.time())}",
                "company_position": "CEO",
                "company_website": "https://example.com",
                "company_description": "A test company for API integration testing"
            }

            response = requests.put(
                f"{API_BASE_URL}/profiles/me",
                json=profile_data,
                headers=self.get_auth_headers()
            )
            response.raise_for_status()

            profile = response.json()
            print(f"✓ Profile updated successfully for {self.address}")
            return profile

        except Exception as e:
            print(f"× Failed to update profile: {str(e)}")
            # if hasattr(e, 'response') and e.response:
            print(f"× Response: {e.response.text}")
            return None


def save_wallet_info(wallet: Web3WalletSimulator, filename="test_wallet.json"):
    """Save wallet information to a JSON file for future use"""
    wallet_info = {
        "address": wallet.address,
        "private_key": wallet.private_key
    }
    with open(filename, "w") as f:
        json.dump(wallet_info, f, indent=2)
    print(f"Wallet information saved to {filename}")


def load_wallet_info(filename="test_wallet.json") -> dict:
    """Load wallet information from a JSON file"""
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def run_tests(generate_new=False):
    """
    Run the full test flow

    Args:
        generate_new (bool): If True, generates a new wallet regardless of existing one
    """
    wallet_info = None if generate_new else load_wallet_info()

    # create new wallet every new test.
    # if wallet_info:
    #     print(f"Loading existing wallet: {wallet_info['address']}")
    #     wallet = Web3WalletSimulator(private_key=wallet_info['private_key'])
    # else:
    print("Creating new test wallet...")
    wallet = Web3WalletSimulator()
    save_wallet_info(wallet)

    print(f"\n=== Test Wallet ===")
    print(f"Address: {wallet.address}")
    print(
        f"Private Key: {wallet.private_key[:10]}...{wallet.private_key[-5:]}")

    print("\n=== Testing Authentication Flow ===")
    if not wallet.authenticate():
        return

    print("\n=== Testing Proposal Creation (Expected to Fail) ===")
    proposal = wallet.create_business_proposal()
    if proposal:
        print("× Proposal creation should have failed without a complete profile")
    else:
        print("✓ Proposal creation failed as expected due to incomplete profile")

    print("\n=== Testing Profile Update ===")
    profile = wallet.update_wallet_profile()
    if not profile:
        return

    print("\n=== Testing Proposal Creation (Should Succeed) ===")
    proposal = wallet.create_business_proposal()
    if not proposal:
        print("× Failed to create the first proposal")
        return

    print("\n=== Testing Single-Proposal Constraint ===")
    second_proposal = wallet.create_business_proposal()
    if not second_proposal:
        print("✓ Only one proposal allowed per wallet user")
    else:
        print("× Constraint violated: second proposal was created")

    print("\n=== Testing Proposal Retrieval ===")
    time.sleep(2)  # Give the server a moment to process
    proposals = wallet.get_my_proposals()

    print("\n=== Testing Wallet Analysis ===")
    time.sleep(2)
    analysis = wallet.verify_wallet_analysis()
    if analysis:
        print(f"\n=== Wallet Analysis Summary ===")
        print(f"Risk Level: {analysis.get('risk_level')}")
        print(f"Score: {analysis.get('final_score')}")

    print("\n=== Test Complete ===")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run Web3 integration tests")
    parser.add_argument("--new-wallet", action="store_true",
                        help="Generate a new wallet for testing regardless of existing one")
    args = parser.parse_args()

    run_tests(generate_new=args.new_wallet)
