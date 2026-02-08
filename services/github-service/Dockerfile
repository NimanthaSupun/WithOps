FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY services/github-service/requirements.txt ./

# Copy shared library
COPY shared/withops-common /tmp/withops-common

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir /tmp/withops-common

# Copy service code
COPY services/github-service/ .

# Copy private keys from backend (shared location)
RUN mkdir -p /app/config/keys
COPY backend/config/keys/*.pem /app/config/keys/

# Set proper permissions for private keys
RUN chmod 600 /app/config/keys/*.pem

# Note: GITHUB_PRIVATE_KEY_PATH is set via environment variable in K8s
# Local: /app/config/keys/withops-devsecops-platform-local.2026-01-22.private-key.pem
# Production: /app/config/keys/withops-devsecops-platform-production.private-key.pem

# Expose port
EXPOSE 8002

# Run the service
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
