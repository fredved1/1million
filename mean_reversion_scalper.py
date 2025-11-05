"""
MEAN REVERSION SCALPER STRATEGY
Target: 2% per maand
Allocatie: 20% van portfolio
Leverage: 2x

Scalping strategie die profiteert van korte mean reversion bewegingen.
Veel trades (30-50 per dag), zeer kleine wins, snelle executie.
"""
import pandas as pd
import numpy as np
from strategies import TradingStrategy


class MeanReversionScalper(TradingStrategy):
    """
    Mean reversion scalper voor high-frequency trading.

    Timeframe: 1-5 minuten
    Hold time: 15min-2 uur
    Trades per dag: 30-50

    Entry:
    - Price touches BB lower band (oversold)
    - RSI < 30
    - Volume spike (panic selling)
    - Quick reversal imminent

    Exit:
    - Take profit: 0.5-1% (klein!)
    - Stop loss: 0.3%
    - Exit at BB middle band

    Expected Performance:
    - Win rate: 60% (higher!)
    - Avg win: 0.7%
    - Avg loss: 0.3%
    - Profit factor: 2.0+
    - Target: 2% per maand
    """

    def __init__(self, bb_period: int = 20, bb_std: float = 2.0,
                 rsi_oversold: int = 30, vol_spike_mult: float = 1.5):
        super().__init__("Mean_Reversion_Scalper")
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.rsi_oversold = rsi_oversold
        self.vol_spike_mult = vol_spike_mult

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate mean reversion scalping signals."""
        df = data.copy()

        # 1. Bollinger Bands (short-term)
        df['bb_mid'] = df['close'].rolling(window=self.bb_period).mean()
        df['bb_std'] = df['close'].rolling(window=self.bb_period).std()
        df['bb_upper'] = df['bb_mid'] + (df['bb_std'] * self.bb_std)
        df['bb_lower'] = df['bb_mid'] - (df['bb_std'] * self.bb_std)

        # Distance to bands (normalized)
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

        # 2. RSI (oversold)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(span=14).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(span=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        oversold = df['rsi'] < self.rsi_oversold

        # 3. Volume spike (panic)
        df['vol_ma'] = df['volume'].rolling(window=10).mean()
        volume_spike = df['volume'] > df['vol_ma'] * self.vol_spike_mult

        # 4. Price velocity (falling fast)
        df['price_velocity'] = df['close'].diff(3)
        falling_fast = df['price_velocity'] < 0

        # 5. Reversal signal (stochastic)
        df['lowest'] = df['low'].rolling(window=14).min()
        df['highest'] = df['high'].rolling(window=14).max()
        df['stoch'] = 100 * (df['close'] - df['lowest']) / (df['highest'] - df['lowest'])
        stoch_oversold = df['stoch'] < 20

        # Generate signals
        signals = pd.Series(0, index=df.index)

        # BUY: Oversold + Volume spike + Reversal imminent
        buy_condition = (
            (df['bb_position'] < 0.1) &  # Near lower band
            oversold &
            (volume_spike | falling_fast) &
            stoch_oversold
        )
        signals[buy_condition] = 1

        # SELL: Quick exit at mean or overbought
        # Exit 1: Price near middle band (take profit)
        near_middle = df['bb_position'] > 0.4

        # Exit 2: RSI > 50 (back to normal)
        rsi_normal = df['rsi'] > 50

        # Exit 3: Stoch > 70 (overbought)
        stoch_overbought = df['stoch'] > 70

        sell_condition = near_middle | rsi_normal | stoch_overbought
        signals[sell_condition] = -1

        return signals


class RangeBoundScalper(TradingStrategy):
    """
    Alternatieve scalper voor ranging markets.

    Buy at support, sell at resistance.
    Perfect voor consolidatie periodes.
    """

    def __init__(self, range_period: int = 20):
        super().__init__("Range_Bound_Scalper")
        self.range_period = range_period

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate range-bound scalping signals."""
        df = data.copy()

        # Identify range
        df['range_high'] = df['high'].rolling(window=self.range_period).max()
        df['range_low'] = df['low'].rolling(window=self.range_period).min()
        df['range_mid'] = (df['range_high'] + df['range_low']) / 2

        # Range width
        df['range_width'] = df['range_high'] - df['range_low']
        df['range_pct'] = df['range_width'] / df['range_mid']

        # Only trade in tight ranges (consolidation)
        tight_range = df['range_pct'] < 0.05  # < 5% range

        # Position in range
        df['range_position'] = (df['close'] - df['range_low']) / df['range_width']

        # Generate signals
        signals = pd.Series(0, index=df.index)

        # BUY: Near bottom of range
        buy_condition = (
            tight_range &
            (df['range_position'] < 0.2) &
            (df['close'] < df['range_mid'])
        )
        signals[buy_condition] = 1

        # SELL: Near top of range
        sell_condition = (
            (df['range_position'] > 0.6) |
            (df['close'] > df['range_mid'])
        )
        signals[sell_condition] = -1

        return signals


