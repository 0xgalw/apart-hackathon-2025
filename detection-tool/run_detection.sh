#!/bin/bash
#
# Runner script to test malicious agent detection on all example traces
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLES_DIR="$SCRIPT_DIR/examples"
DETECTOR="$SCRIPT_DIR/detect_malicious_agent.py"

echo "========================================"
echo "  Malicious Agent Detection Test Suite"
echo "========================================"
echo ""

# Make detector executable
chmod +x "$DETECTOR"

# Test all example traces
for trace_file in "$EXAMPLES_DIR"/*.jsonl; do
    if [ -f "$trace_file" ]; then
        echo ""
        echo "----------------------------------------"
        echo "Testing: $(basename "$trace_file")"
        echo "----------------------------------------"

        python3 "$DETECTOR" "$trace_file"

        echo ""
        echo ""
    fi
done

echo "========================================"
echo "  All tests completed!"
echo "========================================"
echo ""
echo "JSON reports have been saved for each trace."
echo "Check the detection-tool directory for *_report.json files."
