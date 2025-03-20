import boto3
from core.config import settings


# Initialize S3 client
s3_client = boto3.client(
    service_name='s3',
    region_name=settings.AWS_REGION,
    aws_access_key_id=settings.AWS_ACCESS_KEY,
    aws_secret_access_key=settings.AWS_SECRET_KEY
)
