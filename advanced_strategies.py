"""
Advanced trading strategies with better performance potential.
"""
import pandas as pd
import numpy as np
from strategies import TradingStrategy


class MomentumBreakoutStrategy(TradingStrategy):
    """
    Advanced momentum breakout strategy targeting strong trends.
    """

    def __init__(self, lookback: int = 20, breakout_threshold: float = 1.5,
                 volume_filter: bool = True):
        super().__init__("Momentum_Breakout")
        self.lookback = lookback
        self.breakout_threshold = breakout_threshold
        self.volume_filter = volume_filter

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate momentum breakout signals."""
        df = data.copy()

        # Calculate momentum indicators
        df['returns'] = df['close'].pct_change()
        df['momentum'] = df['close'] / df['close'].shift(self.lookback) - 1

        # Rolling high/low
        df['high_roll'] = df['high'].rolling(window=self.lookback).max()
        df['low_roll'] = df['low'].rolling(window=self.lookback).min()

        # ATR for volatility adjustment
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift()),
                abs(df['low'] - df['close'].shift())
            )
        )
        df['atr'] = df['tr'].rolling(window=14).mean()

        # Volume filter
        if self.volume_filter:
            df['vol_ma'] = df['volume'].rolling(window=self.lookback).mean()
            volume_surge = df['volume'] > df['vol_ma'] * 1.2
        else:
            volume_surge = True

        # Breakout detection
        price_breakout_up = df['close'] > df['high_roll'].shift(1)
        strong_momentum = df['momentum'] > self.breakout_threshold / 100

        # Exit signals
        momentum_fade = df['momentum'] < 0

        # Generate signals
        signals = pd.Series(0, index=df.index)

        # Buy on breakout with strong momentum and volume
        buy_condition = price_breakout_up & strong_momentum & volume_surge
        signals[buy_condition] = 1

        # Sell when momentum fades
        signals[momentum_fade] = -1

        return signals


class VolatilityAdjustedStrategy(TradingStrategy):
    """
    Strategy that adjusts to market volatility.
    """

    def __init__(self, fast_ma: int = 10, slow_ma: int = 30, atr_period: int = 14):
        super().__init__("Volatility_Adjusted")
        self.fast_ma = fast_ma
        self.slow_ma = slow_ma
        self.atr_period = atr_period

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate volatility-adjusted signals."""
        df = data.copy()

        # Moving averages
        df['fast_ma'] = df['close'].ewm(span=self.fast_ma).mean()
        df['slow_ma'] = df['close'].ewm(span=self.slow_ma).mean()

        # ATR
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift()),
                abs(df['low'] - df['close'].shift())
            )
        )
        df['atr'] = df['tr'].ewm(span=self.atr_period).mean()

        # Normalized distance from MA
        df['distance'] = (df['close'] - df['slow_ma']) / df['atr']

        # Trend strength
        trend_up = df['fast_ma'] > df['slow_ma']
        strong_trend = abs(df['distance']) > 1.0

        # Generate signals
        signals = pd.Series(0, index=df.index)

        # Buy when uptrend starts and price is not overextended
        buy_condition = (
            trend_up &
            ~trend_up.shift(1).fillna(False) &
            (df['distance'] < 2.0)
        )
        signals[buy_condition] = 1

        # Sell when trend ends or price overextended
        sell_condition = (
            (~trend_up & trend_up.shift(1).fillna(True)) |
            (df['distance'] < -2.0)
        )
        signals[sell_condition] = -1

        return signals


