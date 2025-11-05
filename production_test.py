"""
Production-ready comprehensive testing with all improvements.
"""
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from data_fetcher_simple import generate_sample_data
from enhanced_backtest_engine import EnhancedBacktestEngine
from improved_strategies import (
    ImprovedMomentumBreakout,
    ImprovedTrendFollowing,
    ImprovedMeanReversion,
    PortfolioStrategy
)
from strategies import get_strategy
from analytics import PerformanceAnalyzer
from monte_carlo import MonteCarloSimulator, WalkForwardAnalyzer


def generate_realistic_market_data_v2(days=2000, start_price=100.0):
    """
    Generate highly realistic market data with regime changes.
    """
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')

    # Create market regimes
    regime_length = 200
    n_regimes = days // regime_length + 1

    regimes = []
    for i in range(n_regimes):
        regime_type = np.random.choice(['bull', 'bear', 'sideways', 'volatile'], p=[0.4, 0.2, 0.3, 0.1])
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

    # Add momentum and mean reversion
    returns = np.array(returns)
    for i in range(1, len(returns)):
        # Add momentum (autocorrelation)
        returns[i] += 0.05 * returns[i-1]

        # Add mean reversion
        if i > 20:
            ma = returns[i-20:i].mean()
            returns[i] -= 0.02 * (returns[i] - ma)

    # Generate prices
    closes = start_price * (1 + returns).cumprod()

    # Generate OHLC with realistic intraday movement
    opens = closes * (1 + np.random.normal(0, 0.003, days))
    intraday_range = abs(np.random.normal(0.012, 0.006, days))
    highs = np.maximum(opens, closes) * (1 + intraday_range)
    lows = np.minimum(opens, closes) * (1 - intraday_range)

    # Generate volume with correlation to price movement
    base_volume = 1000000
    vol_impact = abs(returns) * 30
    volumes = base_volume * (1 + vol_impact) * np.random.lognormal(0, 0.4, days)

    df = pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    }, index=dates)

    return df


