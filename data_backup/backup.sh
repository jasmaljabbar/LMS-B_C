#!/bin/bash

# Variables
DB_NAME="cloudnative_lms"
DB_USER="root"
DB_PASS="a"
BACKUP_DIR="backup"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
MYSQLDUMP_PATH="/usr/bin/mysqldump"
GCP_BUCKET="lms-ai"
GCP_DOWNLOAD_DIR="backup/gcp_files"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"
mkdir -p "$GCP_DOWNLOAD_DIR"

# Dump MySQL database
DB_BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_backup_${TIMESTAMP}.sql"
echo "Dumping MySQL database: $DB_NAME..."
$MYSQLDUMP_PATH -u$DB_USER -p$DB_PASS $DB_NAME > "$DB_BACKUP_FILE"
if [ $? -eq 0 ]; then
    echo "Database backup successful: $DB_BACKUP_FILE"
else
    echo "Database backup failed!" >&2
    exit 1
fi

# Download files from GCP bucket
echo "Downloading files from GCP bucket: $GCP_BUCKET..."
gsutil -m cp -r gs://$GCP_BUCKET/* "$GCP_DOWNLOAD_DIR"/
if [ $? -eq 0 ]; then
    echo "Files downloaded successfully to: $GCP_DOWNLOAD_DIR"
else
    echo "Failed to download files from GCP bucket!" >&2
    exit 1
fi

echo "Backup and download process completed successfully."
