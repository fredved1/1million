"""
Trading strategy implementations.
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional


class TradingStrategy:
    """Base class for trading strategies."""

    def __init__(self, name: str):
        self.name = name

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        Generate trading signals from market data.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            Series with signals (1=buy, -1=sell, 0=hold)
        """
        raise NotImplementedError


class MovingAverageCrossover(TradingStrategy):
    """Moving Average Crossover Strategy."""

    def __init__(self, fast_period: int = 20, slow_period: int = 50):
        super().__init__("MA_Crossover")
        self.fast_period = fast_period
        self.slow_period = slow_period

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate signals based on MA crossover."""
        df = data.copy()

        # Calculate moving averages
        df['fast_ma'] = df['close'].rolling(window=self.fast_period).mean()
        df['slow_ma'] = df['close'].rolling(window=self.slow_period).mean()

        # Generate signals
        signals = pd.Series(0, index=df.index)

        # Buy when fast MA crosses above slow MA
        signals[(df['fast_ma'] > df['slow_ma']) &
                (df['fast_ma'].shift(1) <= df['slow_ma'].shift(1))] = 1

        # Sell when fast MA crosses below slow MA
        signals[(df['fast_ma'] < df['slow_ma']) &
                (df['fast_ma'].shift(1) >= df['slow_ma'].shift(1))] = -1

        return signals


class RSIStrategy(TradingStrategy):
    """Relative Strength Index Strategy."""

    def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70):
        super().__init__("RSI")
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate signals based on RSI."""
        df = data.copy()

        # Calculate RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()

        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # Generate signals
        signals = pd.Series(0, index=df.index)

        # Buy when RSI crosses above oversold
        signals[(df['rsi'] > self.oversold) &
                (df['rsi'].shift(1) <= self.oversold)] = 1

        # Sell when RSI crosses below overbought
        signals[(df['rsi'] < self.overbought) &
                (df['rsi'].shift(1) >= self.overbought)] = -1

        return signals


class BollingerBandsStrategy(TradingStrategy):
    """Bollinger Bands Mean Reversion Strategy."""

    def __init__(self, period: int = 20, num_std: float = 2.0):
        super().__init__("Bollinger_Bands")
        self.period = period
        self.num_std = num_std

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate signals based on Bollinger Bands."""
        df = data.copy()

        # Calculate Bollinger Bands
        df['middle_band'] = df['close'].rolling(window=self.period).mean()
        df['std'] = df['close'].rolling(window=self.period).std()
        df['upper_band'] = df['middle_band'] + (df['std'] * self.num_std)
        df['lower_band'] = df['middle_band'] - (df['std'] * self.num_std)

        # Generate signals
        signals = pd.Series(0, index=df.index)

        # Buy when price touches lower band
        signals[df['close'] <= df['lower_band']] = 1

        # Sell when price touches upper band
        signals[df['close'] >= df['upper_band']] = -1

        return signals


class MACDStrategy(TradingStrategy):
    """MACD (Moving Average Convergence Divergence) Strategy."""

    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        super().__init__("MACD")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate signals based on MACD."""
        df = data.copy()

        # Calculate MACD
        df['ema_fast'] = df['close'].ewm(span=self.fast_period, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=self.slow_period, adjust=False).mean()
        df['macd'] = df['ema_fast'] - df['ema_slow']
        df['signal_line'] = df['macd'].ewm(span=self.signal_period, adjust=False).mean()

        # Generate signals
        signals = pd.Series(0, index=df.index)

        # Buy when MACD crosses above signal line
        signals[(df['macd'] > df['signal_line']) &
                (df['macd'].shift(1) <= df['signal_line'].shift(1))] = 1

        # Sell when MACD crosses below signal line
        signals[(df['macd'] < df['signal_line']) &
                (df['macd'].shift(1) >= df['signal_line'].shift(1))] = -1

        return signals


