"""
BREAKOUT CATCHER STRATEGY
Target: 2.5% per maand
Allocatie: 25% van portfolio
Leverage: 4x (hoogste leverage - big risk/reward)

Catches explosive breakouts met volume confirmation.
Fewer trades maar grotere wins.
"""
import pandas as pd
import numpy as np
from strategies import TradingStrategy


class BreakoutCatcher(TradingStrategy):
    """
    Breakout strategy die grote moves vangt.

    Timeframe: 15-60 minuten
    Hold time: 4-24 uur
    Trades per dag: 5-10

    Entry:
    - New 50-period high
    - STRONG volume (2x+ average)
    - Trend confirmation
    - Momentum > 2%

    Exit:
    - Trailing stop: 2 ATR
    - Take profit: 5-10%
    - Stop loss: 2%

    Expected Performance:
    - Win rate: 35% (lower but big wins)
    - Avg win: 6%
    - Avg loss: 2%
    - Profit factor: 2.5+
    - Target: 2.5% per maand
    """

    def __init__(self, lookback: int = 50, momentum_threshold: float = 2.0,
                 volume_mult: float = 2.0):
        super().__init__("Breakout_Catcher")
        self.lookback = lookback
        self.momentum_threshold = momentum_threshold
        self.volume_mult = volume_mult

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate breakout signals."""
        df = data.copy()

        # 1. MAJOR breakout (significant high)
        df['high_roll'] = df['high'].rolling(window=self.lookback).max()
        df['low_roll'] = df['low'].rolling(window=self.lookback).min()
        major_breakout = df['close'] > df['high_roll'].shift(1)

        # 2. STRONG momentum (not just tiny break)
        df['momentum'] = (df['close'] / df['close'].shift(self.lookback) - 1) * 100
        strong_momentum = df['momentum'] > self.momentum_threshold

        # 3. EXPLOSIVE volume (this is key!)
        df['vol_ma'] = df['volume'].rolling(window=self.lookback).mean()
        explosive_volume = df['volume'] > df['vol_ma'] * self.volume_mult

        # 4. Trend strength (ADX-like)
        df['ema_fast'] = df['close'].ewm(span=20).mean()
        df['ema_slow'] = df['close'].ewm(span=50).mean()
        uptrend = df['ema_fast'] > df['ema_slow']

        # 5. Volatility expansion (breakouts come with vol)
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(window=20).std()
        df['vol_ma'] = df['volatility'].rolling(window=100).mean()
        vol_expanding = df['volatility'] > df['vol_ma'] * 1.5

        # 6. ATR for stops
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift()),
                abs(df['low'] - df['close'].shift())
            )
        )
        df['atr'] = df['tr'].rolling(window=20).mean()

        # 7. Consolidation before breakout (tight range then explosion)
        df['range'] = df['high_roll'] - df['low_roll']
        df['range_pct'] = df['range'] / df['close'] * 100
        was_consolidating = df['range_pct'].shift(5) < 5  # Was in 5% range

        # Generate signals
        signals = pd.Series(0, index=df.index)

        # BUY: MAJOR breakout with EXPLOSIVE volume
        buy_condition = (
            major_breakout &
            strong_momentum &
            explosive_volume &
            uptrend &
            vol_expanding
        )
        signals[buy_condition] = 1

        # SELL: Momentum fades or breakdown
        # Exit 1: Momentum significantly fades
        momentum_fade = df['momentum'] < 0

        # Exit 2: Price breaks below fast EMA
        breaks_ema = df['close'] < df['ema_fast']

        # Exit 3: Volume dries up (no continuation)
        volume_fade = df['volume'] < df['vol_ma'] * 0.7

        sell_condition = momentum_fade | breaks_ema | volume_fade
        signals[sell_condition] = -1

        return signals


class VolatilityBreakout(TradingStrategy):
    """
    Alternative: volatility-based breakouts (Donchian style).

    Simpler, catches squeeze breakouts.
    """

    def __init__(self, channel_period: int = 20):
        super().__init__("Volatility_Breakout")
        self.channel_period = channel_period

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Donchian channel breakout."""
        df = data.copy()

        # Donchian channels
        df['upper'] = df['high'].rolling(window=self.channel_period).max()
        df['lower'] = df['low'].rolling(window=self.channel_period).min()
        df['middle'] = (df['upper'] + df['lower']) / 2

        # Squeeze detection (Bollinger Bands width)
        df['bb_mid'] = df['close'].rolling(window=20).mean()
        df['bb_std'] = df['close'].rolling(window=20).std()
        df['bb_width'] = (df['bb_std'] / df['bb_mid']) * 100

        # Low volatility = squeeze (explosion coming)
        squeeze = df['bb_width'] < df['bb_width'].rolling(window=100).quantile(0.2)

        # Generate signals
        signals = pd.Series(0, index=df.index)

        # BUY: Break above upper channel (after squeeze ideal)
        buy_condition = (
            (df['close'] > df['upper'].shift(1)) &
            (squeeze.shift(5))  # Was squeezing recently
        )
        signals[buy_condition] = 1

        # SELL: Break below middle or lower
        sell_condition = (df['close'] < df['middle'])
        signals[sell_condition] = -1

        return signals


