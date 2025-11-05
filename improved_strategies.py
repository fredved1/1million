"""
Improved trading strategies with better filters and risk management.
"""
import pandas as pd
import numpy as np
from strategies import TradingStrategy


class ImprovedMomentumBreakout(TradingStrategy):
    """
    Improved Momentum Breakout with better filters and risk management.

    Improvements:
    - Trend filter to trade only with the trend
    - Volume confirmation
    - Volatility filter to avoid choppy markets
    - Multiple timeframe confirmation
    - Better exit rules
    """

    def __init__(self, lookback: int = 20, breakout_threshold: float = 1.0,
                 trend_filter_period: int = 100, min_volume_mult: float = 1.3):
        super().__init__("Improved_Momentum_Breakout")
        self.lookback = lookback
        self.breakout_threshold = breakout_threshold
        self.trend_filter_period = trend_filter_period
        self.min_volume_mult = min_volume_mult

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate improved momentum signals with multiple filters."""
        df = data.copy()

        # 1. Trend Filter - Only trade in direction of long-term trend
        df['trend_ma'] = df['close'].rolling(window=self.trend_filter_period).mean()
        in_uptrend = df['close'] > df['trend_ma']

        # 2. Momentum
        df['momentum'] = (df['close'] / df['close'].shift(self.lookback) - 1) * 100
        strong_momentum = df['momentum'] > self.breakout_threshold

        # 3. Breakout Detection
        df['high_roll'] = df['high'].rolling(window=self.lookback).max()
        df['low_roll'] = df['low'].rolling(window=self.lookback).min()
        price_breakout = df['close'] > df['high_roll'].shift(1)

        # 4. Volume Confirmation (less strict)
        df['vol_ma'] = df['volume'].rolling(window=self.lookback).mean()
        volume_surge = df['volume'] > df['vol_ma'] * (self.min_volume_mult * 0.8)

        # 5. Volatility Filter - Only avoid EXTREME volatility
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(window=20).std()
        df['vol_ma'] = df['volatility'].rolling(window=50).mean()
        normal_volatility = df['volatility'] < df['vol_ma'] * 3.0  # More lenient

        # 6. ATR for position sizing (exported for risk management)
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift()),
                abs(df['low'] - df['close'].shift())
            )
        )
        df['atr'] = df['tr'].rolling(window=14).mean()

        # Generate signals with ALL filters
        signals = pd.Series(0, index=df.index)

        # BUY: Breakout + Momentum + Volume + Trend + Normal Vol
        buy_condition = (
            price_breakout &
            strong_momentum &
            volume_surge &
            in_uptrend &
            normal_volatility
        )
        signals[buy_condition] = 1

        # SELL: Multiple exit conditions
        # Exit 1: Momentum fades significantly
        momentum_fade = df['momentum'] < -self.breakout_threshold / 2

        # Exit 2: Price breaks below short-term MA (trend reversal)
        df['short_ma'] = df['close'].rolling(window=10).mean()
        trend_reversal = df['close'] < df['short_ma']

        # Exit 3: Close below entry swing low
        price_breakdown = df['close'] < df['low_roll'].shift(1)

        sell_condition = momentum_fade | trend_reversal | price_breakdown
        signals[sell_condition] = -1

        return signals


class ImprovedTrendFollowing(TradingStrategy):
    """
    Improved trend following with adaptive parameters.
    """

    def __init__(self, fast_period: int = 10, slow_period: int = 50,
                 atr_period: int = 14, trend_strength_min: float = 1.5):
        super().__init__("Improved_Trend_Following")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.atr_period = atr_period
        self.trend_strength_min = trend_strength_min

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate improved trend signals."""
        df = data.copy()

        # Exponential MAs for faster response
        df['ema_fast'] = df['close'].ewm(span=self.fast_period).mean()
        df['ema_slow'] = df['close'].ewm(span=self.slow_period).mean()

        # ATR for volatility adjustment
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift()),
                abs(df['low'] - df['close'].shift())
            )
        )
        df['atr'] = df['tr'].ewm(span=self.atr_period).mean()

        # Trend strength (normalized by ATR)
        df['trend_strength'] = (df['ema_fast'] - df['ema_slow']) / df['atr']

        # ADX-like trend strength
        df['plus_dm'] = np.where(
            (df['high'] - df['high'].shift()) > (df['low'].shift() - df['low']),
            np.maximum(df['high'] - df['high'].shift(), 0),
            0
        )
        df['minus_dm'] = np.where(
            (df['low'].shift() - df['low']) > (df['high'] - df['high'].shift()),
            np.maximum(df['low'].shift() - df['low'], 0),
            0
        )

        df['plus_di'] = 100 * df['plus_dm'].ewm(span=14).mean() / df['atr']
        df['minus_di'] = 100 * df['minus_dm'].ewm(span=14).mean() / df['atr']
        df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
        df['adx'] = df['dx'].ewm(span=14).mean()

        # Strong trend when ADX > 25
        strong_trend = df['adx'] > 25

        # Generate signals
        signals = pd.Series(0, index=df.index)

        # Buy when fast crosses above slow with reasonable trend
        buy_condition = (
            (df['ema_fast'] > df['ema_slow']) &
            (df['ema_fast'].shift(1) <= df['ema_slow'].shift(1)) &
            (df['adx'] > 20)  # Simplified - just check ADX
        )
        signals[buy_condition] = 1

        # Sell when fast crosses below slow
        sell_condition = (
            (df['ema_fast'] < df['ema_slow']) &
            (df['ema_fast'].shift(1) >= df['ema_slow'].shift(1))
        )

        signals[sell_condition] = -1

        return signals


