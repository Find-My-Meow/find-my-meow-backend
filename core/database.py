from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv
from core.config import settings


load_dotenv()


class Database:
    client: AsyncIOMotorClient = None


db = Database()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the database connection
    db.client = AsyncIOMotorClient(settings.DATABASE_URL)
    db.database = db.client[settings.DATABASE_NAME]
    print("MongoDB connected.")
    yield  # run
    # Close the database connection
    db.client.close()
    print("MongoDB connection closed.")
