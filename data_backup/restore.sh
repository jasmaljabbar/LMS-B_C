#!/bin/bash

# Variables
DB_NAME="cloudnative_lms"
DB_USER="root"
DB_PASS="a"
BACKUP_DIR="backup"
LATEST_BACKUP=$(ls -t $BACKUP_DIR/${DB_NAME}_backup_*.sql | head -n 1)
MYSQL_PATH="/usr/bin/mysql"
GCP_BUCKET="lms-ai"
GCP_BACKUP_DIR="backup/gcp_files"

# Check if backup file exists
if [ ! -f "$LATEST_BACKUP" ]; then
    echo "No backup file found in $BACKUP_DIR!" >&2
    exit 1
fi

# Drop existing database
echo "Dropping existing database: $DB_NAME..."
$MYSQL_PATH -u$DB_USER -p$DB_PASS -e "DROP DATABASE IF EXISTS $DB_NAME;"
if [ $? -eq 0 ]; then
    echo "Database $DB_NAME dropped successfully."
else
    echo "Failed to drop database $DB_NAME!" >&2
    exit 1
fi

# Create a new database
echo "Creating new database: $DB_NAME..."
$MYSQL_PATH -u$DB_USER -p$DB_PASS -e "CREATE DATABASE $DB_NAME;"
if [ $? -eq 0 ]; then
    echo "Database $DB_NAME created successfully."
else
    echo "Failed to create database $DB_NAME!" >&2
    exit 1
fi

# Restore the latest backup
echo "Restoring database from backup: $LATEST_BACKUP..."
$MYSQL_PATH -u$DB_USER -p$DB_PASS $DB_NAME < "$LATEST_BACKUP"
if [ $? -eq 0 ]; then
    echo "Database restoration successful."
else
    echo "Database restoration failed!" >&2
    exit 1
fi

# Delete contents of GCP bucket
echo "Deleting contents of GCP bucket: $GCP_BUCKET..."
gsutil -m rm -r gs://$GCP_BUCKET/*
if [ $? -eq 0 ]; then
    echo "GCP bucket contents deleted successfully."
else
    echo "Failed to delete contents of GCP bucket!" >&2
    exit 1
fi

# Copy backup data to GCP bucket
echo "Copying backup data to GCP bucket: $GCP_BUCKET..."
gsutil -m cp -r $GCP_BACKUP_DIR/* gs://$GCP_BUCKET/
if [ $? -eq 0 ]; then
    echo "Backup data copied to GCP bucket successfully."
else
    echo "Failed to copy backup data to GCP bucket!" >&2
    exit 1
fi

echo "Database reset, restore, and GCP sync process completed successfully."