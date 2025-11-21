FROM python:3.11-slim

WORKDIR /app

# Install bash (required for the bash tool)
RUN apt-get update && apt-get install -y bash && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Copy prompt file
COPY prompts/ ./prompts/

# Copy config
COPY config.json ./config.json

# Copy example command file
COPY example_for_loop.txt ./example_for_loop.txt

# Set working directory to src
WORKDIR /app/src

# Run the interactive script
# Note: Command file should be passed as argument or mounted as volume
# Use unbuffered python output for better logging
CMD ["python", "-u", "interactive.py", "--loop"] 
#"/app/example_for_loop.txt"]

