from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import lifespan
from routes.posts import post_router
from routes.search import search_router
from dotenv import load_dotenv
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services.emailService import send_daily_email_notifications
from apscheduler.triggers.cron import CronTrigger

# Load environment variables from .env file
load_dotenv()

# Fetch the frontend URL from environment variables
frontend_url = os.getenv("FRONTEND_URL")

# Initialize the scheduler
scheduler = AsyncIOScheduler()

# Function to add the email notification job at 12:00 PM every day
def start_scheduler():
    scheduler.add_job(
        send_daily_email_notifications,
        CronTrigger(hour=12, minute=0, second=0, timezone="Asia/Bangkok"),  # Your timezone
        id='send_daily_email_notifications',
        name='Send daily email notifications at 12:00 PM',
        replace_existing=True
    )
    scheduler.start()

# Lifespan event handler
async def lifespan(app: FastAPI):
    # Start the scheduler when the app starts
    start_scheduler()

    # Yield to allow the app to handle requests
    yield

    # Optional: Any shutdown logic you want to run when the app is stopping (e.g., stopping the scheduler)
    print("Shutting down scheduler.")
    scheduler.shutdown()

# Create FastAPI app with lifespan handler
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(post_router, prefix="/api/v1/posts", tags=["Posts"])
app.include_router(search_router, prefix="/api/v1/search", tags=["Search"])

@app.get("/")
async def root():
    return {"message": "Welcome to FindMyMeow API"}
