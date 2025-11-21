#!/usr/bin/env python3
"""Interactive script to execute for loop bash commands and log them."""
import os
import sys
import subprocess
import time
import getpass
from datetime import datetime
from pathlib import Path

# Import logging_module (assumes we're in the same directory or src/)
from logging_module import log_bash_command, create_session


def execute_for_loop(command: str, log_dir: str = None, log_mode: str = "big", sequence_num: int = 1, session_id: str = None):
    """
    Execute a for loop bash command and log it using log_bash_command.
    
    Args:
        command: The for loop bash command to execute
        log_dir: Directory for logs (defaults to agent-sandbox/logs)
        log_mode: "lean" or "big" logging mode (defaults to "big")
        sequence_num: Sequence number for logging (defaults to 1)
        session_id: Session ID for logging (creates new if None)
    """
    # Set up log directory
    if log_dir is None:
        log_dir = os.getenv("LOG_DIR", "/app/logs")
    
    os.makedirs(log_dir, exist_ok=True)
    jsonl_log_path = os.path.join(log_dir, "agent_trace.jsonl")
    bash_log_path = os.path.join(log_dir, "bash.log")
    
    # Create session ID if not provided
    if session_id is None:
        session_id = create_session()
    
    # Write to bash.log
    with open(bash_log_path, "a", encoding="utf-8") as bash_log:
        bash_log.write(f"CMD: {command}\n")
        bash_log.flush()
    
    # Get execution context
    working_dir = os.getcwd()
    user = getpass.getuser() if hasattr(getpass, 'getuser') else os.getenv("USER", "unknown")
    start_time = time.time()
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    # Initialize variables for logging
    exit_code = 1
    stdout_text = ""
    stderr_text = ""
    
    try:
        # Execute the for loop command
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            executable="/bin/bash",
            timeout=300  # 5 minute timeout for interactive commands
        )
        
        stdout_text = result.stdout
        stderr_text = result.stderr
        exit_code = result.returncode
        
    except subprocess.TimeoutExpired:
        stdout_text = ""
        stderr_text = "Command timed out after 5 minutes"
        exit_code = 124
    except Exception as e:
        # Catch any unexpected errors and still log them
        error_msg = str(e)
        stdout_text = ""
        stderr_text = error_msg
        exit_code = 1
    
    # Calculate duration
    duration_ms = int((time.time() - start_time) * 1000)
    
    # Log the command execution
    log_bash_command(
        timestamp=timestamp,
        session_id=session_id,
        sequence_num=sequence_num,
        command=command,
        working_dir=working_dir,
        exit_code=exit_code,
        stdout=stdout_text,
        stderr=stderr_text,
        duration_ms=duration_ms,
        user=user,
        jsonl_log_path=jsonl_log_path,
        log_mode=log_mode
    )
    
    # Print output to console
    if stdout_text:
        print(stdout_text, end='')
    if stderr_text:
        print(stderr_text, end='', file=sys.stderr)
    
    return exit_code


