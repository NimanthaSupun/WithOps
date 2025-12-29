#!/bin/bash
# Ollama Model Initialization Script
# Pulls required models on container startup

echo "🚀 Starting Ollama service..."

# Start Ollama in the background
ollama serve &

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama to be ready..."
sleep 5

# Check if nomic-embed-text model exists
echo "📦 Checking for nomic-embed-text model..."
if ! ollama list | grep -q "nomic-embed-text"; then
    echo "📥 Pulling nomic-embed-text model..."
    ollama pull nomic-embed-text
    echo "✅ nomic-embed-text model ready"
else
    echo "✅ nomic-embed-text model already exists"
fi

# Keep the container running
echo "✅ Ollama initialized successfully"
wait
