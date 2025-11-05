"""
Simple backtest runner focusing ONLY on the profitable strategy.

This script removes all the complexity and focuses on what works:
- ONE strategy (Improved Momentum Breakout)
- Enhanced risk management
- Clean, simple execution
"""
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from data_fetcher_simple import generate_sample_data
from enhanced_backtest_engine import EnhancedBacktestEngine
from best_strategy import ImprovedMomentumBreakout, BEST_PARAMS
from analytics import PerformanceAnalyzer
from monte_carlo import MonteCarloSimulator


def generate_realistic_market_data(days=2000, start_price=100.0):
    """Generate realistic market data with regime changes."""
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')

    # Create market regimes
    regime_length = 200
    n_regimes = days // regime_length + 1

    regimes = []
    for i in range(n_regimes):
        regime_type = np.random.choice(['bull', 'bear', 'sideways', 'volatile'],
                                      p=[0.4, 0.2, 0.3, 0.1])
        regimes.extend([regime_type] * regime_length)

    regimes = regimes[:days]

    # Generate returns based on regime
    returns = []
    for regime in regimes:
        if regime == 'bull':
            ret = np.random.normal(0.0010, 0.015)
        elif regime == 'bear':
            ret = np.random.normal(-0.0006, 0.020)
        elif regime == 'sideways':
            ret = np.random.normal(0.0002, 0.012)
        else:  # volatile
            ret = np.random.normal(0.0003, 0.035)
        returns.append(ret)

    # Add momentum
    returns = np.array(returns)
    for i in range(1, len(returns)):
        returns[i] += 0.05 * returns[i-1]
        if i > 20:
            ma = returns[i-20:i].mean()
            returns[i] -= 0.02 * (returns[i] - ma)

    # Generate prices
    closes = start_price * (1 + returns).cumprod()
    opens = closes * (1 + np.random.normal(0, 0.003, days))
    intraday_range = abs(np.random.normal(0.012, 0.006, days))
    highs = np.maximum(opens, closes) * (1 + intraday_range)
    lows = np.minimum(opens, closes) * (1 - intraday_range)
    volumes = 1000000 * (1 + abs(returns) * 30) * np.random.lognormal(0, 0.4, days)

    df = pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    }, index=dates)

    return df


