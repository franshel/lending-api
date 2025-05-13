# Wallet Analysis API

A FastAPI application for analyzing blockchain wallet activities and storing the results in a PostgreSQL database.

## Features

-   Store wallet analysis data in PostgreSQL using JSONB for flexible schema
-   Use Alembic for database migrations
-   Analyze wallet transactions for fraud risk
-   RESTful API for retrieving wallet analysis data
-   Docker support for easy deployment

## Setup

### Prerequisites

-   Python 3.8+
-   PostgreSQL
-   Docker and Docker Compose (optional)

### Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/yourusername/lending-api.git
    cd lending-api
    ```

2. Create a virtual environment and install dependencies:

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

3. Create a `.env` file:
    ```bash
    cp .env.example .env
    ```
4. Add your Gemini API key to the `.env` file.

### Database Setup

1. Initialize the database:

    ```bash
    python init_db.py
    ```

2. Set up Alembic migrations:
    ```bash
    python setup_alembic.py
    ```

## Running the Application

### Local Development

1. Start the application:

    ```bash
    python run.py
    ```

2. Access the API at `http://127.0.0.1:8000`

### Docker Deployment

1. Build and start the containers:

    ```bash
    docker-compose up -d
    ```

2. Access the API at `http://localhost:8000`

## API Endpoints

-   `GET /` - API health check
-   `POST /analyze/{wallet_address}` - Analyze a wallet and store the results
-   `GET /wallets/{wallet_address}` - Get analysis for a specific wallet
-   `GET /wallets` - List all analyzed wallets with filtering options
-   `DELETE /wallets/{wallet_address}` - Delete analysis for a specific wallet

## Database Schema

The application uses a PostgreSQL database with a single table `wallet_analyses`:

-   `id`: Primary key
-   `wallet_address`: Unique wallet address
-   `network`: Blockchain network
-   `analysis_timestamp`: When the analysis was performed
-   `final_score`: Risk score (higher = safer)
-   `risk_level`: Risk level category
-   `metadata`: JSONB with wallet metadata
-   `scoring_breakdown`: JSONB with scoring details
-   `behavioral_patterns`: JSONB with behavioral analysis
-   `transactions`: JSONB with transaction data (optional)
-   `token_holdings`: JSONB with token holdings (optional)
-   `comments`: JSONB with additional comments (optional)
-   `created_at`: Record creation timestamp
-   `updated_at`: Record update timestamp
