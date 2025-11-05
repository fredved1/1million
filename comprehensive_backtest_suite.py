"""
COMPREHENSIVE BACKTEST SUITE
Test alle strategieën op ALLE mogelijke manieren.
Validate dat we echt rijk kunnen worden! 💰
"""
import pandas as pd
import numpy as np
from datetime import datetime
import sys
from typing import Dict, List, Tuple
import itertools

from hf_momentum_strategy import HighFrequencyMomentum
from mean_reversion_scalper import MeanReversionScalper
from breakout_catcher import BreakoutCatcher
from trend_follower import TrendFollower
from swing_reversal import SwingReversal
from data_fetcher_simple import generate_sample_data


class ComprehensiveBacktestSuite:
    """
    Complete test suite voor multi-strategy validation.
    """

    def __init__(self, initial_capital: float = 10000):
        self.initial_capital = initial_capital
        self.results = []

    def run_strategy_backtest(self, strategy, data, allocation, leverage):
        """Run single strategy backtest."""
        strategy_capital = self.initial_capital * allocation
        capital = strategy_capital
        position = 0
        entry_price = 0
        trades = []

        # Generate signals
        try:
            signals = strategy.generate_signals(data)
        except Exception as e:
            print(f"  ⚠️  Signal generation failed: {e}")
            return None

        for i in range(1, len(data)):
            if signals.iloc[i] == 1 and position == 0:  # Buy
                entry_price = data['close'].iloc[i]
                position = (capital * 0.95 / entry_price) * leverage

            elif signals.iloc[i] == -1 and position > 0:  # Sell
                exit_price = data['close'].iloc[i]
                pnl = (exit_price - entry_price) * position
                capital += pnl
                trades.append({
                    'pnl': pnl,
                    'return': (exit_price / entry_price - 1) * 100 * leverage
                })
                position = 0

        if len(trades) == 0:
            return None

        wins = [t for t in trades if t['pnl'] > 0]
        losses = [t for t in trades if t['pnl'] < 0]

        return {
            'name': strategy.name,
            'final_capital': capital,
            'total_return': (capital - strategy_capital) / strategy_capital * 100,
            'num_trades': len(trades),
            'win_rate': len(wins) / len(trades) * 100 if trades else 0,
            'profit_factor': (sum([t['pnl'] for t in wins]) / abs(sum([t['pnl'] for t in losses]))) if losses else 999,
        }

    def test_configuration(self, config: Dict, data: pd.DataFrame) -> Dict:
        """
        Test een complete portfolio configuratie.

        Args:
            config: Dict met strategy parameters, allocations, leverage
            data: Market data

        Returns:
            Performance metrics
        """
        strategies = [
            (HighFrequencyMomentum(**config['hf_params']),
             config['allocations']['hf'],
             config['leverage']['hf']),

            (MeanReversionScalper(**config['mr_params']),
             config['allocations']['mr'],
             config['leverage']['mr']),

            (BreakoutCatcher(**config['bo_params']),
             config['allocations']['bo'],
             config['leverage']['bo']),

            (TrendFollower(**config['tf_params']),
             config['allocations']['tf'],
             config['leverage']['tf']),

            (SwingReversal(**config['sr_params']),
             config['allocations']['sr'],
             config['leverage']['sr'])
        ]

        results = []
        for strategy, allocation, leverage in strategies:
            result = self.run_strategy_backtest(strategy, data, allocation, leverage)
            if result:
                results.append(result)

        if not results:
            return None

        # Combine results
        total_capital = sum([r['final_capital'] for r in results])
        total_return = (total_capital - self.initial_capital) / self.initial_capital * 100

        return {
            'config_name': config['name'],
            'total_capital': total_capital,
            'total_return': total_return,
            'total_trades': sum([r['num_trades'] for r in results]),
            'avg_win_rate': np.mean([r['win_rate'] for r in results]),
            'strategies': results
        }

    def test_1_relaxed_parameters(self):
        """TEST 1: Relaxed parameters voor meer trades."""
        print("\n" + "="*80)
        print("  TEST 1: RELAXED PARAMETERS (Meer Trades Genereren)")
        print("="*80)

        configs = [
            {
                'name': 'Relaxed_Conservative',
                'hf_params': {'lookback': 5, 'momentum_threshold': 0.3, 'rsi_min': 35, 'rsi_max': 70},
                'mr_params': {'bb_period': 15, 'bb_std': 1.8, 'rsi_oversold': 35, 'vol_spike_mult': 1.2},
                'bo_params': {'lookback': 20, 'momentum_threshold': 1.0, 'volume_mult': 1.5},
                'tf_params': {'ema_fast': 15, 'ema_slow': 40, 'adx_threshold': 20, 'atr_period': 14},
                'sr_params': {'rsi_oversold': 35, 'lookback': 40},
                'allocations': {'hf': 0.30, 'mr': 0.20, 'bo': 0.25, 'tf': 0.15, 'sr': 0.10},
                'leverage': {'hf': 3.0, 'mr': 2.0, 'bo': 4.0, 'tf': 2.0, 'sr': 2.0}
            },
            {
                'name': 'Relaxed_Aggressive',
                'hf_params': {'lookback': 3, 'momentum_threshold': 0.2, 'rsi_min': 30, 'rsi_max': 75},
                'mr_params': {'bb_period': 10, 'bb_std': 1.5, 'rsi_oversold': 40, 'vol_spike_mult': 1.0},
                'bo_params': {'lookback': 15, 'momentum_threshold': 0.8, 'volume_mult': 1.3},
                'tf_params': {'ema_fast': 10, 'ema_slow': 30, 'adx_threshold': 15, 'atr_period': 10},
                'sr_params': {'rsi_oversold': 40, 'lookback': 30},
                'allocations': {'hf': 0.30, 'mr': 0.20, 'bo': 0.25, 'tf': 0.15, 'sr': 0.10},
                'leverage': {'hf': 3.0, 'mr': 2.0, 'bo': 4.0, 'tf': 2.0, 'sr': 2.0}
            },
            {
                'name': 'Super_Relaxed',
                'hf_params': {'lookback': 2, 'momentum_threshold': 0.1, 'rsi_min': 25, 'rsi_max': 80},
                'mr_params': {'bb_period': 8, 'bb_std': 1.3, 'rsi_oversold': 45, 'vol_spike_mult': 0.8},
                'bo_params': {'lookback': 10, 'momentum_threshold': 0.5, 'volume_mult': 1.2},
                'tf_params': {'ema_fast': 8, 'ema_slow': 25, 'adx_threshold': 12, 'atr_period': 8},
                'sr_params': {'rsi_oversold': 45, 'lookback': 25},
                'allocations': {'hf': 0.30, 'mr': 0.20, 'bo': 0.25, 'tf': 0.15, 'sr': 0.10},
                'leverage': {'hf': 3.0, 'mr': 2.0, 'bo': 4.0, 'tf': 2.0, 'sr': 2.0}
            }
        ]

        data = generate_sample_data(n_days=365, volatility=0.03)
        results = []

        for config in configs:
            print(f"\n🔧 Testing: {config['name']}")
            result = self.test_configuration(config, data)
            if result:
                results.append(result)
                days = 365
                months = days / 30.0
                monthly_return = result['total_return'] / months
                print(f"  Total Return: {result['total_return']:.2f}%")
                print(f"  Monthly Return: {monthly_return:.2f}%")
                print(f"  Total Trades: {result['total_trades']}")
                print(f"  Avg Win Rate: {result['avg_win_rate']:.1f}%")

        return results

    def test_2_leverage_variations(self):
        """TEST 2: Test verschillende leverage settings."""
        print("\n" + "="*80)
        print("  TEST 2: LEVERAGE VARIATIONS (1x, 2x, 3x, 5x, 10x)")
        print("="*80)

        base_config = {
            'name': 'Base',
            'hf_params': {'lookback': 5, 'momentum_threshold': 0.3, 'rsi_min': 35, 'rsi_max': 70},
            'mr_params': {'bb_period': 15, 'bb_std': 1.8, 'rsi_oversold': 35, 'vol_spike_mult': 1.2},
            'bo_params': {'lookback': 20, 'momentum_threshold': 1.0, 'volume_mult': 1.5},
            'tf_params': {'ema_fast': 15, 'ema_slow': 40, 'adx_threshold': 20, 'atr_period': 14},
            'sr_params': {'rsi_oversold': 35, 'lookback': 40},
            'allocations': {'hf': 0.30, 'mr': 0.20, 'bo': 0.25, 'tf': 0.15, 'sr': 0.10},
        }

        leverage_configs = [
            {'name': 'No_Leverage_1x', 'hf': 1.0, 'mr': 1.0, 'bo': 1.0, 'tf': 1.0, 'sr': 1.0},
            {'name': 'Conservative_2x', 'hf': 2.0, 'mr': 2.0, 'bo': 2.0, 'tf': 2.0, 'sr': 2.0},
            {'name': 'Standard_3x', 'hf': 3.0, 'mr': 2.0, 'bo': 4.0, 'tf': 2.0, 'sr': 2.0},
            {'name': 'Aggressive_5x', 'hf': 5.0, 'mr': 4.0, 'bo': 6.0, 'tf': 4.0, 'sr': 3.0},
            {'name': 'EXTREME_10x', 'hf': 10.0, 'mr': 8.0, 'bo': 12.0, 'tf': 8.0, 'sr': 6.0},
        ]

        data = generate_sample_data(n_days=365, volatility=0.03)
        results = []

        for lev_config in leverage_configs:
            config = base_config.copy()
            config['name'] = lev_config['name']
            config['leverage'] = {k: v for k, v in lev_config.items() if k != 'name'}

            print(f"\n⚡ Testing: {config['name']}")
            result = self.test_configuration(config, data)
            if result:
                results.append(result)
                monthly_return = result['total_return'] / 12
                print(f"  Total Return: {result['total_return']:.2f}%")
                print(f"  Monthly Return: {monthly_return:.2f}%")
                print(f"  Total Trades: {result['total_trades']}")

        return results

    def test_3_allocation_strategies(self):
        """TEST 3: Test verschillende allocation strategies."""
        print("\n" + "="*80)
        print("  TEST 3: ALLOCATION STRATEGIES")
        print("="*80)

        base_config = {
            'hf_params': {'lookback': 5, 'momentum_threshold': 0.3, 'rsi_min': 35, 'rsi_max': 70},
            'mr_params': {'bb_period': 15, 'bb_std': 1.8, 'rsi_oversold': 35, 'vol_spike_mult': 1.2},
            'bo_params': {'lookback': 20, 'momentum_threshold': 1.0, 'volume_mult': 1.5},
            'tf_params': {'ema_fast': 15, 'ema_slow': 40, 'adx_threshold': 20, 'atr_period': 14},
            'sr_params': {'rsi_oversold': 35, 'lookback': 40},
            'leverage': {'hf': 3.0, 'mr': 2.0, 'bo': 4.0, 'tf': 2.0, 'sr': 2.0}
        }

        allocation_strategies = [
            {'name': 'Equal_Weight', 'hf': 0.20, 'mr': 0.20, 'bo': 0.20, 'tf': 0.20, 'sr': 0.20},
            {'name': 'Standard', 'hf': 0.30, 'mr': 0.20, 'bo': 0.25, 'tf': 0.15, 'sr': 0.10},
            {'name': 'Focus_MeanReversion', 'hf': 0.15, 'mr': 0.50, 'bo': 0.15, 'tf': 0.10, 'sr': 0.10},
            {'name': 'Focus_Breakout', 'hf': 0.15, 'mr': 0.15, 'bo': 0.50, 'tf': 0.10, 'sr': 0.10},
            {'name': 'Aggressive_Split', 'hf': 0.40, 'mr': 0.10, 'bo': 0.40, 'tf': 0.05, 'sr': 0.05},
        ]

        data = generate_sample_data(n_days=365, volatility=0.03)
        results = []

        for alloc in allocation_strategies:
            config = base_config.copy()
            config['name'] = alloc['name']
            config['allocations'] = {k: v for k, v in alloc.items() if k != 'name'}

            print(f"\n💼 Testing: {config['name']}")
            result = self.test_configuration(config, data)
            if result:
                results.append(result)
                monthly_return = result['total_return'] / 12
                print(f"  Total Return: {result['total_return']:.2f}%")
                print(f"  Monthly Return: {monthly_return:.2f}%")

        return results

    def test_4_volatility_levels(self):
        """TEST 4: Test op verschillende volatility levels."""
        print("\n" + "="*80)
        print("  TEST 4: DIFFERENT VOLATILITY LEVELS")
        print("="*80)

        config = {
            'name': 'Standard',
            'hf_params': {'lookback': 5, 'momentum_threshold': 0.3, 'rsi_min': 35, 'rsi_max': 70},
            'mr_params': {'bb_period': 15, 'bb_std': 1.8, 'rsi_oversold': 35, 'vol_spike_mult': 1.2},
            'bo_params': {'lookback': 20, 'momentum_threshold': 1.0, 'volume_mult': 1.5},
            'tf_params': {'ema_fast': 15, 'ema_slow': 40, 'adx_threshold': 20, 'atr_period': 14},
            'sr_params': {'rsi_oversold': 35, 'lookback': 40},
            'allocations': {'hf': 0.30, 'mr': 0.20, 'bo': 0.25, 'tf': 0.15, 'sr': 0.10},
            'leverage': {'hf': 3.0, 'mr': 2.0, 'bo': 4.0, 'tf': 2.0, 'sr': 2.0}
        }

        volatility_levels = [
            ('Very_Low', 0.01),
            ('Low', 0.02),
            ('Medium', 0.03),
            ('High', 0.05),
            ('Very_High', 0.08),
            ('EXTREME', 0.15)
        ]

        results = []

        for vol_name, vol_level in volatility_levels:
            print(f"\n📊 Testing volatility: {vol_name} ({vol_level*100:.0f}%)")
            data = generate_sample_data(n_days=365, volatility=vol_level)
            result = self.test_configuration(config, data)
            if result:
                result['volatility'] = vol_level
                result['volatility_name'] = vol_name
                results.append(result)
                monthly_return = result['total_return'] / 12
                print(f"  Total Return: {result['total_return']:.2f}%")
                print(f"  Monthly Return: {monthly_return:.2f}%")

        return results

    def test_5_monte_carlo(self, n_simulations: int = 100):
        """TEST 5: Monte Carlo simulation."""
        print("\n" + "="*80)
        print(f"  TEST 5: MONTE CARLO SIMULATION ({n_simulations} runs)")
        print("="*80)

        config = {
            'name': 'Standard',
            'hf_params': {'lookback': 5, 'momentum_threshold': 0.3, 'rsi_min': 35, 'rsi_max': 70},
            'mr_params': {'bb_period': 15, 'bb_std': 1.8, 'rsi_oversold': 35, 'vol_spike_mult': 1.2},
            'bo_params': {'lookback': 20, 'momentum_threshold': 1.0, 'volume_mult': 1.5},
            'tf_params': {'ema_fast': 15, 'ema_slow': 40, 'adx_threshold': 20, 'atr_period': 14},
            'sr_params': {'rsi_oversold': 35, 'lookback': 40},
            'allocations': {'hf': 0.30, 'mr': 0.20, 'bo': 0.25, 'tf': 0.15, 'sr': 0.10},
            'leverage': {'hf': 3.0, 'mr': 2.0, 'bo': 4.0, 'tf': 2.0, 'sr': 2.0}
        }

        returns = []

        for i in range(n_simulations):
            if (i + 1) % 20 == 0:
                print(f"  Run {i+1}/{n_simulations}...")

            # Generate random market data
            data = generate_sample_data(n_days=365, volatility=np.random.uniform(0.02, 0.05))
            result = self.test_configuration(config, data)
            if result:
                monthly_return = result['total_return'] / 12
                returns.append(monthly_return)

        if returns:
            print(f"\n📈 Monte Carlo Results:")
            print(f"  Average Monthly Return: {np.mean(returns):.2f}%")
            print(f"  Median Monthly Return: {np.median(returns):.2f}%")
            print(f"  Std Dev: {np.std(returns):.2f}%")
            print(f"  Min: {np.min(returns):.2f}%")
            print(f"  Max: {np.max(returns):.2f}%")
            print(f"  Win Rate: {(np.array(returns) > 0).sum() / len(returns) * 100:.1f}%")
            print(f"  Probability > 5%/month: {(np.array(returns) > 5).sum() / len(returns) * 100:.1f}%")
            print(f"  Probability > 10%/month: {(np.array(returns) > 10).sum() / len(returns) * 100:.1f}%")

        return returns

    def test_6_market_conditions(self):
        """TEST 6: Bull, bear, sideways markets."""
        print("\n" + "="*80)
        print("  TEST 6: DIFFERENT MARKET CONDITIONS")
        print("="*80)

        config = {
            'name': 'Standard',
            'hf_params': {'lookback': 5, 'momentum_threshold': 0.3, 'rsi_min': 35, 'rsi_max': 70},
            'mr_params': {'bb_period': 15, 'bb_std': 1.8, 'rsi_oversold': 35, 'vol_spike_mult': 1.2},
            'bo_params': {'lookback': 20, 'momentum_threshold': 1.0, 'volume_mult': 1.5},
            'tf_params': {'ema_fast': 15, 'ema_slow': 40, 'adx_threshold': 20, 'atr_period': 14},
            'sr_params': {'rsi_oversold': 35, 'lookback': 40},
            'allocations': {'hf': 0.30, 'mr': 0.20, 'bo': 0.25, 'tf': 0.15, 'sr': 0.10},
            'leverage': {'hf': 3.0, 'mr': 2.0, 'bo': 4.0, 'tf': 2.0, 'sr': 2.0}
        }

        # Generate different market conditions
        market_conditions = []

        # Bull market
        print(f"\n🐂 Testing: BULL MARKET")
        dates = pd.date_range(end=datetime.now(), periods=365, freq='D')
        bull_trend = np.linspace(0, 0.5, 365)  # 50% uptrend
        returns = np.random.normal(0.002, 0.03, 365) + bull_trend / 365
        closes = 100 * (1 + returns).cumprod()
        data_bull = pd.DataFrame({
            'open': closes * 0.99,
            'high': closes * 1.02,
            'low': closes * 0.98,
            'close': closes,
            'volume': np.random.lognormal(15, 1, 365)
        }, index=dates)
        result = self.test_configuration(config, data_bull)
        if result:
            result['market'] = 'BULL'
            market_conditions.append(result)
            print(f"  Total Return: {result['total_return']:.2f}%")
            print(f"  Monthly Return: {result['total_return']/12:.2f}%")

        # Bear market
        print(f"\n🐻 Testing: BEAR MARKET")
        bear_trend = np.linspace(0, -0.3, 365)  # -30% downtrend
        returns = np.random.normal(-0.001, 0.03, 365) + bear_trend / 365
        closes = 100 * (1 + returns).cumprod()
        data_bear = pd.DataFrame({
            'open': closes * 0.99,
            'high': closes * 1.02,
            'low': closes * 0.98,
            'close': closes,
            'volume': np.random.lognormal(15, 1, 365)
        }, index=dates)
        result = self.test_configuration(config, data_bear)
        if result:
            result['market'] = 'BEAR'
            market_conditions.append(result)
            print(f"  Total Return: {result['total_return']:.2f}%")
            print(f"  Monthly Return: {result['total_return']/12:.2f}%")

        # Sideways market
        print(f"\n↔️  Testing: SIDEWAYS MARKET")
        returns = np.random.normal(0, 0.02, 365)  # No trend
        closes = 100 * (1 + returns).cumprod()
        data_sideways = pd.DataFrame({
            'open': closes * 0.99,
            'high': closes * 1.02,
            'low': closes * 0.98,
            'close': closes,
            'volume': np.random.lognormal(15, 1, 365)
        }, index=dates)
        result = self.test_configuration(config, data_sideways)
        if result:
            result['market'] = 'SIDEWAYS'
            market_conditions.append(result)
            print(f"  Total Return: {result['total_return']:.2f}%")
            print(f"  Monthly Return: {result['total_return']/12:.2f}%")

        return market_conditions

    def run_all_tests(self):
        """Run ALL tests."""
        print("\n" + "="*80)
        print("  🚀 COMPREHENSIVE BACKTEST SUITE")
        print("  Testing ALLES om te valideren dat we RIJK worden! 💰")
        print("="*80)

        all_results = {}

        # Test 1: Relaxed parameters
        all_results['relaxed'] = self.test_1_relaxed_parameters()

        # Test 2: Leverage variations
        all_results['leverage'] = self.test_2_leverage_variations()

        # Test 3: Allocation strategies
        all_results['allocations'] = self.test_3_allocation_strategies()

        # Test 4: Volatility levels
        all_results['volatility'] = self.test_4_volatility_levels()

        # Test 5: Monte Carlo
        all_results['monte_carlo'] = self.test_5_monte_carlo(n_simulations=100)

        # Test 6: Market conditions
        all_results['markets'] = self.test_6_market_conditions()

        return all_results


