"""
Interactive Brokers TWS connection and API wrapper using ib_insync.
"""
import asyncio
import logging
from typing import List, Dict, Optional, Callable, Any
from datetime import datetime, timedelta
import pandas as pd

from ib_insync import IB, Stock, Contract, BarData, util
from ib_insync.objects import PortfolioItem, Position as IBPosition, AccountValue

from ..core.config import config
from ..core.exceptions import IBConnectionError, IBAPIError, DataException

logger = logging.getLogger(__name__)


class IBConnector:
    """Interactive Brokers connection manager and API wrapper"""
    
    def __init__(self):
        self.ib = IB()
        self.is_connected = False
        self.account_id = None
        self.connection_callbacks: List[Callable] = []
        self.disconnection_callbacks: List[Callable] = []
        
        # Rate limiting
        self.last_historical_request = datetime.now()
        self.min_request_interval = timedelta(seconds=11)  # IB pacing requirement
        
        # Setup event handlers
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Setup IB event handlers"""
        self.ib.connectedEvent += self._on_connected
        self.ib.disconnectedEvent += self._on_disconnected
        self.ib.errorEvent += self._on_error
        self.ib.orderStatusEvent += self._on_order_status
        self.ib.execDetailsEvent += self._on_execution
    
    async def connect(self, retries: int = None) -> bool:
        """Connect to Interactive Brokers TWS/Gateway"""
        if retries is None:
            retries = config.ib.max_retries
            
        for attempt in range(retries + 1):
            try:
                logger.info(f"Attempting to connect to IB TWS (attempt {attempt + 1}/{retries + 1})")
                
                await self.ib.connectAsync(
                    host=config.ib.host,
                    port=config.ib.port,
                    clientId=config.ib.client_id,
                    timeout=config.ib.timeout
                )
                
                # Wait for connection to be established
                await asyncio.sleep(1)
                
                if self.ib.isConnected():
                    self.is_connected = True
                    self.account_id = self.ib.managedAccounts()[0] if self.ib.managedAccounts() else None
                    logger.info(f"Successfully connected to IB TWS. Account: {self.account_id}")
                    return True
                
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < retries:
                    await asyncio.sleep(config.ib.retry_delay)
                else:
                    raise IBConnectionError(f"Failed to connect to IB TWS after {retries + 1} attempts: {e}")
        
        return False
    
    def disconnect(self):
        """Disconnect from IB TWS"""
        if self.is_connected:
            self.ib.disconnect()
            self.is_connected = False
            logger.info("Disconnected from IB TWS")
    
    def add_connection_callback(self, callback: Callable):
        """Add callback for connection events"""
        self.connection_callbacks.append(callback)
    
    def add_disconnection_callback(self, callback: Callable):
        """Add callback for disconnection events"""
        self.disconnection_callbacks.append(callback)
    
    async def get_historical_data(self, 
                                  symbol: str,
                                  duration: str = "1 Y",
                                  bar_size: str = "1 day",
                                  what_to_show: str = "TRADES") -> pd.DataFrame:
        """
        Fetch historical data for a symbol.
        
        Args:
            symbol: Stock symbol (e.g., 'QQQ')
            duration: Data duration ('1 Y', '2 Y', '5 Y', etc.)
            bar_size: Bar size ('1 min', '5 mins', '1 hour', '1 day')
            what_to_show: Data type ('TRADES', 'MIDPOINT', 'BID', 'ASK')
        """
        if not self.is_connected:
            raise IBConnectionError("Not connected to IB TWS")
        
        # Rate limiting - ensure we don't exceed IB's pacing requirements
        await self._wait_for_pacing()
        
        try:
            # Create contract
            contract = Stock(symbol, 'SMART', 'USD')
            
            # Request historical data
            logger.info(f"Requesting historical data: {symbol} {duration} {bar_size}")
            
            bars = await self.ib.reqHistoricalDataAsync(
                contract=contract,
                endDateTime='',
                durationStr=duration,
                barSizeSetting=bar_size,
                whatToShow=what_to_show,
                useRTH=True,  # Regular trading hours only
                formatDate=1
            )
            
            if not bars:
                raise DataException(f"No historical data returned for {symbol}")
            
            # Convert to DataFrame
            df = util.df(bars)
            df['symbol'] = symbol
            df['timeframe'] = self._normalize_timeframe(bar_size)
            
            logger.info(f"Retrieved {len(df)} bars for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            raise IBAPIError(f"Failed to fetch historical data: {e}")
    
    async def get_account_summary(self) -> Dict[str, Any]:
        """Get account summary information"""
        if not self.is_connected:
            raise IBConnectionError("Not connected to IB TWS")
        
        try:
            # Request account summary
            account_summary = await self.ib.reqAccountSummaryAsync()
            
            # Convert to dictionary
            summary = {}
            for item in account_summary:
                summary[item.tag] = {
                    'value': item.value,
                    'currency': item.currency,
                    'account': item.account
                }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error fetching account summary: {e}")
            raise IBAPIError(f"Failed to fetch account summary: {e}")
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get current portfolio positions"""
        if not self.is_connected:
            raise IBConnectionError("Not connected to IB TWS")
        
        try:
            positions = await self.ib.reqPositionsAsync()
            
            position_list = []
            for position in positions:
                position_dict = {
                    'account': position.account,
                    'symbol': position.contract.symbol,
                    'quantity': position.position,
                    'avg_price': position.avgCost,
                    'market_price': 0.0,  # Will be updated with market data
                    'market_value': 0.0,
                    'unrealized_pnl': 0.0
                }
                position_list.append(position_dict)
            
            return position_list
            
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            raise IBAPIError(f"Failed to fetch positions: {e}")
    
    async def get_portfolio_items(self) -> List[Dict[str, Any]]:
        """Get detailed portfolio information"""
        if not self.is_connected:
            raise IBConnectionError("Not connected to IB TWS")
        
        try:
            portfolio_items = await self.ib.reqAccountUpdatesAsync(self.account_id)
            
            portfolio_list = []
            for item in self.ib.portfolio():
                portfolio_dict = {
                    'symbol': item.contract.symbol,
                    'position': item.position,
                    'market_price': item.marketPrice,
                    'market_value': item.marketValue,
                    'average_cost': item.averageCost,
                    'unrealized_pnl': item.unrealizedPNL,
                    'realized_pnl': item.realizedPNL,
                    'account': item.account
                }
                portfolio_list.append(portfolio_dict)
            
            return portfolio_list
            
        except Exception as e:
            logger.error(f"Error fetching portfolio items: {e}")
            raise IBAPIError(f"Failed to fetch portfolio items: {e}")
    
    def get_market_data_subscription(self, symbol: str) -> None:
        """Subscribe to real-time market data"""
        if not self.is_connected:
            raise IBConnectionError("Not connected to IB TWS")
        
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            self.ib.reqMktData(contract, '', False, False)
            logger.info(f"Subscribed to market data for {symbol}")
            
        except Exception as e:
            logger.error(f"Error subscribing to market data for {symbol}: {e}")
            raise IBAPIError(f"Failed to subscribe to market data: {e}")
    
    def cancel_market_data_subscription(self, symbol: str) -> None:
        """Cancel real-time market data subscription"""
        if not self.is_connected:
            return
        
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            self.ib.cancelMktData(contract)
            logger.info(f"Cancelled market data subscription for {symbol}")
            
        except Exception as e:
            logger.error(f"Error cancelling market data for {symbol}: {e}")
    
    async def _wait_for_pacing(self):
        """Wait for IB pacing requirements (11 seconds between historical data requests)"""
        elapsed = datetime.now() - self.last_historical_request
        if elapsed < self.min_request_interval:
            wait_time = (self.min_request_interval - elapsed).total_seconds()
            logger.info(f"Waiting {wait_time:.1f} seconds for IB pacing...")
            await asyncio.sleep(wait_time)
        
        self.last_historical_request = datetime.now()
    
    def _normalize_timeframe(self, bar_size: str) -> str:
        """Normalize IB bar size to internal timeframe format"""
        mapping = {
            '1 min': '1min',
            '5 mins': '5min',
            '15 mins': '15min',
            '30 mins': '30min',
            '1 hour': '1hour',
            '1 day': '1day'
        }
        return mapping.get(bar_size, bar_size.replace(' ', '').lower())
    
    def _on_connected(self):
        """Handle connection event"""
        logger.info("IB connection established")
        for callback in self.connection_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in connection callback: {e}")
    
    def _on_disconnected(self):
        """Handle disconnection event"""
        logger.warning("IB connection lost")
        self.is_connected = False
        for callback in self.disconnection_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in disconnection callback: {e}")
    
    def _on_error(self, reqId, errorCode, errorString, contract):
        """Handle IB error events"""
        logger.error(f"IB Error {errorCode}: {errorString} (reqId: {reqId})")
        
        # Handle specific error codes
        if errorCode in [1100, 1101, 1102]:  # Connection lost errors
            self.is_connected = False
        elif errorCode == 162:  # Historical Market Data Service error
            logger.warning("Historical data service temporarily unavailable")
        elif errorCode == 200:  # No security definition found
            logger.error(f"Security not found: {contract}")
    
    def _on_order_status(self, trade):
        """Handle order status updates"""
        logger.info(f"Order status update: {trade.orderStatus.status} for {trade.contract.symbol}")
    
    def _on_execution(self, trade, fill):
        """Handle order execution events"""
        logger.info(f"Order executed: {fill.execution.shares} shares of {trade.contract.symbol} "
                   f"at {fill.execution.price}")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


# Global IB connector instance
ib_connector = IBConnector()
