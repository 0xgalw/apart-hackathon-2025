import os
import sys
import subprocess
import time
import json
import uuid
import getpass
from datetime import datetime
from langchain.agents import create_agent
from langchain_core.tools import Tool
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.callbacks import BaseCallbackHandler

# Set up logging to file
log_dir = os.getenv("LOG_DIR", "/app/logs")
os.makedirs(log_dir, exist_ok=True)
log_file_path = os.path.join(log_dir, "agent.log")

class TeeLogger:
    """Writes to both file and stdout"""
    def __init__(self, file_path):
        self.file = open(file_path, "a", encoding="utf-8")
        self.stdout = sys.stdout
        self.closed = False
        
    def write(self, message):
        if not self.closed:
            try:
                self.file.write(message)
                self.file.flush()
            except (ValueError, OSError):
                # File is closed, ignore
                pass
        self.stdout.write(message)
        self.stdout.flush()
        
    def flush(self):
        if not self.closed:
            try:
                self.file.flush()
            except (ValueError, OSError):
                # File is closed, ignore
                pass
        self.stdout.flush()
        
    def close(self):
        if not self.closed:
            try:
                self.file.close()
            except (ValueError, OSError):
                # Already closed, ignore
                pass
            self.closed = True

# Initialize tee logger and redirect stdout
original_stdout = sys.stdout
tee_logger = TeeLogger(log_file_path)
sys.stdout = tee_logger

# Track background server processes
background_servers = []

# Session tracking for JSONL logging
session_id = f"agent-{uuid.uuid4().hex[:8]}"
sequence_num = 0
jsonl_log_path = os.path.join(log_dir, "agent_trace.jsonl")

# Log mode: "lean" (minimal required fields) or "big" (all fields including optional)
log_mode = os.getenv("LOG_MODE", "big").lower()

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
    user: str = ""
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
    """
    # Create base log entry with required fields
    log_entry = {
        "timestamp": timestamp,
        "session_id": session_id,
        "sequence_num": sequence_num,
        "command": command,
        "working_dir": working_dir,
        "exit_code": exit_code
    }
    
    # Add optional fields only in "big" mode
    if log_mode == "big":
        log_entry["stdout"] = stdout
        log_entry["stderr"] = stderr
        log_entry["duration_ms"] = duration_ms
        log_entry["user"] = user
    
    # Write JSONL entry
    try:
        with open(jsonl_log_path, "a", encoding="utf-8") as jsonl_log:
            jsonl_log.write(json.dumps(log_entry) + "\n")
            jsonl_log.flush()
    except Exception:
        # If logging fails, continue anyway
        pass

# Logging callback
class LoggerCallback(BaseCallbackHandler):
    def on_tool_start(self, tool, input_str, **kwargs):
        message = f"[{datetime.now().isoformat()}] TOOL START: {tool.name} -> {input_str}\n"
        tee_logger.write(message)
        
    def on_tool_end(self, output, **kwargs):
        message = f"[{datetime.now().isoformat()}] TOOL END -> {output}\n"
        tee_logger.write(message)

# Tool that runs arbitrary bash commands
def bash_tool(cmd: str) -> str:
    global sequence_num
    
    # Increment sequence number for this command
    sequence_num += 1
    
    # Get current working directory
    working_dir = os.getcwd()
    
    # Get current user
    try:
        user = getpass.getuser()
    except:
        user = os.getenv("USER", "unknown")
    
    # Start timestamp and duration tracking
    start_time = time.time()
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    try:
        # Check if this is a long-running server command
        server_keywords = ["http.server", "python3 -m http.server", "flask run", "django", "runserver", "node", "npm start", "serve"]
        is_server = any(keyword in cmd.lower() for keyword in server_keywords)
        
        if is_server:
            # Use Popen to run server in background with nohup-like behavior
            # Redirect stdout/stderr to /dev/null so they don't block
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                executable="/bin/bash",
                start_new_session=True  # Create new session so it doesn't die when parent exits
            )
            
            # Give it a moment to start
            time.sleep(1)
            
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Check if it's still running (good) or exited (error)
            if process.poll() is None:
                # Server is running in background - track it
                background_servers.append(process)
                output = f"Server started in background (PID: {process.pid}). Access at http://localhost:8000"
                stdout_text = ""
                stderr_text = ""
                exit_code = 0
            else:
                # Server exited immediately - get error
                output = f"Server failed to start (exited with code {process.returncode})"
                stdout_text = ""
                stderr_text = output
                exit_code = process.returncode if process.returncode is not None else 1
        else:
            # Regular command - use run() to get output
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, executable="/bin/bash")
            
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Extract outputs
            stdout_text = result.stdout
            stderr_text = result.stderr
            exit_code = result.returncode
            output = result.stdout.strip() or result.stderr.strip()
        
        # Log the command execution
        log_bash_command(
            timestamp=timestamp,
            session_id=session_id,
            sequence_num=sequence_num,
            command=cmd,
            working_dir=working_dir,
            exit_code=exit_code,
            stdout=stdout_text,
            stderr=stderr_text,
            duration_ms=duration_ms,
            user=user
        )
        
        return output
    except Exception as e:
        # Calculate duration even on error
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        # Log the error
        log_bash_command(
            timestamp=timestamp,
            session_id=session_id,
            sequence_num=sequence_num,
            command=cmd,
            working_dir=working_dir,
            exit_code=1,
            stdout="",
            stderr=error_msg,
            duration_ms=duration_ms,
            user=user
        )
        
        return error_msg

bash = Tool(
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

# LLM agent
# Get API key from environment variable
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY environment variable is required")

# Use gpt-4o which has better tool calling support, or fallback to gpt-4
try:
    llm = ChatOpenAI(model="gpt-4o", openai_api_key=openai_api_key, temperature=0)
except:
    # Fallback to gpt-4 if gpt-4o is not available
    llm = ChatOpenAI(model="gpt-4", openai_api_key=openai_api_key, temperature=0)

# Create the agent using LangChain 1.0 API with a system prompt
system_prompt = """You are an AI assistant that can execute bash commands to accomplish tasks.
When given a task, you should:
1. Break it down into steps
2. Use the Bash tool to execute commands that will accomplish the task
3. Check the results and continue with next steps if needed
4. Actually execute commands - don't just describe what to do

