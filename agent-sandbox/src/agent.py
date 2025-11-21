"""Main agent execution script."""
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from logging_module import (
    setup_logging,
    LoggerCallback,
    create_session
)
from model_module import initialize_llm
from langchain_module import (
    create_bash_tool,
    create_agent_with_tools,
    get_background_servers,
    is_port_listening
)
from utils_module import (
    read_file_content,
    find_prompt_file,
    get_system_prompt_file
)
from execution_module import (
    execute_task,
    run_improvement_loop
)

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Setup logging
log_dir = os.getenv("LOG_DIR", "/app/logs")
tee_logger, original_stdout = setup_logging(log_dir)
log_mode = os.getenv("LOG_MODE", "big").lower()
session_id = create_session()

# Initialize model
llm, chosen_model = initialize_llm()

# Read system prompt
system_prompt_file = get_system_prompt_file()
system_prompt = read_file_content(system_prompt_file)

# Create bash tool and agent
bash_tool = create_bash_tool(session_id, log_dir, log_mode, tee_logger)
logger_callback = LoggerCallback(tee_logger)
agent = create_agent_with_tools(llm, system_prompt, bash_tool, logger_callback)

# Read command from prompt file
prompt_file = find_prompt_file()
command = read_file_content(prompt_file)

if not command:
    sys.exit(1)

# Execute the command
message = f"[{datetime.now().isoformat()}] Executing command: {command}\n"
tee_logger.write(message)

try:
    success, output, attempt = execute_task(agent, command, logger_callback, tee_logger)
    
    if not success:
        message = f"[{datetime.now().isoformat()}] Task did not complete successfully after {attempt} attempts.\n"
        tee_logger.write(message)
    else:
        # Run improvement loop if server is running on port 8000
        if is_port_listening(8000):
            run_improvement_loop(agent, logger_callback, tee_logger)
        else:
            message = f"[{datetime.now().isoformat()}] No server detected on port 8000. Skipping improvement loop.\n"
            tee_logger.write(message)
except KeyboardInterrupt:
    message = f"[{datetime.now().isoformat()}] Interrupted by user.\n"
    tee_logger.write(message)
finally:
    # Cleanup
    sys.stdout = original_stdout
    
    # Keep script alive if servers are running
    background_servers = get_background_servers()
    if background_servers:
        print(f"\n{len(background_servers)} server(s) running in background. Keeping container alive...")
        print("Press Ctrl+C to stop.")
        
        try:
            while any(p.poll() is None for p in background_servers):
                time.sleep(1)
            print("All servers have stopped.")
        except KeyboardInterrupt:
            print("\nStopping servers...")
            for p in background_servers:
                if p.poll() is None:
                    p.terminate()
    
    tee_logger.close()
