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
COPY prompt.txt /app/prompt.txt

# Set working directory to src
WORKDIR /app/src

# Run the agent
# Note: OPENAI_API_KEY must be provided as environment variable
# Use unbuffered python output for better logging
CMD ["python", "-u", "agent.py"]

