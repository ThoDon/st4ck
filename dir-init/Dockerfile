FROM alpine:latest

# Install bash for better script support
RUN apk add --no-cache bash

# Copy the directory creation script
COPY create-dirs.sh /create-dirs.sh
RUN chmod +x /create-dirs.sh

# Set the script as the entrypoint
ENTRYPOINT ["/create-dirs.sh"]
