"""
MULTI-STRATEGY PORTFOLIO MANAGER
Target: 10% per maand door 5 strategieën parallel te draaien

Dit is het hoofd-systeem dat alle strategieën coördineert.
"""
import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime
from enhanced_backtest_engine import EnhancedBacktestEngine


class MultiStrategyPortfolio:
    """
    Portfolio manager die meerdere strategieën parallel uitvoert.

    Strategieën:
    1. HF Momentum (30% allocatie) - 3% per maand target
    2. Mean Reversion (20% allocatie) - 2% per maand target
    3. Breakout (25% allocatie) - 2.5% per maand target
    4. Trend Following (15% allocatie) - 1.5% per maand target
    5. Swing Reversal (10% allocatie) - 1% per maand target

    TOTAAL TARGET: 10% per maand
    """

    def __init__(self, initial_capital: float = 10000):
        self.initial_capital = initial_capital
        self.total_capital = initial_capital

        # Strategy allocations (moet totaal 1.0 zijn)
        self.allocations = {
            'hf_momentum': 0.30,      # 30% - Most aggressive
            'mean_reversion': 0.20,   # 20% - High frequency
            'breakout': 0.25,         # 25% - Medium frequency
            'trend_following': 0.15,  # 15% - Lower frequency
            'swing_reversal': 0.10    # 10% - Lowest frequency
        }

        # Leverage per strategie (controlled risk)
        self.leverage = {
            'hf_momentum': 3.0,       # 3x voor snelle trades
            'mean_reversion': 2.0,    # 2x voor scalping
            'breakout': 4.0,          # 4x voor breakouts (higher risk/reward)
            'trend_following': 2.0,   # 2x voor trends
            'swing_reversal': 2.0     # 2x voor swings
        }

        # Performance tracking
        self.strategy_performance = {name: [] for name in self.allocations.keys()}
        self.portfolio_equity = [initial_capital]
        self.monthly_returns = []

        # Risk limits
        self.max_portfolio_drawdown = 0.30  # Stop at -30%
        self.max_total_leverage = 3.0       # Max 3x gemiddeld
        self.peak_capital = initial_capital

    def calculate_position_sizes(self) -> Dict[str, float]:
        """
        Bereken position size voor elke strategie.

        Returns:
            Dict met strategy_name -> capital allocated
        """
        positions = {}

        for strategy, allocation in self.allocations.items():
            base_capital = self.total_capital * allocation
            leverage_factor = self.leverage[strategy]
            effective_capital = base_capital * leverage_factor
            positions[strategy] = effective_capital

        return positions

    def check_portfolio_risk(self) -> bool:
        """
        Check of portfolio binnen risk limits blijft.

        Returns:
            True als OK om te traden, False als stop
        """
        # Update peak
        if self.total_capital > self.peak_capital:
            self.peak_capital = self.total_capital

        # Calculate drawdown
        drawdown = (self.peak_capital - self.total_capital) / self.peak_capital

        if drawdown > self.max_portfolio_drawdown:
            print(f"⚠️ STOP: Max drawdown {drawdown*100:.1f}% bereikt!")
            return False

        # Check total leverage
        total_positions = sum(self.calculate_position_sizes().values())
        avg_leverage = total_positions / self.total_capital

        if avg_leverage > self.max_total_leverage:
            print(f"⚠️ WARNING: Leverage {avg_leverage:.1f}x te hoog!")
            return False

        return True

    def execute_portfolio(self, market_data: pd.DataFrame,
                         strategies: Dict) -> Dict:
        """
        Voer alle strategieën parallel uit.

        Args:
            market_data: Market data voor alle timeframes
            strategies: Dict van strategy_name -> strategy object

        Returns:
            Dict met resultaten per strategie
        """
        if not self.check_portfolio_risk():
            return {'status': 'STOPPED', 'reason': 'Risk limit exceeded'}

        results = {}
        position_sizes = self.calculate_position_sizes()

        for name, strategy in strategies.items():
            if name not in self.allocations:
                continue

            try:
                # Generate signals
                signals = strategy.generate_signals(market_data)

                # Calculate capital voor deze strategie
                strategy_capital = position_sizes[name]

                # Execute backtest
                engine = EnhancedBacktestEngine(
                    initial_capital=strategy_capital / self.leverage[name],
                    use_risk_management=True
                )

                result = engine.run(market_data, signals, use_trailing_stop=True)

                # Store results
                results[name] = {
                    'return': result.metrics.get('total_return', 0),
                    'trades': result.metrics.get('total_trades', 0),
                    'sharpe': result.metrics.get('sharpe_ratio', 0),
                    'max_dd': result.metrics.get('max_drawdown', 0),
                    'final_capital': result.final_capital
                }

                # Update strategy performance
                self.strategy_performance[name].append(result.metrics.get('total_return', 0))

            except Exception as e:
                print(f"Error in strategy {name}: {e}")
                results[name] = {'error': str(e)}

        return results

    def calculate_portfolio_return(self, strategy_results: Dict) -> float:
        """
        Bereken total portfolio return.

        Args:
            strategy_results: Results van execute_portfolio

        Returns:
            Total portfolio return percentage
        """
        total_return = 0.0

        for name, result in strategy_results.items():
            if 'error' in result:
                continue

            allocation = self.allocations.get(name, 0)
            strategy_return = result.get('return', 0)
            leverage = self.leverage.get(name, 1.0)

            # Gewogen return met leverage
            weighted_return = allocation * strategy_return * leverage
            total_return += weighted_return

        return total_return

    def print_portfolio_summary(self, strategy_results: Dict):
        """Print portfolio performance summary."""
        print("\n" + "="*80)
        print("  MULTI-STRATEGY PORTFOLIO PERFORMANCE")
        print("="*80 + "\n")

        total_return = self.calculate_portfolio_return(strategy_results)

        print(f"Portfolio Total Return: {total_return:.2f}%")
        print(f"Total Capital: ${self.total_capital:,.2f}\n")

        print("Strategy Breakdown:")
        print("-" * 80)

        for name, result in strategy_results.items():
            if 'error' in result:
                print(f"{name:20s}: ERROR - {result['error']}")
                continue

            allocation = self.allocations[name]
            leverage = self.leverage[name]
            ret = result.get('return', 0)
            trades = result.get('trades', 0)
            sharpe = result.get('sharpe', 0)

            contribution = allocation * ret * leverage

            print(f"{name:20s}: {ret:>6.2f}% | "
                  f"Trades: {trades:>3d} | "
                  f"Sharpe: {sharpe:>5.2f} | "
                  f"Contrib: {contribution:>6.2f}%")

        print("-" * 80)
        print(f"{'PORTFOLIO TOTAL':20s}: {total_return:>6.2f}%")
        print("="*80 + "\n")

    def get_diversification_score(self, strategy_results: Dict) -> float:
        """
        Bereken diversification score (hoger = beter).

        Returns:
            Score 0-1, waarbij 1 = perfect gediversifieerd
        """
        returns = []
        for name, result in strategy_results.items():
            if 'error' not in result:
                returns.append(result.get('return', 0))

        if len(returns) < 2:
            return 0.0

        # Check hoe verschillend de returns zijn
        std_dev = np.std(returns)
        mean_abs = np.mean(np.abs(returns))

        if mean_abs == 0:
            return 0.0

        diversity_score = min(std_dev / mean_abs, 1.0)
        return diversity_score


