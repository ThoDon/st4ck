FROM alpine:latest

# Install curl
RUN apk add --no-cache curl

# Copy the mover script
COPY mover.sh /usr/local/bin/mover.sh

# Make the script executable
RUN chmod +x /usr/local/bin/mover.sh

# Set the entrypoint
ENTRYPOINT ["/usr/local/bin/mover.sh"]
