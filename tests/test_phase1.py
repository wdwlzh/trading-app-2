"""
Basic tests for Phase 1 implementation
"""
import pytest
import asyncio
import pandas as pd
from datetime import datetime, timedelta

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.core.config import Config
from src.core.database import DatabaseManager, MarketData
from src.data.data_manager import DataManager


class TestConfig:
    """Test configuration management"""
    
    def test_config_initialization(self):
        """Test config loads properly"""
        config = Config()
        assert config.trading.initial_capital > 0
        assert config.ib.host is not None
        assert config.database.postgres_host is not None
    
    def test_database_url_generation(self):
        """Test database URL generation"""
        config = Config()
        db_url = config.get_db_url()
        assert 'postgresql://' in db_url
        assert config.database.postgres_db in db_url


class TestDatabase:
    """Test database operations"""
    
    @pytest.fixture
    def db_manager(self):
        """Database manager fixture"""
        return DatabaseManager()
    
    def test_database_tables_creation(self, db_manager):
        """Test that database tables can be created"""
        try:
            db_manager.create_tables()
            # If no exception, tables were created successfully
            assert True
        except Exception as e:
            pytest.fail(f"Failed to create database tables: {e}")
    
    def test_session_creation(self, db_manager):
        """Test database session creation"""
        session = db_manager.get_session()
        assert session is not None
        session.close()
    
    def test_redis_connection(self, db_manager):
        """Test Redis connection"""
        try:
            redis_client = db_manager.get_redis()
            redis_client.ping()
            assert True
        except Exception as e:
            pytest.skip(f"Redis not available: {e}")


class TestDataManager:
    """Test data management operations"""
    
    @pytest.fixture
    def data_manager(self):
        """Data manager fixture"""
        return DataManager()
    
    def test_data_validation(self, data_manager):
        """Test data quality validation"""
        # Create sample data
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'open': [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0],
            'high': [101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0],
            'low': [99.0, 100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0],
            'close': [100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5, 107.5, 108.5, 109.5],
            'volume': [1000000] * 10
        }, index=dates)
        
        # Test validation
        result = data_manager._validate_data_quality(df, '1day')
        assert result['valid'] is True
        assert len(result['issues']) == 0
    
    def test_timeframe_conversion(self, data_manager):
        """Test timeframe format conversion"""
        assert data_manager._get_ib_timeframe('1min') == '1 min'
        assert data_manager._get_ib_timeframe('5min') == '5 mins'
        assert data_manager._get_ib_timeframe('1hour') == '1 hour'
        assert data_manager._get_ib_timeframe('1day') == '1 day'
    
    def test_invalid_data_validation(self, data_manager):
        """Test validation catches invalid data"""
        # Create invalid data (high < low)
        dates = pd.date_range('2023-01-01', periods=5, freq='D')
        df = pd.DataFrame({
            'open': [100.0, 101.0, 102.0, 103.0, 104.0],
            'high': [99.0, 100.0, 101.0, 102.0, 103.0],  # Invalid: high < low
            'low': [101.0, 102.0, 103.0, 104.0, 105.0],
            'close': [100.5, 101.5, 102.5, 103.5, 104.5],
            'volume': [1000000] * 5
        }, index=dates)
        
        result = data_manager._validate_data_quality(df, '1day')
        assert result['valid'] is False
        assert any('High < Low' in issue for issue in result['issues'])


class TestMarketDataModel:
    """Test market data database model"""
    
    def test_market_data_creation(self):
        """Test creating market data record"""
        market_data = MarketData(
            timestamp=datetime.now(),
            symbol='QQQ',
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000000,
            timeframe='1day'
        )
        
        assert market_data.symbol == 'QQQ'
        assert market_data.open == 100.0
        assert market_data.timeframe == '1day'
    
    def test_market_data_to_dict(self):
        """Test market data conversion to dictionary"""
        market_data = MarketData(
            timestamp=datetime.now(),
            symbol='QQQ',
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000000,
            timeframe='1day'
        )
        
        data_dict = market_data.to_dict()
        assert 'symbol' in data_dict
        assert 'open' in data_dict
        assert data_dict['symbol'] == 'QQQ'
        assert data_dict['open'] == 100.0


# Integration tests (require actual database and IB connection)
class TestIntegration:
    """Integration tests - run only if services are available"""
    
    @pytest.mark.asyncio
    async def test_full_data_workflow(self):
        """Test complete data workflow - requires IB connection"""
        pytest.skip("Requires IB connection - run manually")
        
        data_manager = DataManager()
        
        # Initialize
        await data_manager.initialize()
        
        # This would test actual data fetching
        # df = await data_manager.get_historical_data('QQQ', '1day', periods=10)
        # assert not df.empty


if __name__ == "__main__":
    # Run basic tests
    pytest.main([__file__, "-v"])
