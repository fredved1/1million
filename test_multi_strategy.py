"""
MULTI-STRATEGY PORTFOLIO BACKTEST
Tests all 5 strategies combined to validate 10% per month target.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys

# Import all strategies
from hf_momentum_strategy import HighFrequencyMomentum
from mean_reversion_scalper import MeanReversionScalper
from breakout_catcher import BreakoutCatcher
from trend_follower import TrendFollower
from swing_reversal import SwingReversal
from multi_strategy_portfolio import MultiStrategyPortfolio
from enhanced_backtest_engine import EnhancedBacktestEngine
from data_fetcher_simple import generate_sample_data


def run_strategy_backtest(strategy, data, allocation, leverage, initial_capital=10000):
    """
    Run backtest for a single strategy.

    Args:
        strategy: TradingStrategy instance
        data: DataFrame with OHLCV data
        allocation: Portfolio allocation (0-1)
        leverage: Leverage multiplier
        initial_capital: Starting capital

    Returns:
        dict with performance metrics
    """
    strategy_capital = initial_capital * allocation

    # Generate signals
    signals = strategy.generate_signals(data)

    # Simple backtest logic
    capital = strategy_capital
    position = 0
    entry_price = 0
    trades = []
    equity_curve = [capital]

    for i in range(1, len(data)):
        if signals.iloc[i] == 1 and position == 0:  # Buy signal
            # Enter position with leverage
            entry_price = data['close'].iloc[i]
            position = (capital * 0.95 / entry_price) * leverage  # Use 95% of capital

        elif signals.iloc[i] == -1 and position > 0:  # Sell signal
            # Exit position
            exit_price = data['close'].iloc[i]
            pnl = (exit_price - entry_price) * position
            capital += pnl

            trades.append({
                'entry': entry_price,
                'exit': exit_price,
                'pnl': pnl,
                'return': (exit_price / entry_price - 1) * 100 * leverage
            })

            position = 0
            entry_price = 0

        # Track equity
        if position > 0:
            current_price = data['close'].iloc[i]
            unrealized_pnl = (current_price - entry_price) * position
            equity_curve.append(capital + unrealized_pnl)
        else:
            equity_curve.append(capital)

    # Calculate metrics
    if len(trades) == 0:
        return {
            'name': strategy.name,
            'allocation': allocation,
            'leverage': leverage,
            'final_capital': strategy_capital,
            'total_return': 0,
            'num_trades': 0,
            'win_rate': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'profit_factor': 0,
            'max_drawdown': 0,
            'sharpe_ratio': 0
        }

    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] < 0]

    win_rate = len(wins) / len(trades) * 100 if trades else 0
    avg_win = np.mean([t['return'] for t in wins]) if wins else 0
    avg_loss = np.mean([t['return'] for t in losses]) if losses else 0

    total_win = sum([t['pnl'] for t in wins]) if wins else 0
    total_loss = abs(sum([t['pnl'] for t in losses])) if losses else 0
    profit_factor = total_win / total_loss if total_loss > 0 else 0

    # Calculate max drawdown
    peak = equity_curve[0]
    max_dd = 0
    for equity in equity_curve:
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak * 100
        if dd > max_dd:
            max_dd = dd

    # Calculate Sharpe (simplified)
    returns = pd.Series(equity_curve).pct_change().dropna()
    sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0

    total_return = (capital - strategy_capital) / strategy_capital * 100

    return {
        'name': strategy.name,
        'allocation': allocation,
        'leverage': leverage,
        'initial_capital': strategy_capital,
        'final_capital': capital,
        'total_return': total_return,
        'num_trades': len(trades),
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'max_drawdown': max_dd,
        'sharpe_ratio': sharpe,
        'equity_curve': equity_curve
    }


def test_multi_strategy_portfolio():
    """
    Test all 5 strategies together.
    """
    print("="*80)
    print("  MULTI-STRATEGY PORTFOLIO BACKTEST")
    print("  Target: 10% Per Maand")
    print("="*80)
    print()

    # Initial parameters
    initial_capital = 10000

    # Load data (using sample data for now)
    print("📊 Loading market data...")
    data = generate_sample_data(n_days=365, volatility=0.03)
    print(f"✓ Loaded {len(data)} bars of data")
    print(f"  Date range: {data.index[0]} to {data.index[-1]}")
    print(f"  Days: {(data.index[-1] - data.index[0]).days}")
    print()

    # Initialize portfolio
    portfolio = MultiStrategyPortfolio(initial_capital=initial_capital)

    # Initialize strategies
    strategies = [
        (HighFrequencyMomentum(lookback=10, momentum_threshold=0.5, rsi_min=40, rsi_max=65),
         portfolio.allocations['hf_momentum'],
         portfolio.leverage['hf_momentum'],
         "3%/month target, 10-20 trades/day"),

        (MeanReversionScalper(bb_period=20, bb_std=2.0, rsi_oversold=30, vol_spike_mult=1.5),
         portfolio.allocations['mean_reversion'],
         portfolio.leverage['mean_reversion'],
         "2%/month target, 30-50 trades/day"),

        (BreakoutCatcher(lookback=50, momentum_threshold=2.0, volume_mult=2.0),
         portfolio.allocations['breakout'],
         portfolio.leverage['breakout'],
         "2.5%/month target, 5-10 trades/day"),

        (TrendFollower(ema_fast=20, ema_slow=50, adx_threshold=25, atr_period=14),
         portfolio.allocations['trend_following'],
         portfolio.leverage['trend_following'],
         "1.5%/month target, 2-5 trades/day"),

        (SwingReversal(rsi_oversold=30, lookback=50),
         portfolio.allocations['swing_reversal'],
         portfolio.leverage['swing_reversal'],
         "1%/month target, 1-3 trades/day")
    ]

    # Run backtest for each strategy
    print("🚀 Running backtests for all strategies...\n")
    results = []

    for strategy, allocation, leverage, description in strategies:
        print(f"Testing {strategy.name}...")
        print(f"  Allocation: {allocation*100:.0f}% | Leverage: {leverage}x | {description}")

        result = run_strategy_backtest(
            strategy=strategy,
            data=data,
            allocation=allocation,
            leverage=leverage,
            initial_capital=initial_capital
        )
        results.append(result)

        print(f"  ✓ Return: {result['total_return']:.2f}%")
        print(f"  ✓ Trades: {result['num_trades']}")
        print(f"  ✓ Win Rate: {result['win_rate']:.1f}%")
        print(f"  ✓ Max DD: {result['max_drawdown']:.2f}%")
        print()

    # Calculate combined portfolio performance
    print("="*80)
    print("  COMBINED PORTFOLIO RESULTS")
    print("="*80)
    print()

    # Combine equity curves
    total_initial = initial_capital
    total_final = sum([r['final_capital'] for r in results])
    total_return = (total_final - total_initial) / total_initial * 100

    # Calculate time period
    days = (data.index[-1] - data.index[0]).days
    months = days / 30.0
    monthly_return = total_return / months if months > 0 else 0

    print(f"Initial Capital:    ${total_initial:,.2f}")
    print(f"Final Capital:      ${total_final:,.2f}")
    print(f"Total Return:       {total_return:.2f}%")
    print(f"Period:             {days} days ({months:.1f} months)")
    print(f"Monthly Return:     {monthly_return:.2f}%")
    print()

    print("📊 Individual Strategy Performance:")
    print("-" * 80)
    print(f"{'Strategy':<25} {'Alloc':<8} {'Lev':<6} {'Return':<10} {'Trades':<8} {'Win%':<8} {'MaxDD':<8}")
    print("-" * 80)

    for r in results:
        print(f"{r['name']:<25} {r['allocation']*100:>5.0f}%   {r['leverage']:>4}x  "
              f"{r['total_return']:>8.2f}%  {r['num_trades']:>6}   "
              f"{r['win_rate']:>6.1f}%  {r['max_drawdown']:>6.2f}%")

    print("-" * 80)
    print(f"{'PORTFOLIO TOTAL':<25} {'100%':<8} {'~3x':<6} {total_return:>8.2f}%")
    print()

    # Check if target achieved
    target_monthly = 10.0
    print("🎯 TARGET VALIDATION:")
    print(f"   Target:   {target_monthly:.1f}% per month")
    print(f"   Actual:   {monthly_return:.2f}% per month")

    if monthly_return >= target_monthly:
        print(f"   ✅ TARGET ACHIEVED! (+{monthly_return - target_monthly:.2f}% above target)")
    elif monthly_return >= target_monthly * 0.7:
        print(f"   ⚠️  Close to target ({monthly_return/target_monthly*100:.0f}% of goal)")
    else:
        print(f"   ❌ Below target ({monthly_return/target_monthly*100:.0f}% of goal)")
    print()

    # Risk metrics
    total_trades = sum([r['num_trades'] for r in results])
    avg_win_rate = np.mean([r['win_rate'] for r in results if r['num_trades'] > 0])
    max_dd = max([r['max_drawdown'] for r in results])

    print("📈 Risk Metrics:")
    print(f"   Total Trades:        {total_trades}")
    print(f"   Avg Win Rate:        {avg_win_rate:.1f}%")
    print(f"   Max Drawdown:        {max_dd:.2f}%")
    print()

    # Projection
    print("💰 12-Month Projection (if performance continues):")
    monthly_growth = 1 + (monthly_return / 100)
    projected_12m = initial_capital * (monthly_growth ** 12)
    print(f"   Starting:    ${initial_capital:,.2f}")
    print(f"   After 12m:   ${projected_12m:,.2f}")
    print(f"   Gain:        ${projected_12m - initial_capital:,.2f} ({(projected_12m/initial_capital - 1)*100:.1f}%)")
    print()

    print("="*80)
    print("✅ BACKTEST COMPLETE")
    print("="*80)

    return {
        'total_return': total_return,
        'monthly_return': monthly_return,
        'results': results,
        'target_achieved': monthly_return >= target_monthly
    }


if __name__ == "__main__":
    try:
        result = test_multi_strategy_portfolio()

        print("\n🎬 Next Steps:")
        if result['target_achieved']:
            print("1. ✅ Run on more historical data (2+ years)")
            print("2. ✅ Test on different market conditions")
            print("3. ✅ Paper trade for 2 weeks")
            print("4. ✅ Deploy to testnet with small capital")
        else:
            print("1. ⚠️  Optimize strategy parameters")
            print("2. ⚠️  Test with more aggressive position sizing")
            print("3. ⚠️  Consider adding more strategies")
            print("4. ⚠️  Increase leverage cautiously")

    except Exception as e:
        print(f"\n❌ Error during backtest: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
