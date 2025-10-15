# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json pnpm-lock.yaml* yarn.lock* ./

# Install dependencies
RUN npm install

# Copy source code (excluding node_modules and other generated files via .dockerignore)
COPY . .

# Build the application with environment variable
ARG VITE_API_URL=http://localhost:8081
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# Production stage
FROM node:20-alpine AS production

WORKDIR /app

# Install serve to run the built app
RUN npm install -g serve

# Copy built application from builder stage
COPY --from=builder /app/dist ./dist

# Create a runtime configuration script
RUN echo '#!/bin/sh' > /app/start.sh && \
    echo 'echo "Starting UI with API URL: ${VITE_API_URL:-http://localhost:8081}"' >> /app/start.sh && \
    echo 'serve -s dist -l 3000' >> /app/start.sh && \
    chmod +x /app/start.sh

EXPOSE 3000

CMD ["/app/start.sh"]