def read_command_from_file(file_path: str) -> str:
    """
    Read bash command from a file.
    
    Args:
        file_path: Path to the file containing the command
        
    Returns:
        The command string with leading/trailing whitespace stripped
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            command = f.read().strip()
        if not command:
            raise ValueError(f"File {file_path} is empty")
        return command
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except IOError as e:
        raise IOError(f"Error reading file {file_path}: {e}")


def read_command_from_stdin() -> str:
    """
    Read bash command from stdin.
    
    Returns:
        The command string with leading/trailing whitespace stripped
    """
    try:
        command = sys.stdin.read().strip()
        if not command:
            raise ValueError("No command provided via stdin")
        return command
    except (EOFError, KeyboardInterrupt):
        raise ValueError("No command provided via stdin")


def get_command_interactive(prompt: str = "Enter bash command: ") -> str:
    """
    Prompt user for command interactively.
    
    Args:
        prompt: Prompt string to display
        
    Returns:
        The command string with leading/trailing whitespace stripped, or None if user wants to exit
    """
    try:
        command = input(prompt).strip()
        if not command:
            return None
        return command
    except (EOFError, KeyboardInterrupt):
        return None


def main():
    """Main entry point."""
    log_dir = None
    log_mode = "big"
    command = None
    
    # Parse arguments
    args = sys.argv[1:]
    
    # Check for log_dir and log_mode flags
    if "--log-dir" in args:
        idx = args.index("--log-dir")
        if idx + 1 < len(args):
            log_dir = args[idx + 1]
            args = args[:idx] + args[idx + 2:]
    
    if "--log-mode" in args:
        idx = args.index("--log-mode")
        if idx + 1 < len(args):
            log_mode = args[idx + 1]
            args = args[:idx] + args[idx + 2:]
    
    # Determine command source
    if len(args) == 0:
        # No arguments: try stdin first, then interactive prompt
        if not sys.stdin.isatty():
            # Reading from pipe/redirect
            try:
                command = read_command_from_stdin()
            except ValueError:
                print("Error: No command provided via stdin", file=sys.stderr)
                sys.exit(1)
        else:
            # Interactive mode
            command = get_command_interactive()
    elif len(args) == 1:
        arg = args[0]
        # Check if it's a file path or a direct command
        if arg.startswith("for ") or arg.startswith("FOR ") or ";" in arg or "do " in arg.lower():
            # Looks like a direct command
            command = arg
        elif os.path.isfile(arg) or arg.startswith("/"):
            # Looks like a file path
            try:
                command = read_command_from_file(arg)
            except (FileNotFoundError, IOError, ValueError) as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            # Try as file first, if not found, treat as command
            try:
                command = read_command_from_file(arg)
            except FileNotFoundError:
                # Not a file, treat as command
                command = arg
    else:
        # Multiple arguments: treat as command
        command = " ".join(args)
    
    # Check for loop mode
    loop_mode = "--loop" in sys.argv or "-l" in sys.argv
    
    if not command and not loop_mode:
        print("Usage: interactive.py [command|command_file] [--log-dir DIR] [--log-mode MODE] [--loop]")
        print("       interactive.py 'for i in 1 2 3; do echo $i; done'")
        print("       interactive.py example_for_loop.txt")
        print("       echo 'for i in 1 2 3; do echo $i; done' | interactive.py")
        print("       interactive.py  # Interactive prompt mode (single command)")
        print("       interactive.py --loop  # Interactive loop mode (multiple commands)")
        sys.exit(1)
    
    # Initialize session for multiple commands
    session_id = create_session()
    sequence_num = 1
    
    try:
        if loop_mode:
            # Loop mode: keep prompting for commands
            is_tty = sys.stdin.isatty()
            if is_tty:
                print("Interactive loop mode. Enter commands (empty line or Ctrl+D to exit).")
            else:
                print("Reading commands from stdin (one per line). Empty line or EOF to exit.", flush=True)
            
            while True:
                if is_tty:
                    cmd = get_command_interactive(f"[{sequence_num}] Enter bash command: ")
                    if cmd is None:
                        print("\nExiting loop mode...")
                        break
                else:
                    # Read from stdin line by line (non-interactive)
                    try:
                        line = sys.stdin.readline()
                        if not line:  # EOF
                            break
                        cmd = line.strip()
                        if not cmd:
                            break
                    except (EOFError, KeyboardInterrupt):
                        break
                
                if not cmd:
                    break
                
                exit_code = execute_for_loop(cmd, log_dir, log_mode, sequence_num, session_id)
                sequence_num += 1
                
                if exit_code != 0:
                    print(f"Command exited with code {exit_code}", file=sys.stderr, flush=True)
        else:
            # Single command mode
            exit_code = execute_for_loop(command, log_dir, log_mode, sequence_num, session_id)
            sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

