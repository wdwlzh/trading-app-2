"""
Main application entry point for the trading system.
"""
import asyncio
import logging
import sys
from datetime import datetime
from typing import Dict, List

from src.core.config import config
from src.core.database import db_manager
from src.data.data_manager import data_manager
from src.data.ib_connector import ib_connector


# Setup logging
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class TradingApplication:
    """Main trading application class"""
    
    def __init__(self):
        self.is_running = False
        self.startup_complete = False
        
    async def startup(self) -> bool:
        """Initialize all application components"""
        logger.info("Starting Trading Application...")
        
        try:
            # Create database tables
            logger.info("Initializing database...")
            db_manager.create_tables()
            
            # Initialize data manager
            logger.info("Initializing data manager...")
            if not await data_manager.initialize():
                raise Exception("Failed to initialize data manager")
            
            # Test IB connection
            logger.info("Testing IB connection...")
            if not ib_connector.is_connected:
                logger.warning("IB connection not established - running in offline mode")
            
            self.startup_complete = True
            logger.info("Trading application startup completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start trading application: {e}")
            return False
    
    async def shutdown(self):
        """Gracefully shutdown the application"""
        logger.info("Shutting down trading application...")
        
        try:
            # Disconnect from IB
            if ib_connector.is_connected:
                ib_connector.disconnect()
            
            # Close database connections
            db_manager.close()
            
            self.is_running = False
            logger.info("Trading application shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    async def run_data_collection(self, symbols: List[str] = None):
        """Run initial data collection for specified symbols"""
        if symbols is None:
            symbols = [config.trading.primary_symbol]
        
        logger.info(f"Starting data collection for symbols: {symbols}")
        
        for symbol in symbols:
            try:
                logger.info(f"Collecting historical data for {symbol}")
                
                # Fetch 2 years of data in multiple timeframes
                results = await data_manager.fetch_and_store_historical_data(
                    symbol=symbol,
                    duration="2 Y",
                    timeframes=['1 day', '1 hour', '5 mins']
                )
                
                logger.info(f"Data collection results for {symbol}: {results}")
                
                # Fetch 5 years of daily data
                daily_results = await data_manager.fetch_and_store_historical_data(
                    symbol=symbol,
                    duration="5 Y", 
                    timeframes=['1 day']
                )
                
                logger.info(f"Long-term daily data for {symbol}: {daily_results}")
                
            except Exception as e:
                logger.error(f"Error collecting data for {symbol}: {e}")
    
    async def verify_data_quality(self, symbols: List[str] = None):
        """Verify the quality of stored data"""
        if symbols is None:
            symbols = [config.trading.primary_symbol]
        
        logger.info("Verifying data quality...")
        
        for symbol in symbols:
            for timeframe in ['1day', '1hour', '5min']:
                try:
                    # Get sample data
                    df = await data_manager.get_historical_data(
                        symbol=symbol,
                        timeframe=timeframe,
                        periods=100
                    )
                    
                    if not df.empty:
                        logger.info(f"{symbol} {timeframe}: {len(df)} records, "
                                  f"from {df.index[0]} to {df.index[-1]}")
                    else:
                        logger.warning(f"No data found for {symbol} {timeframe}")
                        
                except Exception as e:
                    logger.error(f"Error verifying {symbol} {timeframe}: {e}")


async def main():
    """Main application function"""
    app = TradingApplication()
    
    try:
        # Startup
        if not await app.startup():
            logger.error("Failed to start application")
            return 1
        
        # Run initial data collection for QQQ
        logger.info("Phase 1: Running initial data collection...")
        await app.run_data_collection(['QQQ'])
        
        # Verify data quality
        logger.info("Phase 1: Verifying data quality...")
        await app.verify_data_quality(['QQQ'])
        
        logger.info("Phase 1 implementation completed successfully!")
        logger.info("Next steps:")
        logger.info("1. Review the collected QQQ data")
        logger.info("2. Implement basic trading strategies")
        logger.info("3. Set up backtesting framework")
        logger.info("4. Add portfolio management")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        return 0
    except Exception as e:
        logger.error(f"Application error: {e}")
        return 1
    finally:
        await app.shutdown()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
