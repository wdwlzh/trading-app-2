FROM mcr.microsoft.com/vscode/devcontainers/python:0-3.11

# Install system dependencies
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
        postgresql-client \
        redis-tools \
        curl \
        wget \
        git \
        build-essential \
        libpq-dev \
        pkg-config \
        libhdf5-dev \
    && apt-get autoremove -y && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# Install Python dependencies for common data science packages
# This speeds up container startup by pre-installing heavy packages
RUN pip install --upgrade pip setuptools wheel

# Pre-install common heavy packages to speed up development
RUN pip install \
    pandas>=1.5.0 \
    numpy>=1.24.0 \
    scipy>=1.10.0 \
    sqlalchemy>=2.0.0 \
    psycopg2-binary>=2.9.0 \
    redis>=4.5.0 \
    asyncio-mqtt \
    fastapi>=0.95.0 \
    uvicorn>=0.21.0

# Install Interactive Brokers API
RUN pip install ib_insync>=0.9.86

# Install development tools
RUN pip install \
    pytest>=7.3.0 \
    black>=23.0.0 \
    flake8>=6.0.0 \
    jupyter \
    ipython

# Create workspace directory
RUN mkdir -p /workspace
WORKDIR /workspace

# Create non-root user for security
RUN groupadd --gid 1000 vscode \
    && useradd --uid 1000 --gid vscode --shell /bin/bash --create-home vscode \
    && mkdir -p /home/vscode/.vscode-server/extensions \
    && chown -R vscode:vscode /home/vscode \
    && chown -R vscode:vscode /workspace

# Switch to non-root user
USER vscode

# Set environment variables
ENV PYTHONPATH=/workspace/src
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
