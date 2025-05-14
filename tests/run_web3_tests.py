import os
import sys
from test_web3_integration import run_tests

if __name__ == "__main__":
    print("=== Starting Web3 Authentication and Proposal Test ===")
    print(f"Testing against API at: http://localhost:8000/api")

    try:
        # First make sure the server is running
        import requests
        try:
            response = requests.get("http://localhost:8000/health")
            if response.status_code != 200:
                print(
                    "ERROR: API server does not appear to be running or is not healthy.")
                print(f"Response: {response.status_code} - {response.text}")
                sys.exit(1)
            print("API server is running and healthy.")
        except requests.RequestException:
            print(
                "ERROR: Could not connect to API server. Is it running at http://localhost:8000?")
            sys.exit(1)

        # Run the tests
        run_tests()

    except Exception as e:
        print(f"Error running tests: {str(e)}")
        import traceback
        print(traceback.format_exc())
        sys.exit(1)
