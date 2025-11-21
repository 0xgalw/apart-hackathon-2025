import subprocess
import sys
import time

container_name = "malicious-agent-demo"
filepath = "/app/logs/agent_trace.jsonl"

print(f"Attaching to {container_name} {filepath}...")

cmd = ['docker', 'exec', container_name, 'tail', '-f', filepath]

process = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1
)

print("Attached. Waiting for lines...")

try:
    while True:
        line = process.stdout.readline()
        if not line:
            if process.poll() is not None:
                print("Process exited")
                break
            time.sleep(0.1)
            continue
        print(f"LINE: {line.strip()}")
except KeyboardInterrupt:
    process.terminate()
