FROM python:3.10-slim

WORKDIR /app

# Copy dependency definition
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy codebase
COPY . .

# Expose port
EXPOSE 8080

# Run API server
CMD ["python", "server.py", "--port", "8080"]
