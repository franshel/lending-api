import requests
from datetime import datetime
import json

BASE_URL = "http://localhost:8000"


def print_json(data):
    """Print JSON data in a readable format"""
    print(json.dumps(data, indent=2, default=str))


def test_api():
    """Test the business proposals API endpoints"""
    try:
        # Test root endpoint
        response = requests.get(f"{BASE_URL}/")
        print("\n=== Root Endpoint ===")
        print_json(response.json())

        # Test creating a new proposal
        print("\n=== Creating a New Proposal ===")
        proposal_data = {
            "company_name": "Green Energy Solutions",
            "logo": "/green-energy.svg",
            "accepted_token": "ETH",
            "total_pooled": "10.5 ETH",
            "short_description": "Sustainable energy solutions for businesses",
            "full_description": "Green Energy Solutions provides renewable energy services for businesses looking to reduce their carbon footprint and energy costs.",
            "business_plan": "We provide consulting, installation, and maintenance services for solar, wind, and other renewable energy systems. Our revenue model combines upfront fees and ongoing maintenance contracts.",
            "expected_return": "15-18% APY",
            "duration": "36 months",
            "minimum_investment": "0.2 ETH",
            "maximum_investment": "2.0 ETH",
            "proposer_wallet": "0x123456789abcdef0123456789abcdef01234567",
            "deadline": "2025-12-31T23:59:59",
            "target_funding": "50 ETH",
            "website": "https://greenenergy.example.com",
            "social_media": {
                "twitter": "https://twitter.com/greenenergy",
                "linkedin": "https://linkedin.com/company/greenenergy"
            },
            "tags": ["Renewable Energy", "Sustainability", "B2B"]
        }

        response = requests.post(f"{BASE_URL}/proposals", json=proposal_data)
        if response.status_code == 201:
            print("Proposal created successfully!")
            print_json(response.json())
            proposal_id = response.json().get("id")
        else:
            print(f"Failed to create proposal: {response.status_code}")
            print(response.text)

        # Test getting all proposals
        print("\n=== Getting All Proposals ===")
        response = requests.get(f"{BASE_URL}/proposals")
        if response.status_code == 200:
            print_json(response.json())
        else:
            print(f"Failed to get proposals: {response.status_code}")
            print(response.text)

        # Test getting proposal by ID
        print("\n=== Getting Proposal by ID ===")
        response = requests.get(f"{BASE_URL}/proposals/prop-001")
        if response.status_code == 200:
            print_json(response.json())
        else:
            print(f"Failed to get proposal: {response.status_code}")
            print(response.text)

    except requests.exceptions.ConnectionError:
        print("Connection error: Make sure the API server is running")
    except Exception as e:
        print(f"Error testing API: {str(e)}")


if __name__ == "__main__":
    test_api()
