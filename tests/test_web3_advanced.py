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

# Define the API base URL
API_BASE_URL = "http://localhost:8000/api"

# Set up Web3 connection (just for signing, we don't need a working provider)
w3 = Web3()


class TestScenario:
    """Base class for test scenarios"""

    def __init__(self, name):
        self.name = name
        self.passed = None
        self.error = None

    def run(self):
        print(f"\n=== Running Test: {self.name} ===")
        start_time = time.time()

        try:
            self._execute()
            self.passed = True
            print(f"✓ PASSED: {self.name}")
        except Exception as e:
            self.passed = False
            self.error = str(e)
            print(f"× FAILED: {self.name} - {str(e)}")
            if hasattr(e, 'response') and e.response:
                print(f"× Response: {e.response.text}")
            # Don't re-raise, we want to run all tests

        duration = time.time() - start_time
        print(f"Test duration: {duration:.2f}s")
        return self.passed

    def _execute(self):
        """Implement this method in subclasses"""
        raise NotImplementedError()


class TestRunner:
    """Runs a collection of tests and reports results"""

    def __init__(self):
        self.tests = []
        self.results = {
            "passed": 0,
            "failed": 0,
            "total": 0,
            "details": []
        }

    def add_test(self, test):
        self.tests.append(test)

    def run_all(self):
        print(f"\n=== Starting Test Suite with {len(self.tests)} tests ===\n")
        start_time = time.time()

        for test in self.tests:
            result = test.run()
            self.results["total"] += 1

            if result:
                self.results["passed"] += 1
            else:
                self.results["failed"] += 1

            self.results["details"].append({
                "name": test.name,
                "passed": test.passed,
                "error": test.error
            })

        duration = time.time() - start_time

        # Print summary
        print(f"\n=== Test Suite Complete ===")
        print(f"Duration: {duration:.2f}s")
        print(f"Total Tests: {self.results['total']}")
        print(f"Passed: {self.results['passed']}")
        print(f"Failed: {self.results['failed']}")

        # Print failed tests
        if self.results["failed"] > 0:
            print("\nFailed Tests:")
            for detail in self.results["details"]:
                if not detail["passed"]:
                    print(f"- {detail['name']}: {detail['error']}")

        return self.results


