FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY services/ai-service/requirements.txt ./

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY services/ai-service/ .

# Expose portcompact vdisk

EXPOSE 8001

# Run the service
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
