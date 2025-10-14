FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    redis-tools \
    curl \
    wget \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Docker CLI
RUN curl -fsSL https://get.docker.com -o get-docker.sh && \
    sh get-docker.sh && \
    rm get-docker.sh

# Create alias for m4b-tool using Docker with proper volume mounting
RUN echo '#!/bin/bash\n# m4b-tool wrapper for Docker-in-Docker\n# Mount the root directory and use absolute paths\n\ndocker run --rm -u $(id -u):$(id -g) -v /:/mnt --workdir /mnt sandreas/m4b-tool:latest "$@"' > /usr/local/bin/m4b-tool && \
    chmod +x /usr/local/bin/m4b-tool

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create output directory and ensure permissions
RUN mkdir -p /converted && \
    chmod 777 /converted

# Run as root for Docker-in-Docker access
# USER converter

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import redis; r=redis.Redis(host='redis', port=6379, db=0); r.ping()" || exit 1

# Default command
CMD ["python", "converter.py"]