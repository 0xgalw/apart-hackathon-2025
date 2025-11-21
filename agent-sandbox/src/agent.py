import os
import sys
import subprocess
import time
import json
import uuid
import getpass
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import Tool
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.callbacks import BaseCallbackHandler

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

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
    bash_log_path = os.path.join(log_dir, "bash.log")
    try:
        # Log the command to bash.log
        with open(bash_log_path, "a", encoding="utf-8") as bash_log:
            bash_log.write(f"CMD: {cmd}\n")
            bash_log.flush()
    except Exception:
        # If logging fails, continue anyway
        pass
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
# Read system prompt from file
system_prompt_file = os.getenv("SYSTEM_PROMPT_FILE", str(Path(__file__).parent.parent / "prompts" / "system_prompt.txt"))
try:
    with open(system_prompt_file, "r", encoding="utf-8") as f:
        system_prompt = f.read().strip()
except FileNotFoundError:
    print(f"Error: System prompt file not found: {system_prompt_file}", file=sys.stderr)
    sys.exit(1)

agent = create_agent(
    model=llm,
    tools=[bash],
    system_prompt=system_prompt,
    debug=True
)

# Read command from prompt file
# Default to /app/prompts/prompt.txt in Docker, or relative path when running locally
prompt_file = None
env_prompt_file = os.getenv("PROMPT_FILE")

# Try paths in order of preference
candidate_paths = []
if env_prompt_file:
    candidate_paths.append(env_prompt_file)
# Add Docker path
candidate_paths.append("/app/prompts/prompt.txt")
# Add relative path for local development
candidate_paths.append(str(Path(__file__).parent.parent / "prompts" / "prompt.txt"))

# Find the first path that exists
for path in candidate_paths:
    if os.path.exists(path):
        prompt_file = path
        break

# If no file found, use the Docker path as default (will show clear error)
if prompt_file is None:
    prompt_file = "/app/prompts/prompt.txt"

try:
    with open(prompt_file, "r") as f:
        command = f.read().strip()
except FileNotFoundError:
    print(f"Error: Prompt file not found: {prompt_file}", file=sys.stderr)
    print(f"Tried paths: {', '.join(candidate_paths)}", file=sys.stderr)
    sys.exit(1)

if not command:
    print("Error: Prompt file is empty", file=sys.stderr)
    sys.exit(1)

# Execute the command with persistent retry loop
message = f"[{datetime.now().isoformat()}] Executing command: {command}\n"
tee_logger.write(message)

try:
    # Retry loop - keep trying until success
    max_attempts = None  # None means infinite retries
    attempt = 0
    success = False
    last_error = None

    while not success:
        attempt += 1
        message = f"[{datetime.now().isoformat()}] Attempt {attempt}...\n"
        tee_logger.write(message)
        
        try:
            # Invoke the agent graph with the command
            # LangChain 1.0 agent expects messages in the input
            # Add context about previous attempts if this is a retry
            messages = [HumanMessage(content=command)]
            if attempt > 1 and last_error:
                retry_message = f"The previous attempt encountered an error: {last_error}. Please try again with a different approach and keep trying until the task succeeds."
                messages.append(HumanMessage(content=retry_message))
            
            result = agent.invoke(
                {"messages": messages},
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
            
            # Check if the output indicates success or failure
            # Default to success unless we see clear error indicators
            output_lower = output.lower()
            success_indicators = ["successfully", "completed", "done", "finished", "accomplished", "created", "installed", "running"]
            error_indicators = ["error:", "failed to", "cannot", "unable to", "exception", "traceback", "fatal error"]
            
            has_success = any(indicator in output_lower for indicator in success_indicators)
            has_error = any(indicator in output_lower for indicator in error_indicators)
            
            # If we have success indicators or no clear errors, consider it success
            # Only retry if we have explicit error indicators and no success indicators
            if has_success or not has_error:
                # Looks like success
                message = f"[{datetime.now().isoformat()}] Result (Attempt {attempt}): {output}\n"
                tee_logger.write(message)
                success = True
            else:
                # Clear error indicators found, retry
                last_error = output
                message = f"[{datetime.now().isoformat()}] Attempt {attempt} encountered errors: {output}\n"
                message += f"[{datetime.now().isoformat()}] Retrying with a different approach...\n"
                tee_logger.write(message)
                time.sleep(1)  # Brief pause before retry
                
        except Exception as e:
            last_error = str(e)
            message = f"[{datetime.now().isoformat()}] Attempt {attempt} error: {str(e)}\n"
            message += f"[{datetime.now().isoformat()}] Retrying...\n"
            tee_logger.write(message)
            time.sleep(1)  # Brief pause before retry
        
        # Safety check - if max_attempts is set and we've exceeded it, break
        if max_attempts is not None and attempt >= max_attempts:
            message = f"[{datetime.now().isoformat()}] Reached maximum attempts ({max_attempts}). Stopping.\n"
            tee_logger.write(message)
            break

    if not success:
        message = f"[{datetime.now().isoformat()}] Task did not complete successfully after {attempt} attempts.\n"
        tee_logger.write(message)
except KeyboardInterrupt:
    message = f"[{datetime.now().isoformat()}] Interrupted by user.\n"
    tee_logger.write(message)
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
