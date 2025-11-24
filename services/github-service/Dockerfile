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

# Expose port
EXPOSE 8002

# Run the service
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
