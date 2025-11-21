"""Main execution logic for agent."""
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from langchain_core.messages import HumanMessage
from langchain_module import get_background_servers, is_port_listening
from utils_module import get_review_prompt_file, read_file_content


def extract_output(result):
    """Extract output message from agent result."""
    if "messages" in result and len(result["messages"]) > 0:
        last_message = result["messages"][-1]
        if hasattr(last_message, "content"):
            return last_message.content
        return str(last_message)
    return str(result)


def check_success(output):
    """Check if output indicates success."""
    output_lower = output.lower()
    success_indicators = [
        "successfully", "completed", "done", "finished",
        "accomplished", "created", "installed", "running"
    ]
    error_indicators = [
        "error:", "failed to", "cannot", "unable to",
        "exception", "traceback", "fatal error"
    ]
    
    has_success = any(indicator in output_lower for indicator in success_indicators)
    has_error = any(indicator in output_lower for indicator in error_indicators)
    
    return has_success or not has_error


def invoke_agent_with_timeout(agent, messages, logger_callback, timeout=300):
    """
    Invoke agent with timeout protection.
    
    Args:
        agent: Agent instance
        messages: List of messages
        logger_callback: Logger callback
        timeout: Timeout in seconds
        
    Returns:
        Agent result
        
    Raises:
        FutureTimeoutError: If invocation times out
    """
    def invoke_agent():
        return agent.invoke(
            {"messages": messages},
            config={"callbacks": [logger_callback]}
        )
    
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(invoke_agent)
        return future.result(timeout=timeout)


def execute_task(agent, command, logger_callback, tee_logger, max_attempts=None):
    """
    Execute task with retry logic.
    
    Args:
        agent: Agent instance
        command: Task command/prompt
        logger_callback: Logger callback
        tee_logger: Tee logger instance
        max_attempts: Maximum retry attempts (None for infinite)
        
    Returns:
        Tuple of (success: bool, output: str, attempt: int)
    """
    attempt = 0
    last_error = None
    
    while True:
        attempt += 1
        message = f"[{datetime.now().isoformat()}] Attempt {attempt}...\n"
        tee_logger.write(message)
        
        messages = [HumanMessage(content=command)]
        if attempt > 1 and last_error:
            retry_message = (
                f"The previous attempt encountered an error: {last_error}. "
                "Please try again with a different approach and keep trying until the task succeeds."
            )
            messages.append(HumanMessage(content=retry_message))
        
        message = f"[{datetime.now().isoformat()}] Invoking agent (timeout: 5 minutes)...\n"
        tee_logger.write(message)
        
        try:
            result = invoke_agent_with_timeout(agent, messages, logger_callback, timeout=300)
            output = extract_output(result)
            
            if check_success(output):
                message = f"[{datetime.now().isoformat()}] Result (Attempt {attempt}): {output}\n"
                tee_logger.write(message)
                return True, output, attempt
            else:
                last_error = output
                message = f"[{datetime.now().isoformat()}] Attempt {attempt} encountered errors: {output}\n"
                message += f"[{datetime.now().isoformat()}] Retrying with a different approach...\n"
                tee_logger.write(message)
                time.sleep(1)
                
        except FutureTimeoutError:
            last_error = "Agent invocation timed out"
            message = f"[{datetime.now().isoformat()}] Agent invocation timed out after 5 minutes. Retrying...\n"
            tee_logger.write(message)
            time.sleep(2)
            
        if max_attempts is not None and attempt >= max_attempts:
            message = f"[{datetime.now().isoformat()}] Reached maximum attempts ({max_attempts}). Stopping.\n"
            tee_logger.write(message)
            return False, last_error or "Max attempts reached", attempt


def run_improvement_loop(agent, logger_callback, tee_logger, max_improvements=None):
    """
    Run improvement loop for website enhancement.
    
    Args:
        agent: Agent instance
        logger_callback: Logger callback
        tee_logger: Tee logger instance
        max_improvements: Maximum improvement iterations (None for infinite)
    """
    # Check if port 8000 is listening (more reliable than checking process list)
    if not is_port_listening(8000):
        message = f"[{datetime.now().isoformat()}] No server detected on port 8000. Skipping improvement loop.\n"
        tee_logger.write(message)
        return
    
    message = f"[{datetime.now().isoformat()}] Website server is running. Sleeping for 5 seconds before starting improvement loop...\n"
    tee_logger.write(message)
    time.sleep(5)
    
    message = f"[{datetime.now().isoformat()}] Starting improvement loop to enhance the website...\n"
    tee_logger.write(message)
    
    improvement_attempt = 0
    
    while True:
        improvement_attempt += 1
        message = f"[{datetime.now().isoformat()}] Improvement iteration {improvement_attempt}...\n"
        tee_logger.write(message)
        
        # Check if server is still running on port 8000
        if not is_port_listening(8000):
            message = f"[{datetime.now().isoformat()}] Server stopped. Exiting improvement loop.\n"
            tee_logger.write(message)
            break
        
        review_prompt_file = get_review_prompt_file()
        improvement_prompt = read_file_content(review_prompt_file)
        messages = [HumanMessage(content=improvement_prompt)]
        
        message = f"[{datetime.now().isoformat()}] Invoking agent for improvement (timeout: 5 minutes)...\n"
        tee_logger.write(message)
        
        try:
            result = invoke_agent_with_timeout(agent, messages, logger_callback, timeout=300)
            output = extract_output(result)
            
            message = f"[{datetime.now().isoformat()}] Improvement {improvement_attempt} completed: {output}\n"
            tee_logger.write(message)
            time.sleep(2)
            
        except FutureTimeoutError:
            message = f"[{datetime.now().isoformat()}] Improvement invocation timed out after 5 minutes. Continuing to next improvement...\n"
            tee_logger.write(message)
            time.sleep(2)
            continue
        
        if max_improvements is not None and improvement_attempt >= max_improvements:
            message = f"[{datetime.now().isoformat()}] Reached maximum improvements ({max_improvements}). Stopping improvement loop.\n"
            tee_logger.write(message)
            break

