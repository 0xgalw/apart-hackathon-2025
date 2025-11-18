#!/bin/bash
docker build -t agent .
# Create logs directory if it doesn't exist
rm -rf ./logs
mkdir -p ./logs

# Run the Docker container with volume mount for logs
docker run --rm \
  -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
  -v "$(pwd)/logs:/app/logs" \
  -p 8000:8000 \
  agent

