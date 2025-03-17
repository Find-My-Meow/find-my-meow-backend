import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class Settings:
    """App configuration from environment variables."""

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME")

    # AWS
    AWS_S3_BUCKET_NAME: str = os.getenv("AWS_S3_BUCKET_NAME")
    AWS_REGION: str = os.getenv("AWS_REGION")
    AWS_ACCESS_KEY: str = os.getenv("AWS_ACCESS_KEY")
    AWS_SECRET_KEY: str = os.getenv("AWS_SECRET_KEY")

    # Backend URL
    BACKEND_URL: str = os.getenv("BACKEND_URL")

    # Frontend URL
    FRONTEND_URL: str = os.getenv("FRONTEND_URL")


# Create an instance of Settings to use in other files
settings = Settings()
