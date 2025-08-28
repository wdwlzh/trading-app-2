"""
Custom exceptions for the trading application.
"""


class TradingAppException(Exception):
    """Base exception for all trading application errors"""
    pass


class DataException(TradingAppException):
    """Exceptions related to data operations"""
    pass


class DataConnectionError(DataException):
    """Error connecting to data source"""
    pass


class DataQualityError(DataException):
    """Data quality validation error"""
    pass


class DataNotFoundError(DataException):
    """Requested data not found"""
    pass


class IBConnectionError(TradingAppException):
    """Interactive Brokers connection error"""
    pass


class IBAPIError(TradingAppException):
    """Interactive Brokers API error"""
    pass


class OrderException(TradingAppException):
    """Exceptions related to order management"""
    pass


class InvalidOrderError(OrderException):
    """Invalid order parameters"""
    pass


class OrderRejectedError(OrderException):
    """Order was rejected by broker"""
    pass


class InsufficientFundsError(OrderException):
    """Insufficient funds for order"""
    pass


class PortfolioException(TradingAppException):
    """Exceptions related to portfolio management"""
    pass


class RiskLimitExceededError(PortfolioException):
    """Risk limit exceeded"""
    pass


class PositionNotFoundError(PortfolioException):
    """Position not found in portfolio"""
    pass


class StrategyException(TradingAppException):
    """Exceptions related to trading strategies"""
    pass


class StrategyNotFoundError(StrategyException):
    """Strategy not found"""
    pass


class InvalidSignalError(StrategyException):
    """Invalid trading signal"""
    pass


class BacktestException(TradingAppException):
    """Exceptions related to backtesting"""
    pass


class InvalidBacktestDataError(BacktestException):
    """Invalid backtesting data"""
    pass


class DatabaseException(TradingAppException):
    """Database-related exceptions"""
    pass


class DatabaseConnectionError(DatabaseException):
    """Database connection error"""
    pass


class DatabaseQueryError(DatabaseException):
    """Database query error"""
    pass
