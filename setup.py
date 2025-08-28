"""
Setup script for initial database and environment configuration.
"""
import asyncio
import os
import sys
from datetime import datetime

# Add src to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.core.config import config
from src.core.database import db_manager


async def setup_database():
    """Setup database and create initial tables"""
    print("Setting up database...")
    
    try:
        # Create all tables
        db_manager.create_tables()
        print("✓ Database tables created successfully")
        
        # Test database connection
        with db_manager.get_session() as session:
            result = session.execute("SELECT 1").fetchone()
            if result:
                print("✓ Database connection test passed")
        
        # Test Redis connection
        redis_client = db_manager.get_redis()
        redis_client.ping()
        print("✓ Redis connection test passed")
        
        return True
        
    except Exception as e:
        print(f"✗ Database setup failed: {e}")
        return False


def check_environment():
    """Check if all required environment variables are set"""
    print("Checking environment configuration...")
    
    required_vars = [
        'POSTGRES_PASSWORD',
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"✗ Missing environment variables: {missing_vars}")
        print("Please create a .env file based on .env.example")
        return False
    
    print("✓ Environment configuration is valid")
    return True


def check_ib_connection():
    """Check if IB TWS/Gateway is running and accessible"""
    print("Checking IB TWS connection...")
    
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((config.ib.host, config.ib.port))
        sock.close()
        
        if result == 0:
            print("✓ IB TWS/Gateway is accessible")
            return True
        else:
            print("⚠ IB TWS/Gateway is not running or not accessible")
            print(f"  Make sure TWS or Gateway is running on {config.ib.host}:{config.ib.port}")
            print("  The application will run in offline mode for now")
            return False
            
    except Exception as e:
        print(f"⚠ Could not check IB connection: {e}")
        return False


def create_directories():
    """Create necessary directories"""
    print("Creating directories...")
    
    directories = [
        'logs',
        'data',
        'data/backups',
        'config'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    print("✓ Directories created")


async def main():
    """Main setup function"""
    print("=" * 50)
    print("Trading Application Setup")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        return 1
    
    # Create directories
    create_directories()
    
    # Setup database
    if not await setup_database():
        return 1
    
    # Check IB connection (optional for Phase 1)
    check_ib_connection()
    
    print("\n" + "=" * 50)
    print("Setup completed successfully!")
    print("=" * 50)
    print("\nNext steps:")
    print("1. Start IB TWS or Gateway (if not already running)")
    print("2. Run: python main.py")
    print("3. Check the logs directory for application logs")
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
