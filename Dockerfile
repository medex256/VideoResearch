FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x ./scripts/deployment/init-db.sh
EXPOSE 5000

# Optimized settings for production workloads:
# - 6 worker processes (good for both t3.large and m5.large)
# - 4 threads per worker for concurrent requests
# - gthread worker class for better IO performance
# - 30s timeout for slow requests
# - Keep-alive 5s to free up workers faster
CMD ["gunicorn", "--workers=6", "--threads=4", "--worker-class=gthread", "--timeout=30", "--keep-alive=5", "--max-requests=1000", "--max-requests-jitter=100", "--log-level=info", "--bind", "0.0.0.0:5000", "app:app"]