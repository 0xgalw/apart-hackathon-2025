"""Logging module for agent execution tracking."""
import os
import sys
import json
import uuid
import getpass
from datetime import datetime
from pathlib import Path
from langchain_core.callbacks import BaseCallbackHandler


class TeeLogger:
    """Writes to both file and stdout."""
    
    def __init__(self, file_path):
        self.file = open(file_path, "a", encoding="utf-8")
        self.stdout = sys.stdout
        self.closed = False
        
    def write(self, message):
        if not self.closed:
            self.file.write(message)
            self.file.flush()
        self.stdout.write(message)
        self.stdout.flush()
        
    def flush(self):
        if not self.closed:
            self.file.flush()
        self.stdout.flush()
        
    def close(self):
        if not self.closed:
            self.file.close()
            self.closed = True


def setup_logging(log_dir=None):
    """Initialize logging infrastructure."""
    if log_dir is None:
        log_dir = os.getenv("LOG_DIR", "/app/logs")
    
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, "agent.log")
    
    tee_logger = TeeLogger(log_file_path)
    original_stdout = sys.stdout
    sys.stdout = tee_logger
    
    return tee_logger, original_stdout


def log_bash_command(
    timestamp: str,
    session_id: str,
    sequence_num: int,
    command: str,
    working_dir: str,
    exit_code: int,
    stdout: str = "",
    stderr: str = "",
    duration_ms: int = 0,
    user: str = "",
    jsonl_log_path: str = None,
    log_mode: str = "big"
) -> None:
    """
    Log a bash command execution to JSONL file.
    
    Args:
        timestamp: ISO 8601 timestamp
        session_id: Unique session identifier
        sequence_num: Sequential command number
        command: The bash command executed
        working_dir: Working directory where command was executed
        exit_code: Exit code from command
        stdout: Standard output (optional, only in big mode)
        stderr: Standard error (optional, only in big mode)
        duration_ms: Execution duration in milliseconds (optional, only in big mode)
        user: User account (optional, only in big mode)
        jsonl_log_path: Path to JSONL log file
        log_mode: "lean" (minimal) or "big" (all fields)
    """
    if jsonl_log_path is None:
        log_dir = os.getenv("LOG_DIR", "/app/logs")
        jsonl_log_path = os.path.join(log_dir, "agent_trace.jsonl")
    
    # Ensure log directory exists
    log_dir = os.path.dirname(jsonl_log_path)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    log_entry = {
        "timestamp": timestamp,
        "session_id": session_id,
        "sequence_num": sequence_num,
        "command": command,
        "working_dir": working_dir,
        "exit_code": exit_code
    }
    
    if log_mode == "big":
        log_entry["stdout"] = stdout
        log_entry["stderr"] = stderr
        log_entry["duration_ms"] = duration_ms
        log_entry["user"] = user
    
    # Write log entry with error handling
    try:
        with open(jsonl_log_path, "a", encoding="utf-8") as jsonl_log:
            jsonl_log.write(json.dumps(log_entry) + "\n")
            jsonl_log.flush()
    except (OSError, IOError) as e:
        # Log error to stderr but don't crash
        sys.stderr.write(f"Failed to write to {jsonl_log_path}: {e}\n")
        sys.stderr.flush()


class LoggerCallback(BaseCallbackHandler):
    """Callback handler for logging tool execution."""
    
    def __init__(self, tee_logger):
        self.tee_logger = tee_logger
        
    def on_tool_start(self, tool, input_str, **kwargs):
        message = f"[{datetime.now().isoformat()}] TOOL START: {tool.name} -> {input_str}\n"
        self.tee_logger.write(message)
        
    def on_tool_end(self, output, **kwargs):
        message = f"[{datetime.now().isoformat()}] TOOL END -> {output}\n"
        self.tee_logger.write(message)


def create_session():
    """Create a new session for tracking."""
    session_id = f"agent-{uuid.uuid4().hex[:8]}"
    return session_id

