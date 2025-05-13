import uvicorn
from app import app
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

if __name__ == "__main__":    # Get host and port from environment variables or use defaults
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 8001))  # Changed to port 8001
    print(f"Starting Wallet Analysis API server at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, reload=False)
