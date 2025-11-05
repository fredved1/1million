"""
Simple data fetching module using direct API calls (no yfinance dependency).
"""
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Optional
import time


class SimpleDataFetcher:
    """Fetch market data using simple HTTP requests."""

    def __init__(self):
        self.cache = {}

    def fetch_yahoo_finance(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch data from Yahoo Finance using direct API.

        Args:
            symbol: Ticker symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            DataFrame with OHLCV data
        """
        cache_key = f"{symbol}_{start_date}_{end_date}"

        if cache_key in self.cache:
            print(f"Using cached data for {symbol}")
            return self.cache[cache_key].copy()

        print(f"Fetching {symbol} data...")

        # Convert dates to timestamps
        start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp())
        end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp())

        # Yahoo Finance API endpoint
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

        params = {
            'period1': start_ts,
            'period2': end_ts,
            'interval': '1d',
            'events': 'history'
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()

            if 'chart' not in data or 'result' not in data['chart']:
                raise ValueError(f"Invalid response for {symbol}")

            result = data['chart']['result'][0]

            if 'timestamp' not in result:
                raise ValueError(f"No data available for {symbol}")

            # Extract data
            timestamps = result['timestamp']
            quote = result['indicators']['quote'][0]

            df = pd.DataFrame({
                'timestamp': pd.to_datetime(timestamps, unit='s'),
                'open': quote['open'],
                'high': quote['high'],
                'low': quote['low'],
                'close': quote['close'],
                'volume': quote['volume']
            })

            df.set_index('timestamp', inplace=True)
            df = df.dropna()

            self.cache[cache_key] = df.copy()
            print(f"Fetched {len(df)} rows for {symbol}")

            return df

        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            raise

    def validate_data(self, df: pd.DataFrame) -> tuple:
        """Validate fetched data."""
        if df.empty:
            return False, "DataFrame is empty"

        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            return False, f"Missing columns: {missing}"

        if df[required_cols].isna().any().any():
            return False, "Contains NaN values"

        return True, "Data is valid"


# Create sample data generator for testing
def generate_sample_data(n_days: int = 252, start_price: float = 100.0,
                        volatility: float = 0.02) -> pd.DataFrame:
    """Generate synthetic price data for testing."""
    import numpy as np

    dates = pd.date_range(end=datetime.now(), periods=n_days, freq='D')

    # Generate realistic OHLCV data
    returns = np.random.normal(0.0005, volatility, n_days)
    closes = start_price * (1 + returns).cumprod()

    # Generate OHLC from close
    opens = closes * (1 + np.random.normal(0, 0.005, n_days))
    highs = np.maximum(opens, closes) * (1 + abs(np.random.normal(0, 0.01, n_days)))
    lows = np.minimum(opens, closes) * (1 - abs(np.random.normal(0, 0.01, n_days)))
    volumes = np.random.lognormal(15, 1, n_days)

    df = pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    }, index=dates)

    return df


if __name__ == "__main__":
    # Test fetcher
    fetcher = SimpleDataFetcher()

    try:
        df = fetcher.fetch_yahoo_finance('AAPL', '2024-01-01', '2024-12-31')
        print(f"\nData shape: {df.shape}")
        print(f"\nFirst 3 rows:\n{df.head(3)}")
        print(f"\nLast 3 rows:\n{df.tail(3)}")

        is_valid, msg = fetcher.validate_data(df)
        print(f"\nValidation: {is_valid} - {msg}")
    except Exception as e:
        print(f"Fetch failed: {e}")
        print("\nGenerating sample data instead...")
        df = generate_sample_data(252)
        print(f"Generated {len(df)} rows of synthetic data")
