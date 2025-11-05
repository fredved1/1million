"""
Analytics and performance reporting module.
"""
import pandas as pd
import numpy as np
from typing import List, Dict
from backtest_engine import BacktestResult, Trade
from tabulate import tabulate


class PerformanceAnalyzer:
    """Analyze and report on backtest performance."""

    @staticmethod
    def print_summary(result: BacktestResult, strategy_name: str = "Strategy"):
        """Print a formatted summary of backtest results."""
        print("\n" + "=" * 70)
        print(f"  {strategy_name.upper()} - BACKTEST RESULTS")
        print("=" * 70)

        metrics = result.metrics

        # Overall Performance
        print("\n📊 OVERALL PERFORMANCE")
        print("-" * 70)
        data = [
            ["Initial Capital", f"${metrics.get('final_capital', 0) - (metrics.get('total_return', 0) / 100) * (metrics.get('final_capital', 0) / (1 + metrics.get('total_return', 0) / 100)):,.2f}"],
            ["Final Capital", f"${metrics.get('final_capital', 0):,.2f}"],
            ["Total Return", f"{metrics.get('total_return', 0):.2f}%"],
            ["Sharpe Ratio", f"{metrics.get('sharpe_ratio', 0):.3f}"],
            ["Max Drawdown", f"{metrics.get('max_drawdown', 0):.2f}%"],
            ["Profit Factor", f"{metrics.get('profit_factor', 0):.2f}"],
        ]
        print(tabulate(data, tablefmt="simple"))

        # Trading Activity
        print("\n📈 TRADING ACTIVITY")
        print("-" * 70)
        data = [
            ["Total Trades", metrics.get('total_trades', 0)],
            ["Winning Trades", metrics.get('winning_trades', 0)],
            ["Losing Trades", metrics.get('losing_trades', 0)],
            ["Win Rate", f"{metrics.get('win_rate', 0):.2f}%"],
            ["Avg Win", f"${metrics.get('avg_win', 0):.2f}"],
            ["Avg Loss", f"${metrics.get('avg_loss', 0):.2f}"],
        ]
        print(tabulate(data, tablefmt="simple"))

        # Trade Analysis
        if len(result.trades) > 0:
            print("\n💰 TRADE ANALYSIS")
            print("-" * 70)

            profits = [t.pnl for t in result.trades if t.pnl]
            if profits:
                data = [
                    ["Best Trade", f"${max(profits):.2f}"],
                    ["Worst Trade", f"${min(profits):.2f}"],
                    ["Avg Trade", f"${np.mean(profits):.2f}"],
                    ["Std Dev", f"${np.std(profits):.2f}"],
                ]
                print(tabulate(data, tablefmt="simple"))

        print("\n" + "=" * 70 + "\n")

    @staticmethod
    def compare_strategies(results: Dict[str, BacktestResult]):
        """Compare multiple strategy results."""
        print("\n" + "=" * 90)
        print("  STRATEGY COMPARISON")
        print("=" * 90 + "\n")

        data = []
        for name, result in results.items():
            m = result.metrics
            data.append([
                name,
                f"${m.get('final_capital', 0):,.0f}",
                f"{m.get('total_return', 0):.1f}%",
                f"{m.get('sharpe_ratio', 0):.2f}",
                f"{m.get('max_drawdown', 0):.1f}%",
                m.get('total_trades', 0),
                f"{m.get('win_rate', 0):.1f}%"
            ])

        headers = ["Strategy", "Final $", "Return", "Sharpe", "Max DD", "Trades", "Win Rate"]
        print(tabulate(data, headers=headers, tablefmt="grid"))
        print()

    @staticmethod
    def print_top_trades(trades: List[Trade], n: int = 10):
        """Print the top N trades by P&L."""
        if not trades:
            print("No trades to display")
            return

        sorted_trades = sorted(trades, key=lambda t: t.pnl or 0, reverse=True)
        top_trades = sorted_trades[:n]

        print(f"\n🏆 TOP {n} TRADES")
        print("-" * 90)

        data = []
        for i, trade in enumerate(top_trades, 1):
            data.append([
                i,
                trade.entry_date.strftime('%Y-%m-%d'),
                trade.exit_date.strftime('%Y-%m-%d') if trade.exit_date else 'Open',
                trade.direction.upper(),
                f"${trade.entry_price:.2f}",
                f"${trade.exit_price:.2f}" if trade.exit_price else 'N/A',
                f"${trade.pnl:.2f}" if trade.pnl else 'N/A',
                f"{trade.pnl_pct:.2f}%" if trade.pnl_pct else 'N/A',
            ])

        headers = ["#", "Entry Date", "Exit Date", "Dir", "Entry $", "Exit $", "P&L", "Return"]
        print(tabulate(data, headers=headers, tablefmt="grid"))
        print()

    @staticmethod
    def analyze_monthly_returns(equity_curve: pd.Series) -> pd.DataFrame:
        """Calculate monthly returns from equity curve."""
        df = equity_curve.to_frame('equity')
        df['month'] = df.index.to_period('M')

        # Calculate monthly returns
        monthly = df.groupby('month')['equity'].agg(['first', 'last'])
        monthly['return'] = ((monthly['last'] - monthly['first']) / monthly['first']) * 100

        return monthly

    @staticmethod
    def calculate_risk_metrics(equity_curve: pd.Series) -> Dict:
        """Calculate additional risk metrics."""
        returns = equity_curve.pct_change().dropna()

        # Value at Risk (95% confidence)
        var_95 = np.percentile(returns, 5)

        # Conditional Value at Risk (Expected Shortfall)
        cvar_95 = returns[returns <= var_95].mean()

        # Calmar Ratio (return / max drawdown)
        total_return = (equity_curve.iloc[-1] - equity_curve.iloc[0]) / equity_curve.iloc[0]
        cummax = equity_curve.expanding().max()
        drawdown = (equity_curve - cummax) / cummax
        max_drawdown = abs(drawdown.min())
        calmar_ratio = total_return / max_drawdown if max_drawdown > 0 else 0

        # Sortino Ratio (uses only downside deviation)
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() if len(downside_returns) > 0 else 0
        sortino_ratio = (returns.mean() / downside_std) * np.sqrt(252) if downside_std > 0 else 0

        return {
            'var_95': var_95 * 100,
            'cvar_95': cvar_95 * 100,
            'calmar_ratio': calmar_ratio,
            'sortino_ratio': sortino_ratio,
            'volatility': returns.std() * np.sqrt(252) * 100,
        }

    @staticmethod
    def print_risk_metrics(equity_curve: pd.Series):
        """Print detailed risk metrics."""
        metrics = PerformanceAnalyzer.calculate_risk_metrics(equity_curve)

        print("\n⚠️  RISK METRICS")
        print("-" * 70)

        data = [
            ["Annualized Volatility", f"{metrics['volatility']:.2f}%"],
            ["Value at Risk (95%)", f"{metrics['var_95']:.2f}%"],
            ["Conditional VaR (95%)", f"{metrics['cvar_95']:.2f}%"],
            ["Calmar Ratio", f"{metrics['calmar_ratio']:.3f}"],
            ["Sortino Ratio", f"{metrics['sortino_ratio']:.3f}"],
        ]
        print(tabulate(data, tablefmt="simple"))
        print()

    @staticmethod
    def save_results_to_csv(result: BacktestResult, filename: str):
        """Save backtest results to CSV files."""
        # Save trades
        if result.trades:
            trades_data = []
            for trade in result.trades:
                trades_data.append({
                    'entry_date': trade.entry_date,
                    'exit_date': trade.exit_date,
                    'direction': trade.direction,
                    'entry_price': trade.entry_price,
                    'exit_price': trade.exit_price,
                    'size': trade.size,
                    'pnl': trade.pnl,
                    'pnl_pct': trade.pnl_pct,
                })
            trades_df = pd.DataFrame(trades_data)
            trades_df.to_csv(f"{filename}_trades.csv", index=False)
            print(f"Trades saved to {filename}_trades.csv")

        # Save equity curve
        result.equity_curve.to_csv(f"{filename}_equity.csv")
        print(f"Equity curve saved to {filename}_equity.csv")

        # Save metrics
        metrics_df = pd.DataFrame([result.metrics])
        metrics_df.to_csv(f"{filename}_metrics.csv", index=False)
        print(f"Metrics saved to {filename}_metrics.csv")


if __name__ == "__main__":
    print("Analytics module loaded successfully")