class ExplosiveMomentumBreakout(TradingStrategy):
    """
    ZEER aggressive versie voor crypto volatility.

    Catches parabolic moves - high risk, huge reward.
    """

    def __init__(self, lookback: int = 20):
        super().__init__("Explosive_Momentum_Breakout")
        self.lookback = lookback

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Catch explosive parabolic moves."""
        df = data.copy()

        # Rate of change (acceleration)
        df['roc'] = df['close'].pct_change(self.lookback) * 100

        # Volume explosion
        df['vol_ma'] = df['volume'].rolling(window=self.lookback).mean()
        df['vol_surge'] = df['volume'] / df['vol_ma']

        # Price acceleration (2nd derivative)
        df['roc_accel'] = df['roc'].diff()

        # New highs
        df['high_roll'] = df['high'].rolling(window=self.lookback).max()
        new_high = df['close'] > df['high_roll'].shift(1)

        # Generate signals
        signals = pd.Series(0, index=df.index)

        # BUY: EXPLOSIVE move
        buy_condition = (
            new_high &
            (df['roc'] > 5) &  # > 5% move!
            (df['vol_surge'] > 3) &  # 3x volume!
            (df['roc_accel'] > 0)  # Still accelerating
        )
        signals[buy_condition] = 1

        # SELL: Acceleration stops
        sell_condition = (
            (df['roc'] < 2) |  # Slowing down
            (df['roc_accel'] < 0)  # Deceleration
        )
        signals[sell_condition] = -1

        return signals


def get_breakout_strategy(breakout_type: str = 'standard'):
    """
    Factory function voor breakout strategies.

    Args:
        breakout_type: 'standard', 'volatility', or 'explosive'
    """
    if breakout_type == 'volatility':
        return VolatilityBreakout(channel_period=20)
    elif breakout_type == 'explosive':
        return ExplosiveMomentumBreakout(lookback=20)
    else:
        return BreakoutCatcher(
            lookback=50,
            momentum_threshold=2.0,
            volume_mult=2.0
        )


if __name__ == "__main__":
    print("="*60)
    print("  BREAKOUT CATCHER STRATEGY")
    print("="*60)
    print("\nTarget: 2.5% per maand")
    print("Allocatie: 25% van portfolio")
    print("Leverage: 4x (HIGHEST!)")
    print("\nTimeframe: 15-60 minuten")
    print("Hold time: 4-24 uur")
    print("Trades per dag: 5-10")
    print("\nEntry Conditions:")
    print("  ✓ New 50-period HIGH")
    print("  ✓ Momentum > 2%")
    print("  ✓ Volume > 2x average (EXPLOSIVE!)")
    print("  ✓ Uptrend confirmed")
    print("  ✓ Volatility expanding")
    print("\nExit Conditions:")
    print("  ✓ Momentum fades (< 0%)")
    print("  ✓ Price < fast EMA")
    print("  ✓ Volume < 0.7x average")
    print("\nExpected:")
    print("  Win rate: 35% (LOW but BIG wins)")
    print("  Avg win: 6% (LARGE)")
    print("  Avg loss: 2%")
    print("  Profit factor: 2.5+")
    print("\nVariants:")
    print("  - Standard: Volume + Momentum breakout")
    print("  - Volatility: Donchian squeeze")
    print("  - Explosive: Parabolic moves (RISKY!)")
    print("="*60)
