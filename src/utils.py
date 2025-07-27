"""Utility functions for the MLOps pipeline."""

import os
import boto3
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


def get_s3_client():
    """Get S3 client configured for LocalStack."""
    return boto3.client(
        's3',
        endpoint_url=os.getenv('S3_ENDPOINT_URL'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_DEFAULT_REGION')
    )


def ensure_bucket_exists(bucket_name: str):
    """Create S3 bucket if it doesn't exist."""
    s3_client = get_s3_client()
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"Bucket {bucket_name} already exists")
    except:
        s3_client.create_bucket(Bucket=bucket_name)
        print(f"Created bucket {bucket_name}")


def upload_file_to_s3(local_path: str, bucket: str, s3_key: str):
    """Upload file to S3."""
    s3_client = get_s3_client()
    s3_client.upload_file(local_path, bucket, s3_key)
    print(f"Uploaded {local_path} to s3://{bucket}/{s3_key}")


def download_file_from_s3(bucket: str, s3_key: str, local_path: str):
    """Download file from S3."""
    s3_client = get_s3_client()
    s3_client.download_file(bucket, s3_key, local_path)
    print(f"Downloaded s3://{bucket}/{s3_key} to {local_path}")


def read_parquet_from_s3(bucket: str, s3_key: str) -> pd.DataFrame:
    """Read parquet file directly from S3."""
    import io
    s3_client = get_s3_client()
    obj = s3_client.get_object(Bucket=bucket, Key=s3_key)
    
    # Read into memory buffer to avoid seek issues
    buffer = io.BytesIO(obj['Body'].read())
    return pd.read_parquet(buffer)


def save_parquet_to_s3(df: pd.DataFrame, bucket: str, s3_key: str):
    """Save DataFrame as parquet to S3."""
    import io
    s3_client = get_s3_client()
    
    # Save to bytes buffer
    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False)
    buffer.seek(0)
    
    # Upload to S3
    s3_client.put_object(
        Bucket=bucket,
        Key=s3_key,
        Body=buffer.getvalue()
    )
    print(f"Saved DataFrame to s3://{bucket}/{s3_key}")
