# Trading Application Phase 1

This is the Phase 1 implementation of the trading application as outlined in the architecture design.

## Phase 1 Components Implemented

### ✅ Core Infrastructure
- **Configuration Management**: Environment-based configuration with support for development/production
- **Database Schema**: PostgreSQL tables for market data, positions, orders, trades, and accounts
- **Exception Handling**: Custom exception hierarchy for different error types
- **Logging**: Structured logging with file and console output

### ✅ Data Management  
- **IB Connector**: Interactive Brokers TWS/Gateway connection using ib_insync
- **Data Manager**: Historical data fetching, storage, and retrieval with caching
- **Database Models**: SQLAlchemy models for all trading data
- **Data Validation**: Quality checks and data integrity validation

### ✅ Application Structure
- **Modular Design**: Clean separation between core, data, trading, and backtesting modules
- **Async Support**: Full asyncio support for concurrent operations
- **Error Handling**: Robust error handling and recovery mechanisms

## Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Setup Database** (requires PostgreSQL and Redis):
   ```bash
   python setup.py
   ```

4. **Run Application**:
   ```bash
   python main.py
   ```

## Configuration

### Database Setup
- Install PostgreSQL and Redis
- Create database: `trading_app`
- Create user: `trading_user` with password
- Update `.env` file with your database credentials

### Interactive Brokers Setup
- Install IB TWS or Gateway
- Configure for paper trading (port 7497) or live trading (port 7496)
- Enable API connections in TWS settings
- Set appropriate client ID (default: 1)

## Features

### Data Collection
- Fetches historical data for QQQ (1min, 5min, 1hour, 1day timeframes)
- Stores data in TimescaleDB-optimized PostgreSQL schema
- Implements IB pacing requirements (11-second intervals)
- Data quality validation and error handling

### Database Schema
- **market_data**: OHLCV data with timestamp indexing
- **positions**: Portfolio positions tracking
- **orders**: Order management and status tracking
- **trades**: Completed trade records with P&L
- **accounts**: Account summary and margin information
- **strategy_performance**: Strategy-specific performance metrics

### Caching
- Redis caching for frequently accessed data
- Latest price caching with TTL
- Historical data caching for small datasets

## Architecture

```
trading_app/
├── src/
│   ├── core/           # Configuration, database, exceptions
│   ├── data/           # IB connector, data management
│   ├── trading/        # Trading strategies (Phase 2)
│   └── backtesting/    # Backtesting engine (Phase 2)
├── tests/              # Unit tests
├── config/             # Configuration files
├── data/               # Data storage
├── logs/               # Application logs
└── main.py             # Application entry point
```

## Next Steps (Phase 2)

1. **Trading Strategies**: Implement base strategy classes and algorithms
2. **Backtesting Engine**: Build comprehensive backtesting framework
3. **Portfolio Management**: Position sizing and risk management
4. **Order Management**: Order execution and tracking

## Monitoring

- Logs are written to `logs/trading_app.log`
- Database performance can be monitored via PostgreSQL logs
- Redis cache statistics available via Redis CLI

## Development

### Adding New Features
1. Follow the modular architecture
2. Add appropriate error handling
3. Include logging for debugging
4. Update database schema if needed
5. Add configuration options to config.py

### Testing
```bash
# Run tests (when implemented)
pytest tests/

# Check code formatting
black src/
flake8 src/
```

## Troubleshooting

### Common Issues
1. **IB Connection Failed**: Ensure TWS/Gateway is running and API is enabled
2. **Database Connection**: Check PostgreSQL is running and credentials are correct
3. **Redis Connection**: Verify Redis server is running
4. **Permission Errors**: Check file system permissions for logs and data directories

### Error Codes
- IB Error 1100-1102: Connection issues
- IB Error 162: Historical data service unavailable
- IB Error 200: Security definition not found
