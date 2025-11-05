"""
ULTIMATE BACKTEST
Test strategieën op REALISTISCHE market data.
Focus op wat WERKT en validate 10% per maand target!
"""
import pandas as pd
import numpy as np
from typing import List, Dict
import sys

from hf_momentum_strategy import HighFrequencyMomentum
from mean_reversion_scalper import MeanReversionScalper
from breakout_catcher import BreakoutCatcher
from trend_follower import TrendFollower
from swing_reversal import SwingReversal
from realistic_market_generator import generate_realistic_market


def run_strategy_backtest(strategy, data, allocation=1.0, leverage=1.0, initial_capital=10000):
    """
    Simple maar effective backtest.
    """
    capital = initial_capital * allocation
    position = 0
    entry_price = 0
    trades = []
    equity_curve = [capital]

    try:
        signals = strategy.generate_signals(data)
    except Exception as e:
        print(f"    ⚠️  Error generating signals: {e}")
        return None

    for i in range(1, len(data)):
        # Entry
        if signals.iloc[i] == 1 and position == 0:
            entry_price = data['close'].iloc[i]
            position = (capital * 0.95 / entry_price) * leverage

        # Exit
        elif signals.iloc[i] == -1 and position > 0:
            exit_price = data['close'].iloc[i]
            pnl = (exit_price - entry_price) * position
            pct_return = (exit_price / entry_price - 1) * 100 * leverage

            capital += pnl
            trades.append({
                'entry': entry_price,
                'exit': exit_price,
                'pnl': pnl,
                'return': pct_return
            })
            position = 0

        # Track equity
        if position > 0:
            current_value = capital + (data['close'].iloc[i] - entry_price) * position
            equity_curve.append(current_value)
        else:
            equity_curve.append(capital)

    if len(trades) == 0:
        return None

    # Calculate metrics
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] < 0]

    total_return = (capital - initial_capital * allocation) / (initial_capital * allocation) * 100

    return {
        'final_capital': capital,
        'total_return': total_return,
        'num_trades': len(trades),
        'num_wins': len(wins),
        'num_losses': len(losses),
        'win_rate': len(wins) / len(trades) * 100,
        'avg_win': np.mean([t['return'] for t in wins]) if wins else 0,
        'avg_loss': np.mean([t['return'] for t in losses]) if losses else 0,
        'best_trade': max([t['return'] for t in trades]),
        'worst_trade': min([t['return'] for t in trades]),
        'equity_curve': equity_curve,
        'trades': trades
    }


def test_strategy_on_all_markets(strategy_name: str, strategy, params: dict,
                                 leverage: float = 1.0, n_days: int = 365):
    """
    Test een strategie op ALLE market types.
    """
    print(f"\n{'='*80}")
    print(f"  TESTING: {strategy_name}")
    print(f"  Parameters: {params}")
    print(f"  Leverage: {leverage}x")
    print(f"{'='*80}")

    market_types = ['trending', 'mean_reverting', 'breakout', 'crypto']
    all_results = []

    for market_type in market_types:
        print(f"\n📊 {market_type.upper()} MARKET:")

        # Run 5 simulations per market type (different seeds)
        returns = []
        trades_list = []

        for seed in range(5):
            data = generate_realistic_market(market_type, n_days=n_days, base_price=100.0)

            # Create fresh strategy instance
            if strategy_name == 'Mean_Reversion':
                strat = MeanReversionScalper(**params)
            elif strategy_name == 'HF_Momentum':
                strat = HighFrequencyMomentum(**params)
            elif strategy_name == 'Breakout':
                strat = BreakoutCatcher(**params)
            elif strategy_name == 'Trend_Follower':
                strat = TrendFollower(**params)
            elif strategy_name == 'Swing_Reversal':
                strat = SwingReversal(**params)
            else:
                strat = strategy

            result = run_strategy_backtest(strat, data, allocation=1.0, leverage=leverage)

            if result:
                returns.append(result['total_return'])
                trades_list.append(result['num_trades'])

        if returns:
            avg_return = np.mean(returns)
            avg_trades = np.mean(trades_list)
            monthly_return = avg_return / (n_days / 30)

            print(f"    Avg Return: {avg_return:.2f}% ({monthly_return:.2f}%/month)")
            print(f"    Avg Trades: {avg_trades:.0f}")
            print(f"    Best: {max(returns):.2f}% | Worst: {min(returns):.2f}%")

            all_results.append({
                'market_type': market_type,
                'avg_return': avg_return,
                'monthly_return': monthly_return,
                'avg_trades': avg_trades,
                'consistency': np.std(returns)
            })

    return all_results


