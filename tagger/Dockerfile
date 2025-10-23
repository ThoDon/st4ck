FROM python:3.11-alpine

# Install system dependencies
RUN apk add --no-cache curl

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the tagger script and required modules
COPY tagger.py .
COPY m4b_tagger.py .
COPY audible_client.py .
COPY constants.py .
COPY tagger_types.py .
COPY __init__.py .

# Make the script executable
RUN chmod +x tagger.py

# Set the entrypoint
ENTRYPOINT ["python", "tagger.py"]
