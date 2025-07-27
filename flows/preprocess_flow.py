"""
Prefect flow for data preprocessing and uploading to S3.
"""

import os
from pathlib import Path
from prefect import flow, task
from dotenv import load_dotenv

# Import our custom modules
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.utils import ensure_bucket_exists, upload_file_to_s3

load_dotenv()


@task
def create_s3_bucket():
    """Create S3 bucket if it doesn't exist."""
    bucket_name = os.getenv('S3_BUCKET_NAME', 'volatility-news-data')
    ensure_bucket_exists(bucket_name)
    return bucket_name


@task
def upload_processed_data(bucket_name: str):
    """Upload processed data files to S3."""
    
    # Define data directory
    data_dir = Path(__file__).parent.parent / "data"
    processed_dir = data_dir / "processed"
    raw_dir = data_dir / "raw"
    
    files_to_upload = [
        # Processed files
        (processed_dir / "train_tall.parquet", "processed/train_tall.parquet"),
        (processed_dir / "val_tall.parquet", "processed/val_tall.parquet"),
        (processed_dir / "test_tall.parquet", "processed/test_tall.parquet"),
        (processed_dir / "volatility_tall_dataset.parquet", "processed/volatility_tall_dataset.parquet"),
        
        # Raw file for reference
        (raw_dir / "Combined_News_DJIA.csv", "raw/Combined_News_DJIA.csv")
    ]
    
    uploaded_files = []
    for local_path, s3_key in files_to_upload:
        if local_path.exists():
            upload_file_to_s3(str(local_path), bucket_name, s3_key)
            uploaded_files.append(s3_key)
        else:
            print(f"Warning: File {local_path} not found, skipping...")
    
    return uploaded_files


@task
def verify_upload(bucket_name: str, uploaded_files: list):
    """Verify that files were uploaded successfully."""
    from src.utils import get_s3_client
    
    s3_client = get_s3_client()
    
    for s3_key in uploaded_files:
        try:
            response = s3_client.head_object(Bucket=bucket_name, Key=s3_key)
            size = response['ContentLength']
            print(f"✅ {s3_key}: {size:,} bytes")
        except Exception as e:
            print(f"❌ {s3_key}: {e}")
    
    print(f"\n📊 Summary: {len(uploaded_files)} files uploaded to s3://{bucket_name}/")


@flow(name="preprocess-flow")
def preprocess_flow():
    """
    Main preprocessing flow that:
    1. Creates S3 bucket
    2. Uploads processed data files to S3
    3. Verifies successful upload
    """
    
    print("🚀 Starting data preprocessing flow...")
    
    # Create bucket
    bucket_name = create_s3_bucket()
    
    # Upload data files
    uploaded_files = upload_processed_data(bucket_name)
    
    # Verify upload
    verify_upload(bucket_name, uploaded_files)
    
    print("✅ Preprocessing flow completed successfully!")
    return {
        "bucket_name": bucket_name,
        "uploaded_files": uploaded_files
    }


if __name__ == "__main__":
    # Run the flow locally for testing
    preprocess_flow()
