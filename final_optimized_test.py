"""
Final optimized backtest with advanced strategies and better parameters.
"""
import pandas as pd
import numpy as np
from datetime import datetime

from data_fetcher_simple import generate_sample_data
from backtest_engine import BacktestEngine
from advanced_strategies import get_advanced_strategy
from strategies import get_strategy
from optimizer import StrategyOptimizer
from analytics import PerformanceAnalyzer


def generate_bull_market_data(days=2000):
    """Generate realistic bull market data."""
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    np.random.seed(42)

    start_price = 100.0

    # Bull market with corrections
    returns = []
    for i in range(days):
        # Base upward drift with occasional corrections
        if i % 200 < 180:  # Bull phase
            ret = np.random.normal(0.0012, 0.015)
        else:  # Correction phase
            ret = np.random.normal(-0.0008, 0.025)

        returns.append(ret)

    returns = np.array(returns)
    closes = start_price * (1 + returns).cumprod()

    # Generate OHLC
    opens = closes * (1 + np.random.normal(0, 0.003, days))
    daily_range = abs(np.random.normal(0.01, 0.005, days))
    highs = np.maximum(opens, closes) * (1 + daily_range)
    lows = np.minimum(opens, closes) * (1 - daily_range)
    volumes = np.random.lognormal(15, 0.5, days)

    df = pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    }, index=dates)

    return df


def test_advanced_strategies():
    """Test advanced strategies."""
    print("\n" + "="*80)
    print("  ADVANCED STRATEGIES BACKTEST")
    print("="*80 + "\n")

    # Generate good bull market data
    data = generate_bull_market_data(days=2000)

    print(f"Testing period: {len(data)} days")
    print(f"Price change: ${data['close'].iloc[0]:.2f} → ${data['close'].iloc[-1]:.2f}")
    buy_hold_return = ((data['close'].iloc[-1] / data['close'].iloc[0]) - 1) * 100
    print(f"Buy & Hold Return: {buy_hold_return:.2f}%\n")

    strategies_config = {
        # Basic strategies
        'MA_Crossover_Fast': ('ma_crossover', {'fast_period': 10, 'slow_period': 30}, False),
        'MA_Crossover_Slow': ('ma_crossover', {'fast_period': 20, 'slow_period': 50}, False),
        'Bollinger_Bands': ('bollinger_bands', {'period': 20, 'num_std': 2.0}, False),
        'RSI_Aggressive': ('rsi', {'period': 7, 'oversold': 35, 'overbought': 65}, False),

        # Advanced strategies
        'Momentum_Breakout': ('momentum_breakout', {'lookback': 20, 'breakout_threshold': 1.0}, True),
        'Volatility_Adjusted': ('volatility_adjusted', {'fast_ma': 10, 'slow_ma': 30}, True),
        'Multi_Timeframe': ('multi_timeframe', {'short_period': 5, 'medium_period': 20, 'long_period': 50}, True),
        'Adaptive': ('adaptive', {'regime_period': 50, 'trend_threshold': 0.02}, True),
        'Advanced_Composite': ('advanced_composite', {}, True),
    }

    results = {}

    for name, (strat_type, params, is_advanced) in strategies_config.items():
        try:
            if is_advanced:
                strategy = get_advanced_strategy(strat_type, **params)
            else:
                strategy = get_strategy(strat_type, **params)

            signals = strategy.generate_signals(data)

            if (signals != 0).sum() == 0:
                print(f"{name}: No signals generated")
                continue

            # Run with aggressive position sizing
            engine = BacktestEngine(initial_capital=10000, commission=0.001, slippage=0.0005)
            result = engine.run(data, signals, position_size=0.98, stop_loss=0.03, take_profit=0.10)

            results[name] = result

            print(f"{name}:")
            print(f"  Return: {result.metrics['total_return']:.2f}%")
            print(f"  Sharpe: {result.metrics['sharpe_ratio']:.2f}")
            print(f"  Max DD: {result.metrics['max_drawdown']:.2f}%")
            print(f"  Win Rate: {result.metrics['win_rate']:.1f}%")
            print(f"  Trades: {result.metrics['total_trades']}\n")

        except Exception as e:
            print(f"{name}: Error - {e}\n")

    # Compare and find best
    if results:
        print("\n" + "="*80)
        print("  STRATEGY COMPARISON")
        print("="*80 + "\n")

        PerformanceAnalyzer.compare_strategies(results)

        # Find best by total return
        best_return = max(results.items(), key=lambda x: x[1].metrics['total_return'])
        # Find best by Sharpe
        best_sharpe = max(results.items(), key=lambda x: x[1].metrics['sharpe_ratio'])

        print(f"\n🏆 BEST BY TOTAL RETURN: {best_return[0]}")
        print(f"   Return: {best_return[1].metrics['total_return']:.2f}%")
        print(f"   Sharpe: {best_return[1].metrics['sharpe_ratio']:.2f}")

        print(f"\n🏆 BEST BY SHARPE RATIO: {best_sharpe[0]}")
        print(f"   Return: {best_sharpe[1].metrics['total_return']:.2f}%")
        print(f"   Sharpe: {best_sharpe[1].metrics['sharpe_ratio']:.2f}")

        return results, best_return[1], best_return[0]

    return None, None, None


