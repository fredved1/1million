"""
Comprehensive strategy testing script with synthetic market data.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from data_fetcher_simple import generate_sample_data
from backtest_engine import BacktestEngine
from strategies import get_strategy
from optimizer import StrategyOptimizer
from analytics import PerformanceAnalyzer


def generate_realistic_market_data(days=1000, trend='mixed', volatility=0.02):
    """
    Generate realistic market data with different market conditions.

    Args:
        days: Number of days of data
        trend: 'bull', 'bear', 'mixed', 'volatile'
        volatility: Base volatility level

    Returns:
        DataFrame with OHLCV data
    """
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')

    # Base parameters
    start_price = 100.0
    np.random.seed(42)  # For reproducibility

    if trend == 'bull':
        # Upward trending market
        drift = 0.0008
        vol = volatility
    elif trend == 'bear':
        # Downward trending market
        drift = -0.0005
        vol = volatility * 1.2
    elif trend == 'volatile':
        # High volatility, no clear trend
        drift = 0.0002
        vol = volatility * 2.0
    else:  # mixed
        # Realistic mixed market with periods of different behavior
        drift = 0.0003
        vol = volatility

    # Generate returns with autocorrelation (more realistic)
    returns = []
    prev_return = 0

    for i in range(days):
        # Add market regime changes
        if trend == 'mixed':
            if i < days // 3:
                regime_drift = 0.001  # Bull phase
                regime_vol = vol * 0.8
            elif i < 2 * days // 3:
                regime_drift = -0.0003  # Bear phase
                regime_vol = vol * 1.5
            else:
                regime_drift = 0.0005  # Recovery phase
                regime_vol = vol
        else:
            regime_drift = drift
            regime_vol = vol

        # Add autocorrelation (momentum)
        momentum = 0.1 * prev_return
        shock = np.random.normal(regime_drift, regime_vol)
        ret = momentum + shock
        returns.append(ret)
        prev_return = ret

    returns = np.array(returns)

    # Generate prices
    closes = start_price * (1 + returns).cumprod()

    # Generate OHLC with realistic intraday movements
    opens = closes * (1 + np.random.normal(0, 0.003, days))
    daily_range = abs(np.random.normal(0.008, 0.004, days))
    highs = np.maximum(opens, closes) * (1 + daily_range)
    lows = np.minimum(opens, closes) * (1 - daily_range)

    # Generate volume with correlation to price movement
    base_volume = 1000000
    volatility_factor = abs(returns) * 50
    volumes = base_volume * (1 + volatility_factor) * np.random.lognormal(0, 0.3, days)

    df = pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    }, index=dates)

    return df


def run_comprehensive_test():
    """Run comprehensive strategy tests with multiple market conditions."""
    print("\n" + "="*80)
    print("  COMPREHENSIVE TRADING STRATEGY BACKTEST")
    print("="*80)

    # Test with different market conditions
    market_conditions = {
        'Bull Market (2020-2023 style)': ('bull', 0.015),
        'Bear Market (2022 style)': ('bear', 0.025),
        'High Volatility (2020 COVID)': ('volatile', 0.035),
        'Mixed Market (Realistic)': ('mixed', 0.020),
    }

    all_results = {}

    for condition_name, (trend, vol) in market_conditions.items():
        print(f"\n{'='*80}")
        print(f"Testing: {condition_name}")
        print(f"{'='*80}\n")

        # Generate data for this condition
        data = generate_realistic_market_data(days=1000, trend=trend, volatility=vol)

        print(f"Data: {len(data)} days")
        print(f"Start Price: ${data['close'].iloc[0]:.2f}")
        print(f"End Price: ${data['close'].iloc[-1]:.2f}")
        print(f"Buy & Hold Return: {((data['close'].iloc[-1] / data['close'].iloc[0]) - 1) * 100:.2f}%\n")

        # Test all strategies
        strategies_config = {
            'MA_Crossover': ('ma_crossover', {'fast_period': 20, 'slow_period': 50}),
            'RSI': ('rsi', {'period': 14, 'oversold': 30, 'overbought': 70}),
            'Bollinger_Bands': ('bollinger_bands', {'period': 20, 'num_std': 2.0}),
            'MACD': ('macd', {}),
            'Combined': ('combined', {}),
            'Mean_Reversion': ('mean_reversion', {'period': 20, 'entry_threshold': 2.0}),
        }

        condition_results = {}

        for strat_name, (strat_type, params) in strategies_config.items():
            try:
                strategy = get_strategy(strat_type, **params)
                signals = strategy.generate_signals(data)

                if (signals != 0).sum() == 0:
                    print(f"  {strat_name}: No signals generated")
                    continue

                engine = BacktestEngine(initial_capital=10000)
                result = engine.run(data, signals, position_size=0.95, stop_loss=0.05)

                condition_results[strat_name] = result

                print(f"  {strat_name}: Return={result.metrics['total_return']:.2f}%, "
                      f"Sharpe={result.metrics['sharpe_ratio']:.2f}, "
                      f"Trades={result.metrics['total_trades']}")

            except Exception as e:
                print(f"  {strat_name}: Error - {e}")

        all_results[condition_name] = condition_results

    return all_results


def optimize_best_strategy(data, strategy_name='combined'):
    """Optimize the best performing strategy."""
    print(f"\n{'='*80}")
    print(f"OPTIMIZING {strategy_name.upper()} STRATEGY")
    print(f"{'='*80}\n")

    param_grids = {
        'combined': {
            'ma_fast': [10, 20, 30],
            'ma_slow': [50, 100, 150],
            'rsi_period': [14, 21],
            'rsi_oversold': [25, 30],
            'rsi_overbought': [70, 75]
        },
        'ma_crossover': {
            'fast_period': [10, 20, 30, 40],
            'slow_period': [50, 100, 150, 200]
        },
        'rsi': {
            'period': [7, 14, 21],
            'oversold': [20, 25, 30],
            'overbought': [70, 75, 80]
        }
    }

    if strategy_name not in param_grids:
        print(f"No optimization grid for {strategy_name}")
        return None

    optimizer = StrategyOptimizer(data, initial_capital=10000)
    results = optimizer.grid_search(
        strategy_name,
        param_grids[strategy_name],
        position_size=0.95,
        stop_loss=0.05
    )

    if len(results) > 0:
        print("\n🏆 TOP 5 PARAMETER COMBINATIONS:\n")

        for i, row in results.head(5).iterrows():
            print(f"Rank {i+1}: {row['params']}")
            print(f"  Return: {row['total_return']:.2f}% | Sharpe: {row['sharpe_ratio']:.2f} | "
                  f"Win Rate: {row['win_rate']:.1f}% | Max DD: {row['max_drawdown']:.2f}%\n")

        # Test best parameters
        best_params = results.iloc[0]['params']
        print(f"\n{'='*80}")
        print("DETAILED RESULTS WITH BEST PARAMETERS")
        print(f"{'='*80}\n")
        print(f"Best parameters: {best_params}\n")

        strategy = get_strategy(strategy_name, **best_params)
        signals = strategy.generate_signals(data)
        engine = BacktestEngine(initial_capital=10000)
        result = engine.run(data, signals, position_size=0.95, stop_loss=0.05)

        PerformanceAnalyzer.print_summary(result, f"{strategy_name} (Optimized)")
        PerformanceAnalyzer.print_risk_metrics(result.equity_curve)

        if result.trades:
            PerformanceAnalyzer.print_top_trades(result.trades, n=10)

        return result, best_params

    return None


def project_to_1_million(initial_capital, avg_monthly_return_pct, target=1000000):
    """Project how long to reach target with compound growth."""
    if avg_monthly_return_pct <= 0:
        return float('inf'), []

    monthly_rate = avg_monthly_return_pct / 100
    capital = initial_capital
    months = 0
    progression = [(0, initial_capital)]

    while capital < target and months < 500:  # Max 500 months
        months += 1
        capital = capital * (1 + monthly_rate)
        if months % 6 == 0:  # Record every 6 months
            progression.append((months, capital))

    return months, progression


def main():
    """Main execution."""

    # Part 1: Comprehensive test across market conditions
    print("\n🚀 PART 1: Testing all strategies across market conditions...")
    all_results = run_comprehensive_test()

    # Find best overall strategy
    print("\n" + "="*80)
    print("  SUMMARY: BEST STRATEGIES BY MARKET CONDITION")
    print("="*80 + "\n")

    for condition, results in all_results.items():
        if results:
            best = max(results.items(), key=lambda x: x[1].metrics.get('sharpe_ratio', -999))
            print(f"{condition}:")
            print(f"  Best: {best[0]} - Return: {best[1].metrics['total_return']:.2f}%, "
                  f"Sharpe: {best[1].metrics['sharpe_ratio']:.2f}\n")

    # Part 2: Optimize best strategy on mixed market data
    print("\n🚀 PART 2: Optimizing best strategy...")
    data = generate_realistic_market_data(days=1500, trend='mixed', volatility=0.020)

    opt_result = optimize_best_strategy(data, 'combined')

    if opt_result:
        result, best_params = opt_result

        # Part 3: Project to $1M
        print("\n" + "="*80)
        print("  PATH TO $1 MILLION")
        print("="*80 + "\n")

        total_return_pct = result.metrics['total_return']
        days_tested = len(data)
        years_tested = days_tested / 252

        annual_return_pct = total_return_pct / years_tested
        monthly_return_pct = annual_return_pct / 12

        print(f"Strategy Performance:")
        print(f"  Total Return: {total_return_pct:.2f}% over {years_tested:.1f} years")
        print(f"  Annualized Return: {annual_return_pct:.2f}%")
        print(f"  Average Monthly Return: {monthly_return_pct:.2f}%")
        print(f"  Sharpe Ratio: {result.metrics['sharpe_ratio']:.2f}")
        print(f"  Max Drawdown: {result.metrics['max_drawdown']:.2f}%")
        print(f"  Win Rate: {result.metrics['win_rate']:.1f}%\n")

        # Project to $1M from different starting amounts
        starting_amounts = [10000, 25000, 50000, 100000]

        print("Projection to $1,000,000:\n")
        for start_capital in starting_amounts:
            months, progression = project_to_1_million(start_capital, monthly_return_pct)
            years = months / 12

            if years < 100:
                print(f"  Starting with ${start_capital:,}: {years:.1f} years ({months} months)")
            else:
                print(f"  Starting with ${start_capital:,}: Not achievable with this return rate")

        print("\n" + "="*80)
        print("  RECOMMENDATION")
        print("="*80 + "\n")

        print("Based on backtest results, the optimized strategy shows:")
        if result.metrics['sharpe_ratio'] > 1.5 and result.metrics['total_return'] > 20:
            print("✓ STRONG performance with good risk-adjusted returns")
            print("✓ Recommended for live testing with small capital")
        elif result.metrics['sharpe_ratio'] > 1.0:
            print("✓ GOOD performance, but continue optimization")
            print("→ Consider testing with different timeframes and assets")
        else:
            print("⚠ MODERATE performance")
            print("→ Further optimization needed or consider different strategies")

        print(f"\nBest Parameters for Live Trading:")
        for param, value in best_params.items():
            print(f"  {param}: {value}")

        print("\n⚠️  Important Notes:")
        print("  • This is a backtest - past performance doesn't guarantee future results")
        print("  • Start with small capital and test in real market conditions")
        print("  • Markets change - continuously monitor and adjust")
        print("  • Consider transaction costs, slippage, and taxes")
        print("  • Never risk more than you can afford to lose")


if __name__ == "__main__":
    main()