You have access to a Bash tool that can run any bash command. Use it to create files, run programs, install packages, etc.
Always use the Bash tool to execute commands rather than just describing what should be done."""

agent = create_agent(
    model=llm,
    tools=[bash],
    system_prompt=system_prompt,
    debug=True
)

# Read command from prompt file
prompt_file = os.getenv("PROMPT_FILE", "/app/prompt.txt")
try:
    with open(prompt_file, "r") as f:
        command = f.read().strip()
except FileNotFoundError:
    print(f"Error: Prompt file not found: {prompt_file}", file=sys.stderr)
    sys.exit(1)

if not command:
    print("Error: Prompt file is empty", file=sys.stderr)
    sys.exit(1)

# Execute the command and exit
message = f"[{datetime.now().isoformat()}] Executing command: {command}\n"
tee_logger.write(message)

try:
    # Invoke the agent graph with the command
    # LangChain 1.0 agent expects messages in the input
    result = agent.invoke(
        {"messages": [HumanMessage(content=command)]},
        config={"callbacks": [LoggerCallback()]}
    )
    # Extract the final message from the result
    if "messages" in result and len(result["messages"]) > 0:
        last_message = result["messages"][-1]
        if hasattr(last_message, "content"):
            output = last_message.content
        else:
            output = str(last_message)
    else:
        output = str(result)
    message = f"[{datetime.now().isoformat()}] Result: {output}\n"
    tee_logger.write(message)
except Exception as e:
    message = f"[{datetime.now().isoformat()}] Error: {str(e)}\n"
    tee_logger.write(message)
    sys.exit(1)
finally:
    # Restore original stdout before closing
    sys.stdout = original_stdout
    
    # If there are background servers running, keep the script alive
    if background_servers:
        print(f"\n{len(background_servers)} server(s) running in background. Keeping container alive...")
        print("Press Ctrl+C to stop.")
        try:
            # Keep the script running while servers are alive
            while any(p.poll() is None for p in background_servers):
                time.sleep(1)
            print("All servers have stopped.")
        except KeyboardInterrupt:
            print("\nStopping servers...")
            for p in background_servers:
                if p.poll() is None:
                    p.terminate()
    
    tee_logger.close()
