# Dockerfile

# 1. Choose a base Python image
# Using slim variant for smaller size. Adjust Python version if needed (e.g., 3.10, 3.12)
FROM python:3.11-slim

# 2. Set environment variables
# Prevents Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1
# Define the *expected* path for GCP credentials inside the container.
# This file will be mounted as a volume during `docker run`.
#ENV GOOGLE_APPLICATION_CREDENTIALS=/app/gcp_credentials.json
# Add other non-secret environment variables needed at build time if any.
# Secrets and runtime configs (like DB URL) should be passed during `docker run`.

# 3. Set working directory
WORKDIR /app

# 4. Install dependencies
# Copy only requirements first to leverage Docker cache
COPY requirements.txt .
# Upgrade pip and install requirements without cache
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 5. Copy application code
# Copy the entire backend directory into the container's /app/backend
COPY ./backend /app/backend

# 6. Expose the port the app runs on
EXPOSE 8080

# 7. Define the command to run the application
# Use uvicorn directly for production. Adjust workers if needed for performance.
# Use 0.0.0.0 to listen on all available network interfaces inside the container.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