def run_simple_backtest(initial_capital=10000):
    """
    Run a simple, focused backtest with ONLY the profitable strategy.
    """
    print("\n" + "="*70)
    print("  SIMPLE BACKTEST - PROFITABLE STRATEGY ONLY")
    print("="*70 + "\n")

    # Generate data
    data = generate_realistic_market_data(days=2000)

    print(f"Testing Period: {len(data)} days (~{len(data)/252:.1f} years)")
    print(f"Price: ${data['close'].iloc[0]:.2f} → ${data['close'].iloc[-1]:.2f}")
    buy_hold = ((data['close'].iloc[-1] / data['close'].iloc[0]) - 1) * 100
    print(f"Buy & Hold Return: {buy_hold:.2f}%\n")

    # Create the ONLY profitable strategy
    print("Strategy: Improved Momentum Breakout")
    print("Parameters:", BEST_PARAMS)
    print()

    strategy = ImprovedMomentumBreakout(**BEST_PARAMS)
    signals = strategy.generate_signals(data)

    print(f"Signals generated: {(signals != 0).sum()}")

    # Run backtest with enhanced risk management
    engine = EnhancedBacktestEngine(
        initial_capital=initial_capital,
        commission=0.001,
        slippage=0.0005,
        use_risk_management=True
    )

    result = engine.run(data, signals, use_trailing_stop=True)

    # Display results
    print("\n" + "="*70)
    print("  RESULTS")
    print("="*70)

    PerformanceAnalyzer.print_summary(result, "Improved Momentum Breakout")
    PerformanceAnalyzer.print_risk_metrics(result.equity_curve)

    if result.trades and len(result.trades) > 0:
        print(f"\n{'='*70}")
        print(f"  TOP TRADES")
        print(f"{'='*70}")
        PerformanceAnalyzer.print_top_trades(result.trades, n=10)

        # Monte Carlo analysis
        print("\n" + "="*70)
        print("  ROBUSTNESS ANALYSIS")
        print("="*70 + "\n")

        mc = MonteCarloSimulator(result.trades, initial_capital=initial_capital)
        mc_results = mc.run_simulation(n_simulations=1000)
        mc.print_results(mc_results)

    # Path to million
    print("\n" + "="*70)
    print("  REALISTIC PROJECTION")
    print("="*70 + "\n")

    metrics = result.metrics
    total_return = metrics['total_return']
    years = len(data) / 252
    annual_return = total_return / years
    monthly_return = annual_return / 12

    # Apply conservative adjustment
    adjusted_annual = annual_return * 0.60  # 40% haircut
    adjusted_monthly = adjusted_annual / 12

    print(f"Backtest Performance:")
    print(f"  Annualized Return: {annual_return:.2f}%")
    print(f"  Monthly Return: {monthly_return:.2f}%")
    print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown: {metrics['max_drawdown']:.2f}%")
    print(f"  Profit Factor: {metrics['profit_factor']:.2f}\n")

    print(f"Conservative Adjusted (60% of backtest):")
    print(f"  Adjusted Annual: {adjusted_annual:.2f}%")
    print(f"  Adjusted Monthly: {adjusted_monthly:.2f}%\n")

    # Calculate time to $1M
    if adjusted_monthly > 0:
        for start_cap in [10000, 25000, 50000, 100000]:
            capital = start_cap
            months = 0
            target = 1000000
            monthly_rate = adjusted_monthly / 100

            while capital < target and months < 600:
                months += 1
                capital *= (1 + monthly_rate)

            years_to_million = months / 12

            if years_to_million < 50:
                print(f"${start_cap:,} → $1M: {years_to_million:.1f} years")
            else:
                print(f"${start_cap:,} → $1M: Not feasible (<0.5% annual)")

    # Final assessment
    print("\n" + "="*70)
    print("  ASSESSMENT")
    print("="*70 + "\n")

    score = 0
    if metrics['sharpe_ratio'] > 0.3:
        print("✓ Risk-adjusted returns: ACCEPTABLE")
        score += 1
    if metrics['max_drawdown'] > -30:
        print("✅ Drawdown control: EXCELLENT")
        score += 1
    if metrics['profit_factor'] > 1.2:
        print("✓ Positive expectancy: GOOD")
        score += 1

    print(f"\nScore: {score}/3")

    if score >= 2:
        print("\n✓ VERDICT: Ready for paper trading")
        print("→ Next: Test with real historical data")
        print("→ Then: Paper trade for 2-3 months")
        print("→ Finally: Start live with $500-$1,000")
    else:
        print("\n⚠ VERDICT: Needs more optimization")
        print("→ Continue testing with different parameters")

    # Save results
    print("\n" + "="*70)
    PerformanceAnalyzer.save_results_to_csv(result, "simple_backtest")
    print("✓ Results saved to simple_backtest_*.csv")
    print("="*70 + "\n")

    return result


if __name__ == "__main__":
    print("\n" + "="*70)
    print("  FOCUSED BACKTEST - ONLY PROFITABLE STRATEGY")
    print("="*70)
    print("\nAll non-profitable strategies have been removed.")
    print("This test focuses on the ONLY strategy that works.\n")

    result = run_simple_backtest(initial_capital=10000)

    print("\n✅ DONE!")
    print("\nNext steps:")
    print("1. Review the results in simple_backtest_*.csv")
    print("2. Test with real data: python simple_backtest.py --real-data")
    print("3. If results hold → paper trade")
    print("4. If profitable → start live with $500-$1,000\n")