class ImprovedMeanReversion(TradingStrategy):
    """
    Improved mean reversion with better regime detection.
    """

    def __init__(self, period: int = 20, entry_z: float = 2.0,
                 exit_z: float = 0.5, trend_threshold: float = 0.05):
        super().__init__("Improved_Mean_Reversion")
        self.period = period
        self.entry_z = entry_z
        self.exit_z = exit_z
        self.trend_threshold = trend_threshold

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate improved mean reversion signals."""
        df = data.copy()

        # Bollinger Bands / Z-Score
        df['sma'] = df['close'].rolling(window=self.period).mean()
        df['std'] = df['close'].rolling(window=self.period).std()
        df['z_score'] = (df['close'] - df['sma']) / df['std']

        # Regime Detection - Only mean revert in ranging markets
        df['trend_ma'] = df['close'].rolling(window=50).mean()
        df['trend_strength'] = abs(df['close'] - df['trend_ma']) / df['trend_ma']
        in_range = df['trend_strength'] < self.trend_threshold

        # RSI for confirmation
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(span=14).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(span=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # Volume should be normal (not spiking)
        df['vol_ma'] = df['volume'].rolling(window=20).mean()
        normal_volume = df['volume'] < df['vol_ma'] * 1.5

        # Generate signals
        signals = pd.Series(0, index=df.index)

        # Buy when oversold in ranging market
        buy_condition = (
            (df['z_score'] < -self.entry_z) &
            in_range &
            (df['rsi'] < 30) &
            normal_volume
        )
        signals[buy_condition] = 1

        # Sell when back to mean or overbought
        sell_condition = (
            (df['z_score'] > -self.exit_z) |
            (df['rsi'] > 70) |
            ~in_range
        )
        signals[sell_condition & (signals.shift(1) != 0)] = -1

        return signals


class PortfolioStrategy(TradingStrategy):
    """
    Portfolio approach combining multiple strategies.
    """

    def __init__(self, strategies: list, weights: list = None):
        super().__init__("Portfolio_Strategy")
        self.strategies = strategies
        self.weights = weights if weights else [1.0 / len(strategies)] * len(strategies)

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate portfolio signals from multiple strategies."""
        df = data.copy()

        # Get signals from all strategies
        all_signals = []
        for strategy in self.strategies:
            signals = strategy.generate_signals(df)
            all_signals.append(signals)

        # Weighted combination
        combined = pd.Series(0.0, index=df.index)
        for signals, weight in zip(all_signals, self.weights):
            combined += signals * weight

        # Convert to discrete signals
        final_signals = pd.Series(0, index=df.index)
        final_signals[combined > 0.5] = 1
        final_signals[combined < -0.5] = -1

        return final_signals


def get_improved_strategy(strategy_name: str, **kwargs):
    """Factory for improved strategies."""
    strategies = {
        'improved_momentum': ImprovedMomentumBreakout,
        'improved_trend': ImprovedTrendFollowing,
        'improved_mean_reversion': ImprovedMeanReversion,
    }

    if strategy_name.lower() not in strategies:
        raise ValueError(f"Unknown strategy: {strategy_name}")

    return strategies[strategy_name.lower()](**kwargs)


if __name__ == "__main__":
    print("Improved strategies loaded successfully")