class TrendFollowingStrategy(TradingStrategy):
    """Advanced Trend Following Strategy with multiple indicators."""

    def __init__(self, ma_period: int = 50, atr_period: int = 14, atr_multiplier: float = 2.0):
        super().__init__("Trend_Following")
        self.ma_period = ma_period
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate signals based on trend following."""
        df = data.copy()

        # Calculate indicators
        df['ma'] = df['close'].rolling(window=self.ma_period).mean()

        # Calculate ATR for volatility
        df['high_low'] = df['high'] - df['low']
        df['high_close'] = abs(df['high'] - df['close'].shift())
        df['low_close'] = abs(df['low'] - df['close'].shift())
        df['tr'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
        df['atr'] = df['tr'].rolling(window=self.atr_period).mean()

        # Calculate trend strength
        df['trend_strength'] = (df['close'] - df['ma']) / df['atr']

        # Generate signals
        signals = pd.Series(0, index=df.index)

        # Buy when price is above MA and trend is strong
        signals[(df['close'] > df['ma']) &
                (df['trend_strength'] > self.atr_multiplier)] = 1

        # Sell when price crosses below MA or trend weakens
        signals[(df['close'] < df['ma']) |
                (df['trend_strength'] < -self.atr_multiplier)] = -1

        return signals


class CombinedStrategy(TradingStrategy):
    """Combined strategy using multiple indicators for consensus."""

    def __init__(self, ma_fast: int = 20, ma_slow: int = 50, rsi_period: int = 14,
                 rsi_oversold: int = 30, rsi_overbought: int = 70):
        super().__init__("Combined")
        self.ma_fast = ma_fast
        self.ma_slow = ma_slow
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate signals based on multiple indicators."""
        df = data.copy()

        # Moving averages
        df['fast_ma'] = df['close'].rolling(window=self.ma_fast).mean()
        df['slow_ma'] = df['close'].rolling(window=self.ma_slow).mean()

        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # MACD
        df['ema_fast'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema_fast'] - df['ema_slow']
        df['signal_line'] = df['macd'].ewm(span=9, adjust=False).mean()

        # Generate individual signals
        ma_bullish = df['fast_ma'] > df['slow_ma']
        rsi_not_overbought = df['rsi'] < self.rsi_overbought
        rsi_not_oversold = df['rsi'] > self.rsi_oversold
        macd_bullish = df['macd'] > df['signal_line']

        # Combined signals (require majority consensus)
        signals = pd.Series(0, index=df.index)

        # Buy when majority indicators are bullish and RSI not overbought
        buy_conditions = (
            ma_bullish &
            rsi_not_overbought &
            (df['rsi'] > self.rsi_oversold) &
            macd_bullish
        )
        signals[buy_conditions & ~buy_conditions.shift(1).fillna(False)] = 1

        # Sell when indicators turn bearish
        sell_conditions = (
            (~ma_bullish) |
            (df['rsi'] > self.rsi_overbought) |
            (~macd_bullish)
        )
        signals[sell_conditions & ~sell_conditions.shift(1).fillna(False)] = -1

        return signals


class MeanReversionStrategy(TradingStrategy):
    """Mean Reversion Strategy with Z-Score."""

    def __init__(self, period: int = 20, entry_threshold: float = 2.0, exit_threshold: float = 0.5):
        super().__init__("Mean_Reversion")
        self.period = period
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate signals based on mean reversion."""
        df = data.copy()

        # Calculate Z-Score
        df['mean'] = df['close'].rolling(window=self.period).mean()
        df['std'] = df['close'].rolling(window=self.period).std()
        df['z_score'] = (df['close'] - df['mean']) / df['std']

        # Generate signals
        signals = pd.Series(0, index=df.index)

        # Buy when price is significantly below mean (oversold)
        signals[(df['z_score'] < -self.entry_threshold) &
                (df['z_score'].shift(1) >= -self.entry_threshold)] = 1

        # Exit when price returns to mean
        signals[(df['z_score'] > -self.exit_threshold) &
                (df['z_score'].shift(1) <= -self.exit_threshold)] = -1

        # Short when price is significantly above mean (overbought)
        # signals[(df['z_score'] > self.entry_threshold) &
        #         (df['z_score'].shift(1) <= self.entry_threshold)] = -1

        return signals


def get_strategy(strategy_name: str, **kwargs) -> TradingStrategy:
    """
    Factory function to get a strategy by name.

    Args:
        strategy_name: Name of the strategy
        **kwargs: Strategy parameters

    Returns:
        TradingStrategy instance
    """
    strategies = {
        'ma_crossover': MovingAverageCrossover,
        'rsi': RSIStrategy,
        'bollinger_bands': BollingerBandsStrategy,
        'macd': MACDStrategy,
        'trend_following': TrendFollowingStrategy,
        'combined': CombinedStrategy,
        'mean_reversion': MeanReversionStrategy,
    }

    if strategy_name.lower() not in strategies:
        raise ValueError(f"Unknown strategy: {strategy_name}. Available: {list(strategies.keys())}")

    return strategies[strategy_name.lower()](**kwargs)


if __name__ == "__main__":
    print("Available strategies:")
    strategies = ['ma_crossover', 'rsi', 'bollinger_bands', 'macd',
                  'trend_following', 'combined', 'mean_reversion']
    for i, strat in enumerate(strategies, 1):
        print(f"{i}. {strat}")