def test_production_strategies():
    """Test production-ready strategies with all improvements."""
    print("\n" + "="*90)
    print("  PRODUCTION-READY STRATEGY TESTING WITH ADVANCED RISK MANAGEMENT")
    print("="*90 + "\n")

    # Generate realistic data
    data = generate_realistic_market_data_v2(days=2000)

    print(f"Testing Period: {len(data)} days (~{len(data)/252:.1f} years)")
    print(f"Price Range: ${data['close'].iloc[0]:.2f} → ${data['close'].iloc[-1]:.2f}")
    buy_hold = ((data['close'].iloc[-1] / data['close'].iloc[0]) - 1) * 100
    print(f"Buy & Hold Return: {buy_hold:.2f}%\n")

    results = {}

    # Test 1: Improved Momentum Breakout
    print("=" * 90)
    print("TEST 1: IMPROVED MOMENTUM BREAKOUT (With Risk Management)")
    print("=" * 90)

    strategy = ImprovedMomentumBreakout(
        lookback=20,
        breakout_threshold=1.5,
        trend_filter_period=100,
        min_volume_mult=1.3
    )
    signals = strategy.generate_signals(data)

    engine = EnhancedBacktestEngine(
        initial_capital=10000,
        commission=0.001,
        slippage=0.0005,
        use_risk_management=True
    )
    result = engine.run(data, signals, use_trailing_stop=True)
    results['Improved_Momentum'] = result

    print(f"\n✓ Generated {(signals != 0).sum()} signals, executed {result.metrics['total_trades']} trades")
    print(f"Return: {result.metrics['total_return']:.2f}% | Sharpe: {result.metrics['sharpe_ratio']:.2f}")
    print(f"Max DD: {result.metrics['max_drawdown']:.2f}% | Win Rate: {result.metrics['win_rate']:.1f}%\n")

    # Test 2: Improved Trend Following
    print("=" * 90)
    print("TEST 2: IMPROVED TREND FOLLOWING (With ADX)")
    print("=" * 90)

    strategy = ImprovedTrendFollowing(
        fast_period=10,
        slow_period=50,
        atr_period=14,
        trend_strength_min=1.5
    )
    signals = strategy.generate_signals(data)

    engine = EnhancedBacktestEngine(initial_capital=10000, use_risk_management=True)
    result = engine.run(data, signals, use_trailing_stop=True)
    results['Improved_Trend'] = result

    print(f"\n✓ Generated {(signals != 0).sum()} signals, executed {result.metrics['total_trades']} trades")
    print(f"Return: {result.metrics['total_return']:.2f}% | Sharpe: {result.metrics['sharpe_ratio']:.2f}")
    print(f"Max DD: {result.metrics['max_drawdown']:.2f}% | Win Rate: {result.metrics['win_rate']:.1f}%\n")

    # Test 3: Improved Mean Reversion
    print("=" * 90)
    print("TEST 3: IMPROVED MEAN REVERSION (With Regime Detection)")
    print("=" * 90)

    strategy = ImprovedMeanReversion(
        period=20,
        entry_z=2.0,
        exit_z=0.5,
        trend_threshold=0.05
    )
    signals = strategy.generate_signals(data)

    engine = EnhancedBacktestEngine(initial_capital=10000, use_risk_management=True)
    result = engine.run(data, signals, use_trailing_stop=True)
    results['Improved_MeanRev'] = result

    print(f"\n✓ Generated {(signals != 0).sum()} signals, executed {result.metrics['total_trades']} trades")
    print(f"Return: {result.metrics['total_return']:.2f}% | Sharpe: {result.metrics['sharpe_ratio']:.2f}")
    print(f"Max DD: {result.metrics['max_drawdown']:.2f}% | Win Rate: {result.metrics['win_rate']:.1f}%\n")

    # Test 4: Portfolio Strategy (Ensemble)
    print("=" * 90)
    print("TEST 4: PORTFOLIO STRATEGY (Ensemble of Best Strategies)")
    print("=" * 90)

    strat1 = ImprovedMomentumBreakout(lookback=20, breakout_threshold=1.5)
    strat2 = ImprovedTrendFollowing(fast_period=10, slow_period=50)
    strat3 = ImprovedMeanReversion(period=20, entry_z=2.0)

    portfolio = PortfolioStrategy(
        strategies=[strat1, strat2, strat3],
        weights=[0.5, 0.3, 0.2]  # Weight momentum higher
    )
    signals = portfolio.generate_signals(data)

    engine = EnhancedBacktestEngine(initial_capital=10000, use_risk_management=True)
    result = engine.run(data, signals, use_trailing_stop=True)
    results['Portfolio_Ensemble'] = result

    print(f"\n✓ Generated {(signals != 0).sum()} signals, executed {result.metrics['total_trades']} trades")
    print(f"Return: {result.metrics['total_return']:.2f}% | Sharpe: {result.metrics['sharpe_ratio']:.2f}")
    print(f"Max DD: {result.metrics['max_drawdown']:.2f}% | Win Rate: {result.metrics['win_rate']:.1f}%\n")

    # Compare all strategies
    print("\n" + "="*90)
    print("  STRATEGY COMPARISON")
    print("="*90 + "\n")

    PerformanceAnalyzer.compare_strategies(results)

    # Find best strategy
    best_name = max(results.keys(), key=lambda k: results[k].metrics.get('sharpe_ratio', -999))
    best_result = results[best_name]

    print(f"\n🏆 BEST STRATEGY (by Sharpe Ratio): {best_name}")
    print(f"   Return: {best_result.metrics['total_return']:.2f}%")
    print(f"   Sharpe: {best_result.metrics['sharpe_ratio']:.2f}")
    print(f"   Max DD: {best_result.metrics['max_drawdown']:.2f}%")
    print(f"   Calmar: {best_result.metrics['calmar_ratio']:.2f}")

    return results, best_result, best_name, data


def run_monte_carlo_analysis(best_result):
    """Run Monte Carlo simulation on best strategy."""
    print("\n" + "="*90)
    print("  MONTE CARLO ROBUSTNESS ANALYSIS")
    print("="*90)

    if not best_result.trades:
        print("\nNo trades to analyze")
        return None

    mc = MonteCarloSimulator(best_result.trades, initial_capital=10000)
    mc_results = mc.run_simulation(n_simulations=1000)
    mc.print_results(mc_results)

    return mc_results


def run_walk_forward_analysis(data):
    """Run walk-forward validation."""
    print("\n" + "="*90)
    print("  WALK-FORWARD VALIDATION")
    print("="*90)

    param_grid = {
        'lookback': [20],
        'breakout_threshold': [1.5],
        'trend_filter_period': [100],
        'min_volume_mult': [1.3]
    }

    wf = WalkForwardAnalyzer(
        data=data,
        strategy_class=ImprovedMomentumBreakout,
        param_grid=param_grid
    )

    wf_results = wf.run_walk_forward(train_size=252, test_size=63)

    return wf_results


