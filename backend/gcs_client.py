# backend/utils/gcs_client.py
import os
from google.cloud import storage

def get_gcs_client_and_bucket():
    if os.getenv("GCP_ENV", "false").lower() == "true":
        client = storage.Client()
        bucket_name = os.getenv("GCS_BUCKET_NAME")
        bucket = client.get_bucket(bucket_name)
        print(f"✅ Connected to GCS bucket: {bucket_name}")
        return client, bucket
    else:
        print("⚠️ Skipping GCS client and bucket initialization in local development")
        return None, None
