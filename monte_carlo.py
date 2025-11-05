"""
Monte Carlo simulation for strategy robustness testing.
"""
import pandas as pd
import numpy as np
from typing import List, Dict
from backtest_engine import BacktestResult
from enhanced_backtest_engine import EnhancedBacktestEngine


class MonteCarloSimulator:
    """
    Monte Carlo simulation to test strategy robustness.
    """

    def __init__(self, trades: List, initial_capital: float = 10000):
        """
        Initialize Monte Carlo simulator.

        Args:
            trades: List of Trade objects from a backtest
            initial_capital: Starting capital
        """
        self.trades = trades
        self.initial_capital = initial_capital
        self.trade_returns = [t.pnl / initial_capital for t in trades if t.pnl is not None]

    def run_simulation(self, n_simulations: int = 1000, n_trades: int = None) -> Dict:
        """
        Run Monte Carlo simulation by randomly reordering trades.

        Args:
            n_simulations: Number of simulations to run
            n_trades: Number of trades per simulation (None = same as original)

        Returns:
            Dictionary with simulation results
        """
        if not self.trade_returns:
            return {'error': 'No trades to simulate'}

        if n_trades is None:
            n_trades = len(self.trade_returns)

        print(f"\nRunning {n_simulations} Monte Carlo simulations...")
        print(f"Each simulation: {n_trades} trades")

        final_capitals = []
        max_drawdowns = []
        sharpe_ratios = []

        for sim in range(n_simulations):
            # Randomly sample trades with replacement
            sampled_returns = np.random.choice(self.trade_returns, size=n_trades, replace=True)

            # Calculate equity curve
            equity = self.initial_capital
            equity_curve = [equity]

            for ret in sampled_returns:
                equity = equity * (1 + ret)
                equity_curve.append(equity)

            equity_series = pd.Series(equity_curve)

            # Calculate metrics
            final_capital = equity_series.iloc[-1]
            final_capitals.append(final_capital)

            # Max drawdown
            cummax = equity_series.expanding().max()
            drawdown = (equity_series - cummax) / cummax
            max_dd = drawdown.min() * 100
            max_drawdowns.append(max_dd)

            # Sharpe ratio
            returns = equity_series.pct_change().dropna()
            if len(returns) > 0 and returns.std() > 0:
                sharpe = (returns.mean() / returns.std()) * np.sqrt(252)
                sharpe_ratios.append(sharpe)

            if (sim + 1) % 200 == 0:
                print(f"  Progress: {sim + 1}/{n_simulations}")

        # Analyze results
        final_capitals = np.array(final_capitals)
        max_drawdowns = np.array(max_drawdowns)
        sharpe_ratios = np.array(sharpe_ratios)

        total_returns = ((final_capitals - self.initial_capital) / self.initial_capital) * 100

        # Calculate statistics
        results = {
            'n_simulations': n_simulations,
            'n_trades': n_trades,

            # Return statistics
            'mean_return': np.mean(total_returns),
            'median_return': np.median(total_returns),
            'std_return': np.std(total_returns),
            'min_return': np.min(total_returns),
            'max_return': np.max(total_returns),
            'percentile_5': np.percentile(total_returns, 5),
            'percentile_25': np.percentile(total_returns, 25),
            'percentile_75': np.percentile(total_returns, 75),
            'percentile_95': np.percentile(total_returns, 95),

            # Probability of profit
            'prob_profit': np.sum(total_returns > 0) / n_simulations,
            'prob_double': np.sum(total_returns > 100) / n_simulations,
            'prob_loss_50': np.sum(total_returns < -50) / n_simulations,

            # Drawdown statistics
            'mean_max_drawdown': np.mean(max_drawdowns),
            'worst_max_drawdown': np.min(max_drawdowns),
            'best_max_drawdown': np.max(max_drawdowns),

            # Sharpe statistics
            'mean_sharpe': np.mean(sharpe_ratios),
            'median_sharpe': np.median(sharpe_ratios),

            # Raw data
            'all_returns': total_returns,
            'all_drawdowns': max_drawdowns,
            'all_sharpes': sharpe_ratios,
        }

        return results

    def print_results(self, results: Dict):
        """Print Monte Carlo simulation results."""
        print("\n" + "="*80)
        print("  MONTE CARLO SIMULATION RESULTS")
        print("="*80 + "\n")

        print(f"Simulations Run: {results['n_simulations']:,}")
        print(f"Trades per Simulation: {results['n_trades']}\n")

        print("📊 RETURN DISTRIBUTION")
        print("-" * 80)
        print(f"Mean Return:      {results['mean_return']:>8.2f}%")
        print(f"Median Return:    {results['median_return']:>8.2f}%")
        print(f"Std Deviation:    {results['std_return']:>8.2f}%")
        print(f"Min Return:       {results['min_return']:>8.2f}%")
        print(f"Max Return:       {results['max_return']:>8.2f}%\n")

        print("📈 PERCENTILES")
        print("-" * 80)
        print(f"5th Percentile:   {results['percentile_5']:>8.2f}%  (95% chance to do better)")
        print(f"25th Percentile:  {results['percentile_25']:>8.2f}%")
        print(f"75th Percentile:  {results['percentile_75']:>8.2f}%")
        print(f"95th Percentile:  {results['percentile_95']:>8.2f}%  (5% chance to do better)\n")

        print("🎯 PROBABILITIES")
        print("-" * 80)
        print(f"Probability of Profit:     {results['prob_profit']*100:>6.1f}%")
        print(f"Probability of 2x Return:  {results['prob_double']*100:>6.1f}%")
        print(f"Probability of -50% Loss:  {results['prob_loss_50']*100:>6.1f}%\n")

        print("📉 DRAWDOWN ANALYSIS")
        print("-" * 80)
        print(f"Mean Max Drawdown:    {results['mean_max_drawdown']:>8.2f}%")
        print(f"Worst Max Drawdown:   {results['worst_max_drawdown']:>8.2f}%")
        print(f"Best Max Drawdown:    {results['best_max_drawdown']:>8.2f}%\n")

        print("📊 RISK-ADJUSTED RETURNS")
        print("-" * 80)
        print(f"Mean Sharpe Ratio:    {results['mean_sharpe']:>8.2f}")
        print(f"Median Sharpe Ratio:  {results['median_sharpe']:>8.2f}\n")

        # Interpretation
        print("="*80)
        print("  INTERPRETATION")
        print("="*80 + "\n")

        if results['prob_profit'] > 0.70 and results['mean_return'] > 30:
            print("✅ EXCELLENT: High probability of profit with strong returns")
        elif results['prob_profit'] > 0.60 and results['mean_return'] > 20:
            print("✓ GOOD: Solid probability of profit with decent returns")
        elif results['prob_profit'] > 0.50:
            print("⚠ MODERATE: Better than coin flip but needs improvement")
        else:
            print("❌ POOR: Low probability of profit - strategy needs work")

        if results['worst_max_drawdown'] > -30:
            print("✅ EXCELLENT: Well-controlled risk even in worst case")
        elif results['worst_max_drawdown'] > -50:
            print("✓ ACCEPTABLE: Risk is manageable")
        else:
            print("❌ HIGH RISK: Large drawdowns possible")

        print()


