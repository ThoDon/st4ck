FROM alpine:latest

# Install curl and redis-cli
RUN apk add --no-cache curl redis

# Copy the mover script
COPY mover.sh /usr/local/bin/mover.sh

# Make the script executable
RUN chmod +x /usr/local/bin/mover.sh

# Verify the script exists and is executable
RUN ls -la /usr/local/bin/mover.sh

# Set the entrypoint using sh to execute the script
ENTRYPOINT ["sh", "/usr/local/bin/mover.sh"]
