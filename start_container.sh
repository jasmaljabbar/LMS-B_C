#!/bin/bash -x
DB_IP=localhost
docker run -d \
  --restart unless-stopped \
  -p 8080:8080 \
  -v /home/rajan/.config/gcloud/application_default_credentials.json:/app/gcp_credentials.json:ro \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/gcp_credentials.json \
  -e DATABASE_URL="mysql+pymysql://root:a@${DB_IP}/cloudnative_lms" \
  -e GCS_BUCKET_NAME="zoraai-lms-ai-staging" \
  -e JWT_EXPIRY_MINUTES="30" \
  -e PROJECT_ID="zoraai-staging" \
  -e LOCATION="us-central1" \
  -e MODEL_NAME="gemini-2.5-pro-preview-05-06" \
  -e GOOGLE_CLOUD_PROJECT="zoraai-staging" \
  -e VERTEX_AI_LOCATION="us-central1" \
  -e VERTEX_AI_MODEL="gemini-2.5-pro-preview-05-06" \
  -e SECRET_KEY="replace_with_your_actual_strong_secret_key" \
  --name lms-backend \
  rathinamtrainers/lmsai

