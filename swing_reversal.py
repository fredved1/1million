"""
SWING REVERSAL STRATEGY
Target: 1% per maand
Allocatie: 10% van portfolio
Leverage: 2x

Catches reversals na downtrends bij support levels.
Patient strategy - fewer trades, grotere wins.
"""
import pandas as pd
import numpy as np
from strategies import TradingStrategy


class SwingReversal(TradingStrategy):
    """
    Swing reversal strategie die trend reversals vangt.

    Timeframe: 4h-1d
    Hold time: 3-14 dagen
    Trades per dag: 1-3

    Entry:
    - Oversold after downtrend
    - RSI/Price divergence
    - Support level hold
    - Reversal pattern

    Exit:
    - Take profit: 15-30%
    - Stop loss: 4%
    - Trailing stop: 4 ATR

    Expected Performance:
    - Win rate: 35% (lower but BIG wins)
    - Avg win: 20%
    - Avg loss: 4%
    - Profit factor: 1.8+
    - Target: 1% per maand
    """

    def __init__(self, rsi_oversold: int = 30, lookback: int = 50):
        super().__init__("Swing_Reversal")
        self.rsi_oversold = rsi_oversold
        self.lookback = lookback

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate swing reversal signals."""
        df = data.copy()

        # 1. Identify downtrend (price below MA)
        df['ma'] = df['close'].rolling(window=self.lookback).mean()
        in_downtrend = df['close'] < df['ma']

        # Recent downtrend (was down recently)
        df['returns_lookback'] = df['close'].pct_change(self.lookback) * 100
        recent_decline = df['returns_lookback'] < -5  # At least 5% down

        # 2. RSI oversold
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(span=14).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(span=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        oversold = df['rsi'] < self.rsi_oversold

        # 3. RSI/Price DIVERGENCE (key signal!)
        # Price making lower low, but RSI making higher low
        df['price_low'] = df['low'].rolling(window=10).min()
        df['rsi_low'] = df['rsi'].rolling(window=10).min()

        # Price lower low
        price_lower_low = (
            (df['low'] < df['price_low'].shift(10)) &
            (df['low'] == df['price_low'])
        )

        # RSI higher low (divergence)
        rsi_higher_low = (
            (df['rsi'] > df['rsi_low'].shift(10)) &
            (df['rsi'] == df['rsi_low'])
        )

        bullish_divergence = price_lower_low & rsi_higher_low

        # 4. Support level (price bouncing)
        df['support'] = df['low'].rolling(window=self.lookback).min()
        near_support = df['close'] < df['support'] * 1.02  # Within 2% of support

        # Bouncing off support (low wick)
        df['lower_wick'] = df['close'] - df['low']
        df['body_size'] = abs(df['close'] - df['open'])
        df['wick_ratio'] = df['lower_wick'] / df['body_size']
        hammer_candle = df['wick_ratio'] > 2  # Long lower wick = hammer

        # 5. Reversal signs (momentum turning)
        df['momentum'] = df['close'].pct_change(5) * 100
        momentum_turning = df['momentum'] > df['momentum'].shift(2)

        # 6. Volume surge (buying pressure)
        df['vol_ma'] = df['volume'].rolling(window=20).mean()
        volume_surge = df['volume'] > df['vol_ma'] * 1.3

        # 7. Stochastic oversold and turning up
        df['lowest'] = df['low'].rolling(window=14).min()
        df['highest'] = df['high'].rolling(window=14).max()
        df['stoch'] = 100 * (df['close'] - df['lowest']) / (df['highest'] - df['lowest'])
        df['stoch_ma'] = df['stoch'].rolling(window=3).mean()

        stoch_oversold = df['stoch'] < 20
        stoch_turning_up = df['stoch'] > df['stoch'].shift(1)

        # Generate signals
        signals = pd.Series(0, index=df.index)

        # BUY: Reversal setup (multiple confirmations)
        # Strong reversal signal = divergence OR (oversold + support + hammer)
        strong_reversal_signal = (
            bullish_divergence |
            (oversold & near_support & hammer_candle)
        )

        # Additional confirmations
        additional_confirmations = (
            momentum_turning &
            (volume_surge | (stoch_oversold & stoch_turning_up))
        )

        buy_condition = (
            (in_downtrend | recent_decline) &
            strong_reversal_signal &
            additional_confirmations
        )
        signals[buy_condition] = 1

        # SELL: Reversal complete or failed
        # Exit 1: Price reaches resistance (take profit area)
        df['resistance'] = df['high'].rolling(window=self.lookback).max()
        near_resistance = df['close'] > df['resistance'] * 0.95

        # Exit 2: RSI overbought (rally exhausted)
        overbought = df['rsi'] > 70

        # Exit 3: Momentum fading after rally
        rally_exhausted = (df['momentum'] < 0) & (df['rsi'] > 50)

        # Exit 4: Price breaks support again (reversal failed)
        breaks_support = df['close'] < df['support'] * 0.98

        sell_condition = near_resistance | overbought | rally_exhausted | breaks_support
        signals[sell_condition] = -1

        return signals


class SupportResistanceReversal(TradingStrategy):
    """
    Alternative: Support/Resistance based reversal.

    Simpler approach focusing on key levels.
    """

    def __init__(self, sr_period: int = 50):
        super().__init__("Support_Resistance_Reversal")
        self.sr_period = sr_period

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """S/R reversal signals."""
        df = data.copy()

        # Identify support and resistance
        df['support'] = df['low'].rolling(window=self.sr_period).min()
        df['resistance'] = df['high'].rolling(window=self.sr_period).max()
        df['range_mid'] = (df['support'] + df['resistance']) / 2

        # Position in range
        df['range_position'] = (df['close'] - df['support']) / (df['resistance'] - df['support'])

        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(span=14).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(span=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # Generate signals
        signals = pd.Series(0, index=df.index)

        # BUY: Near support + oversold
        buy_condition = (
            (df['range_position'] < 0.2) &  # Near support
            (df['rsi'] < 35) &
            (df['close'] > df['support'])  # Above support
        )
        signals[buy_condition] = 1

        # SELL: Near resistance
        sell_condition = (
            (df['range_position'] > 0.7) |  # Near resistance
            (df['rsi'] > 65)
        )
        signals[sell_condition] = -1

        return signals


class OversoldBounce(TradingStrategy):
    """
    Zeer simpele oversold bounce strategy.

    Entry na extreme oversold, exit snel.
    """

    def __init__(self, rsi_threshold: int = 25):
        super().__init__("Oversold_Bounce")
        self.rsi_threshold = rsi_threshold

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Oversold bounce signals."""
        df = data.copy()

        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(span=14).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(span=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # Stochastic
        df['lowest'] = df['low'].rolling(window=14).min()
        df['highest'] = df['high'].rolling(window=14).max()
        df['stoch'] = 100 * (df['close'] - df['lowest']) / (df['highest'] - df['lowest'])

        # Generate signals
        signals = pd.Series(0, index=df.index)

        # BUY: Extreme oversold
        buy_condition = (
            (df['rsi'] < self.rsi_threshold) &
            (df['stoch'] < 15)
        )
        signals[buy_condition] = 1

        # SELL: Back to normal or overbought
        sell_condition = (
            (df['rsi'] > 50) |
            (df['stoch'] > 70)
        )
        signals[sell_condition] = -1

        return signals


class VolumeReversalDetector(TradingStrategy):
    """
    Volume-based reversal detection.

    Catches capitulation bottoms met volume spikes.
    """

    def __init__(self, vol_spike_threshold: float = 2.5):
        super().__init__("Volume_Reversal_Detector")
        self.vol_spike_threshold = vol_spike_threshold

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Volume reversal signals."""
        df = data.copy()

        # Volume analysis
        df['vol_ma'] = df['volume'].rolling(window=20).mean()
        df['vol_spike'] = df['volume'] / df['vol_ma']

        # Capitulation = huge volume on down day
        df['daily_change'] = df['close'].pct_change()
        capitulation = (
            (df['vol_spike'] > self.vol_spike_threshold) &
            (df['daily_change'] < -0.03)  # Down 3%+
        )

        # Follow-up day: volume decreases, price stable
        df['volume_decreasing'] = df['volume'] < df['volume'].shift(1)
        df['price_stabilizing'] = abs(df['close'].pct_change()) < 0.01

        # RSI oversold
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(span=14).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(span=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # Generate signals
        signals = pd.Series(0, index=df.index)

        # BUY: After capitulation, when price stabilizes
        buy_condition = (
            capitulation.shift(1) &  # Capitulation yesterday
            df['volume_decreasing'] &
            (df['price_stabilizing'] | (df['daily_change'] > 0)) &
            (df['rsi'] < 40)
        )
        signals[buy_condition] = 1

        # SELL: After bounce
        sell_condition = (
            (df['rsi'] > 60) |
            (df['daily_change'] > 0.05)  # Quick 5% profit
        )
        signals[sell_condition] = -1

        return signals


def get_swing_reversal(reversal_type: str = 'standard'):
    """
    Factory function voor swing reversal strategies.

    Args:
        reversal_type: 'standard', 'support_resistance', 'oversold_bounce', or 'volume'
    """
    if reversal_type == 'support_resistance':
        return SupportResistanceReversal(sr_period=50)
    elif reversal_type == 'oversold_bounce':
        return OversoldBounce(rsi_threshold=25)
    elif reversal_type == 'volume':
        return VolumeReversalDetector(vol_spike_threshold=2.5)
    else:
        return SwingReversal(
            rsi_oversold=30,
            lookback=50
        )


if __name__ == "__main__":
    print("="*60)
    print("  SWING REVERSAL STRATEGY")
    print("="*60)
    print("\nTarget: 1% per maand")
    print("Allocatie: 10% van portfolio")
    print("Leverage: 2x")
    print("\nTimeframe: 4h-1d")
    print("Hold time: 3-14 dagen")
    print("Trades per dag: 1-3")
    print("\nEntry Conditions:")
    print("  ✓ Downtrend + Recent decline")
    print("  ✓ RSI oversold (< 30)")
    print("  ✓ Bullish divergence (RSI/Price)")
    print("  ✓ Near support level")
    print("  ✓ Hammer candle pattern")
    print("  ✓ Momentum turning up")
    print("  ✓ Volume surge OR Stoch turning up")
    print("\nExit Conditions:")
    print("  ✓ Near resistance (take profit)")
    print("  ✓ RSI > 70 (overbought)")
    print("  ✓ Momentum fading after rally")
    print("  ✓ Breaks support (failed reversal)")
    print("\nExpected:")
    print("  Win rate: 35% (LOW but BIG wins)")
    print("  Avg win: 20% (LARGE)")
    print("  Avg loss: 4%")
    print("  Profit factor: 1.8+")
    print("\nVariants:")
    print("  - Standard: Divergence + multi-confirmation")
    print("  - Support/Resistance: Key level bounces")
    print("  - Oversold Bounce: Simple RSI + Stoch")
    print("  - Volume: Capitulation detection")
    print("="*60)
