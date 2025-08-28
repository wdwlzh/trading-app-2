"""
Core configuration settings for the trading application.
"""
import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class IBConfig:
    """Interactive Brokers connection configuration"""
    host: str = "127.0.0.1"
    port: int = 7497  # Paper trading port (7496 for live)
    client_id: int = 1
    account_id: Optional[str] = None
    
    # Connection settings
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 5.0


@dataclass
class DatabaseConfig:
    """Database configuration"""
    # PostgreSQL for transactional data
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "trading_app"
    postgres_user: str = "trading_user"
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "")
    
    # Redis for caching
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = os.getenv("REDIS_PASSWORD", "")
    
    # Connection pool settings
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30


@dataclass
class TradingConfig:
    """Trading configuration"""
    # Risk management
    initial_capital: float = 100000.0
    max_position_size_pct: float = 0.10  # 10% of account
    max_daily_loss_pct: float = 0.05     # 5% daily loss limit
    risk_per_trade_pct: float = 0.02     # 2% risk per trade
    
    # Order execution
    default_order_type: str = "MKT"
    commission_rate: float = 0.0005      # 5 basis points
    min_commission: float = 1.0
    
    # Market data
    primary_symbol: str = "QQQ"
    data_timeframes: list = None
    
    def __post_init__(self):
        if self.data_timeframes is None:
            self.data_timeframes = ["1 min", "5 mins", "1 hour", "1 day"]


@dataclass
class BacktestConfig:
    """Backtesting configuration"""
    initial_capital: float = 100000.0
    commission_rate: float = 0.001
    slippage_rate: float = 0.0005
    
    # Data settings
    lookback_years: int = 5
    warmup_period: int = 50
    
    # Performance settings
    benchmark_symbol: str = "SPY"
    risk_free_rate: float = 0.02


class Config:
    """Main configuration class"""
    
    def __init__(self):
        self.ib = IBConfig()
        self.database = DatabaseConfig()
        self.trading = TradingConfig()
        self.backtest = BacktestConfig()
        
        # Environment settings
        self.environment = os.getenv("TRADING_ENV", "development")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        
        # Logging
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_file = os.getenv("LOG_FILE", "logs/trading_app.log")
        
        # Data directories
        self.data_dir = "data"
        self.backup_dir = "data/backups"
        
        # Load environment-specific overrides
        self._load_env_overrides()
    
    def _load_env_overrides(self):
        """Load environment-specific configuration overrides"""
        if self.environment == "production":
            self.ib.port = 7496  # Live trading port
            self.trading.commission_rate = 0.0005  # Production commission rate
        elif self.environment == "testing":
            self.database.postgres_db = "trading_app_test"
            self.trading.initial_capital = 10000.0  # Smaller test capital
    
    def get_db_url(self) -> str:
        """Get PostgreSQL database URL"""
        return (f"postgresql://{self.database.postgres_user}:"
                f"{self.database.postgres_password}@"
                f"{self.database.postgres_host}:{self.database.postgres_port}/"
                f"{self.database.postgres_db}")
    
    def get_redis_url(self) -> str:
        """Get Redis connection URL"""
        auth = f":{self.database.redis_password}@" if self.database.redis_password else ""
        return (f"redis://{auth}{self.database.redis_host}:"
                f"{self.database.redis_port}/{self.database.redis_db}")


# Global configuration instance
config = Config()
