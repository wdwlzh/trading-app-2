#!/bin/bash

# DigitalOcean deployment script
# Usage: ./deploy.sh [environment]

set -e

ENVIRONMENT=${1:-production}
DROPLET_IP=${DROPLET_IP:-"your-droplet-ip"}
DEPLOY_USER=${DEPLOY_USER:-"root"}

echo "🚀 Deploying Trading App to DigitalOcean ($ENVIRONMENT)"

# Check if required environment variables are set
if [ "$DROPLET_IP" = "your-droplet-ip" ]; then
    echo "❌ Please set DROPLET_IP environment variable"
    exit 1
fi

# Create deployment directory on droplet
ssh $DEPLOY_USER@$DROPLET_IP "mkdir -p /opt/trading-app"

# Copy files to droplet
echo "📦 Copying files to droplet..."
rsync -avz --exclude 'logs/' --exclude 'data/' --exclude '.git/' \
    ./ $DEPLOY_USER@$DROPLET_IP:/opt/trading-app/

# Set up environment file
ssh $DEPLOY_USER@$DROPLET_IP "cd /opt/trading-app && \
    if [ ! -f .env ]; then \
        cp .env.example .env; \
        echo '⚠️  Please edit /opt/trading-app/.env with your configuration'; \
    fi"

# Install Docker if not present
ssh $DEPLOY_USER@$DROPLET_IP "
    if ! command -v docker &> /dev/null; then
        echo '🐳 Installing Docker...'
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        systemctl enable docker
        systemctl start docker
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo '🐳 Installing Docker Compose...'
        curl -L \"https://github.com/docker/compose/releases/download/v2.20.2/docker-compose-\$(uname -s)-\$(uname -m)\" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
    fi
"

# Deploy the application
ssh $DEPLOY_USER@$DROPLET_IP "
    cd /opt/trading-app
    
    echo '🏗️  Building and starting services...'
    docker-compose -f docker-compose.prod.yml down
    docker-compose -f docker-compose.prod.yml build --no-cache
    docker-compose -f docker-compose.prod.yml up -d
    
    echo '⏳ Waiting for services to start...'
    sleep 30
    
    echo '🔍 Checking service status...'
    docker-compose -f docker-compose.prod.yml ps
    
    echo '📊 Application logs:'
    docker-compose -f docker-compose.prod.yml logs --tail=50 trading-app
"

echo "✅ Deployment completed!"
echo "🌐 Your trading app is running at: http://$DROPLET_IP"
echo "📝 Check logs: ssh $DEPLOY_USER@$DROPLET_IP 'cd /opt/trading-app && docker-compose -f docker-compose.prod.yml logs -f'"
