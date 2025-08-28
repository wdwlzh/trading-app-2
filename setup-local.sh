#!/bin/bash

# Local development setup script
# Use this if you prefer local development without containers

echo "🔧 Setting up Trading App for Local Development"

# Check Python version
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
major_version=$(echo $python_version | cut -d. -f1)
minor_version=$(echo $python_version | cut -d. -f2)

if [ "$major_version" -lt 3 ] || [ "$major_version" -eq 3 -a "$minor_version" -lt 9 ]; then
    echo "❌ Python 3.9+ required. Found: Python $python_version"
    exit 1
fi

echo "✅ Python $python_version detected"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "🔧 Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "🔧 Installing Python dependencies..."
pip install -r requirements.txt

# Create environment file
if [ ! -f ".env" ]; then
    echo "🔧 Creating environment file..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration"
fi

# Create necessary directories
echo "🔧 Creating directories..."
mkdir -p logs data data/backups config

echo "✅ Local development setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Edit .env file with your database credentials"
echo "2. Install and start PostgreSQL and Redis"
echo "3. Run: source venv/bin/activate"
echo "4. Run: python setup.py"
echo "5. Run: python main.py"
echo ""
echo "🐳 Alternative: Use 'code .' and select 'Reopen in Container' for full containerized development"
