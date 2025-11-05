"""
Main execution script for running backtests and optimizations.
"""
import argparse
from datetime import datetime
import sys

try:
    from data_fetcher import DataFetcher
except:
    from data_fetcher_simple import SimpleDataFetcher as DataFetcher
from backtest_engine import BacktestEngine
from strategies import get_strategy
from optimizer import StrategyOptimizer
from analytics import PerformanceAnalyzer


def run_single_backtest(symbol: str, strategy_name: str, start_date: str, end_date: str,
                       initial_capital: float = 10000, position_size: float = 1.0,
                       stop_loss: float = None, take_profit: float = None,
                       **strategy_params):
    """Run a single backtest with specified parameters."""
    print(f"\n{'='*70}")
    print(f"Running backtest: {symbol} | {strategy_name}")
    print(f"Period: {start_date} to {end_date}")
    print(f"{'='*70}\n")

    # Fetch data
    fetcher = DataFetcher()
    data = fetcher.fetch_yahoo_finance(symbol, start_date, end_date)

    # Validate data
    is_valid, msg = fetcher.validate_data(data)
    if not is_valid:
        print(f"❌ Data validation failed: {msg}")
        return None

    print(f"✓ Fetched {len(data)} days of data")

    # Create strategy
    strategy = get_strategy(strategy_name, **strategy_params)
    print(f"✓ Strategy: {strategy.name}")

    # Generate signals
    signals = strategy.generate_signals(data)
    signal_count = (signals != 0).sum()
    print(f"✓ Generated {signal_count} signals")

    if signal_count == 0:
        print("⚠️  No signals generated - check strategy parameters")
        return None

    # Run backtest
    engine = BacktestEngine(initial_capital=initial_capital)
    result = engine.run(data, signals, position_size=position_size,
                       stop_loss=stop_loss, take_profit=take_profit)

    # Print results
    PerformanceAnalyzer.print_summary(result, strategy_name)
    PerformanceAnalyzer.print_risk_metrics(result.equity_curve)

    if result.trades:
        PerformanceAnalyzer.print_top_trades(result.trades, n=5)

    return result


def run_optimization(symbol: str, strategy_name: str, start_date: str, end_date: str,
                    initial_capital: float = 10000):
    """Run parameter optimization for a strategy."""
    print(f"\n{'='*70}")
    print(f"Running optimization: {symbol} | {strategy_name}")
    print(f"{'='*70}\n")

    # Fetch data
    fetcher = DataFetcher()
    data = fetcher.fetch_yahoo_finance(symbol, start_date, end_date)

    is_valid, msg = fetcher.validate_data(data)
    if not is_valid:
        print(f"❌ Data validation failed: {msg}")
        return

    print(f"✓ Fetched {len(data)} days of data\n")

    # Define parameter grids for different strategies
    param_grids = {
        'ma_crossover': {
            'fast_period': [10, 20, 30, 50],
            'slow_period': [50, 100, 150, 200]
        },
        'rsi': {
            'period': [7, 14, 21, 28],
            'oversold': [20, 25, 30, 35],
            'overbought': [65, 70, 75, 80]
        },
        'bollinger_bands': {
            'period': [10, 20, 30],
            'num_std': [1.5, 2.0, 2.5, 3.0]
        },
        'macd': {
            'fast_period': [8, 12, 16],
            'slow_period': [21, 26, 31],
            'signal_period': [7, 9, 11]
        },
        'combined': {
            'ma_fast': [10, 20, 30],
            'ma_slow': [50, 100, 150],
            'rsi_period': [14, 21],
            'rsi_oversold': [25, 30],
            'rsi_overbought': [70, 75]
        }
    }

    if strategy_name not in param_grids:
        print(f"❌ No parameter grid defined for {strategy_name}")
        return

    # Run optimization
    optimizer = StrategyOptimizer(data, initial_capital)
    results = optimizer.grid_search(
        strategy_name,
        param_grids[strategy_name],
        position_size=1.0
    )

    # Display top results
    print("\n🏆 TOP 10 PARAMETER COMBINATIONS")
    print("-" * 120)

    if len(results) > 0:
        top_10 = results.head(10)
        for i, row in top_10.iterrows():
            print(f"\nRank {i+1}:")
            print(f"  Parameters: {row['params']}")
            print(f"  Return: {row['total_return']:.2f}% | Sharpe: {row['sharpe_ratio']:.2f} | "
                  f"Max DD: {row['max_drawdown']:.2f}% | Win Rate: {row['win_rate']:.1f}%")

        # Test best parameters with full backtest
        print("\n" + "="*70)
        print("TESTING BEST PARAMETERS")
        print("="*70)

        best_params = results.iloc[0]['params']
        print(f"\nBest parameters: {best_params}\n")

        strategy = get_strategy(strategy_name, **best_params)
        signals = strategy.generate_signals(data)
        engine = BacktestEngine(initial_capital=initial_capital)
        result = engine.run(data, signals, position_size=1.0)

        PerformanceAnalyzer.print_summary(result, f"{strategy_name} (Optimized)")
        PerformanceAnalyzer.print_risk_metrics(result.equity_curve)

        # Save results
        PerformanceAnalyzer.save_results_to_csv(
            result,
            f"backtest_{symbol}_{strategy_name}_optimized"
        )
    else:
        print("❌ No valid optimization results")


