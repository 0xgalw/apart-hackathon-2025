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
        # Go to the end of the file
        f.seek(0, 2)
        
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)
                continue
            yield line

def follow_docker_logs(container_name: str, filepath: str) -> Generator[str, None, None]:
    """Yield new lines from a file inside a docker container"""
    print(f"Waiting for container '{container_name}' to start...")
    
    # Wait for container to be running
    while True:
        try:
            result = subprocess.run(
                ['docker', 'inspect', '-f', '{{.State.Running}}', container_name],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip() == 'true':
                break
        except Exception:
            pass
        time.sleep(0.5)
        
    print(f"Container '{container_name}' found. Attaching to logs...")
    
    # Use tail -f inside the container to stream logs
    # We use stdbuf to ensure line buffering
    cmd = ['docker', 'exec', container_name, 'tail', '-f', filepath]
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1  # Line buffered
    )
    
    try:
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                yield line
    except GeneratorExit:
        process.terminate()
        raise

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
    parser.add_argument('--docker', help='Docker container name to monitor', default=None)
    
    args = parser.parse_args()
    
    if args.docker:
        print(f"Starting live monitor on Docker container '{args.docker}' file '{args.trace_file}'...")
        log_generator = follow_docker_logs(args.docker, args.trace_file)
    else:
        print(f"Starting live monitor on local file '{args.trace_file}'...")
        log_generator = follow_file(args.trace_file)

    print("Loading Sigma rules...")
    # Resolve sigma_repo path relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sigma_repo_path = os.path.join(script_dir, 'sigma_repo')
    
    detector = SigmaDetectionEngine(sigma_repo_path=sigma_repo_path)
    rules_count = detector.load_rules()
    print(f"Loaded {rules_count} Sigma rules.")
    print("Waiting for agent activity...")
    print("=" * 60)
    
    try:
        for line in log_generator:
            line = line.strip()
            if not line:
                continue
                
            try:
                entry = json.loads(line)
                
                # Print command being executed (benign or not)
                cmd = entry.get('command', '')
                print(f"EXEC: {cmd}")
                
                # Analyze
                flags = detector.analyze_entry(entry)
                detector.flags.extend(flags)
                
                # Print immediate flags
                for flag in flags:
                    print_flag(flag)
                
                # Show current score if it changed
                verdict, confidence = calculate_verdict(detector.suspicion_score)
                if detector.suspicion_score > 0:
                    score_color = '\033[92m' # Green
                    if detector.suspicion_score >= 40: score_color = '\033[93m' # Yellow
                    if detector.suspicion_score >= 70: score_color = '\033[91m' # Red
                    
                    print(f"Current Suspicion Score: {score_color}{detector.suspicion_score}{'\033[0m'} ({verdict})")
                    
            except json.JSONDecodeError:
                pass
                
    except KeyboardInterrupt:
        print("\nStopping monitor.")
        verdict, confidence = calculate_verdict(detector.suspicion_score)
        print(f"\nFinal Verdict: {verdict} (Score: {detector.suspicion_score})")

if __name__ == '__main__':
    main()
