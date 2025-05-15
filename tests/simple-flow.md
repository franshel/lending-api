# Web3 Integration Testing Flow

## Overview
This document outlines the testing flow for the Web3 integration with our lending API, based on the test suite in `test_web3_integration.py`.

## Test Flow Sequence

1. **Wallet Setup**
   - System checks for existing test wallet in `test_wallet.json`
   - If exists: loads the wallet
   - If not: creates new wallet and saves credentials
   - Output: Ethereum address and private key (partially hidden)

2. **Authentication Process**
   - Request a message to sign from `/api/auth/request-message`
   - Sign the message using wallet's private key
   - Send signed message to `/api/auth/verify` for verification
   - Receive JWT authentication token
   - Store token for subsequent API calls

3. **Initial Proposal Creation (Expected Failure)**
   - Attempt to create a business proposal without a complete profile
   - System correctly rejects the request
   - Verifies that profile completion is enforced

4. **Profile Update**
   - Update wallet profile with required information:
     - Display name
     - Email
     - Company details
     - Position
     - Website
     - Company description
   - Profile is marked as complete

5. **Proposal Creation (Success)**
   - Create a new business proposal with:
     - Company information
     - Token details (ETH)
     - Funding requirements
     - Business plan
     - Duration and returns
     - Investment limits
     - Deadlines
     - Social media links
     - Tags and documents
   - System accepts the proposal
   - Returns proposal ID and details

6. **Verification Steps**
   - Retrieve all proposals for the authenticated wallet
   - Verify the newly created proposal is listed
   - Check wallet analysis has been performed
   - Review risk level and scoring

## Key API Endpoints Used
- `/api/auth/request-message`
- `/api/auth/verify`
- `/api/proposals/`
- `/api/proposals/me`
- `/api/wallets/{address}`
- `/api/profiles/me`

## Important Notes
- Each proposal creation triggers a fresh wallet analysis
- Profile must be complete before creating proposals
- All API calls (except authentication) require valid JWT token
- Test wallet credentials are persisted for reuse
