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

# Update the private key path to use absolute path in container
ENV GITHUB_PRIVATE_KEY_PATH=/app/config/keys/withops-devsecops-platform-local.2026-01-22.private-key.pem

# Expose port
EXPOSE 8002

# Run the service
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
