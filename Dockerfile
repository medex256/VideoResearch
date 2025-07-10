```dockerfile
# filepath: c:\Users\Madi\Documents\ResearchVideo\VideoProject\NewPortal\Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p instance

# Make scripts executable
RUN chmod +x scripts/setup.sh

EXPOSE 5000

CMD ["python", "app.py"]
```