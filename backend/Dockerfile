# Dockerfile for WithOps DevSecOps Backend (FastAPI + GitHub Integration)

# Use official Python image as base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y build-essential libffi-dev libssl-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY backend/requirements.txt ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Create keys directory and copy private keys
# These will be available for both local and production
RUN mkdir -p /app/config/keys
COPY backend/config/keys/*.pem /app/config/keys/

# Set proper permissions for private keys
RUN chmod 600 /app/config/keys/*.pem

# Expose FastAPI port (change if needed)
EXPOSE 8000

# Set environment variables for production (override in docker-compose or at runtime)
# ENV GITHUB_APP_ID=... \
#     GITHUB_APP_CLIENT_ID=... \
#     GITHUB_APP_CLIENT_SECRET=... \
#     GITHUB_PRIVATE_KEY_PATH=... \
#     GITHUB_OAUTH_CLIENT_ID=... \
#     GITHUB_OAUTH_CLIENT_SECRET=...

# Start FastAPI app (adjust if your entrypoint is different)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
