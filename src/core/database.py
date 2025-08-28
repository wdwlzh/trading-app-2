"""
Database models and connection management using SQLAlchemy.
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from decimal import Decimal

from sqlalchemy import (
    create_engine, 
    Column, 
    Integer, 
    String, 
    Decimal as SQLDecimal, 
    DateTime, 
    Text, 
    Boolean,
    BigInteger,
    Index,
    ForeignKey
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.pool import QueuePool
import redis

from .config import config
from .exceptions import DatabaseConnectionError, DatabaseException

Base = declarative_base()


class MarketData(Base):
    """Time series market data table"""
    __tablename__ = 'market_data'
    
    id = Column(BigInteger, primary_key=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    symbol = Column(String(10), nullable=False)
    open = Column(SQLDecimal(10, 4), nullable=False)
    high = Column(SQLDecimal(10, 4), nullable=False)
    low = Column(SQLDecimal(10, 4), nullable=False)
    close = Column(SQLDecimal(10, 4), nullable=False)
    volume = Column(BigInteger, nullable=False)
    timeframe = Column(String(10), nullable=False)  # '1min', '5min', '1hour', '1day'
    
    # Composite unique constraint
    __table_args__ = (
        Index('idx_market_data_symbol_time_tf', 'symbol', 'timestamp', 'timeframe', unique=True),
        Index('idx_market_data_timestamp', 'timestamp'),
        Index('idx_market_data_symbol_tf', 'symbol', 'timeframe'),
    )
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'symbol': self.symbol,
            'open': float(self.open),
            'high': float(self.high),
            'low': float(self.low),
            'close': float(self.close),
            'volume': self.volume,
            'timeframe': self.timeframe
        }


class Position(Base):
    """Portfolio positions table"""
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True)
    account_id = Column(String(50), nullable=False)
    symbol = Column(String(10), nullable=False)
    quantity = Column(Integer, nullable=False)
    avg_price = Column(SQLDecimal(10, 4), nullable=False)
    market_price = Column(SQLDecimal(10, 4), nullable=False)
    market_value = Column(SQLDecimal(12, 2), nullable=False)
    unrealized_pnl = Column(SQLDecimal(12, 2), nullable=False)
    realized_pnl = Column(SQLDecimal(12, 2), default=0.0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_positions_account_symbol', 'account_id', 'symbol', unique=True),
    )


class Order(Base):
    """Orders table"""
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(String(50), unique=True, nullable=False)
    account_id = Column(String(50), nullable=False)
    symbol = Column(String(10), nullable=False)
    action = Column(String(10), nullable=False)  # BUY/SELL
    quantity = Column(Integer, nullable=False)
    order_type = Column(String(20), nullable=False)  # MKT, LMT, STP, etc.
    limit_price = Column(SQLDecimal(10, 4), nullable=True)
    stop_price = Column(SQLDecimal(10, 4), nullable=True)
    status = Column(String(20), nullable=False)  # PENDING, FILLED, CANCELLED, etc.
    filled_quantity = Column(Integer, default=0)
    avg_fill_price = Column(SQLDecimal(10, 4), nullable=True)
    commission = Column(SQLDecimal(8, 2), default=0.0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    filled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    
    # Strategy metadata
    strategy_name = Column(String(50), nullable=True)
    signal_strength = Column(SQLDecimal(3, 2), nullable=True)
    metadata = Column(Text, nullable=True)  # JSON metadata
    
    __table_args__ = (
        Index('idx_orders_account_symbol', 'account_id', 'symbol'),
        Index('idx_orders_status', 'status'),
        Index('idx_orders_created_at', 'created_at'),
    )


class Trade(Base):
    """Completed trades table"""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    account_id = Column(String(50), nullable=False)
    symbol = Column(String(10), nullable=False)
    
    # Entry order
    entry_order_id = Column(String(50), nullable=False)
    entry_price = Column(SQLDecimal(10, 4), nullable=False)
    entry_quantity = Column(Integer, nullable=False)
    entry_timestamp = Column(DateTime(timezone=True), nullable=False)
    entry_commission = Column(SQLDecimal(8, 2), nullable=False)
    
    # Exit order (if applicable)
    exit_order_id = Column(String(50), nullable=True)
    exit_price = Column(SQLDecimal(10, 4), nullable=True)
    exit_quantity = Column(Integer, nullable=True)
    exit_timestamp = Column(DateTime(timezone=True), nullable=True)
    exit_commission = Column(SQLDecimal(8, 2), nullable=True)
    
    # Trade results
    realized_pnl = Column(SQLDecimal(12, 2), nullable=True)
    return_pct = Column(SQLDecimal(8, 4), nullable=True)
    trade_duration_minutes = Column(Integer, nullable=True)
    
    # Strategy information
    strategy_name = Column(String(50), nullable=True)
    entry_signal_strength = Column(SQLDecimal(3, 2), nullable=True)
    exit_reason = Column(String(50), nullable=True)  # STOP_LOSS, TAKE_PROFIT, SIGNAL, etc.
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_trades_account_symbol', 'account_id', 'symbol'),
        Index('idx_trades_strategy', 'strategy_name'),
        Index('idx_trades_entry_timestamp', 'entry_timestamp'),
    )


class Account(Base):
    """Account information table"""
    __tablename__ = 'accounts'
    
    id = Column(Integer, primary_key=True)
    account_id = Column(String(50), unique=True, nullable=False)
    account_type = Column(String(20), nullable=False)  # PAPER, LIVE
    
    # Account values
    net_liquidation = Column(SQLDecimal(12, 2), nullable=False)
    total_cash_value = Column(SQLDecimal(12, 2), nullable=False)
    settled_cash = Column(SQLDecimal(12, 2), nullable=False)
    buying_power = Column(SQLDecimal(12, 2), nullable=False)
    gross_position_value = Column(SQLDecimal(12, 2), nullable=False)
    unrealized_pnl = Column(SQLDecimal(12, 2), nullable=False)
    realized_pnl = Column(SQLDecimal(12, 2), nullable=False)
    
    # Risk metrics
    initial_margin_req = Column(SQLDecimal(12, 2), nullable=False)
    maintenance_margin_req = Column(SQLDecimal(12, 2), nullable=False)
    available_funds = Column(SQLDecimal(12, 2), nullable=False)
    excess_liquidity = Column(SQLDecimal(12, 2), nullable=False)
    
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    positions = relationship("Position", backref="account")
    orders = relationship("Order", backref="account")
    trades = relationship("Trade", backref="account")


class StrategyPerformance(Base):
    """Strategy performance tracking"""
    __tablename__ = 'strategy_performance'
    
    id = Column(Integer, primary_key=True)
    strategy_name = Column(String(50), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    
    # Performance metrics
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(SQLDecimal(5, 2), default=0.0)
    
    total_pnl = Column(SQLDecimal(12, 2), default=0.0)
    gross_profit = Column(SQLDecimal(12, 2), default=0.0)
    gross_loss = Column(SQLDecimal(12, 2), default=0.0)
    profit_factor = Column(SQLDecimal(8, 4), default=0.0)
    
    avg_win = Column(SQLDecimal(10, 2), default=0.0)
    avg_loss = Column(SQLDecimal(10, 2), default=0.0)
    max_win = Column(SQLDecimal(10, 2), default=0.0)
    max_loss = Column(SQLDecimal(10, 2), default=0.0)
    
    total_commission = Column(SQLDecimal(10, 2), default=0.0)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_strategy_performance_name_date', 'strategy_name', 'date'),
    )


class DatabaseManager:
    """Database connection and session management"""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self.redis_client = None
        self._initialize_connections()
    
    def _initialize_connections(self):
        """Initialize database connections"""
        try:
            # PostgreSQL connection
            self.engine = create_engine(
                config.get_db_url(),
                poolclass=QueuePool,
                pool_size=config.database.pool_size,
                max_overflow=config.database.max_overflow,
                pool_timeout=config.database.pool_timeout,
                echo=config.debug
            )
            
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            # Redis connection
            self.redis_client = redis.from_url(
                config.get_redis_url(),
                decode_responses=True,
                socket_connect_timeout=10,
                socket_timeout=10
            )
            
            # Test connections
            self._test_connections()
            
        except Exception as e:
            raise DatabaseConnectionError(f"Failed to initialize database connections: {e}")
    
    def _test_connections(self):
        """Test database connections"""
        try:
            # Test PostgreSQL
            with self.engine.connect() as conn:
                conn.execute("SELECT 1")
            
            # Test Redis
            self.redis_client.ping()
            
        except Exception as e:
            raise DatabaseConnectionError(f"Database connection test failed: {e}")
    
    def create_tables(self):
        """Create all database tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
        except Exception as e:
            raise DatabaseException(f"Failed to create tables: {e}")
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()
    
    def get_redis(self) -> redis.Redis:
        """Get Redis client"""
        return self.redis_client
    
    def close(self):
        """Close database connections"""
        if self.engine:
            self.engine.dispose()
        if self.redis_client:
            self.redis_client.close()


# Global database manager instance
db_manager = DatabaseManager()
