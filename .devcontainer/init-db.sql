-- Initialize database with TimescaleDB extension and create user

-- Create the trading user if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'trading_user') THEN
        CREATE ROLE trading_user LOGIN PASSWORD 'secure_password_123';
    END IF;
END
$$;

-- Grant necessary privileges
GRANT ALL PRIVILEGES ON DATABASE trading_app TO trading_user;

-- Connect to the trading_app database
\c trading_app

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO trading_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO trading_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO trading_user;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO trading_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO trading_user;