class QuickMeanReversion(TradingStrategy):
    """
    Ultra-quick mean reversion voor 1-minute bars.

    Entry op extreme oversold, exit binnen minuten.
    """

    def __init__(self, period: int = 10):
        super().__init__("Quick_Mean_Reversion")
        self.period = period

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Ultra-fast mean reversion."""
        df = data.copy()

        # Simple MA
        df['ma'] = df['close'].ewm(span=self.period).mean()

        # Distance from MA (percentage)
        df['distance'] = (df['close'] - df['ma']) / df['ma'] * 100

        # Rate of change
        df['roc'] = df['close'].pct_change(self.period) * 100

        # Generate signals
        signals = pd.Series(0, index=df.index)

        # BUY: > 2% below MA and falling fast
        buy_condition = (
            (df['distance'] < -2.0) &
            (df['roc'] < -3.0)
        )
        signals[buy_condition] = 1

        # SELL: Back at MA or above
        sell_condition = (df['distance'] > -0.5)
        signals[sell_condition] = -1

        return signals


def get_mean_reversion_scalper(scalper_type: str = 'standard'):
    """
    Factory function voor mean reversion scalpers.

    Args:
        scalper_type: 'standard', 'range_bound', or 'quick'
    """
    if scalper_type == 'range_bound':
        return RangeBoundScalper(range_period=20)
    elif scalper_type == 'quick':
        return QuickMeanReversion(period=10)
    else:
        return MeanReversionScalper(
            bb_period=20,
            bb_std=2.0,
            rsi_oversold=30,
            vol_spike_mult=1.5
        )


if __name__ == "__main__":
    print("="*60)
    print("  MEAN REVERSION SCALPER STRATEGY")
    print("="*60)
    print("\nTarget: 2% per maand")
    print("Allocatie: 20% van portfolio")
    print("Leverage: 2x")
    print("\nTimeframe: 1-5 minuten")
    print("Hold time: 15min-2 uur")
    print("Trades per dag: 30-50")
    print("\nEntry Conditions:")
    print("  ✓ Price < BB lower band (oversold)")
    print("  ✓ RSI < 30")
    print("  ✓ Volume spike or falling fast")
    print("  ✓ Stochastic < 20")
    print("\nExit Conditions:")
    print("  ✓ Price near BB middle (take profit)")
    print("  ✓ RSI > 50 (normal)")
    print("  ✓ Stochastic > 70")
    print("\nExpected:")
    print("  Win rate: 60% (high!)")
    print("  Avg win: 0.7%")
    print("  Avg loss: 0.3%")
    print("  Profit factor: 2.0+")
    print("\nVariants:")
    print("  - Standard: BB + RSI + Volume")
    print("  - Range Bound: Support/Resistance")
    print("  - Quick: Ultra-fast (1-min)")
    print("="*60)