class WalkForwardAnalyzer:
    """Walk-forward analysis for out-of-sample testing."""

    def __init__(self, data: pd.DataFrame, strategy_class, param_grid: Dict):
        """
        Initialize walk-forward analyzer.

        Args:
            data: Historical data
            strategy_class: Strategy class to test
            param_grid: Parameter grid for optimization
        """
        self.data = data
        self.strategy_class = strategy_class
        self.param_grid = param_grid

    def run_walk_forward(self, train_size: int = 252, test_size: int = 63) -> Dict:
        """
        Run walk-forward analysis.

        Args:
            train_size: Training period size (days)
            test_size: Testing period size (days)

        Returns:
            Dictionary with walk-forward results
        """
        print("\n" + "="*80)
        print("  WALK-FORWARD ANALYSIS")
        print("="*80 + "\n")

        print(f"Training Period: {train_size} days (~{train_size/252:.1f} years)")
        print(f"Testing Period: {test_size} days (~{test_size/252:.1f} years)\n")

        results = []
        n_periods = len(self.data)
        current_pos = 0
        window_num = 1

        while current_pos + train_size + test_size <= n_periods:
            print(f"Window {window_num}: Position {current_pos} to {current_pos + train_size + test_size}")

            # Split data
            train_data = self.data.iloc[current_pos:current_pos + train_size]
            test_data = self.data.iloc[current_pos + train_size:current_pos + train_size + test_size]

            # Simple parameter selection (use first parameter set for now)
            # In production, you'd optimize on train_data
            param_names = list(self.param_grid.keys())
            params = {name: self.param_grid[name][0] for name in param_names}

            # Test on out-of-sample data
            try:
                strategy = self.strategy_class(**params)
                signals = strategy.generate_signals(test_data)

                if (signals != 0).sum() == 0:
                    print(f"  Warning: No signals in test period\n")
                    current_pos += test_size
                    window_num += 1
                    continue

                engine = EnhancedBacktestEngine(initial_capital=10000)
                result = engine.run(test_data, signals)

                results.append({
                    'window': window_num,
                    'start_pos': current_pos,
                    'return': result.metrics['total_return'],
                    'sharpe': result.metrics['sharpe_ratio'],
                    'max_dd': result.metrics['max_drawdown'],
                    'trades': result.metrics['total_trades'],
                    'win_rate': result.metrics['win_rate'],
                    'params': params
                })

                print(f"  Return: {result.metrics['total_return']:>6.2f}% | "
                      f"Sharpe: {result.metrics['sharpe_ratio']:>5.2f} | "
                      f"Trades: {result.metrics['total_trades']}\n")

            except Exception as e:
                print(f"  Error: {e}\n")

            current_pos += test_size
            window_num += 1

        # Aggregate results
        if results:
            returns = [r['return'] for r in results]
            sharpes = [r['sharpe'] for r in results]
            drawdowns = [r['max_dd'] for r in results]

            aggregate = {
                'n_windows': len(results),
                'avg_return': np.mean(returns),
                'std_return': np.std(returns),
                'avg_sharpe': np.mean(sharpes),
                'avg_drawdown': np.mean(drawdowns),
                'profitable_windows': sum(1 for r in returns if r > 0),
                'consistency': sum(1 for r in returns if r > 0) / len(returns),
                'all_windows': results
            }

            self._print_wf_results(aggregate)
            return aggregate
        else:
            print("No valid walk-forward results")
            return {}

    def _print_wf_results(self, results: Dict):
        """Print walk-forward results."""
        print("\n" + "="*80)
        print("  WALK-FORWARD SUMMARY")
        print("="*80 + "\n")

        print(f"Total Windows: {results['n_windows']}")
        print(f"Profitable Windows: {results['profitable_windows']} ({results['consistency']*100:.1f}%)\n")

        print(f"Average Return per Window: {results['avg_return']:.2f}%")
        print(f"Std Dev of Returns: {results['std_return']:.2f}%")
        print(f"Average Sharpe Ratio: {results['avg_sharpe']:.2f}")
        print(f"Average Max Drawdown: {results['avg_drawdown']:.2f}%\n")

        if results['consistency'] > 0.70:
            print("✅ EXCELLENT: Strategy is highly consistent across time periods")
        elif results['consistency'] > 0.60:
            print("✓ GOOD: Strategy shows reasonable consistency")
        elif results['consistency'] > 0.50:
            print("⚠ MODERATE: Strategy is marginally consistent")
        else:
            print("❌ POOR: Strategy lacks consistency - likely overfit")

        print()


if __name__ == "__main__":
    print("Monte Carlo simulation module loaded successfully")
