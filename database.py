from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv
import os


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME")


class Database:
    client: AsyncIOMotorClient = None


db = Database()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the database connection
    db.client = AsyncIOMotorClient(DATABASE_URL)
    db.database = db.client[DATABASE_NAME]
    print("MongoDB connected.")
    yield  # run
    # Close the database connection
    db.client.close()
    print("MongoDB connection closed.")
