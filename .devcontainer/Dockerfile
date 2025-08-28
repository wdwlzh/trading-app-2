FROM mcr.microsoft.com/devcontainers/python:1-3.11-bullseye

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    redis-tools \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /workspace

# Set environment variables
ENV PYTHONPATH=/workspace/src
ENV PYTHONUNBUFFERED=1
