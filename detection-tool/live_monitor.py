#!/usr/bin/env python3
"""
Live Malicious Agent Monitor
Tails a log file and runs detection logic in real-time
"""

import time
import json
import sys
import os
from typing import Generator, Dict, Any
from detect_malicious_agent import MaliciousPatternDetector

def follow_file(filepath: str) -> Generator[str, None, None]:
    """Yield new lines from a file as they are written"""
    # Wait for file to exist
    while not os.path.exists(filepath):
        time.sleep(0.1)
    
    with open(filepath, 'r') as f:
        # Go to the end of the file
        f.seek(0, 2)
        
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)
                continue
            yield line

def print_flag(flag: Dict[str, Any]):
    """Print a detected flag with color coding"""
    severity = flag.get('severity', 0)
    description = flag.get('description', 'Unknown issue')
    command = flag.get('command', '')
    category = flag.get('category', 'unknown')
    
    # Color coding based on severity
    if severity >= 70:
        color = '\033[91m'  # Red
        icon = '🚨'
    elif severity >= 40:
        color = '\033[93m'  # Yellow
        icon = '⚠️ '
    else:
        color = '\033[96m'  # Cyan
        icon = 'ℹ️ '
        
    reset = '\033[0m'
    
    print(f"{color}{icon} [{category.upper()}] {description} (Severity: {severity}){reset}")
    if command:
        print(f"   Command: {command}")
    print("-" * 60)

def main():
    if len(sys.argv) < 2:
        print("Usage: python live_monitor.py <trace_file.jsonl>")
        sys.exit(1)
        
    trace_file = sys.argv[1]
    print(f"Starting live monitor on {trace_file}...")
    print("Waiting for agent activity...")
    print("=" * 60)
    
    detector = MaliciousPatternDetector()
    
    try:
        for line in follow_file(trace_file):
            line = line.strip()
            if not line:
                continue
                
            try:
                entry = json.loads(line)
                
                # Print command being executed (benign or not)
                cmd = entry.get('command', '')
                print(f"EXEC: {cmd}")
                
                # Analyze
                flags = detector.analyze_command(entry)
                detector.flags.extend(flags)
                
                # Check for behavioral anomalies (needs history)
                # We pass a list of just this entry to check for immediate anomalies,
                # but for full context we might need to keep a buffer.
                # For now, let's just check the single entry for immediate flags.
                # Behavioral anomalies in the original code require the full list.
                # We can maintain a history list.
                
                # Update history for behavioral checks
                if not hasattr(detector, 'history'):
                    detector.history = []
                detector.history.append(entry)
                
                # Run behavioral detection on full history
                # Note: This might duplicate flags if we are not careful, 
                # but the original detector appends to self.flags.
                # We should check if new flags were added.
                
                prev_flag_count = len(detector.flags)
                detector.detect_behavioral_anomalies(detector.history)
                new_flag_count = len(detector.flags)
                
                # Print immediate flags
                for flag in flags:
                    print_flag(flag)
                
                # Print new behavioral flags
                if new_flag_count > prev_flag_count:
                    for i in range(prev_flag_count, new_flag_count):
                        print_flag(detector.flags[i])
                
                # Show current score if it changed
                verdict, confidence = detector.calculate_verdict()
                if detector.suspicion_score > 0:
                    score_color = '\033[92m' # Green
                    if detector.suspicion_score >= 40: score_color = '\033[93m' # Yellow
                    if detector.suspicion_score >= 70: score_color = '\033[91m' # Red
                    
                    print(f"Current Suspicion Score: {score_color}{detector.suspicion_score}{'\033[0m'} ({verdict})")
                    
            except json.JSONDecodeError:
                pass
                
    except KeyboardInterrupt:
        print("\nStopping monitor.")
        verdict, confidence = detector.calculate_verdict()
        print(f"\nFinal Verdict: {verdict} (Score: {detector.suspicion_score})")

if __name__ == '__main__':
    main()
