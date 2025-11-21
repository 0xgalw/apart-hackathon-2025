#!/usr/bin/env python3
"""
Live Malicious Agent Monitor
Tails a log file and runs detection logic in real-time
"""

import time
import json
import sys
import os
import subprocess
import argparse
from typing import Generator, Dict, Any
from sigma_engine import SigmaDetectionEngine
from detect_malicious_agent import calculate_verdict

def follow_file(filepath: str) -> Generator[str, None, None]:
    """Yield new lines from a file as they are written"""
    # Wait for file to exist
    while not os.path.exists(filepath):
        time.sleep(0.1)
    
    with open(filepath, 'r') as f:
        # Start from the beginning of the file
        # f.seek(0, 2)  <-- Removed to read from start
        
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
    rule_level = flag.get('rule_level', 'unknown')
    mitre_tags = flag.get('mitre_tags', [])
    
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
    
    print(f"{color}{icon} [{rule_level.upper()}] {description} (Severity: {severity}){reset}")
    if command:
        print(f"   Command: {command}")
    if mitre_tags:
        print(f"   MITRE: {', '.join(mitre_tags[:3])}")
    print("-" * 60)

def main():
    parser = argparse.ArgumentParser(description='Live Malicious Agent Monitor')
    parser.add_argument('trace_file', help='Path to trace file (local or inside container)')
    
    args = parser.parse_args()
    
    # Derive the bash.log path from trace_file path
    trace_dir = os.path.dirname(args.trace_file)
    bash_log_path = os.path.join(trace_dir, 'bash.log')
    
    print("=" * 80)
    print("🔍 MALICIOUS AGENT DETECTION SYSTEM")
    print("=" * 80)
    print(f"📊 Monitoring: {args.trace_file}")
    print(f"📝 Full command history: {bash_log_path}")
    print("=" * 80)
    
    log_generator = follow_file(args.trace_file)

    print("Loading Sigma rules...")
    # Resolve sigma_repo path relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sigma_repo_path = os.path.join(script_dir, 'sigma_repo')
    
    detector = SigmaDetectionEngine(sigma_repo_path=sigma_repo_path)
    rules_count = detector.load_rules()
    print(f"✓ Loaded {rules_count} Sigma rules")
    print("\n⏳ Waiting for agent activity...\n")
    
    try:
        for line in log_generator:
            line = line.strip()
            if not line:
                continue
                
            try:
                entry = json.loads(line)
                
                # Print command being executed (truncated for readability)
                cmd = entry.get('command', '')
                # Truncate long commands
                max_cmd_length = 80
                if len(cmd) > max_cmd_length:
                    cmd_display = cmd[:max_cmd_length] + "..."
                else:
                    cmd_display = cmd
                print(f"▶ {cmd_display}")
                
                # Analyze
                flags = detector.analyze_entry(entry)
                detector.flags.extend(flags)
                
                # Print immediate flags with extra visibility
                if flags:
                    print("\n" + "!" * 80)
                    for flag in flags:
                        print_flag(flag)
                    print("!" * 80 + "\n")
                
                # Show current score if it changed
                verdict, confidence = calculate_verdict(detector.suspicion_score)
                if detector.suspicion_score > 0:
                    score_color = '\033[92m' # Green
                    if detector.suspicion_score >= 40: score_color = '\033[93m' # Yellow
                    if detector.suspicion_score >= 70: score_color = '\033[91m' # Red
                    
                    print(f"📊 Suspicion Score: {score_color}{detector.suspicion_score}{'\033[0m'} ({verdict})\n")
                    
            except json.JSONDecodeError:
                pass
                
    except KeyboardInterrupt:
        print("\n" + "=" * 80)
        print("Stopping monitor.")
        verdict, confidence = calculate_verdict(detector.suspicion_score)
        print(f"\n🎯 Final Verdict: {verdict} (Score: {detector.suspicion_score})")
        print("=" * 80)

if __name__ == '__main__':
    main()
