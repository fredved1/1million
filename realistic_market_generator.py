"""
REALISTIC MARKET DATA GENERATOR
Simuleert echte market patterns ipv pure random walk.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class RealisticMarketGenerator:
    """
    Genereert realistische market data met:
    - Trends (bull/bear cycles)
    - Mean reversion zones
    - Breakout patterns
    - Volatility clustering
    - Volume patterns
    """

    def __init__(self, seed: int = None):
        if seed:
            np.random.seed(seed)

    def generate_trending_market(self, n_days: int = 365, base_price: float = 100.0,
                                 trend_strength: float = 0.3, volatility: float = 0.02):
        """
        Genereert markt met trends en cyclussen.

        Args:
            n_days: Aantal dagen data
            base_price: Start prijs
            trend_strength: Hoe sterk de trends zijn (0-1)
            volatility: Dagelijkse volatiliteit
        """
        dates = pd.date_range(end=datetime.now(), periods=n_days, freq='D')

        # Create trend cycles (bull/bear periods)
        cycle_length = 60  # dagen per cycle
        n_cycles = n_days // cycle_length + 1

        # Random bull/bear cycles
        cycle_directions = np.random.choice([-1, 1], size=n_cycles)
        trend = np.zeros(n_days)

        for i in range(n_cycles):
            start_idx = i * cycle_length
            end_idx = min((i + 1) * cycle_length, n_days)
            cycle_len = end_idx - start_idx

            # Smooth trend binnen cycle
            if cycle_directions[i] > 0:
                # Bull cycle
                cycle_trend = np.linspace(0, trend_strength, cycle_len)
            else:
                # Bear cycle
                cycle_trend = np.linspace(0, -trend_strength * 0.7, cycle_len)

            trend[start_idx:end_idx] = cycle_trend

        # Add mean reversion within trends
        mean_reversion_noise = np.random.normal(0, volatility, n_days)

        # Add occasional sharp moves (breakouts/crashes)
        breakout_prob = 0.02  # 2% kans per dag
        breakouts = np.random.random(n_days) < breakout_prob
        breakout_sizes = np.random.choice([-1, 1], n_days) * np.random.uniform(0.02, 0.05, n_days)
        breakout_returns = breakouts * breakout_sizes

        # Combine all effects
        daily_returns = (trend / n_days) + mean_reversion_noise + breakout_returns

        # Generate price series
        closes = base_price * (1 + daily_returns).cumprod()

        # Generate OHLC
        daily_range = abs(daily_returns) * 2
        opens = closes * (1 + np.random.normal(0, 0.003, n_days))
        highs = np.maximum(opens, closes) * (1 + abs(np.random.normal(0, daily_range, n_days)))
        lows = np.minimum(opens, closes) * (1 - abs(np.random.normal(0, daily_range, n_days)))

        # Generate volume (higher on big moves)
        base_volume = np.random.lognormal(15, 0.5, n_days)
        volume_multiplier = 1 + abs(daily_returns) * 10  # Meer volume op grote moves
        volumes = base_volume * volume_multiplier

        df = pd.DataFrame({
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        }, index=dates)

        return df

    def generate_mean_reverting_market(self, n_days: int = 365, base_price: float = 100.0,
                                       reversion_speed: float = 0.1, volatility: float = 0.02):
        """
        Genereert sterk mean-reverting market (range-bound).
        Perfect voor mean reversion strategies!
        """
        dates = pd.date_range(end=datetime.now(), periods=n_days, freq='D')

        prices = [base_price]
        center = base_price

        for i in range(n_days - 1):
            # Mean reversion force
            distance_from_center = (prices[-1] - center) / center
            reversion_force = -distance_from_center * reversion_speed

            # Random noise
            noise = np.random.normal(0, volatility)

            # Next price
            daily_return = reversion_force + noise
            next_price = prices[-1] * (1 + daily_return)
            prices.append(next_price)

        closes = np.array(prices)

        # Generate OHLC
        opens = closes * (1 + np.random.normal(0, 0.003, n_days))
        daily_range = volatility * 1.5
        highs = np.maximum(opens, closes) * (1 + abs(np.random.normal(0, daily_range, n_days)))
        lows = np.minimum(opens, closes) * (1 - abs(np.random.normal(0, daily_range, n_days)))

        # Volume (higher at extremes)
        distance_from_center_pct = abs(closes - center) / center
        base_volume = np.random.lognormal(15, 0.5, n_days)
        volumes = base_volume * (1 + distance_from_center_pct * 5)

        df = pd.DataFrame({
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        }, index=dates)

        return df

    def generate_breakout_market(self, n_days: int = 365, base_price: float = 100.0,
                                 breakout_frequency: int = 30, volatility: float = 0.02):
        """
        Genereert market met consolidation + breakout patterns.
        Perfect voor breakout strategies!
        """
        dates = pd.date_range(end=datetime.now(), periods=n_days, freq='D')

        prices = [base_price]
        in_consolidation = True
        consolidation_days = 0
        breakout_direction = 1

        for i in range(n_days - 1):
            if in_consolidation:
                # Range-bound movement
                noise = np.random.normal(0, volatility * 0.5)
                daily_return = noise
                consolidation_days += 1

                # Time for breakout?
                if consolidation_days >= breakout_frequency:
                    if np.random.random() < 0.7:  # 70% kans op breakout
                        in_consolidation = False
                        breakout_direction = np.random.choice([-1, 1])
                        consolidation_days = 0
            else:
                # Breakout movement
                trend = breakout_direction * 0.02  # 2% per dag
                noise = np.random.normal(0, volatility)
                daily_return = trend + noise

                # Breakout duurt 5-10 dagen
                if np.random.random() < 0.15:  # 15% kans om te stoppen
                    in_consolidation = True

            next_price = prices[-1] * (1 + daily_return)
            prices.append(next_price)

        closes = np.array(prices)

        # Generate OHLC
        opens = closes * (1 + np.random.normal(0, 0.003, n_days))
        daily_changes = abs(np.diff(closes, prepend=closes[0]) / closes)
        highs = np.maximum(opens, closes) * (1 + daily_changes * 2)
        lows = np.minimum(opens, closes) * (1 - daily_changes * 2)

        # Volume (spikes on breakouts)
        base_volume = np.random.lognormal(15, 0.5, n_days)
        volume_multiplier = 1 + daily_changes * 20  # Veel volume op breakouts
        volumes = base_volume * volume_multiplier

        df = pd.DataFrame({
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        }, index=dates)

        return df

    def generate_volatile_crypto_market(self, n_days: int = 365, base_price: float = 100.0):
        """
        Simuleert crypto market: hoge volatiliteit, sterke trends, scherpe reversals.
        """
        dates = pd.date_range(end=datetime.now(), periods=n_days, freq='D')

        # Crypto heeft:
        # - Hoge volatiliteit (5-10% per dag mogelijk)
        # - Sterke trends (pump & dump)
        # - Scherpe reversals
        # - Volume spikes

        prices = [base_price]

        # Create pump & dump cycles
        for i in range(n_days - 1):
            # Base volatility
            vol = np.random.uniform(0.03, 0.08)  # 3-8% daily

            # Trend (changes every ~20 days)
            cycle_position = (i % 40) / 40
            if cycle_position < 0.6:
                # Pump phase
                trend = 0.03  # 3% uptrend
            else:
                # Dump phase
                trend = -0.05  # -5% downtrend

            # Occasional sharp moves
            if np.random.random() < 0.05:
                shock = np.random.choice([-1, 1]) * np.random.uniform(0.1, 0.3)
            else:
                shock = 0

            daily_return = trend + np.random.normal(0, vol) + shock
            next_price = prices[-1] * (1 + daily_return)
            prices.append(max(next_price, base_price * 0.1))  # Never go below 10%

        closes = np.array(prices)

        # OHLC with large wicks
        opens = closes * (1 + np.random.normal(0, 0.01, n_days))
        daily_vol = abs(np.diff(closes, prepend=closes[0]) / closes)
        highs = np.maximum(opens, closes) * (1 + abs(np.random.normal(0, daily_vol * 3, n_days)))
        lows = np.minimum(opens, closes) * (1 - abs(np.random.normal(0, daily_vol * 3, n_days)))

        # Crypto volume patterns
        base_volume = np.random.lognormal(16, 1, n_days)
        volume_spikes = np.random.random(n_days) < 0.1  # 10% kans
        volumes = base_volume * (1 + volume_spikes * np.random.uniform(3, 10, n_days))

        df = pd.DataFrame({
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        }, index=dates)

        return df


def generate_realistic_market(market_type: str = 'trending', n_days: int = 365,
                              **kwargs) -> pd.DataFrame:
    """
    Factory function voor realistische market data.

    Args:
        market_type: 'trending', 'mean_reverting', 'breakout', 'crypto'
        n_days: Aantal dagen
        **kwargs: Extra parameters voor generator

    Returns:
        DataFrame met OHLCV data
    """
    generator = RealisticMarketGenerator()

    if market_type == 'mean_reverting':
        return generator.generate_mean_reverting_market(n_days=n_days, **kwargs)
    elif market_type == 'breakout':
        return generator.generate_breakout_market(n_days=n_days, **kwargs)
    elif market_type == 'crypto':
        return generator.generate_volatile_crypto_market(n_days=n_days, **kwargs)
    else:  # trending
        return generator.generate_trending_market(n_days=n_days, **kwargs)


if __name__ == "__main__":
    print("="*60)
    print("  REALISTIC MARKET DATA GENERATOR")
    print("="*60)

    # Test alle market types
    market_types = ['trending', 'mean_reverting', 'breakout', 'crypto']

    for market_type in market_types:
        print(f"\n📊 Generating {market_type} market...")
        data = generate_realistic_market(market_type, n_days=365)

        print(f"  Samples: {len(data)}")
        print(f"  Price range: ${data['close'].min():.2f} - ${data['close'].max():.2f}")
        print(f"  Total return: {(data['close'].iloc[-1] / data['close'].iloc[0] - 1) * 100:.2f}%")
        print(f"  Avg daily vol: {data['close'].pct_change().std() * 100:.2f}%")
        print(f"  Max daily move: {data['close'].pct_change().abs().max() * 100:.2f}%")

    print("\n✅ All market types generated successfully!")
