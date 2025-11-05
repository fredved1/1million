"""
Data fetching module for real market data from various sources.
"""
import yfinance as yf
import pandas as pd
import ccxt
from datetime import datetime, timedelta
from typing import Optional, Tuple
import time


class DataFetcher:
    """Fetch real market data from multiple sources."""

    def __init__(self):
        self.yf_cache = {}

    def fetch_yahoo_finance(self, symbol: str, start_date: str, end_date: str,
                           interval: str = '1d') -> pd.DataFrame:
        """
        Fetch data from Yahoo Finance.

        Args:
            symbol: Ticker symbol (e.g., 'AAPL', 'BTC-USD')
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            interval: Data interval (1d, 1h, 15m, etc.)

        Returns:
            DataFrame with OHLCV data
        """
        cache_key = f"{symbol}_{start_date}_{end_date}_{interval}"

        if cache_key in self.yf_cache:
            print(f"Using cached data for {symbol}")
            return self.yf_cache[cache_key].copy()

        print(f"Fetching {symbol} data from Yahoo Finance...")
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date, interval=interval)

            if df.empty:
                raise ValueError(f"No data returned for {symbol}")

            # Standardize column names
            df.columns = [col.lower() for col in df.columns]

            # Ensure we have the essential columns
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in required_cols:
                if col not in df.columns:
                    raise ValueError(f"Missing required column: {col}")

            self.yf_cache[cache_key] = df.copy()
            print(f"Fetched {len(df)} rows of data for {symbol}")
            return df

        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            raise

    def fetch_crypto(self, symbol: str, exchange: str = 'binance',
                    timeframe: str = '1d', limit: int = 1000) -> pd.DataFrame:
        """
        Fetch cryptocurrency data from exchanges.

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            exchange: Exchange name (binance, coinbase, kraken, etc.)
            timeframe: Timeframe (1m, 5m, 1h, 1d, etc.)
            limit: Number of candles to fetch

        Returns:
            DataFrame with OHLCV data
        """
        print(f"Fetching {symbol} data from {exchange}...")
        try:
            # Initialize exchange
            exchange_class = getattr(ccxt, exchange)
            exchange_obj = exchange_class({'enableRateLimit': True})

            # Fetch OHLCV data
            ohlcv = exchange_obj.fetch_ohlcv(symbol, timeframe, limit=limit)

            # Convert to DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            print(f"Fetched {len(df)} rows of data for {symbol}")
            return df

        except Exception as e:
            print(f"Error fetching crypto data: {e}")
            raise

    def get_multiple_symbols(self, symbols: list, start_date: str,
                            end_date: str) -> dict:
        """
        Fetch data for multiple symbols.

        Args:
            symbols: List of ticker symbols
            start_date: Start date
            end_date: End date

        Returns:
            Dictionary of symbol -> DataFrame
        """
        data = {}
        for symbol in symbols:
            try:
                df = self.fetch_yahoo_finance(symbol, start_date, end_date)
                data[symbol] = df
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                print(f"Failed to fetch {symbol}: {e}")

        return data

    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """
        Validate fetched data for quality issues.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if df.empty:
            return False, "DataFrame is empty"

        # Check for required columns
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return False, f"Missing columns: {missing_cols}"

        # Check for NaN values
        nan_counts = df[required_cols].isna().sum()
        if nan_counts.any():
            return False, f"NaN values found: {nan_counts[nan_counts > 0].to_dict()}"

        # Check for invalid OHLC relationships
        invalid_ohlc = (
            (df['high'] < df['low']) |
            (df['high'] < df['close']) |
            (df['high'] < df['open']) |
            (df['low'] > df['close']) |
            (df['low'] > df['open'])
        )

        if invalid_ohlc.any():
            return False, f"Invalid OHLC relationships in {invalid_ohlc.sum()} rows"

        return True, "Data is valid"


if __name__ == "__main__":
    # Test the data fetcher
    fetcher = DataFetcher()

    # Test with stock data
    df = fetcher.fetch_yahoo_finance('AAPL', '2023-01-01', '2024-12-31')
    is_valid, msg = fetcher.validate_data(df)
    print(f"\nValidation: {is_valid} - {msg}")
    print(f"\nFirst 5 rows:\n{df.head()}")
    print(f"\nLast 5 rows:\n{df.tail()}")
    print(f"\nData shape: {df.shape}")
