FROM python:3.12-slim

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional dependencies for tagging
RUN pip install --no-cache-dir mutagen==1.47.0 colorama==0.4.6 tqdm==4.66.1

COPY api/ .

# Copy tagger module from build context
COPY tagger ./tagger

# Copy the print_m4b_tags script
COPY print_m4b_tags.py .

# Copy database initialization script
COPY db-init ./db-init

EXPOSE 8000

CMD ["python", "main.py"]
