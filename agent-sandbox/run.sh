#!/bin/bash
docker build -t agent .
# Create logs directory if it doesn't exist
LOG_DIR="$(pwd)/logs"

mkdir -p $LOG_DIR

# Run the Docker container with volume mounts for logs and output
docker run --rm \
  --name malicious-agent-demo \
  --env-file .env \
  -v "$LOG_DIR:/app/logs" \
  -p 8000:8000 \
  -p 8080:8080 \
  -p 3000:3000 \
  agent

