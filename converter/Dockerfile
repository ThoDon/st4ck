FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    redis-tools \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 converter && chown -R converter:converter /app
USER converter

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import redis; r=redis.Redis(host='redis', port=6379, db=0); r.ping()" || exit 1

# Default command
CMD ["python", "converter.py"]