def find_best_configuration(results: Dict) -> Dict:
    """Find beste configuratie uit alle tests."""
    print("\n" + "="*80)
    print("  🏆 BEST CONFIGURATION FINDER")
    print("="*80)

    best_overall = None
    best_monthly_return = -999

    # Check all test results
    for test_name, test_results in results.items():
        if test_name == 'monte_carlo':  # Skip Monte Carlo (different format)
            continue

        if not test_results or not isinstance(test_results, list):
            continue

        for result in test_results:
            if not result or 'total_return' not in result:
                continue

            monthly_return = result['total_return'] / 12

            if monthly_return > best_monthly_return:
                best_monthly_return = monthly_return
                best_overall = result
                best_overall['test_type'] = test_name

    if best_overall:
        print(f"\n🥇 BESTE CONFIGURATIE GEVONDEN!")
        print(f"  Test Type: {best_overall.get('test_type', 'Unknown')}")
        print(f"  Config Name: {best_overall.get('config_name', 'Unknown')}")
        print(f"  Total Return: {best_overall['total_return']:.2f}%")
        print(f"  Monthly Return: {best_monthly_return:.2f}% 🚀")
        print(f"  Total Trades: {best_overall.get('total_trades', 0)}")
        print(f"  Avg Win Rate: {best_overall.get('avg_win_rate', 0):.1f}%")

        # Projection
        print(f"\n💰 12-MAANDS PROJECTIE:")
        monthly_growth = 1 + (best_monthly_return / 100)
        for months in [3, 6, 12, 24]:
            projected = 10000 * (monthly_growth ** months)
            print(f"  Na {months:2d} maanden: €{projected:,.0f} ({(projected/10000-1)*100:.0f}% gain)")

    return best_overall


if __name__ == "__main__":
    print("\n💎 STARTING COMPREHENSIVE BACKTEST SUITE 💎\n")

    suite = ComprehensiveBacktestSuite(initial_capital=10000)

    try:
        # Run all tests
        all_results = suite.run_all_tests()

        # Find best configuration
        best_config = find_best_configuration(all_results)

        print("\n" + "="*80)
        print("  ✅ ALL TESTS COMPLETED!")
        print("="*80)

        print("\n🎯 CONCLUSIE:")
        if best_config and best_config['total_return'] / 12 >= 10:
            print("  ✅ 10% PER MAAND IS HAALBAAR! 🚀🚀🚀")
            print("  We gaan RIJK worden! 💰💰💰")
        elif best_config and best_config['total_return'] / 12 >= 5:
            print("  ⚠️  5-10% per maand lijkt haalbaar")
            print("  Verdere optimalisatie nodig voor 10% target")
        else:
            print("  ❌ Met daily data halen we het target niet")
            print("  HIGH-FREQUENCY DATA (1-min/5-min) is NODIG!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
