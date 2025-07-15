import os
from google.cloud import storage
from dotenv import load_dotenv
from google.oauth2 import service_account

# Load environment variables from .env file
load_dotenv()
print(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

def upload_file(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    # The ID of your GCS bucket
    # bucket_name = "your-bucket-name"
    # The path to your file to upload
    # source_file_name = "local/path/to/your/file"
    # The ID of your GCS object
    # destination_blob_name = "storage-object-name"

    #Check if the environment variable is set. This provides better error handling.
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
      raise EnvironmentError("The GOOGLE_APPLICATION_CREDENTIALS environment variable is not set.  Make sure it's loaded from your .env file.")

    credentials = service_account.Credentials.from_service_account_file("st-zora-ai-b-c-gcp.json")
   

    storage_client = storage.Client(credentials=credentials)  # Authenticates using GOOGLE_APPLICATION_CREDENTIALS
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_name)

    print(
        f"File {source_file_name} uploaded to {destination_blob_name}."
    )

def download_file(bucket_name, source_blob_name, destination_file_name):
    """Downloads a blob from the bucket."""
    # The ID of your GCS bucket
    # bucket_name = "your-bucket-name"

    # The ID of your GCS object
    # source_blob_name = "storage-object-name"

    # The path to which the file should be downloaded
    # destination_file_name = "local/path/to/your/file"

    #Check if the environment variable is set. This provides better error handling.
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
      
      raise EnvironmentError("The GOOGLE_APPLICATION_CREDENTIALS environment variable is not set. Make sure it's loaded from your .env file.")
    
   

    storage_client = storage.Client(project = "st-zora-ai-b-c") # Authenticates using GOOGLE_APPLICATION_CREDENTIALS


    bucket = storage_client.bucket(bucket_name)

    # Construct a client side representation of a blob.
    # Note Storage does not actually read the contents of this file.
    # with open(destination_file_name, "wb") as file_obj:
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)

    print(
        f"Blob {source_blob_name} downloaded to {destination_file_name}."
    )


# Example Usage:
bucket_name = "zoraai-lms-ai-b-c"  # Replace with your bucket name
local_file = "23.pdf"     # Replace with your local file
gcs_file = "pdfs/new_231.pdf" # Replace with desired GCS path
upload_file(bucket_name, local_file, gcs_file)
download_file(bucket_name, gcs_file, "0023.pdf") #Download the same file
