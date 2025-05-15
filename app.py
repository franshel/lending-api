# filepath: e:\git-repos\lending-api\app.py
import os
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import logging
import time

# Import routers from routes package
from routes import router as api_router

# Import database dependencies
from database.database import SessionLocal, engine, Base
import sys

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
# Enable print statements for development environment
if os.getenv('ENVIRONMENT') != 'production':
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
else:
    # Disable prints in production by redirecting stdout
    sys.stdout = open(os.devnull, 'w')

# Create FastAPI application
app = FastAPI(
    title="Lending API",
    description="API for lending platform services",
    version="1.0.0",
    docs_url="/swagger",
    redoc_url="/redocs",
    openapi_url="/api/v1/openapi.json"
)

# CORS middleware configuration
origins = [
    "http://localhost",
    "http://localhost:3000",  # For React frontend
    "http://localhost:8080",
    "*",  # Allow all origins (consider restricting in production)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database dependency


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Request timing middleware


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Health check endpoint


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "message": "Service is running"}


# Include API router
app.include_router(api_router, prefix="/api")

# Exception handler for unhandled exceptions


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )

# Startup event


@app.on_event("startup")
async def startup_event():
    logger.info("Starting up the application")
    # You can add initialization tasks here, like:
    # 1. Creating database tables if they don't exist
    # 2. Checking database connection
    # 3. Initializing background tasks

# Shutdown event


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down the application")
    # You can add cleanup tasks here
