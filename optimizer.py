"""
Strategy parameter optimization module.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any
from itertools import product
from backtest_engine import BacktestEngine
from strategies import get_strategy
import time


class StrategyOptimizer:
    """Optimize strategy parameters using grid search or other methods."""

    def __init__(self, data: pd.DataFrame, initial_capital: float = 10000):
        """
        Initialize the optimizer.

        Args:
            data: Historical market data
            initial_capital: Starting capital for backtests
        """
        self.data = data
        self.initial_capital = initial_capital
        self.results = []

    def grid_search(self, strategy_name: str, param_grid: Dict[str, List[Any]],
                   position_size: float = 1.0, stop_loss: float = None,
                   take_profit: float = None) -> pd.DataFrame:
        """
        Perform grid search optimization over parameter space.

        Args:
            strategy_name: Name of the strategy to optimize
            param_grid: Dictionary of parameter names to lists of values
            position_size: Position size for backtests
            stop_loss: Stop loss percentage
            take_profit: Take profit percentage

        Returns:
            DataFrame with optimization results sorted by performance
        """
        print(f"\nOptimizing {strategy_name} strategy...")
        print(f"Parameter grid: {param_grid}")

        # Generate all parameter combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(product(*param_values))

        print(f"Testing {len(combinations)} parameter combinations...")

        results = []
        start_time = time.time()

        for i, combo in enumerate(combinations):
            # Create parameter dictionary
            params = dict(zip(param_names, combo))

            try:
                # Create strategy with these parameters
                strategy = get_strategy(strategy_name, **params)

                # Generate signals
                signals = strategy.generate_signals(self.data)

                # Run backtest
                engine = BacktestEngine(initial_capital=self.initial_capital)
                result = engine.run(self.data, signals, position_size=position_size,
                                  stop_loss=stop_loss, take_profit=take_profit)

                # Store results
                result_dict = {
                    'params': params,
                    **result.metrics,
                    'signals_generated': (signals != 0).sum()
                }
                results.append(result_dict)

                if (i + 1) % 10 == 0:
                    elapsed = time.time() - start_time
                    print(f"Progress: {i+1}/{len(combinations)} ({elapsed:.1f}s)")

            except Exception as e:
                print(f"Error with params {params}: {e}")
                continue

        # Convert to DataFrame and sort by Sharpe ratio
        results_df = pd.DataFrame(results)

        if len(results_df) > 0:
            # Sort by multiple criteria
            results_df['score'] = (
                results_df['sharpe_ratio'] * 0.4 +
                results_df['total_return'] * 0.3 +
                results_df['win_rate'] * 0.2 -
                abs(results_df['max_drawdown']) * 0.1
            )
            results_df = results_df.sort_values('score', ascending=False)

        elapsed = time.time() - start_time
        print(f"\nOptimization completed in {elapsed:.1f}s")
        print(f"Valid results: {len(results_df)}/{len(combinations)}")

        return results_df

    def walk_forward_optimization(self, strategy_name: str, param_grid: Dict[str, List[Any]],
                                 train_size: int = 252, test_size: int = 63,
                                 position_size: float = 1.0) -> Dict:
        """
        Perform walk-forward optimization.

        Args:
            strategy_name: Name of the strategy
            param_grid: Parameter grid for optimization
            train_size: Number of periods for training
            test_size: Number of periods for testing
            position_size: Position size for backtests

        Returns:
            Dictionary with walk-forward results
        """
        print(f"\nWalk-forward optimization for {strategy_name}...")

        results = []
        n_periods = len(self.data)
        current_pos = 0

        while current_pos + train_size + test_size <= n_periods:
            print(f"\nWindow: {current_pos} to {current_pos + train_size + test_size}")

            # Split data
            train_data = self.data.iloc[current_pos:current_pos + train_size]
            test_data = self.data.iloc[current_pos + train_size:current_pos + train_size + test_size]

            # Optimize on training data
            temp_optimizer = StrategyOptimizer(train_data, self.initial_capital)
            optimization_results = temp_optimizer.grid_search(
                strategy_name, param_grid, position_size=position_size
            )

            if len(optimization_results) == 0:
                print("No valid results in this window")
                current_pos += test_size
                continue

            # Get best parameters
            best_params = optimization_results.iloc[0]['params']
            print(f"Best params: {best_params}")

            # Test on out-of-sample data
            strategy = get_strategy(strategy_name, **best_params)
            signals = strategy.generate_signals(test_data)
            engine = BacktestEngine(initial_capital=self.initial_capital)
            test_result = engine.run(test_data, signals, position_size=position_size)

            results.append({
                'window_start': current_pos,
                'train_return': optimization_results.iloc[0]['total_return'],
                'test_return': test_result.metrics['total_return'],
                'test_sharpe': test_result.metrics['sharpe_ratio'],
                'test_max_dd': test_result.metrics['max_drawdown'],
                'params': best_params
            })

            current_pos += test_size

        return {
            'windows': results,
            'avg_test_return': np.mean([r['test_return'] for r in results]),
            'avg_test_sharpe': np.mean([r['test_sharpe'] for r in results]),
            'avg_test_drawdown': np.mean([r['test_max_dd'] for r in results]),
        }

    def optimize_risk_parameters(self, strategy_name: str, best_params: Dict,
                                stop_loss_range: List[float] = None,
                                take_profit_range: List[float] = None,
                                position_size_range: List[float] = None) -> pd.DataFrame:
        """
        Optimize risk management parameters.

        Args:
            strategy_name: Strategy name
            best_params: Best strategy parameters from previous optimization
            stop_loss_range: List of stop loss values to test
            take_profit_range: List of take profit values to test
            position_size_range: List of position sizes to test

        Returns:
            DataFrame with risk parameter results
        """
        print("\nOptimizing risk parameters...")

        if stop_loss_range is None:
            stop_loss_range = [None, 0.02, 0.03, 0.05, 0.07, 0.10]
        if take_profit_range is None:
            take_profit_range = [None, 0.05, 0.10, 0.15, 0.20]
        if position_size_range is None:
            position_size_range = [0.5, 0.75, 1.0]

        results = []

        for sl in stop_loss_range:
            for tp in take_profit_range:
                for ps in position_size_range:
                    try:
                        strategy = get_strategy(strategy_name, **best_params)
                        signals = strategy.generate_signals(self.data)
                        engine = BacktestEngine(initial_capital=self.initial_capital)
                        result = engine.run(self.data, signals, position_size=ps,
                                          stop_loss=sl, take_profit=tp)

                        results.append({
                            'stop_loss': sl,
                            'take_profit': tp,
                            'position_size': ps,
                            **result.metrics
                        })
                    except Exception as e:
                        print(f"Error with SL={sl}, TP={tp}, PS={ps}: {e}")

        results_df = pd.DataFrame(results)
        if len(results_df) > 0:
            results_df['score'] = (
                results_df['sharpe_ratio'] * 0.5 +
                results_df['total_return'] * 0.3 -
                abs(results_df['max_drawdown']) * 0.2
            )
            results_df = results_df.sort_values('score', ascending=False)

        return results_df


if __name__ == "__main__":
    print("Strategy optimizer loaded successfully")
