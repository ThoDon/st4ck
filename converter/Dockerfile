FROM ubuntu:22.04

ARG TZ=America/New_York
ENV TZ=$TZ
ENV DEBIAN_FRONTEND=noninteractive

# Install general dependencies + tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    curl \
    wget \
    git \
    unzip \
    build-essential \
    cmake \
    autoconf \
    automake \
    libtool \
    libglib2.0-dev \
    pkg-config \
    ca-certificates \
    gnupg \
    lsb-release \
    software-properties-common \
    ffmpeg \
    redis-tools \
    python3 \
    python3-pip \
    python3-venv \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    dpkg-reconfigure -f noninteractive tzdata

# Create symlinks for python and pip (force overwrite if they exist)
RUN ln -sf /usr/bin/python3 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# Install PHP 8.2 from Sury PPA
RUN add-apt-repository ppa:ondrej/php -y && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    php8.2-cli \
    php8.2-curl \
    php8.2-mbstring \
    php8.2-xml \
    php8.2-zip && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Build and install libmp4v2 from sergiomb2
RUN curl -L https://github.com/sergiomb2/libmp4v2/archive/refs/heads/master.zip -o /tmp/libmp4v2.zip && \
    unzip -o /tmp/libmp4v2.zip -d /tmp && \
    cd /tmp/libmp4v2-master && \
    mkdir -p m4 && \
    autoreconf -i && \
    ./configure CXXFLAGS="-Wno-narrowing" && \
    make -j$(nproc) && \
    make install && \
    ldconfig && \
    rm -rf /tmp/libmp4v2*

# Add m4b-tool
COPY m4b-tool.phar /usr/local/bin/m4b-tool
RUN chmod +x /usr/local/bin/m4b-tool

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make conversion script executable
RUN chmod +x folder_m4b_builder.sh

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