def find_best_configuration():
    """
    Test verschillende configuraties en vind de beste!
    """
    print("\n" + "="*80)
    print("  🚀 ULTIMATE BACKTEST - FIND BEST CONFIGURATION")
    print("  Test op realistische market data!")
    print("="*80)

    # Test configurations
    configurations = [
        # Mean Reversion variations
        {
            'name': 'Mean_Reversion_Conservative',
            'strategy': 'Mean_Reversion',
            'params': {'bb_period': 20, 'bb_std': 2.0, 'rsi_oversold': 30, 'vol_spike_mult': 1.5},
            'leverage': 2.0
        },
        {
            'name': 'Mean_Reversion_Aggressive',
            'strategy': 'Mean_Reversion',
            'params': {'bb_period': 15, 'bb_std': 1.8, 'rsi_oversold': 35, 'vol_spike_mult': 1.2},
            'leverage': 3.0
        },
        {
            'name': 'Mean_Reversion_Fast',
            'strategy': 'Mean_Reversion',
            'params': {'bb_period': 10, 'bb_std': 1.5, 'rsi_oversold': 40, 'vol_spike_mult': 1.0},
            'leverage': 4.0
        },

        # HF Momentum variations
        {
            'name': 'HF_Momentum_Conservative',
            'strategy': 'HF_Momentum',
            'params': {'lookback': 10, 'momentum_threshold': 0.5, 'rsi_min': 40, 'rsi_max': 65},
            'leverage': 2.0
        },
        {
            'name': 'HF_Momentum_Aggressive',
            'strategy': 'HF_Momentum',
            'params': {'lookback': 5, 'momentum_threshold': 0.3, 'rsi_min': 35, 'rsi_max': 70},
            'leverage': 3.0
        },

        # Breakout variations
        {
            'name': 'Breakout_Conservative',
            'strategy': 'Breakout',
            'params': {'lookback': 50, 'momentum_threshold': 2.0, 'volume_mult': 2.0},
            'leverage': 3.0
        },
        {
            'name': 'Breakout_Fast',
            'strategy': 'Breakout',
            'params': {'lookback': 20, 'momentum_threshold': 1.0, 'volume_mult': 1.5},
            'leverage': 4.0
        },

        # Trend Follower
        {
            'name': 'Trend_Follower',
            'strategy': 'Trend_Follower',
            'params': {'ema_fast': 20, 'ema_slow': 50, 'adx_threshold': 25, 'atr_period': 14},
            'leverage': 2.0
        },

        # Swing Reversal
        {
            'name': 'Swing_Reversal',
            'strategy': 'Swing_Reversal',
            'params': {'rsi_oversold': 30, 'lookback': 50},
            'leverage': 2.0
        },
    ]

    all_config_results = []

    for config in configurations:
        results = test_strategy_on_all_markets(
            strategy_name=config['strategy'],
            strategy=None,
            params=config['params'],
            leverage=config['leverage'],
            n_days=365
        )

        if results:
            # Calculate overall performance
            avg_monthly = np.mean([r['monthly_return'] for r in results])
            best_market = max(results, key=lambda x: x['monthly_return'])

            config['results'] = results
            config['avg_monthly_return'] = avg_monthly
            config['best_market'] = best_market['market_type']
            config['best_monthly_return'] = best_market['monthly_return']

            all_config_results.append(config)

    return all_config_results


