# filepath: e:\git-repos\lending-api\app.py
import os
from fastapi import FastAPI, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import logging
import time
import asyncio

# Import routers from routes package
from routes import router as api_router
from utils.pricefeed_task import start_periodic_updates, schedule_price_updates
from utils.liquidate_task import start_periodic_liquidations, schedule_liquidation

# Import database dependencies
from database.database import SessionLocal, engine, Base
import sys

# Load environment variables
load_dotenv()

# # Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Set base level to WARNING to suppress most automated logs
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
# Only show explicit logging calls
logger.setLevel(logging.INFO)

# EXTREME LOGGING
# Configure logging with more detailed settings
# logging.basicConfig(
#     level=logging.DEBUG,  # Set to DEBUG for most verbose logging
#     format='%(asctime)s [%(levelname)s] %(name)s - %(message)s - %(filename)s:%(lineno)d',
#     handlers=[
#         logging.StreamHandler(sys.stdout),
#         logging.FileHandler('app.log')
#     ]
# )

# # Create logger instance
# logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)

# # Log SQL queries
# logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
# logging.getLogger('sqlalchemy.pool').setLevel(logging.DEBUG)

# # Log FastAPI requests
# logging.getLogger("fastapi").setLevel(logging.DEBUG)
# logging.getLogger("uvicorn").setLevel(logging.INFO)
# END OF LOGGING CONFIGURATION

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
    "https://dingdong.loans"
    "http://dingdong.loans"
    # "*",  # Allow all origins (consider restricting in production)
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
app.include_router(api_router)

# Exception handler for unhandled exceptions


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )

# Store background tasks for cleanup
price_update_task = None
liquidation_task = None

# Startup event


@app.on_event("startup")
async def startup_event():
    logger.info("Starting up the application")
    # Create database tables
    Base.metadata.create_all(bind=engine)

    # Start periodic tasks with proper task naming and error handling
    global price_update_task, liquidation_task
    
    # Create the tasks with names for better debugging
    price_update_task = asyncio.create_task(
        start_periodic_updates(14400),
        name="periodic_price_updates"
    )
    
    # Add error handlers to prevent crashing
    price_update_task.add_done_callback(
        lambda t: logger.error(f"Price update task ended unexpectedly: {t.exception()}") 
        if t.exception() else None
    )
    
    liquidation_task = asyncio.create_task(
        start_periodic_liquidations(14400), 
        name="periodic_liquidations"
    )
    
    # Add error handlers to prevent crashing
    liquidation_task.add_done_callback(
        lambda t: logger.error(f"Liquidation task ended unexpectedly: {t.exception()}")
        if t.exception() else None
    )
    
    logger.info("Started periodic price updates and liquidation tasks")

# Shutdown event


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down the application")
    # Cancel the background tasks when shutting down
    for task in [price_update_task, liquidation_task]:
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    logger.info("Stopped all periodic tasks")


@app.post("/trigger-price-update/")
async def trigger_price_update(background_tasks: BackgroundTasks):
    """Manually trigger a price update"""
    return schedule_price_updates(background_tasks)


@app.post("/trigger-liquidation/")
async def trigger_liquidation(background_tasks: BackgroundTasks):
    """Manually trigger a liquidation check"""
    return schedule_liquidation(background_tasks)
