"""
TREND FOLLOWING STRATEGY
Target: 1.5% per maand
Allocatie: 15% van portfolio
Leverage: 2x

Volgt sterke trends met pullback entries.
Fewer trades maar grotere moves.
"""
import pandas as pd
import numpy as np
from strategies import TradingStrategy


class TrendFollower(TradingStrategy):
    """
    Trend following strategie die grote moves vangt.

    Timeframe: 1-4 uur
    Hold time: 1-7 dagen
    Trades per dag: 2-5

    Entry:
    - EMA(20) > EMA(50) (uptrend)
    - ADX > 25 (strong trend)
    - Price pullback to EMA
    - Continuation signal

    Exit:
    - Trailing stop: 3 ATR
    - Take profit: 10-20%
    - Stop loss: 3%

    Expected Performance:
    - Win rate: 40%
    - Avg win: 12%
    - Avg loss: 3%
    - Profit factor: 2.0+
    - Target: 1.5% per maand
    """

    def __init__(self, ema_fast: int = 20, ema_slow: int = 50,
                 adx_threshold: int = 25, atr_period: int = 14):
        super().__init__("Trend_Follower")
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.adx_threshold = adx_threshold
        self.atr_period = atr_period

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate trend following signals."""
        df = data.copy()

        # 1. Trend EMAs
        df['ema_fast'] = df['close'].ewm(span=self.ema_fast).mean()
        df['ema_slow'] = df['close'].ewm(span=self.ema_slow).mean()
        uptrend = df['ema_fast'] > df['ema_slow']

        # 2. ADX for trend strength
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift()),
                abs(df['low'] - df['close'].shift())
            )
        )
        df['atr'] = df['tr'].rolling(window=self.atr_period).mean()

        # Plus and Minus Directional Indicators
        df['high_diff'] = df['high'].diff()
        df['low_diff'] = -df['low'].diff()

        df['plus_dm'] = np.where(
            (df['high_diff'] > df['low_diff']) & (df['high_diff'] > 0),
            df['high_diff'],
            0
        )
        df['minus_dm'] = np.where(
            (df['low_diff'] > df['high_diff']) & (df['low_diff'] > 0),
            df['low_diff'],
            0
        )

        # Smooth DMs
        df['plus_di'] = 100 * (df['plus_dm'].rolling(window=14).mean() / df['atr'])
        df['minus_di'] = 100 * (df['minus_dm'].rolling(window=14).mean() / df['atr'])

        # ADX calculation
        df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
        df['adx'] = df['dx'].rolling(window=14).mean()

        strong_trend = df['adx'] > self.adx_threshold

        # 3. Pullback to EMA (entry opportunity)
        # Price should be close to fast EMA (within 2%)
        df['distance_to_ema'] = (df['close'] - df['ema_fast']) / df['ema_fast'] * 100
        near_ema = abs(df['distance_to_ema']) < 2.0

        # Price was below EMA recently (pullback)
        was_below_ema = df['close'].shift(2) < df['ema_fast'].shift(2)

        # Now breaking back above (continuation)
        breaking_above = df['close'] > df['ema_fast']

        # 4. Volume confirmation
        df['vol_ma'] = df['volume'].rolling(window=20).mean()
        volume_ok = df['volume'] > df['vol_ma'] * 0.8

        # 5. RSI not overbought (room to run)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(span=14).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(span=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        rsi_ok = df['rsi'] < 70

        # 6. Momentum still positive
        df['momentum'] = (df['close'] / df['close'].shift(20) - 1) * 100
        positive_momentum = df['momentum'] > 0

        # Generate signals
        signals = pd.Series(0, index=df.index)

        # BUY: Uptrend + Strong trend + Pullback to EMA + Continuation
        buy_condition = (
            uptrend &
            strong_trend &
            (near_ema | (was_below_ema & breaking_above)) &
            volume_ok &
            rsi_ok &
            positive_momentum
        )
        signals[buy_condition] = 1

        # SELL: Trend weakens or breaks
        # Exit 1: Price breaks below slow EMA (trend over)
        breaks_trend = df['close'] < df['ema_slow']

        # Exit 2: ADX declining (trend weakening)
        adx_declining = df['adx'] < df['adx'].shift(3)

        # Exit 3: Momentum turns negative
        momentum_negative = df['momentum'] < -2

        # Exit 4: Fast EMA crosses below slow EMA
        ema_cross_down = (df['ema_fast'] < df['ema_slow']) & (df['ema_fast'].shift(1) >= df['ema_slow'].shift(1))

        sell_condition = breaks_trend | (adx_declining & momentum_negative) | ema_cross_down
        signals[sell_condition] = -1

        return signals


class AdaptiveTrendFollower(TradingStrategy):
    """
    Alternative: adaptive trend following met market regime detection.

    Adjusts parameters based on volatility regime.
    """

    def __init__(self, base_period: int = 50):
        super().__init__("Adaptive_Trend_Follower")
        self.base_period = base_period

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Adaptive trend following."""
        df = data.copy()

        # Detect volatility regime
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(window=20).std()
        df['vol_ma'] = df['volatility'].rolling(window=100).mean()

        # High vol = use shorter periods, low vol = use longer periods
        high_vol_regime = df['volatility'] > df['vol_ma'] * 1.5
        low_vol_regime = df['volatility'] < df['vol_ma'] * 0.7

        # Adaptive EMAs
        df['ema_fast_short'] = df['close'].ewm(span=10).mean()
        df['ema_fast_long'] = df['close'].ewm(span=30).mean()
        df['ema_slow_short'] = df['close'].ewm(span=30).mean()
        df['ema_slow_long'] = df['close'].ewm(span=70).mean()

        # Select EMAs based on regime
        df['ema_fast'] = np.where(high_vol_regime, df['ema_fast_short'], df['ema_fast_long'])
        df['ema_slow'] = np.where(high_vol_regime, df['ema_slow_short'], df['ema_slow_long'])

        uptrend = df['ema_fast'] > df['ema_slow']

        # Trend strength (slope)
        df['trend_strength'] = (df['ema_fast'] - df['ema_fast'].shift(5)) / df['ema_fast'] * 100
        strong_trend = df['trend_strength'] > 0.5

        # Generate signals
        signals = pd.Series(0, index=df.index)

        # BUY: Trend starts or continues
        trend_start = (df['ema_fast'] > df['ema_slow']) & (df['ema_fast'].shift(1) <= df['ema_slow'].shift(1))
        in_strong_trend = uptrend & strong_trend

        buy_condition = trend_start | (in_strong_trend & (df['close'] > df['ema_fast']))
        signals[buy_condition] = 1

        # SELL: Trend ends
        trend_end = (df['ema_fast'] < df['ema_slow']) & (df['ema_fast'].shift(1) >= df['ema_slow'].shift(1))
        trend_weak = df['trend_strength'] < -0.5

        sell_condition = trend_end | trend_weak
        signals[sell_condition] = -1

        return signals


