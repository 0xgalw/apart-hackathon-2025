import sys
import os

# Add detection-tool to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(script_dir, 'detection-tool'))

from sigma_engine import SigmaDetectionEngine

sigma_repo_path = os.path.join(script_dir, 'detection-tool', 'sigma_repo')

print(f"Loading rules from {sigma_repo_path}")
engine = SigmaDetectionEngine(sigma_repo_path=sigma_repo_path)
count = engine.load_rules()
print(f"Loaded {count} rules")

test_entry = {
    "timestamp": "2025-11-21T10:00:00Z",
    "session_id": "test-001",
    "sequence_num": 1,
    "command": "cp /etc/passwd /tmp/passwd.bak",
    "working_dir": "/app",
    "exit_code": 0,
    "stdout": "",
    "stderr": "",
    "user": "root"
}

print(f"Analyzing command: {test_entry['command']}")
flags = engine.analyze_entry(test_entry)
print(f"Flags detected: {len(flags)}")

for flag in flags:
    print(f"  • {flag['description']} (Level: {flag['rule_level']})")
