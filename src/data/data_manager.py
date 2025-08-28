"""
Data manager for handling historical and real-time market data.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from .ib_connector import ib_connector
from ..core.database import db_manager, MarketData
from ..core.config import config
from ..core.exceptions import DataException, DataNotFoundError, DataQualityError

logger = logging.getLogger(__name__)


class DataManager:
    """Manages historical and real-time market data operations"""
    
    def __init__(self):
        self.ib_connector = ib_connector
        self.db_manager = db_manager
        self.redis_client = self.db_manager.get_redis()
        
        # Cache settings
        self.cache_expiry = 3600  # 1 hour cache expiry
        self.supported_timeframes = ['1min', '5min', '15min', '30min', '1hour', '1day']
        
        # Data validation settings
        self.max_gap_tolerance = {
            '1min': timedelta(minutes=5),
            '5min': timedelta(minutes=25),
            '15min': timedelta(hours=1),
            '30min': timedelta(hours=2),
            '1hour': timedelta(hours=4),
            '1day': timedelta(days=3)
        }
    
    async def initialize(self) -> bool:
        """Initialize data manager and establish connections"""
        try:
            # Connect to IB if not connected
            if not self.ib_connector.is_connected:
                await self.ib_connector.connect()
            
            logger.info("Data manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize data manager: {e}")
            return False
    
    async def fetch_and_store_historical_data(self, 
                                             symbol: str,
                                             duration: str = "2 Y",
                                             timeframes: List[str] = None) -> Dict[str, int]:
        """
        Fetch historical data from IB and store in database.
        
        Args:
            symbol: Stock symbol
            duration: Data duration ('1 Y', '2 Y', '5 Y')
            timeframes: List of timeframes to fetch
            
        Returns:
            Dictionary with counts of records stored per timeframe
        """
        if timeframes is None:
            timeframes = ['1 day', '1 hour', '5 mins']
        
        results = {}
        
        for timeframe in timeframes:
            try:
                logger.info(f"Fetching {symbol} {timeframe} data for {duration}")
                
                # Fetch data from IB
                df = await self.ib_connector.get_historical_data(
                    symbol=symbol,
                    duration=duration,
                    bar_size=timeframe
                )
                
                if df.empty:
                    logger.warning(f"No data received for {symbol} {timeframe}")
                    results[timeframe] = 0
                    continue
                
                # Validate data quality
                validation_result = self._validate_data_quality(df, timeframe)
                if not validation_result['valid']:
                    logger.warning(f"Data quality issues for {symbol} {timeframe}: {validation_result['issues']}")
                
                # Store in database
                stored_count = await self._store_market_data(df, symbol)
                results[timeframe] = stored_count
                
                logger.info(f"Stored {stored_count} records for {symbol} {timeframe}")
                
                # Cache latest data point
                await self._cache_latest_data(symbol, df.iloc[-1:])
                
            except Exception as e:
                logger.error(f"Error fetching {symbol} {timeframe}: {e}")
                results[timeframe] = 0
        
        return results
    
    async def get_historical_data(self, 
                                 symbol: str,
                                 timeframe: str = '1day',
                                 start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None,
                                 periods: Optional[int] = None) -> pd.DataFrame:
        """
        Get historical data from database with optional caching.
        
        Args:
            symbol: Stock symbol
            timeframe: Data timeframe
            start_date: Start date for data
            end_date: End date for data
            periods: Number of recent periods to retrieve
            
        Returns:
            DataFrame with historical data
        """
        try:
            # Check cache first for recent data
            if periods and periods <= 100:
                cached_data = await self._get_cached_data(symbol, timeframe, periods)
                if cached_data is not None:
                    return cached_data
            
            # Query database
            with self.db_manager.get_session() as session:
                query = session.query(MarketData).filter(
                    MarketData.symbol == symbol,
                    MarketData.timeframe == timeframe
                )
                
                if start_date:
                    query = query.filter(MarketData.timestamp >= start_date)
                if end_date:
                    query = query.filter(MarketData.timestamp <= end_date)
                
                query = query.order_by(MarketData.timestamp)
                
                if periods:
                    query = query.order_by(desc(MarketData.timestamp)).limit(periods)
                    # Reverse to get chronological order
                    results = list(reversed(query.all()))
                else:
                    results = query.all()
                
                if not results:
                    raise DataNotFoundError(f"No data found for {symbol} {timeframe}")
                
                # Convert to DataFrame
                df = pd.DataFrame([record.to_dict() for record in results])
                df.set_index('timestamp', inplace=True)
                df.sort_index(inplace=True)
                
                # Cache if small dataset
                if len(df) <= 1000:
                    await self._cache_data(symbol, timeframe, df)
                
                logger.info(f"Retrieved {len(df)} records for {symbol} {timeframe}")
                return df
                
        except Exception as e:
            logger.error(f"Error retrieving historical data for {symbol}: {e}")
            raise DataException(f"Failed to retrieve historical data: {e}")
    
    async def get_latest_data(self, symbol: str, timeframe: str = '1day') -> Optional[Dict]:
        """Get latest data point for a symbol"""
        try:
            # Check cache first
            cache_key = f"latest:{symbol}:{timeframe}"
            cached_data = self.redis_client.hgetall(cache_key)
            
            if cached_data:
                return {k: float(v) if k in ['open', 'high', 'low', 'close'] else v 
                       for k, v in cached_data.items()}
            
            # Query database
            with self.db_manager.get_session() as session:
                latest_record = session.query(MarketData).filter(
                    MarketData.symbol == symbol,
                    MarketData.timeframe == timeframe
                ).order_by(desc(MarketData.timestamp)).first()
                
                if latest_record:
                    data = latest_record.to_dict()
                    # Cache for 5 minutes
                    await self._cache_latest_data_point(symbol, timeframe, data, expiry=300)
                    return data
                
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving latest data for {symbol}: {e}")
            return None
    
    async def update_incremental_data(self, symbol: str) -> Dict[str, int]:
        """Update data with any missing recent periods"""
        results = {}
        
        try:
            for timeframe in self.supported_timeframes:
                ib_timeframe = self._get_ib_timeframe(timeframe)
                if not ib_timeframe:
                    continue
                
                # Get latest data point from database
                latest_data = await self.get_latest_data(symbol, timeframe)
                
                if latest_data:
                    latest_timestamp = pd.to_datetime(latest_data['timestamp'])
                    
                    # Determine how much data to fetch
                    duration = self._calculate_update_duration(latest_timestamp, timeframe)
                    
                    if duration:
                        # Fetch incremental data
                        df = await self.ib_connector.get_historical_data(
                            symbol=symbol,
                            duration=duration,
                            bar_size=ib_timeframe
                        )
                        
                        if not df.empty:
                            # Filter only new data
                            new_data = df[df.index > latest_timestamp]
                            if not new_data.empty:
                                stored_count = await self._store_market_data(new_data, symbol)
                                results[timeframe] = stored_count
                            else:
                                results[timeframe] = 0
                else:
                    # No data exists, fetch initial data
                    results[timeframe] = 0
                    
        except Exception as e:
            logger.error(f"Error updating incremental data for {symbol}: {e}")
        
        return results
    
    async def _store_market_data(self, df: pd.DataFrame, symbol: str) -> int:
        """Store market data in database with conflict handling"""
        stored_count = 0
        
        try:
            with self.db_manager.get_session() as session:
                for idx, row in df.iterrows():
                    # Check if record already exists
                    existing = session.query(MarketData).filter(
                        and_(
                            MarketData.symbol == symbol,
                            MarketData.timestamp == idx,
                            MarketData.timeframe == row['timeframe']
                        )
                    ).first()
                    
                    if not existing:
                        market_data = MarketData(
                            timestamp=idx,
                            symbol=symbol,
                            open=float(row['open']),
                            high=float(row['high']),
                            low=float(row['low']),
                            close=float(row['close']),
                            volume=int(row['volume']),
                            timeframe=row['timeframe']
                        )
                        session.add(market_data)
                        stored_count += 1
                
                session.commit()
                
        except Exception as e:
            logger.error(f"Error storing market data: {e}")
            session.rollback()
            raise DataException(f"Failed to store market data: {e}")
        
        return stored_count
    
    def _validate_data_quality(self, df: pd.DataFrame, timeframe: str) -> Dict:
        """Validate data quality and identify issues"""
        issues = []
        
        if df.empty:
            return {'valid': False, 'issues': ['Empty dataset']}
        
        # Check for required columns
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            issues.append(f"Missing columns: {missing_cols}")
        
        # Check for NaN values
        if df[required_cols].isna().any().any():
            issues.append("Contains NaN values")
        
        # Check OHLC relationships
        if 'high' in df.columns and 'low' in df.columns:
            invalid_high_low = (df['high'] < df['low']).sum()
            if invalid_high_low > 0:
                issues.append(f"High < Low in {invalid_high_low} records")
        
        # Check for negative prices
        for col in ['open', 'high', 'low', 'close']:
            if col in df.columns:
                negative_count = (df[col] <= 0).sum()
                if negative_count > 0:
                    issues.append(f"Negative/zero prices in {col}: {negative_count}")
        
        # Check for data gaps
        if len(df) > 1:
            time_diffs = df.index.to_series().diff().dropna()
            expected_freq = self._get_expected_frequency(timeframe)
            if expected_freq:
                large_gaps = (time_diffs > expected_freq * 3).sum()  # Gaps > 3x expected
                if large_gaps > 0:
                    issues.append(f"Large time gaps detected: {large_gaps}")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'record_count': len(df)
        }
    
    def _get_expected_frequency(self, timeframe: str) -> Optional[timedelta]:
        """Get expected frequency for timeframe"""
        freq_map = {
            '1min': timedelta(minutes=1),
            '5min': timedelta(minutes=5),
            '15min': timedelta(minutes=15),
            '30min': timedelta(minutes=30),
            '1hour': timedelta(hours=1),
            '1day': timedelta(days=1)
        }
        return freq_map.get(timeframe)
    
    def _get_ib_timeframe(self, internal_timeframe: str) -> Optional[str]:
        """Convert internal timeframe to IB timeframe"""
        mapping = {
            '1min': '1 min',
            '5min': '5 mins',
            '15min': '15 mins',
            '30min': '30 mins',
            '1hour': '1 hour',
            '1day': '1 day'
        }
        return mapping.get(internal_timeframe)
    
    def _calculate_update_duration(self, latest_timestamp: datetime, timeframe: str) -> Optional[str]:
        """Calculate duration needed to update from latest timestamp"""
        now = datetime.now(latest_timestamp.tzinfo)
        time_diff = now - latest_timestamp
        
        # Determine appropriate duration based on time difference
        if time_diff <= timedelta(days=1):
            return "1 D"
        elif time_diff <= timedelta(days=7):
            return "1 W"
        elif time_diff <= timedelta(days=30):
            return "1 M"
        else:
            return "3 M"
    
    async def _cache_latest_data(self, symbol: str, df: pd.DataFrame):
        """Cache latest data points in Redis"""
        if df.empty:
            return
        
        latest = df.iloc[-1]
        cache_key = f"latest:{symbol}:{latest['timeframe']}"
        
        data_dict = {
            'timestamp': str(latest.name),
            'open': str(latest['open']),
            'high': str(latest['high']),
            'low': str(latest['low']),
            'close': str(latest['close']),
            'volume': str(latest['volume'])
        }
        
        self.redis_client.hmset(cache_key, data_dict)
        self.redis_client.expire(cache_key, self.cache_expiry)
    
    async def _cache_latest_data_point(self, symbol: str, timeframe: str, data: Dict, expiry: int = 3600):
        """Cache a single data point"""
        cache_key = f"latest:{symbol}:{timeframe}"
        
        data_dict = {k: str(v) for k, v in data.items() if k != 'timestamp'}
        data_dict['timestamp'] = str(data['timestamp'])
        
        self.redis_client.hmset(cache_key, data_dict)
        self.redis_client.expire(cache_key, expiry)
    
    async def _get_cached_data(self, symbol: str, timeframe: str, periods: int) -> Optional[pd.DataFrame]:
        """Get cached data from Redis"""
        cache_key = f"data:{symbol}:{timeframe}:{periods}"
        cached_json = self.redis_client.get(cache_key)
        
        if cached_json:
            try:
                df = pd.read_json(cached_json)
                df.index = pd.to_datetime(df.index)
                return df
            except Exception as e:
                logger.warning(f"Error reading cached data: {e}")
        
        return None
    
    async def _cache_data(self, symbol: str, timeframe: str, df: pd.DataFrame):
        """Cache DataFrame in Redis"""
        cache_key = f"data:{symbol}:{timeframe}:{len(df)}"
        
        try:
            json_data = df.to_json()
            self.redis_client.setex(cache_key, self.cache_expiry, json_data)
        except Exception as e:
            logger.warning(f"Error caching data: {e}")
    
    def cleanup_old_data(self, symbol: str, days_to_keep: int = 1825):  # 5 years default
        """Clean up old data to manage database size"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            with self.db_manager.get_session() as session:
                deleted_count = session.query(MarketData).filter(
                    and_(
                        MarketData.symbol == symbol,
                        MarketData.timestamp < cutoff_date
                    )
                ).delete()
                
                session.commit()
                logger.info(f"Cleaned up {deleted_count} old records for {symbol}")
                
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")


# Global data manager instance
data_manager = DataManager()
