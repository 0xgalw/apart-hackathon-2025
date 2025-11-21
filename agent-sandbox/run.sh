#!/bin/bash
docker build -t agent .
# Create logs directory if it doesn't exist
rm -rf ./logs
mkdir -p ./logs

# Run the Docker container with volume mount for logs
docker run --rm \
  --env-file .env \
  -v "$(pwd)/logs:/app/logs" \
  -p 8000:8000 \
  -p 8080:8080 \
  -p 3000:3000 \
  agent

