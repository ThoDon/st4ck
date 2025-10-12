# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json pnpm-lock.yaml* yarn.lock* ./

# Install dependencies
RUN npm install

# Copy source code (excluding node_modules and other generated files via .dockerignore)
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM node:20-alpine AS production

WORKDIR /app

# Install serve to run the built app
RUN npm install -g serve

# Copy built application from builder stage
COPY --from=builder /app/dist ./dist

# Create a simple startup script that injects the API URL at runtime
RUN echo '#!/bin/sh' > /app/start.sh && \
    echo 'if [ -n "$VITE_API_URL" ]; then' >> /app/start.sh && \
    echo '  echo "Setting API URL to: $VITE_API_URL"' >> /app/start.sh && \
    echo '  # Replace localhost:8081 with the actual API URL in all JS files' >> /app/start.sh && \
    echo '  find /app/dist -name "*.js" -exec sed -i "s|http://localhost:8081|$VITE_API_URL|g" {} \;' >> /app/start.sh && \
    echo 'fi' >> /app/start.sh && \
    echo 'serve -s dist -l 3000' >> /app/start.sh && \
    chmod +x /app/start.sh

EXPOSE 3000

CMD ["/app/start.sh"]
