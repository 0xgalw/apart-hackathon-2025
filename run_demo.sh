#!/bin/bash

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting Malicious Agent Detection Demo...${NC}"

# 1. Setup directories
DEMO_ROOT=$(pwd)
AGENT_DIR="$DEMO_ROOT/agent-sandbox"
DETECTION_DIR="$DEMO_ROOT/detection-tool"
LOGS_DIR="$AGENT_DIR/logs"

# Clean up previous logs
echo -e "${BLUE}Cleaning up previous logs...${NC}"
rm -rf "$LOGS_DIR"
mkdir -p "$LOGS_DIR"

# 2. Build Agent (quietly)
echo -e "${BLUE}Building Agent Docker image...${NC}"
cd "$AGENT_DIR"
docker build -t agent . > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Docker build failed!"
    exit 1
fi
cd "$DEMO_ROOT"

# 3. Start Live Monitor in background
echo -e "${GREEN}Starting Live Monitor...${NC}"
# Ensure log file exists
touch "$LOGS_DIR/agent_trace.jsonl"
# Monitor the file from the volume mount
python3 "$DETECTION_DIR/live_monitor.py" "$LOGS_DIR/agent_trace.jsonl" &
MONITOR_PID=$!

# Give monitor a moment to initialize
sleep 2

# 4. Run Agent
echo -e "${BLUE}Running Malicious Agent...${NC}"
echo -e "${BLUE}----------------------------------------${NC}"
# Ensure clean slate
docker rm -f malicious-agent-demo 2>/dev/null || true
cd "$AGENT_DIR"
./run.sh
cd "$DEMO_ROOT"

# 5. Cleanup
echo -e "${BLUE}----------------------------------------${NC}"
echo -e "${BLUE}Agent finished. Stopping monitor...${NC}"
kill $MONITOR_PID
wait $MONITOR_PID 2>/dev/null

echo -e "${GREEN}Demo completed.${NC}"
