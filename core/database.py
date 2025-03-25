import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv
from core.config import settings


load_dotenv()


class Database:
    client: AsyncIOMotorClient = None


db = Database()
from services.email_service import run_email_every_11_AM, send_daily_email_notifications


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the database connection
    db.client = AsyncIOMotorClient(settings.DATABASE_URL)
    db.database = db.client[settings.DATABASE_NAME]
    print("MongoDB connected.")
    asyncio.create_task(run_email_every_11_AM(send_daily_email_notifications))
    print("create notification")
    yield  # run
    # Close the database connection
    db.client.close()
    print("MongoDB connection closed.")
