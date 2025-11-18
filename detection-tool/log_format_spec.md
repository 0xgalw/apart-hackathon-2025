# Agent Bash Tool Call Trace - JSONL Format Specification

## Overview

This document defines the JSONL (JSON Lines) format for logging AI agent bash tool call traces. Each line in the log file represents a single bash command execution.

## Format: JSONL (JSON Lines)

- One JSON object per line
- Each line is a complete, valid JSON object
- No comma between lines
- Easy to stream, parse, and append

## Schema

Each JSON object contains the following fields:

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string | ISO 8601 timestamp when command was executed |
| `session_id` | string | Unique identifier for the agent session |
| `sequence_num` | integer | Sequential number of command in this session (starts at 1) |
| `command` | string | The bash command that was executed |
| `working_dir` | string | Working directory where command was executed |
| `exit_code` | integer | Exit code returned by the command (0 = success) |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `stdout` | string | Standard output from the command |
| `stderr` | string | Standard error from the command |
| `duration_ms` | integer | How long the command took to execute (milliseconds) |
| `user` | string | User account running the command |
| `description` | string | Agent's description of what it's doing (if available) |

## Example Entry

```json
{"timestamp": "2025-11-21T10:15:30.123Z", "session_id": "agent-abc123", "sequence_num": 1, "command": "ls -la", "working_dir": "/home/user", "exit_code": 0, "stdout": "total 48\ndrwxr-xr-x 12 user user 4096 Nov 21 10:15 .\ndrwxr-xr-x  3 root root 4096 Nov 20 09:00 ..\n", "stderr": "", "duration_ms": 45, "user": "user"}
```

## Example Log File

```jsonl
{"timestamp": "2025-11-21T10:15:30.123Z", "session_id": "agent-abc123", "sequence_num": 1, "command": "pwd", "working_dir": "/home/user", "exit_code": 0, "stdout": "/home/user\n", "stderr": "", "duration_ms": 12}
{"timestamp": "2025-11-21T10:15:31.456Z", "session_id": "agent-abc123", "sequence_num": 2, "command": "ls -la", "working_dir": "/home/user", "exit_code": 0, "stdout": "total 48\ndrwxr-xr-x 12 user user 4096 Nov 21 10:15 .\n", "stderr": "", "duration_ms": 45}
{"timestamp": "2025-11-21T10:15:32.789Z", "session_id": "agent-abc123", "sequence_num": 3, "command": "cat /etc/passwd", "working_dir": "/home/user", "exit_code": 0, "stdout": "root:x:0:0:root:/root:/bin/bash\nuser:x:1000:1000::/home/user:/bin/bash\n", "stderr": "", "duration_ms": 8}
```

## Usage

### Reading Logs (Python)

```python
import json

with open('agent_trace.jsonl', 'r') as f:
    for line in f:
        entry = json.loads(line)
        print(f"Command: {entry['command']}")
```

### Writing Logs (Python)

```python
import json
from datetime import datetime

log_entry = {
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "session_id": "agent-xyz789",
    "sequence_num": 1,
    "command": "echo 'Hello'",
    "working_dir": "/tmp",
    "exit_code": 0,
    "stdout": "Hello\n",
    "stderr": ""
}

with open('agent_trace.jsonl', 'a') as f:
    f.write(json.dumps(log_entry) + '\n')
```

## Detection Considerations

This format captures key information needed for malicious behavior detection:

- **Command patterns**: Detect suspicious commands (e.g., accessing sensitive files)
- **Temporal patterns**: Identify rapid-fire commands or timing-based attacks
- **Directory traversal**: Track movement through filesystem
- **Error patterns**: Failed privilege escalation attempts (non-zero exit codes)
- **Output analysis**: Examine stdout/stderr for data exfiltration indicators
- **Behavioral sequencing**: Detect multi-step attack chains using sequence_num

## Version

- **Version**: 1.0
- **Date**: November 2025
- **Hackathon**: Apart Research Def/Acc 2025