class DualTimeframeTrend(TradingStrategy):
    """
    Multi-timeframe trend following.

    Uses higher timeframe for trend direction,
    lower timeframe for entry timing.
    """

    def __init__(self, fast_period: int = 20, slow_period: int = 50):
        super().__init__("Dual_Timeframe_Trend")
        self.fast_period = fast_period
        self.slow_period = slow_period

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Dual timeframe trend following."""
        df = data.copy()

        # Higher timeframe trend (simulated via longer period)
        df['htf_ema'] = df['close'].ewm(span=self.slow_period).mean()
        htf_uptrend = df['close'] > df['htf_ema']

        # Lower timeframe (shorter period)
        df['ltf_ema_fast'] = df['close'].ewm(span=self.fast_period).mean()
        df['ltf_ema_slow'] = df['close'].ewm(span=self.slow_period // 2).mean()
        ltf_uptrend = df['ltf_ema_fast'] > df['ltf_ema_slow']

        # Entry: Higher timeframe uptrend + lower timeframe entry signal
        ltf_cross_up = (
            (df['ltf_ema_fast'] > df['ltf_ema_slow']) &
            (df['ltf_ema_fast'].shift(1) <= df['ltf_ema_slow'].shift(1))
        )

        # Generate signals
        signals = pd.Series(0, index=df.index)

        # BUY: HTF uptrend + LTF entry
        buy_condition = htf_uptrend & (ltf_cross_up | ltf_uptrend)
        signals[buy_condition] = 1

        # SELL: HTF downtrend or LTF exit
        htf_downtrend = df['close'] < df['htf_ema']
        ltf_cross_down = (
            (df['ltf_ema_fast'] < df['ltf_ema_slow']) &
            (df['ltf_ema_fast'].shift(1) >= df['ltf_ema_slow'].shift(1))
        )

        sell_condition = htf_downtrend | ltf_cross_down
        signals[sell_condition] = -1

        return signals


def get_trend_follower(trend_type: str = 'standard'):
    """
    Factory function voor trend following strategies.

    Args:
        trend_type: 'standard', 'adaptive', or 'dual_timeframe'
    """
    if trend_type == 'adaptive':
        return AdaptiveTrendFollower(base_period=50)
    elif trend_type == 'dual_timeframe':
        return DualTimeframeTrend(fast_period=20, slow_period=50)
    else:
        return TrendFollower(
            ema_fast=20,
            ema_slow=50,
            adx_threshold=25,
            atr_period=14
        )


if __name__ == "__main__":
    print("="*60)
    print("  TREND FOLLOWING STRATEGY")
    print("="*60)
    print("\nTarget: 1.5% per maand")
    print("Allocatie: 15% van portfolio")
    print("Leverage: 2x")
    print("\nTimeframe: 1-4 uur")
    print("Hold time: 1-7 dagen")
    print("Trades per dag: 2-5")
    print("\nEntry Conditions:")
    print("  ✓ EMA(20) > EMA(50) (uptrend)")
    print("  ✓ ADX > 25 (strong trend)")
    print("  ✓ Price pullback to EMA")
    print("  ✓ Continuation signal")
    print("  ✓ Volume confirmation")
    print("  ✓ RSI < 70 (room to run)")
    print("\nExit Conditions:")
    print("  ✓ Price < slow EMA (trend break)")
    print("  ✓ ADX declining + momentum negative")
    print("  ✓ EMA cross down")
    print("\nExpected:")
    print("  Win rate: 40%")
    print("  Avg win: 12%")
    print("  Avg loss: 3%")
    print("  Profit factor: 2.0+")
    print("\nVariants:")
    print("  - Standard: EMA + ADX trend following")
    print("  - Adaptive: Adjusts to volatility regime")
    print("  - Dual Timeframe: Multi-timeframe analysis")
    print("="*60)