def compare_all_strategies(symbol: str, start_date: str, end_date: str,
                          initial_capital: float = 10000):
    """Compare all available strategies."""
    print(f"\n{'='*70}")
    print(f"Comparing all strategies: {symbol}")
    print(f"{'='*70}\n")

    # Fetch data
    fetcher = DataFetcher()
    data = fetcher.fetch_yahoo_finance(symbol, start_date, end_date)

    # Define strategies with default parameters
    strategies_config = {
        'MA Crossover (20/50)': ('ma_crossover', {'fast_period': 20, 'slow_period': 50}),
        'RSI (14, 30/70)': ('rsi', {'period': 14, 'oversold': 30, 'overbought': 70}),
        'Bollinger Bands (20, 2)': ('bollinger_bands', {'period': 20, 'num_std': 2.0}),
        'MACD (12/26/9)': ('macd', {'fast_period': 12, 'slow_period': 26, 'signal_period': 9}),
        'Combined Strategy': ('combined', {}),
        'Mean Reversion': ('mean_reversion', {'period': 20, 'entry_threshold': 2.0}),
    }

    results = {}

    for name, (strat_name, params) in strategies_config.items():
        try:
            print(f"\nTesting: {name}...")
            strategy = get_strategy(strat_name, **params)
            signals = strategy.generate_signals(data)

            if (signals != 0).sum() == 0:
                print(f"  ⚠️  Skipped - no signals generated")
                continue

            engine = BacktestEngine(initial_capital=initial_capital)
            result = engine.run(data, signals, position_size=1.0)
            results[name] = result
            print(f"  ✓ Return: {result.metrics['total_return']:.2f}% | "
                  f"Sharpe: {result.metrics['sharpe_ratio']:.2f}")

        except Exception as e:
            print(f"  ❌ Error: {e}")

    # Compare results
    if results:
        print("\n")
        PerformanceAnalyzer.compare_strategies(results)

        # Find best strategy
        best_name = max(results.keys(), key=lambda k: results[k].metrics['sharpe_ratio'])
        print(f"\n🏆 Best Strategy (by Sharpe): {best_name}")
        print(f"   Return: {results[best_name].metrics['total_return']:.2f}%")
        print(f"   Sharpe: {results[best_name].metrics['sharpe_ratio']:.2f}")
    else:
        print("\n❌ No strategies produced valid results")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Trading Strategy Backtester')

    parser.add_argument('--mode', type=str, default='backtest',
                       choices=['backtest', 'optimize', 'compare'],
                       help='Mode: backtest, optimize, or compare')

    parser.add_argument('--symbol', type=str, default='AAPL',
                       help='Ticker symbol (e.g., AAPL, BTC-USD, TSLA)')

    parser.add_argument('--strategy', type=str, default='combined',
                       choices=['ma_crossover', 'rsi', 'bollinger_bands', 'macd',
                               'combined', 'mean_reversion', 'trend_following'],
                       help='Strategy name')

    parser.add_argument('--start', type=str, default='2020-01-01',
                       help='Start date (YYYY-MM-DD)')

    parser.add_argument('--end', type=str, default='2024-12-31',
                       help='End date (YYYY-MM-DD)')

    parser.add_argument('--capital', type=float, default=10000,
                       help='Initial capital')

    parser.add_argument('--position-size', type=float, default=1.0,
                       help='Position size (0-1)')

    parser.add_argument('--stop-loss', type=float, default=None,
                       help='Stop loss percentage (e.g., 0.02 for 2%%)')

    parser.add_argument('--take-profit', type=float, default=None,
                       help='Take profit percentage (e.g., 0.05 for 5%%)')

    args = parser.parse_args()

    try:
        if args.mode == 'backtest':
            run_single_backtest(
                args.symbol, args.strategy, args.start, args.end,
                args.capital, args.position_size, args.stop_loss, args.take_profit
            )

        elif args.mode == 'optimize':
            run_optimization(
                args.symbol, args.strategy, args.start, args.end, args.capital
            )

        elif args.mode == 'compare':
            compare_all_strategies(
                args.symbol, args.start, args.end, args.capital
            )

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