class Web3Wallet:
    """
    Ethereum wallet for testing the authentication system
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
        """Sign a message with the private key"""
        message_encoded = encode_defunct(text=message)
        signed_message = w3.eth.account.sign_message(
            message_encoded, private_key=self.private_key)
        return signed_message.signature.hex()

    def get_auth_headers(self) -> dict:
        """Get the authorization headers for API requests"""
        if not self.auth_token:
            raise ValueError("Not authenticated. Call authenticate() first.")

        return {"Authorization": f"Bearer {self.auth_token}"}


# Test Scenarios

class AuthenticationTest(TestScenario):
    def __init__(self, wallet):
        super().__init__("Basic Authentication")
        self.wallet = wallet

    def _execute(self):
        # Step 1: Request a message to sign
        response = requests.post(
            f"{API_BASE_URL}/auth/request-message",
            json={"wallet_address": self.wallet.address}
        )
        response.raise_for_status()

        message_data = response.json()
        message = message_data["message"]

        # Step 2: Sign the message
        signature = self.wallet.sign_message(message)

        # Step 3: Send the signed message for verification
        response = requests.post(
            f"{API_BASE_URL}/auth/verify",
            json={
                "wallet_address": self.wallet.address,
                "message": message,
                "signature": signature
            }
        )
        response.raise_for_status()

        auth_data = response.json()
        self.wallet.auth_token = auth_data["access_token"]

        # Verify we can use the token to access protected resources
        response = requests.get(
            f"{API_BASE_URL}/auth/me",
            headers=self.wallet.get_auth_headers()
        )
        response.raise_for_status()

        user_info = response.json()
        assert user_info["wallet_address"] == self.wallet.address
        assert user_info["is_authenticated"] is True


class InvalidSignatureTest(TestScenario):
    def __init__(self, wallet):
        super().__init__("Invalid Signature Rejection")
        self.wallet = wallet

    def _execute(self):
        # Step 1: Request a message to sign
        response = requests.post(
            f"{API_BASE_URL}/auth/request-message",
            json={"wallet_address": self.wallet.address}
        )
        response.raise_for_status()

        message_data = response.json()
        message = message_data["message"]

        # Step 2: Use an invalid signature
        invalid_signature = "0x" + "1" * 130

        # Step 3: Send the invalid signed message for verification
        response = requests.post(
            f"{API_BASE_URL}/auth/verify",
            json={
                "wallet_address": self.wallet.address,
                "message": message,
                "signature": invalid_signature
            }
        )

        # This should fail with 401
        assert response.status_code == 401, f"Expected 401 but got {response.status_code}"
        assert "Invalid signature" in response.text


class ProposalCreationTest(TestScenario):
    def __init__(self, wallet):
        super().__init__("Create Business Proposal")
        self.wallet = wallet

    def _execute(self):
        # Create a sample proposal
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

        # Send the proposal to the API
        response = requests.post(
            f"{API_BASE_URL}/proposals/",
            json=proposal_data,
            headers=self.wallet.get_auth_headers()
        )
        response.raise_for_status()

        proposal = response.json()
        self.proposal_id = proposal.get("id")

        # Verify proposal was created with correct wallet address
        assert proposal.get("proposer_wallet") == self.wallet.address


class RetrieveProposalsTest(TestScenario):
    def __init__(self, wallet):
        super().__init__("Retrieve My Proposals")
        self.wallet = wallet

    def _execute(self):
        response = requests.get(
            f"{API_BASE_URL}/proposals/me",
            headers=self.wallet.get_auth_headers()
        )
        response.raise_for_status()

        proposals_data = response.json()

        # Verify we got a list of proposals
        assert "proposals" in proposals_data
        assert "total" in proposals_data
        assert proposals_data["total"] >= 0

        # Verify the wallet address is correct
        assert proposals_data["wallet_address"] == self.wallet.address


class WalletAnalysisTest(TestScenario):
    def __init__(self, wallet):
        super().__init__("Wallet Analysis Check")
        self.wallet = wallet

    def _execute(self):
        # Wait a bit for analysis to complete (might be asynchronous)
        time.sleep(2)

        response = requests.get(
            f"{API_BASE_URL}/wallets/{self.wallet.address}",
            headers=self.wallet.get_auth_headers()
        )
        response.raise_for_status()

        analysis = response.json()

        # Verify basic analysis structure
        assert "wallet_address" in analysis
        assert analysis["wallet_address"] == self.wallet.address

        # These are the minimum fields we expect
        expected_fields = ["risk_level", "final_score", "wallet_metadata"]
        for field in expected_fields:
            assert field in analysis, f"Expected field {field} missing from wallet analysis"


class UnauthorizedAccessTest(TestScenario):
    def __init__(self, wallet):
        super().__init__("Unauthorized Access Prevention")
        self.wallet = wallet

    def _execute(self):
        # Try to access a protected endpoint without authentication
        response = requests.get(f"{API_BASE_URL}/proposals/me")

        # This should fail with 401 or 403
        assert response.status_code in [
            401, 403], f"Expected 401 or 403 but got {response.status_code}"


def main():
    # Create a test wallet
    wallet = Web3Wallet()
    print(f"Test wallet address: {wallet.address}")
    print(
        f"Test wallet private key: {wallet.private_key[:6]}...{wallet.private_key[-4:]}")

    # Create test runner
    runner = TestRunner()

    # Add tests
    # First run unauthorized access test before we're authenticated
    runner.add_test(UnauthorizedAccessTest(wallet))

    # Do authentication
    auth_test = AuthenticationTest(wallet)
    runner.add_test(auth_test)
    runner.add_test(InvalidSignatureTest(wallet))

    # After authentication, check these tests
    runner.add_test(ProposalCreationTest(wallet))
    runner.add_test(RetrieveProposalsTest(wallet))
    runner.add_test(WalletAnalysisTest(wallet))

    # Run all tests
    results = runner.run_all()

    # Save test wallet info if tests passed
    if results["failed"] == 0:
        wallet_info = {
            "address": wallet.address,
            "private_key": wallet.private_key
        }

        with open("successful_test_wallet.json", "w") as f:
            json.dump(wallet_info, f, indent=2)

        print(f"\nWallet info saved to successful_test_wallet.json")


if __name__ == "__main__":
    main()
