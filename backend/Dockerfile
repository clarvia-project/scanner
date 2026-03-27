FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY schema.sql .

# Copy prebuilt scan data
COPY data/ ./data/

# Create non-root user and ensure data dir is writable (for profiles.json)
RUN useradd --create-home appuser && chown -R appuser:appuser /app/data
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run with uvicorn
# Single worker to fit within 512MB RAM (Render Starter).
# Each worker duplicates all in-memory data (~100MB+), so 2 workers would OOM.
# Uvicorn's async event loop handles concurrency within one process.
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