class PortfolioOptimizer:
    """Optimize portfolio allocations and leverage."""

    def __init__(self, portfolio: MultiStrategyPortfolio):
        self.portfolio = portfolio

    def optimize_allocations(self, historical_results: Dict) -> Dict[str, float]:
        """
        Optimize allocations based op historical performance.

        Simple approach: allocate more naar beter presterende strategieën.
        """
        # Calculate Sharpe ratios
        sharpes = {}
        for name, results in historical_results.items():
            if results:
                sharpe = np.mean([r.get('sharpe', 0) for r in results])
                sharpes[name] = max(sharpe, 0)  # No negative allocations

        # Normalize to sum to 1.0
        total_sharpe = sum(sharpes.values())
        if total_sharpe == 0:
            return self.portfolio.allocations  # Keep original

        optimized = {name: sharpe / total_sharpe for name, sharpe in sharpes.items()}

        return optimized

    def optimize_leverage(self, historical_results: Dict) -> Dict[str, float]:
        """
        Optimize leverage based op volatility.

        Lower volatility = can use higher leverage.
        """
        optimized_leverage = {}

        for name, results in historical_results.items():
            if not results:
                optimized_leverage[name] = 1.0
                continue

            # Calculate volatility (std of returns)
            returns = [r.get('return', 0) for r in results]
            volatility = np.std(returns)

            # Inverse relationship: lower vol = higher leverage
            if volatility < 10:  # Low volatility
                leverage = 4.0
            elif volatility < 20:
                leverage = 3.0
            elif volatility < 30:
                leverage = 2.0
            else:
                leverage = 1.5

            optimized_leverage[name] = leverage

        return optimized_leverage


if __name__ == "__main__":
    print("="*80)
    print("  MULTI-STRATEGY PORTFOLIO MANAGER")
    print("="*80)
    print("\nTarget: 10% per maand via 5 parallel strategieën")
    print("\nAllocaties:")

    portfolio = MultiStrategyPortfolio(initial_capital=10000)

    for name, allocation in portfolio.allocations.items():
        leverage = portfolio.leverage[name]
        effective = allocation * leverage
        print(f"  {name:20s}: {allocation*100:>5.1f}% × {leverage}x = {effective*100:>5.1f}% effective")

    positions = portfolio.calculate_position_sizes()
    total_effective = sum(positions.values())
    avg_leverage = total_effective / portfolio.total_capital

    print(f"\nTotal Effective Exposure: {total_effective/portfolio.total_capital*100:.1f}%")
    print(f"Average Leverage: {avg_leverage:.2f}x")
    print(f"\nMax Drawdown Limit: {portfolio.max_portfolio_drawdown*100}%")
    print(f"Max Leverage Limit: {portfolio.max_total_leverage}x")
    print("\n" + "="*80)
