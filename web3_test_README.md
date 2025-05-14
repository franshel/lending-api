# Web3 Authentication and Proposal Testing Tools

This directory contains several scripts for testing the web3 wallet authentication and proposal systems.

## Prerequisites

-   Python 3.8+
-   The Lending API server must be running on http://localhost:8000

## Required Python packages

Install the required packages:

```bash
pip install requests web3 eth-account
```

## Test Scripts

### 1. Basic Test Script (`test_web3_integration.py`)

A simple script that tests the basic flow of authenticating with a web3 wallet and creating a proposal.

```bash
python test_web3_integration.py
```

This script will:

1. Create a new Ethereum wallet (or use a saved one)
2. Authenticate with the API
3. Create a test business proposal
4. Retrieve the user's proposals
5. Check if wallet analysis was generated

### 2. Runner Script (`run_web3_tests.py`)

A wrapper script that checks if the API server is running and then executes the basic tests.

```bash
python run_web3_tests.py
```

### 3. Advanced Test Suite (`test_web3_advanced.py`)

A more comprehensive test suite that runs a series of tests to verify different aspects of the web3 authentication and proposal system.

```bash
python test_web3_advanced.py
```

This script:

-   Tests authentication with valid and invalid signatures
-   Tests proposal creation and retrieval
-   Tests wallet analysis
-   Tests unauthorized access prevention
-   Provides detailed test reports

### 4. Interactive Demo (`interactive_web3_demo.py`)

An interactive script that allows you to manually test different aspects of the system.

```bash
# Basic interactive mode
python interactive_web3_demo.py

# Load an existing wallet
python interactive_web3_demo.py --load wallet.json

# Save the wallet after use
python interactive_web3_demo.py --save new_wallet.json

# Run a full automatic demo
python interactive_web3_demo.py --auto --save demo_wallet.json
```

Available commands in interactive mode:

-   `info` - Show wallet information
-   `auth` - Authenticate with the API
-   `status` - Check authentication status
-   `create` - Create a new proposal
-   `proposals` - List my proposals
-   `analysis` - Check wallet analysis
-   `save` - Save wallet to file
-   `quit` - Exit the program

## Notes

-   These scripts create Ethereum wallets with private keys. In a real scenario, you would connect to MetaMask or another wallet provider.
-   The private keys are generated randomly and saved locally for testing purposes.
-   If you want to reuse the same wallet, use the saved wallet JSON files.
-   The API URL is set to `http://localhost:8000/api`. Change it in the scripts if your API is running at a different address.
