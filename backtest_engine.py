"""
Core backtesting engine for trading strategies.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Trade:
    """Represents a single trade."""
    entry_date: datetime
    exit_date: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    size: float
    direction: str  # 'long' or 'short'
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None

    def close_trade(self, exit_date: datetime, exit_price: float):
        """Close the trade and calculate P&L."""
        self.exit_date = exit_date
        self.exit_price = exit_price

        if self.direction == 'long':
            self.pnl = (exit_price - self.entry_price) * self.size
            self.pnl_pct = ((exit_price - self.entry_price) / self.entry_price) * 100
        else:  # short
            self.pnl = (self.entry_price - exit_price) * self.size
            self.pnl_pct = ((self.entry_price - exit_price) / self.entry_price) * 100


@dataclass
class BacktestResult:
    """Results from a backtest run."""
    trades: List[Trade]
    equity_curve: pd.Series
    metrics: Dict
    final_capital: float
    total_return: float

    def __repr__(self):
        return f"BacktestResult(trades={len(self.trades)}, return={self.total_return:.2f}%, final=${self.final_capital:,.2f})"


class BacktestEngine:
    """Core backtesting engine."""

    def __init__(self, initial_capital: float = 10000, commission: float = 0.001,
                 slippage: float = 0.0005):
        """
        Initialize the backtest engine.

        Args:
            initial_capital: Starting capital in dollars
            commission: Commission rate (0.001 = 0.1%)
            slippage: Slippage rate (0.0005 = 0.05%)
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.reset()

    def reset(self):
        """Reset the engine state."""
        self.capital = self.initial_capital
        self.position = None
        self.trades = []
        self.equity_curve = []
        self.timestamps = []

    def run(self, data: pd.DataFrame, signals: pd.Series,
            position_size: float = 1.0, stop_loss: Optional[float] = None,
            take_profit: Optional[float] = None) -> BacktestResult:
        """
        Run a backtest with given data and signals.

        Args:
            data: DataFrame with OHLCV data
            signals: Series with signals (1=buy, -1=sell, 0=hold)
            position_size: Fraction of capital to use per trade (0-1)
            stop_loss: Stop loss percentage (e.g., 0.02 for 2%)
            take_profit: Take profit percentage (e.g., 0.05 for 5%)

        Returns:
            BacktestResult object with results
        """
        self.reset()

        # Align data and signals
        data = data.copy()
        signals = signals.reindex(data.index, fill_value=0)

        for i in range(len(data)):
            timestamp = data.index[i]
            row = data.iloc[i]
            signal = signals.iloc[i]

            # Update equity curve
            current_equity = self.capital
            if self.position:
                current_price = row['close']
                if self.position.direction == 'long':
                    unrealized_pnl = (current_price - self.position.entry_price) * self.position.size
                else:
                    unrealized_pnl = (self.position.entry_price - current_price) * self.position.size
                current_equity += unrealized_pnl

            self.equity_curve.append(current_equity)
            self.timestamps.append(timestamp)

            # Check stop loss and take profit
            if self.position and (stop_loss or take_profit):
                current_price = row['close']

                if self.position.direction == 'long':
                    price_change = (current_price - self.position.entry_price) / self.position.entry_price
                else:
                    price_change = (self.position.entry_price - current_price) / self.position.entry_price

                # Check stop loss
                if stop_loss and price_change <= -stop_loss:
                    self._close_position(timestamp, current_price)
                    continue

                # Check take profit
                if take_profit and price_change >= take_profit:
                    self._close_position(timestamp, current_price)
                    continue

            # Process signals
            if signal == 1 and not self.position:  # Buy signal
                self._open_position(timestamp, row['close'], 'long', position_size)

            elif signal == -1:  # Sell signal
                if self.position and self.position.direction == 'long':
                    self._close_position(timestamp, row['close'])
                elif not self.position:
                    self._open_position(timestamp, row['close'], 'short', position_size)

            elif signal == 0 and self.position:  # Exit signal
                self._close_position(timestamp, row['close'])

        # Close any remaining position
        if self.position:
            last_price = data.iloc[-1]['close']
            self._close_position(data.index[-1], last_price)

        # Calculate metrics
        equity_series = pd.Series(self.equity_curve, index=self.timestamps)
        metrics = self._calculate_metrics(equity_series)

        return BacktestResult(
            trades=self.trades,
            equity_curve=equity_series,
            metrics=metrics,
            final_capital=self.capital,
            total_return=((self.capital - self.initial_capital) / self.initial_capital) * 100
        )

    def _open_position(self, timestamp: datetime, price: float,
                      direction: str, position_size: float):
        """Open a new position."""
        # Apply slippage
        if direction == 'long':
            entry_price = price * (1 + self.slippage)
        else:
            entry_price = price * (1 - self.slippage)

        # Calculate position size
        capital_to_use = self.capital * position_size
        commission_cost = capital_to_use * self.commission

        # Account for commission
        available_capital = capital_to_use - commission_cost
        size = available_capital / entry_price

        self.position = Trade(
            entry_date=timestamp,
            exit_date=None,
            entry_price=entry_price,
            exit_price=None,
            size=size,
            direction=direction
        )

        # Deduct capital used
        self.capital -= capital_to_use

    def _close_position(self, timestamp: datetime, price: float):
        """Close the current position."""
        if not self.position:
            return

        # Apply slippage
        if self.position.direction == 'long':
            exit_price = price * (1 - self.slippage)
        else:
            exit_price = price * (1 + self.slippage)

        # Calculate P&L
        self.position.close_trade(timestamp, exit_price)

        # Calculate proceeds
        proceeds = exit_price * self.position.size
        commission_cost = proceeds * self.commission
        net_proceeds = proceeds - commission_cost

        # Update capital
        self.capital += net_proceeds

        # Store trade
        self.trades.append(self.position)
        self.position = None

    def _calculate_metrics(self, equity_curve: pd.Series) -> Dict:
        """Calculate performance metrics."""
        if len(equity_curve) == 0:
            return {}

        returns = equity_curve.pct_change().dropna()

        # Calculate metrics
        total_return = ((equity_curve.iloc[-1] - equity_curve.iloc[0]) / equity_curve.iloc[0]) * 100

        # Winning and losing trades
        winning_trades = [t for t in self.trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl and t.pnl < 0]

        win_rate = len(winning_trades) / len(self.trades) * 100 if self.trades else 0

        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0

        profit_factor = (
            abs(sum([t.pnl for t in winning_trades]) / sum([t.pnl for t in losing_trades]))
            if losing_trades and sum([t.pnl for t in losing_trades]) != 0 else 0
        )

        # Sharpe ratio (annualized)
        if len(returns) > 0 and returns.std() > 0:
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)
        else:
            sharpe_ratio = 0

        # Maximum drawdown
        cummax = equity_curve.expanding().max()
        drawdown = (equity_curve - cummax) / cummax
        max_drawdown = drawdown.min() * 100

        return {
            'total_return': total_return,
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'final_capital': equity_curve.iloc[-1],
        }


if __name__ == "__main__":
    # Simple test
    print("Backtesting engine loaded successfully")