class MultiTimeframeStrategy(TradingStrategy):
    """
    Strategy using multiple timeframe analysis.
    """

    def __init__(self, short_period: int = 5, medium_period: int = 20,
                 long_period: int = 50):
        super().__init__("Multi_Timeframe")
        self.short_period = short_period
        self.medium_period = medium_period
        self.long_period = long_period

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate multi-timeframe signals."""
        df = data.copy()

        # Multiple timeframe MAs
        df['ma_short'] = df['close'].rolling(window=self.short_period).mean()
        df['ma_medium'] = df['close'].rolling(window=self.medium_period).mean()
        df['ma_long'] = df['close'].rolling(window=self.long_period).mean()

        # Trend alignment
        all_aligned_up = (
            (df['ma_short'] > df['ma_medium']) &
            (df['ma_medium'] > df['ma_long']) &
            (df['close'] > df['ma_short'])
        )

        all_aligned_down = (
            (df['ma_short'] < df['ma_medium']) &
            (df['ma_medium'] < df['ma_long']) &
            (df['close'] < df['ma_short'])
        )

        # Generate signals
        signals = pd.Series(0, index=df.index)

        # Buy when all timeframes align up
        signals[all_aligned_up & ~all_aligned_up.shift(1).fillna(False)] = 1

        # Sell when alignment breaks
        signals[all_aligned_down | ~all_aligned_up] = -1

        return signals


class AdaptiveStrategy(TradingStrategy):
    """
    Strategy that adapts to different market regimes.
    """

    def __init__(self, regime_period: int = 50, trend_threshold: float = 0.02):
        super().__init__("Adaptive")
        self.regime_period = regime_period
        self.trend_threshold = trend_threshold

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate adaptive signals based on market regime."""
        df = data.copy()

        # Calculate market regime
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(window=self.regime_period).std()
        df['trend'] = df['close'] / df['close'].shift(self.regime_period) - 1

        # Regime classification
        high_vol = df['volatility'] > df['volatility'].rolling(window=100).median()
        trending = abs(df['trend']) > self.trend_threshold

        # Different strategies for different regimes
        # Trend following in trending markets
        df['ma_fast'] = df['close'].ewm(span=10).mean()
        df['ma_slow'] = df['close'].ewm(span=30).mean()

        # Mean reversion in ranging markets
        df['bb_mid'] = df['close'].rolling(window=20).mean()
        df['bb_std'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']

        # Generate signals based on regime
        signals = pd.Series(0, index=df.index)

        # Trending market: use trend following
        trend_buy = trending & (df['ma_fast'] > df['ma_slow']) & (df['ma_fast'].shift(1) <= df['ma_slow'].shift(1))
        trend_sell = trending & (df['ma_fast'] < df['ma_slow']) & (df['ma_fast'].shift(1) >= df['ma_slow'].shift(1))

        # Ranging market: use mean reversion
        range_buy = ~trending & (df['close'] <= df['bb_lower'])
        range_sell = ~trending & (df['close'] >= df['bb_upper'])

        signals[trend_buy | range_buy] = 1
        signals[trend_sell | range_sell] = -1

        return signals


class AdvancedCompositeStrategy(TradingStrategy):
    """
    Composite strategy combining multiple edge signals.
    """

    def __init__(self, ma_period: int = 20, rsi_period: int = 14,
                 volume_period: int = 20, atr_period: int = 14):
        super().__init__("Advanced_Composite")
        self.ma_period = ma_period
        self.rsi_period = rsi_period
        self.volume_period = volume_period
        self.atr_period = atr_period

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate composite signals from multiple indicators."""
        df = data.copy()

        # 1. Trend
        df['ema'] = df['close'].ewm(span=self.ma_period).mean()
        trend_up = df['close'] > df['ema']

        # 2. RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(span=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(span=self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        rsi_bullish = (df['rsi'] > 40) & (df['rsi'] < 70)

        # 3. Volume
        df['vol_ma'] = df['volume'].ewm(span=self.volume_period).mean()
        volume_surge = df['volume'] > df['vol_ma'] * 1.1

        # 4. Momentum
        df['momentum'] = df['close'] / df['close'].shift(10) - 1
        positive_momentum = df['momentum'] > 0

        # 5. Volatility
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift()),
                abs(df['low'] - df['close'].shift())
            )
        )
        df['atr'] = df['tr'].ewm(span=self.atr_period).mean()
        df['volatility'] = df['atr'] / df['close']
        moderate_vol = (df['volatility'] < df['volatility'].rolling(window=50).quantile(0.8))

        # Composite scoring
        df['score'] = (
            trend_up.astype(int) * 3 +  # Trend is most important
            rsi_bullish.astype(int) * 2 +
            volume_surge.astype(int) * 1 +
            positive_momentum.astype(int) * 2 +
            moderate_vol.astype(int) * 1
        )

        # Generate signals
        signals = pd.Series(0, index=df.index)

        # Buy when score is high
        buy_threshold = 6
        signals[df['score'] >= buy_threshold] = 1

        # Sell when score drops
        sell_threshold = 3
        signals[df['score'] <= sell_threshold] = -1

        return signals


def get_advanced_strategy(strategy_name: str, **kwargs) -> TradingStrategy:
    """Factory function for advanced strategies."""
    strategies = {
        'momentum_breakout': MomentumBreakoutStrategy,
        'volatility_adjusted': VolatilityAdjustedStrategy,
        'multi_timeframe': MultiTimeframeStrategy,
        'adaptive': AdaptiveStrategy,
        'advanced_composite': AdvancedCompositeStrategy,
    }

    if strategy_name.lower() not in strategies:
        raise ValueError(f"Unknown strategy: {strategy_name}")

    return strategies[strategy_name.lower()](**kwargs)


if __name__ == "__main__":
    print("Advanced strategies loaded successfully")
    print("\nAvailable advanced strategies:")
    strategies = ['momentum_breakout', 'volatility_adjusted', 'multi_timeframe',
                  'adaptive', 'advanced_composite']
    for i, strat in enumerate(strategies, 1):
        print(f"{i}. {strat}")
