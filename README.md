# 1 Million Dollar Trading Backtest System

A comprehensive algorithmic trading backtesting framework designed to optimize and test trading strategies with real market data.

## Features

- **Real Market Data**: Integration with Yahoo Finance and cryptocurrency exchanges
- **Multiple Strategies**: Moving Average Crossover, RSI, Bollinger Bands, MACD, and combined strategies
- **Optimization Engine**: Automated parameter tuning and optimization
- **Risk Management**: Position sizing, stop-loss, and portfolio management
- **Performance Metrics**: Sharpe ratio, drawdown analysis, win rate, and more
- **Visualization**: Charts and reports for strategy performance

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```bash
# Run a simple backtest
python main.py --symbol AAPL --strategy ma_crossover --start 2020-01-01 --end 2024-12-31

# Optimize strategy parameters
python optimize.py --symbol BTC-USD --strategy combined --capital 10000

# Run multiple backtests
python batch_test.py
```

## Project Structure

- `data_fetcher.py` - Real market data fetching
- `backtest_engine.py` - Core backtesting logic
- `strategies.py` - Trading strategy implementations
- `optimizer.py` - Strategy optimization
- `risk_manager.py` - Risk and position management
- `analytics.py` - Performance analysis and reporting
- `main.py` - Main execution script

## Strategy to 1 Million

The goal is to develop a consistent, profitable trading strategy through:
1. Historical data analysis
2. Strategy optimization
3. Risk-adjusted returns
4. Compound growth modeling