def calculate_path_to_million(result, initial_capitals=[10000, 25000, 50000, 100000]):
    """Calculate path to $1 million with improved strategy."""
    print("\n" + "="*90)
    print("  REALISTIC PATH TO $1 MILLION")
    print("="*90 + "\n")

    metrics = result.metrics
    total_return = metrics['total_return']
    years_tested = len(result.equity_curve) / 252

    annual_return = total_return / years_tested
    monthly_return = annual_return / 12

    print("Strategy Performance:")
    print(f"  Total Return: {total_return:.2f}% over {years_tested:.1f} years")
    print(f"  Annualized Return: {annual_return:.2f}%")
    print(f"  Monthly Return: {monthly_return:.2f}%")
    print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"  Sortino Ratio: {metrics['sortino_ratio']:.2f}")
    print(f"  Max Drawdown: {metrics['max_drawdown']:.2f}%")
    print(f"  Calmar Ratio: {metrics['calmar_ratio']:.2f}")
    print(f"  Win Rate: {metrics['win_rate']:.1f}%")
    print(f"  Profit Factor: {metrics['profit_factor']:.2f}\n")

    # Conservative adjustment factor (account for real-world challenges)
    print("⚠️  Applying Conservative Adjustment:")
    print("  • Slippage & Market Impact: -20%")
    print("  • Strategy Decay Over Time: -15%")
    print("  • Unforeseen Market Changes: -10%")
    print("  • Total Haircut: ~40%\n")

    adjusted_annual = annual_return * 0.60  # 40% haircut
    adjusted_monthly = adjusted_annual / 12

    print(f"Conservative Adjusted Returns:")
    print(f"  Adjusted Annual: {adjusted_annual:.2f}%")
    print(f"  Adjusted Monthly: {adjusted_monthly:.2f}%\n")

    # Calculate time to $1M
    print("Time to Reach $1,000,000 (Conservative Estimate):\n")

    monthly_rate = adjusted_monthly / 100
    target = 1000000

    for start_cap in initial_capitals:
        capital = start_cap
        months = 0

        while capital < target and months < 600:
            months += 1
            capital *= (1 + monthly_rate)

        years = months / 12

        if years < 50:
            print(f"  ${start_cap:>7,} → $1M: {years:>5.1f} years ({months:>3} months)")
            print(f"    Year 5:  ${start_cap * ((1 + monthly_rate) ** 60):>10,.0f}")
            print(f"    Year 10: ${start_cap * ((1 + monthly_rate) ** 120):>10,.0f}")
            print(f"    Year 15: ${start_cap * ((1 + monthly_rate) ** 180):>10,.0f}\n")
        else:
            print(f"  ${start_cap:>7,}: {years:.1f} years (long-term)\n")

    return adjusted_annual, adjusted_monthly


