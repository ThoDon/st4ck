FROM python:3.12-slim

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional dependencies for tagging
RUN pip install --no-cache-dir mutagen==1.47.0 colorama==0.4.6 tqdm==4.66.1

COPY . .

# Copy tagger module from build context
COPY tagger ./tagger

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
