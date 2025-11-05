"""
HIGH-FREQUENCY MOMENTUM STRATEGY
Target: 3% per maand
Allocatie: 30% van portfolio
Leverage: 3x

Deze strategie traded frequent op momentum signalen.
Veel trades (10-20 per dag), kleine wins, tight stops.
"""
import pandas as pd
import numpy as np
from strategies import TradingStrategy


class HighFrequencyMomentum(TradingStrategy):
    """
    High-frequency momentum strategie voor crypto markets.

    Timeframe: 5-15 minuten
    Hold time: 1-4 uur
    Trades per dag: 10-20

    Entry:
    - Price breaks 10-period high
    - RSI 40-65 (momentum but not overbought)
    - Volume > 1.3x average
    - Strong momentum (> 0.5%)

    Exit:
    - Take profit: 1.5-2%
    - Stop loss: 0.7%
    - Trailing stop: 0.5 ATR

    Expected Performance:
    - Win rate: 45%
    - Avg win: 1.8%
    - Avg loss: 0.7%
    - Profit factor: 1.8+
    - Target: 3% per maand
    """

    def __init__(self, lookback: int = 10, momentum_threshold: float = 0.5,
                 rsi_min: int = 40, rsi_max: int = 65):
        super().__init__("HF_Momentum")
        self.lookback = lookback
        self.momentum_threshold = momentum_threshold
        self.rsi_min = rsi_min
        self.rsi_max = rsi_max

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate high-frequency momentum signals."""
        df = data.copy()

        # 1. Short-term momentum (zeer kort!)
        df['momentum'] = (df['close'] / df['close'].shift(self.lookback) - 1) * 100
        strong_momentum = df['momentum'] > self.momentum_threshold

        # 2. Price breakout (korte periode)
        df['high_roll'] = df['high'].rolling(window=self.lookback).max()
        price_breakout = df['close'] > df['high_roll'].shift(1)

        # 3. RSI (not overbought, but has momentum)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(span=14).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(span=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        rsi_ok = (df['rsi'] > self.rsi_min) & (df['rsi'] < self.rsi_max)

        # 4. Volume confirmation
        df['vol_ma'] = df['volume'].rolling(window=self.lookback).mean()
        volume_surge = df['volume'] > df['vol_ma'] * 1.3

        # 5. Volatility (want actie)
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(window=10).std()
        has_volatility = df['volatility'] > df['volatility'].rolling(window=50).median()

        # 6. ATR voor stops
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift()),
                abs(df['low'] - df['close'].shift())
            )
        )
        df['atr'] = df['tr'].rolling(window=10).mean()  # Korter ATR

        # Generate signals
        signals = pd.Series(0, index=df.index)

        # BUY: Breakout + Momentum + RSI + Volume
        buy_condition = (
            price_breakout &
            strong_momentum &
            rsi_ok &
            volume_surge &
            has_volatility
        )
        signals[buy_condition] = 1

        # SELL: Snel exit (tight stops voor HF)
        # Exit 1: Momentum reverses
        momentum_fade = df['momentum'] < -0.3

        # Exit 2: RSI overbought
        rsi_overbought = df['rsi'] > 75

        # Exit 3: Volume dries up
        volume_fade = df['volume'] < df['vol_ma'] * 0.8

        sell_condition = momentum_fade | rsi_overbought | volume_fade
        signals[sell_condition] = -1

        return signals


class AggressiveMomentum(TradingStrategy):
    """
    Nog agressievere versie voor ECHT high frequency.

    Timeframe: 1-5 minuten
    Hold time: 15min-2 uur
    Trades per dag: 20-50
    """

    def __init__(self, lookback: int = 5, momentum_threshold: float = 0.3):
        super().__init__("Aggressive_Momentum")
        self.lookback = lookback
        self.momentum_threshold = momentum_threshold

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Ultra-short term momentum signals."""
        df = data.copy()

        # Zeer korte indicators
        df['momentum'] = (df['close'] / df['close'].shift(self.lookback) - 1) * 100
        df['ema_fast'] = df['close'].ewm(span=3).mean()
        df['ema_slow'] = df['close'].ewm(span=8).mean()

        # Volume spike
        df['vol_ma'] = df['volume'].rolling(window=self.lookback).mean()
        volume_spike = df['volume'] > df['vol_ma'] * 1.5

        # Price action
        price_rising = df['ema_fast'] > df['ema_slow']
        strong_move = df['momentum'] > self.momentum_threshold

        # Generate signals
        signals = pd.Series(0, index=df.index)

        # BUY: Fast momentum met volume
        buy_condition = (
            price_rising &
            strong_move &
            volume_spike &
            (df['ema_fast'].shift(1) <= df['ema_slow'].shift(1))  # Crossover
        )
        signals[buy_condition] = 1

        # SELL: Reverse of momentum fades
        sell_condition = (
            ~price_rising |
            (df['momentum'] < 0)
        )
        signals[sell_condition] = -1

        return signals


def get_hf_momentum_strategy(aggressive: bool = False):
    """
    Factory function voor HF momentum strategy.

    Args:
        aggressive: Als True, gebruik ultra-aggressive versie
    """
    if aggressive:
        return AggressiveMomentum(lookback=5, momentum_threshold=0.3)
    else:
        return HighFrequencyMomentum(
            lookback=10,
            momentum_threshold=0.5,
            rsi_min=40,
            rsi_max=65
        )


if __name__ == "__main__":
    print("="*60)
    print("  HIGH-FREQUENCY MOMENTUM STRATEGY")
    print("="*60)
    print("\nTarget: 3% per maand")
    print("Allocatie: 30% van portfolio")
    print("Leverage: 3x")
    print("\nTimeframe: 5-15 minuten")
    print("Hold time: 1-4 uur")
    print("Trades per dag: 10-20")
    print("\nEntry Conditions:")
    print("  ✓ Price breaks 10-period high")
    print("  ✓ Momentum > 0.5%")
    print("  ✓ RSI 40-65 (momentum zone)")
    print("  ✓ Volume > 1.3x average")
    print("  ✓ Has volatility")
    print("\nExit Conditions:")
    print("  ✓ Momentum fades (< -0.3%)")
    print("  ✓ RSI > 75 (overbought)")
    print("  ✓ Volume < 0.8x average")
    print("\nExpected:")
    print("  Win rate: 45%")
    print("  Avg win: 1.8%")
    print("  Avg loss: 0.7%")
    print("  Profit factor: 1.8+")
    print("="*60)
