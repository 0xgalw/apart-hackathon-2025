"""LangChain agent and tools configuration."""
import os
import re
import subprocess
import time
import getpass
import socket
from datetime import datetime
from pathlib import Path
from langchain.agents import create_agent
from langchain_core.tools import Tool
from logging_module import log_bash_command


# Track background server processes
background_servers = []


def is_port_listening(port, host='localhost'):
    """Check if a port is listening on the given host."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            result = s.connect_ex((host, port))
            return result == 0
    except Exception:
        return False


def create_bash_tool(session_id, log_dir, log_mode, tee_logger):
    """
    Create a bash tool for executing commands.
    
    Args:
        session_id: Session ID for logging
        log_dir: Directory for logs
        log_mode: "lean" or "big" logging mode
        tee_logger: Logger instance for writing
        
    Returns:
        Tool instance
    """
    sequence_num = [0]  # Use list to allow modification in nested function
    jsonl_log_path = os.path.join(log_dir, "agent_trace.jsonl")
    bash_log_path = os.path.join(log_dir, "bash.log")
    
    def bash_tool(cmd: str) -> str:
        """Execute bash command and return output."""
        with open(bash_log_path, "a", encoding="utf-8") as bash_log:
            bash_log.write(f"CMD: {cmd}\n")
            bash_log.flush()
        
        sequence_num[0] += 1
        working_dir = os.getcwd()
        user = getpass.getuser() if hasattr(getpass, 'getuser') else os.getenv("USER", "unknown")
        
        start_time = time.time()
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Initialize variables for logging
        exit_code = 1
        stdout_text = ""
        stderr_text = ""
        output = ""
        
        try:
            server_keywords = [
                "http.server", "python3 -m http.server", "flask run",
                "django", "runserver", "node", "npm start", "serve"
            ]
            is_server = any(keyword in cmd.lower() for keyword in server_keywords)
            
            if is_server:
                # Extract port from command if possible (default to 8000)
                port = 8000
                port_match = re.search(r':(\d+)', cmd)
                if port_match:
                    try:
                        port = int(port_match.group(1))
                    except ValueError:
                        pass
                
                # Check if port is already listening
                if is_port_listening(port):
                    output = f"Server is already running on port {port}. Access at http://localhost:{port}"
                    stdout_text = ""
                    stderr_text = ""
                    exit_code = 0
                else:
                    process = subprocess.Popen(
                        cmd,
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        executable="/bin/bash",
                        start_new_session=True
                    )
                    
                    time.sleep(1)
                    
                    # Check if process is running OR if port is now listening
                    if process.poll() is None:
                        background_servers.append(process)
                        output = f"Server started in background (PID: {process.pid}). Access at http://localhost:{port}"
                        stdout_text = ""
                        stderr_text = ""
                        exit_code = 0
                    elif is_port_listening(port):
                        # Process exited but port is listening - server is running (maybe started by another process)
                        output = f"Server is running on port {port}. Access at http://localhost:{port}"
                        stdout_text = ""
                        stderr_text = ""
                        exit_code = 0
                    else:
                        # Process exited and port is not listening - actual failure
                        output = f"Server failed to start (exited with code {process.returncode})"
                        stdout_text = ""
                        stderr_text = output
                        exit_code = process.returncode if process.returncode is not None else 1
            else:
                try:
                    result = subprocess.run(
                        cmd,
                        shell=True,
                        capture_output=True,
                        text=True,
                        executable="/bin/bash",
                        timeout=30
                    )
                    
                    stdout_text = result.stdout
                    stderr_text = result.stderr
                    exit_code = result.returncode
                    output = result.stdout.strip() or result.stderr.strip()
                except subprocess.TimeoutExpired:
                    output = "Command timed out after 30 seconds"
                    stdout_text = ""
                    stderr_text = output
                    exit_code = 124
        except Exception as e:
            # Catch any unexpected errors and still log them
            error_msg = str(e)
            output = error_msg
            stdout_text = ""
            stderr_text = error_msg
            exit_code = 1
        
        # Always log, even if there was an error
        duration_ms = int((time.time() - start_time) * 1000)
        log_bash_command(
            timestamp=timestamp,
            session_id=session_id,
            sequence_num=sequence_num[0],
            command=cmd,
            working_dir=working_dir,
            exit_code=exit_code,
            stdout=stdout_text,
            stderr=stderr_text,
            duration_ms=duration_ms,
            user=user,
            jsonl_log_path=jsonl_log_path,
            log_mode=log_mode
        )
        
        return output
    
    return Tool(
        name="Bash",
        func=bash_tool,
        description="""Executes a bash command and returns the output. 
Use this tool to:
- Create files and directories (e.g., 'mkdir mydir', 'touch file.txt', 'echo "content" > file.html')
- Run programs and scripts
- Install packages (e.g., 'pip install package', 'apt-get install package')
- Check system status (e.g., 'ls', 'pwd', 'which python')
- Build and compile code
- Any other bash command needed to accomplish the task

The command will be executed in the current working directory (/app/src). Always use this tool to actually execute commands rather than just describing them."""
    )


def create_agent_with_tools(llm, system_prompt, bash_tool, logger_callback):
    """
    Create LangChain agent with tools.
    
    Args:
        llm: Language model instance
        system_prompt: System prompt string
        bash_tool: Bash tool instance
        logger_callback: Logger callback instance
        
    Returns:
        Agent instance
    """
    return create_agent(
        model=llm,
        tools=[bash_tool],
        system_prompt=system_prompt,
        debug=False
    )


def get_background_servers():
    """Get list of background server processes."""
    return background_servers