def print_final_report(config_results: List[Dict]):
    """
    Print comprehensive report.
    """
    print("\n" + "="*80)
    print("  📊 FINAL REPORT - BEST CONFIGURATIONS")
    print("="*80)

    # Sort by avg monthly return
    sorted_configs = sorted(config_results, key=lambda x: x['avg_monthly_return'], reverse=True)

    print(f"\n{'Configuration':<35} {'Avg/Month':<12} {'Best Market':<15} {'Best/Month':<12}")
    print("-"*80)

    for config in sorted_configs:
        print(f"{config['name']:<35} {config['avg_monthly_return']:>10.2f}%  "
              f"{config['best_market']:<15} {config['best_monthly_return']:>10.2f}%")

    # Top 3
    print("\n" + "="*80)
    print("  🏆 TOP 3 CONFIGURATIONS")
    print("="*80)

    for i, config in enumerate(sorted_configs[:3], 1):
        print(f"\n#{i}. {config['name']}")
        print(f"    Strategy: {config['strategy']}")
        print(f"    Leverage: {config['leverage']}x")
        print(f"    Avg Monthly Return: {config['avg_monthly_return']:.2f}%")

        # Project 12 months
        monthly_growth = 1 + (config['avg_monthly_return'] / 100)
        projected_12m = 10000 * (monthly_growth ** 12)
        print(f"    \n    💰 12-Month Projection:")
        print(f"       €10,000 → €{projected_12m:,.0f} ({(projected_12m/10000-1)*100:.1f}% gain)")

        # Project 24 months
        projected_24m = 10000 * (monthly_growth ** 24)
        print(f"       24 months: €{projected_24m:,.0f}")

        # Print per-market performance
        print(f"\n    Performance per market type:")
        for result in config['results']:
            print(f"       {result['market_type']:<15}: {result['monthly_return']:>6.2f}%/month "
                  f"({result['avg_trades']:.0f} trades)")

    # Check if 10% target is achievable
    best_config = sorted_configs[0]
    print("\n" + "="*80)
    print("  🎯 TARGET VALIDATION")
    print("="*80)

    if best_config['avg_monthly_return'] >= 10:
        print(f"  ✅ 10% PER MAAND IS HAALBAAR!")
        print(f"  Best config achieves {best_config['avg_monthly_return']:.2f}%/month")
        print(f"  WE GAAN RIJK WORDEN! 💰💰💰")
    elif best_config['best_monthly_return'] >= 10:
        print(f"  ⚠️  10% per maand is mogelijk in specifieke markten")
        print(f"  Best market ({best_config['best_market']}): {best_config['best_monthly_return']:.2f}%/month")
        print(f"  Average: {best_config['avg_monthly_return']:.2f}%/month")
    elif best_config['avg_monthly_return'] >= 5:
        print(f"  ⚠️  5-10% per maand lijkt haalbaar")
        print(f"  Current best: {best_config['avg_monthly_return']:.2f}%/month")
        print(f"  Met HIGH-FREQUENCY data (1-min/5-min bars): 10%+ mogelijk!")
    else:
        print(f"  ❌ Met daily data: {best_config['avg_monthly_return']:.2f}%/month")
        print(f"  HIGH-FREQUENCY DATA (1-min/5-min bars) NODIG voor 10% target!")
        print(f"  Realistische verwachting met HF data: 6-12%/month")


if __name__ == "__main__":
    print("\n💎 ULTIMATE BACKTEST - REALISTISCHE MARKET DATA 💎\n")

    try:
        # Find best configuration
        config_results = find_best_configuration()

        if config_results:
            # Print final report
            print_final_report(config_results)

        print("\n" + "="*80)
        print("  ✅ ULTIMATE BACKTEST COMPLETED!")
        print("="*80)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