def generate_final_report(best_name, best_result, mc_results, wf_results):
    """Generate final comprehensive report."""
    print("\n" + "="*90)
    print("  FINAL ASSESSMENT & RECOMMENDATIONS")
    print("="*90 + "\n")

    # Detailed analysis
    PerformanceAnalyzer.print_summary(best_result, f"{best_name} (Production Ready)")
    PerformanceAnalyzer.print_risk_metrics(best_result.equity_curve)

    if best_result.trades:
        PerformanceAnalyzer.print_top_trades(best_result.trades, n=10)

    # Overall assessment
    print("\n" + "="*90)
    print("  OVERALL ASSESSMENT")
    print("="*90 + "\n")

    metrics = best_result.metrics
    score = 0
    max_score = 5

    print("Evaluation Criteria:\n")

    # 1. Risk-Adjusted Returns
    if metrics['sharpe_ratio'] > 1.5:
        print("✅ Sharpe Ratio > 1.5: EXCELLENT risk-adjusted returns")
        score += 1
    elif metrics['sharpe_ratio'] > 1.0:
        print("✓ Sharpe Ratio > 1.0: GOOD risk-adjusted returns")
        score += 0.7
    else:
        print("⚠ Sharpe Ratio < 1.0: Needs improvement")
        score += 0.3

    # 2. Drawdown Control
    if metrics['max_drawdown'] > -30:
        print("✅ Max Drawdown < 30%: EXCELLENT risk control")
        score += 1
    elif metrics['max_drawdown'] > -50:
        print("✓ Max Drawdown < 50%: ACCEPTABLE risk")
        score += 0.7
    else:
        print("⚠ Max Drawdown > 50%: HIGH risk")
        score += 0.3

    # 3. Consistency
    if metrics['win_rate'] > 50 and metrics['profit_factor'] > 1.5:
        print("✅ Win Rate >50% + PF >1.5: EXCELLENT consistency")
        score += 1
    elif metrics['profit_factor'] > 1.2:
        print("✓ Profit Factor >1.2: GOOD consistency")
        score += 0.7
    else:
        print("⚠ Profit Factor <1.2: Inconsistent")
        score += 0.3

    # 4. Monte Carlo Robustness
    if mc_results and mc_results.get('prob_profit', 0) > 0.70:
        print("✅ Monte Carlo Profit Prob >70%: ROBUST strategy")
        score += 1
    elif mc_results and mc_results.get('prob_profit', 0) > 0.60:
        print("✓ Monte Carlo Profit Prob >60%: SOLID strategy")
        score += 0.7
    else:
        print("⚠ Monte Carlo: Needs validation")
        score += 0.3

    # 5. Walk-Forward Validation
    if wf_results and wf_results.get('consistency', 0) > 0.65:
        print("✅ Walk-Forward Consistency >65%: NOT overfit")
        score += 1
    elif wf_results and wf_results.get('consistency', 0) > 0.55:
        print("✓ Walk-Forward Consistency >55%: Reasonable")
        score += 0.7
    else:
        print("⚠ Walk-Forward: May be overfit")
        score += 0.3

    # Final Score
    print(f"\n📊 OVERALL SCORE: {score:.1f}/{max_score} ({score/max_score*100:.0f}%)\n")

    if score >= 4.0:
        print("🌟 RATING: EXCELLENT - Ready for paper trading")
        print("→ Recommended: Start paper trading with full position sizing")
    elif score >= 3.0:
        print("✓ RATING: GOOD - Promising but needs validation")
        print("→ Recommended: Paper trade with reduced sizing, continue monitoring")
    elif score >= 2.0:
        print("⚠ RATING: MODERATE - Requires further optimization")
        print("→ Recommended: More testing before paper trading")
    else:
        print("❌ RATING: NEEDS WORK - Not ready for live trading")
        print("→ Recommended: Significant improvements needed")

    # Action plan
    print("\n" + "="*90)
    print("  RECOMMENDED ACTION PLAN")
    print("="*90 + "\n")

    print("Phase 1: Additional Validation (2-4 weeks)")
    print("  [ ] Test with real historical data from Yahoo Finance")
    print("  [ ] Test on multiple assets (tech stocks, ETFs, indices)")
    print("  [ ] Validate across 2020-2024 actual market data")
    print("  [ ] Document all parameter choices\n")

    print("Phase 2: Paper Trading (2-3 months)")
    print("  [ ] Set up paper trading account (ThinkorSwim, TradingView, etc)")
    print("  [ ] Trade with full capital allocation")
    print("  [ ] Track slippage, execution quality, fill rates")
    print("  [ ] Monitor performance weekly")
    print("  [ ] Compare against backtest expectations\n")

    print("Phase 3: Live Testing (Start Small)")
    print("  [ ] Start with $500-$1,000 maximum")
    print("  [ ] Trade for minimum 3 months")
    print("  [ ] Keep detailed journal of all trades")
    print("  [ ] If profitable after 3 months, increase to $2,500")
    print("  [ ] Scale gradually: $5K → $10K → $25K → $50K\n")

    print("Phase 4: Scaling to $100K+ (Only if consistently profitable)")
    print("  [ ] Maintain 2% risk per trade maximum")
    print("  [ ] Diversify across multiple uncorrelated strategies")
    print("  [ ] Add more markets (crypto, forex, commodities)")
    print("  [ ] Consider automation for execution")
    print("  [ ] Regular strategy review and adjustment\n")

    print("=" * 90)
    print("⚠️  CRITICAL REMINDERS")
    print("=" * 90)
    print("• This is a SIMULATION - real markets will be different")
    print("• Start small and scale slowly based on proven results")
    print("• Never risk money you can't afford to lose")
    print("• Markets change - strategies that work today may not work tomorrow")
    print("• Emotional discipline is as important as the strategy itself")
    print("• Consider working with a financial advisor for large capital")
    print("=" * 90 + "\n")


def main():
    """Main execution."""
    print("\n" + "="*90)
    print("  PRODUCTION-READY TRADING SYSTEM - COMPREHENSIVE TESTING")
    print("="*90)

    # Run all tests
    results, best_result, best_name, data = test_production_strategies()

    # Monte Carlo analysis
    mc_results = run_monte_carlo_analysis(best_result)

    # Walk-forward validation
    wf_results = run_walk_forward_analysis(data)

    # Path to $1M with conservative estimates
    adjusted_annual, adjusted_monthly = calculate_path_to_million(best_result)

    # Generate final report
    generate_final_report(best_name, best_result, mc_results, wf_results)

    # Save results
    print("\n💾 Saving results...")
    PerformanceAnalyzer.save_results_to_csv(best_result, f"production_{best_name}")
    print(f"✓ Results saved to production_{best_name}_*.csv\n")


if __name__ == "__main__":
    main()
