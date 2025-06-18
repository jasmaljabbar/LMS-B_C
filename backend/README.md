### Create admin user with password "Coimbatore"

```
INSERT INTO users (username, password_hash, user_type, is_active)
    VALUES (
        'admin',
        '$2b$12$WofojNbsiCmELgmExBz0D.aLla5l3GI9BQwEXjR3FYeBmWxO1O3gO',
        'Admin',
        TRUE
    );
```


### Deploy app in Cloud Run  (Staging)
```shell
gcloud run deploy lms-backend \
  --image=$(docker inspect docker.io/rathinamtrainers/lmsai:20250609-1100 --format='{{index .RepoDigests 0}}')  \
  --region=us-central1 \
  --add-cloudsql-instances=zoraai-staging:us-central1:zora-ai-staging \
  --set-env-vars="DATABASE_URL=mysql+pymysql://root:a@/cloudnative_lms?unix_socket=/cloudsql/zoraai-staging:us-central1:zora-ai-staging" \
  --set-env-vars="GCS_BUCKET_NAME=zoraai-lms-ai-staging,JWT_EXPIRY_MINUTES=30,PROJECT_ID=zoraai-staging,LOCATION=us-central1,MODEL_NAME=gemini-2.5-pro-preview-05-06,GOOGLE_CLOUD_PROJECT=zoraai-staging,VERTEX_AI_LOCATION=us-central1,VERTEX_AI_MODEL=gemini-2.5-pro-preview-05-06,SECRET_KEY=replace_with_your_actual_strong_secret_key" \
  --service-account="zora-ai@zoraai-staging.iam.gserviceaccount.com" \
  --allow-unauthenticated

```

### Deploy app in Cloud Run  (production)

```shell
gcloud run deploy lms-backend \
  --image=$(docker inspect docker.io/rathinamtrainers/lmsai:latest --format='{{index .RepoDigests 0}}')  \
  --region=us-central1 \
  --add-cloudsql-instances=ai-powered-lms:us-central1:cloudnative-lms-instance \
  --set-env-vars="DATABASE_URL=mysql+pymysql://lms_user:Coimbatore@/cloudnative_lms?unix_socket=/cloudsql/ai-powered-lms:us-central1:cloudnative-lms-instance" \
  --set-env-vars="GCS_BUCKET_NAME=lms-ai,JWT_EXPIRY_MINUTES=30,PROJECT_ID=ai-powered-lms,LOCATION=us-central1,MODEL_NAME=gemini-2.5-pro-preview-05-06,GOOGLE_CLOUD_PROJECT=ai-powered-lms,VERTEX_AI_LOCATION=us-central1,VERTEX_AI_MODEL=gemini-2.5-pro-preview-05-06,SECRET_KEY=replace_with_your_actual_strong_secret_key" \
  --service-account="lms-ai@ai-powered-lms.iam.gserviceaccount.com" \
  --allow-unauthenticated

```