def project_to_million(result, initial_capital=10000):
    """Project path to $1 million."""
    print("\n" + "="*80)
    print("  PATH TO $1 MILLION")
    print("="*80 + "\n")

    total_return = result.metrics['total_return']
    years_tested = len(result.equity_curve) / 252

    annual_return = total_return / years_tested
    monthly_return = annual_return / 12

    print(f"Performance Metrics:")
    print(f"  Total Return: {total_return:.2f}% over {years_tested:.1f} years")
    print(f"  Annualized Return: {annual_return:.2f}%")
    print(f"  Monthly Return: {monthly_return:.2f}%")
    print(f"  Sharpe Ratio: {result.metrics['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown: {result.metrics['max_drawdown']:.2f}%")
    print(f"  Win Rate: {result.metrics['win_rate']:.1f}%\n")

    # Calculate compound growth
    monthly_rate = monthly_return / 100

    projections = {}
    starting_amounts = [10000, 25000, 50000, 100000]

    print("Time to reach $1,000,000:\n")

    for start in starting_amounts:
        capital = start
        months = 0
        target = 1000000

        while capital < target and months < 600:
            months += 1
            capital *= (1 + monthly_rate)

        years = months / 12

        if years < 50:
            projections[start] = years
            print(f"  ${start:,} → $1,000,000: {years:.1f} years ({months} months)")
            print(f"    At year 5: ${start * ((1 + monthly_rate) ** 60):,.0f}")
            print(f"    At year 10: ${start * ((1 + monthly_rate) ** 120):,.0f}\n")
        else:
            print(f"  ${start:,}: {years:.1f} years (long-term projection)\n")

    return projections


def main():
    """Main execution."""
    print("\n" + "="*80)
    print("  ULTIMATE TRADING BACKTEST - OPTIMIZED FOR PROFITABILITY")
    print("="*80)

    # Test advanced strategies
    results, best_result, best_name = test_advanced_strategies()

    if best_result:
        # Detailed analysis of best strategy
        print("\n" + "="*80)
        print(f"  DETAILED ANALYSIS: {best_name}")
        print("="*80)

        PerformanceAnalyzer.print_summary(best_result, best_name)
        PerformanceAnalyzer.print_risk_metrics(best_result.equity_curve)

        if best_result.trades:
            PerformanceAnalyzer.print_top_trades(best_result.trades, n=10)

        # Project to $1M
        projections = project_to_million(best_result, 10000)

        # Save results
        PerformanceAnalyzer.save_results_to_csv(best_result, f"best_strategy_{best_name}")
        print(f"\n✓ Results saved to best_strategy_{best_name}_*.csv\n")

        # Final recommendations
        print("="*80)
        print("  FINAL RECOMMENDATIONS")
        print("="*80 + "\n")

        if best_result.metrics['sharpe_ratio'] > 2.0 and best_result.metrics['total_return'] > 100:
            print("✅ EXCELLENT strategy with strong risk-adjusted returns!")
            print("✅ This strategy shows high potential for consistent profitability")
        elif best_result.metrics['sharpe_ratio'] > 1.0 and best_result.metrics['total_return'] > 50:
            print("✓ GOOD strategy with promising results")
            print("→ Recommended for paper trading and further validation")
        else:
            print("⚠ MODERATE strategy")
            print("→ Consider further optimization or testing alternative approaches")

        print(f"\nKey Success Factors:")
        print(f"  • Win Rate: {best_result.metrics['win_rate']:.1f}%")
        print(f"  • Profit Factor: {best_result.metrics['profit_factor']:.2f}")
        print(f"  • Risk/Reward Balance: Sharpe {best_result.metrics['sharpe_ratio']:.2f}")

        print("\n💡 Next Steps:")
        print("  1. Validate strategy with different market conditions")
        print("  2. Test with real historical data from multiple assets")
        print("  3. Implement paper trading with live data")
        print("  4. Start with small capital ($500-$1000) for live testing")
        print("  5. Monitor performance and adjust parameters as needed")

        print("\n⚠️  Risk Management:")
        print("  • Never risk more than 1-2% of capital per trade")
        print("  • Use stop losses religiously")
        print("  • Diversify across multiple assets if possible")
        print("  • Be prepared for drawdowns - they are inevitable")
        print("  • Past performance does NOT guarantee future results")


if __name__ == "__main__":
    main()
