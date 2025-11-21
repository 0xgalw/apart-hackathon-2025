#!/bin/bash
docker build -t interactive . -f interactive.Dockerfile
# Create logs directory if it doesn't exist
LOG_DIR="$(pwd)/logs"
rm -rf $LOG_DIR
mkdir -p $LOG_DIR
mkdir -p $LOG_DIR/output

# Remove any existing container with the same name
docker rm -f interactive-agent 2>/dev/null || true

# Check if loop mode is requested
if [ "$1" = "--loop" ] || [ "$1" = "-l" ]; then
  # Loop mode - use interactive terminal
  docker run --rm -it \
    --name interactive-agent \
    --env-file .env \
    -v "$LOG_DIR:/app/logs" \
    interactive python -u /app/src/interactive.py --loop
else
  # Get command file from argument or use default
  COMMAND_FILE="${1:-example_for_loop.txt}"
  
  # Check if it's a direct command (starts with 'for' or contains ';')
  if [[ "$COMMAND_FILE" =~ ^for ]] || [[ "$COMMAND_FILE" == *";"* ]]; then
    # Direct command
    docker run --rm -i \
      --name interactive-agent \
      --env-file .env \
      -v "$LOG_DIR:/app/logs" \
      interactive python -u /app/src/interactive.py "$COMMAND_FILE"
  elif [ -f "$COMMAND_FILE" ]; then
    # File exists locally - mount it
    docker run --rm -i \
      --name interactive-agent \
      --env-file .env \
      -v "$LOG_DIR:/app/logs" \
      -v "$(pwd)/$COMMAND_FILE:/app/$COMMAND_FILE:ro" \
      interactive python -u /app/src/interactive.py "/app/$COMMAND_FILE"
  else
    # File doesn't exist - try using the one in the image
    docker run --rm -i \
      --name interactive-agent \
      --env-file .env \
      -v "$LOG_DIR:/app/logs" \
      interactive python -u /app/src/interactive.py "/app/$COMMAND_FILE"
  fi
fi

