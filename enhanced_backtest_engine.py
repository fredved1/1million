"""
Enhanced backtesting engine with advanced risk management.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from backtest_engine import Trade, BacktestResult
from risk_manager import RiskManager, TrailingStopManager


class EnhancedBacktestEngine:
    """Enhanced backtesting engine with dynamic risk management."""

    def __init__(self, initial_capital: float = 10000, commission: float = 0.001,
                 slippage: float = 0.0005, use_risk_management: bool = True):
        """
        Initialize enhanced backtest engine.

        Args:
            initial_capital: Starting capital
            commission: Commission rate
            slippage: Slippage rate
            use_risk_management: Whether to use advanced risk management
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.use_risk_management = use_risk_management

        self.risk_manager = RiskManager(
            initial_capital=initial_capital,
            max_risk_per_trade=0.02,  # 2% risk per trade
            max_drawdown_limit=0.40     # Stop if DD exceeds 40%
        )

        self.reset()

    def reset(self):
        """Reset engine state."""
        self.capital = self.initial_capital
        self.position = None
        self.trades = []
        self.equity_curve = []
        self.timestamps = []
        self.trailing_stop = None

        # Performance tracking
        self.consecutive_losses = 0
        self.recent_trades = []

    def run(self, data: pd.DataFrame, signals: pd.Series,
            use_trailing_stop: bool = True) -> BacktestResult:
        """
        Run backtest with enhanced risk management.

        Args:
            data: DataFrame with OHLCV data
            signals: Trading signals
            use_trailing_stop: Whether to use trailing stops

        Returns:
            BacktestResult
        """
        self.reset()

        data = data.copy()
        signals = signals.reindex(data.index, fill_value=0)

        # Calculate ATR for all data
        data['tr'] = np.maximum(
            data['high'] - data['low'],
            np.maximum(
                abs(data['high'] - data['close'].shift()),
                abs(data['low'] - data['close'].shift())
            )
        )
        data['atr'] = data['tr'].rolling(window=14).mean()

        for i in range(len(data)):
            timestamp = data.index[i]
            row = data.iloc[i]
            signal = signals.iloc[i]

            # Check if we should stop trading due to drawdown
            if not self.risk_manager.check_drawdown_limit(self.capital):
                print(f"WARNING: Max drawdown limit exceeded at {timestamp}. Stopping trading.")
                if self.position:
                    self._close_position(timestamp, row['close'], reason="Drawdown limit")
                break

            # Update equity curve
            current_equity = self._calculate_current_equity(row['close'])
            self.equity_curve.append(current_equity)
            self.timestamps.append(timestamp)

            # Manage existing position
            if self.position:
                # Update trailing stop
                if use_trailing_stop and self.trailing_stop:
                    current_stop = self.trailing_stop.update(
                        row['close'],
                        self.position.direction,
                        row['atr']
                    )

                    # Check if stopped out
                    if self.trailing_stop.is_stopped_out(row['close'], self.position.direction):
                        self._close_position(timestamp, current_stop, reason="Trailing stop")
                        continue

                # Check static stop loss
                if hasattr(self.position, 'stop_loss') and self.position.stop_loss:
                    if self.position.direction == 'long' and row['low'] <= self.position.stop_loss:
                        self._close_position(timestamp, self.position.stop_loss, reason="Stop loss")
                        continue
                    elif self.position.direction == 'short' and row['high'] >= self.position.stop_loss:
                        self._close_position(timestamp, self.position.stop_loss, reason="Stop loss")
                        continue

                # Check take profit
                if hasattr(self.position, 'take_profit') and self.position.take_profit:
                    if self.position.direction == 'long' and row['high'] >= self.position.take_profit:
                        self._close_position(timestamp, self.position.take_profit, reason="Take profit")
                        continue
                    elif self.position.direction == 'short' and row['low'] <= self.position.take_profit:
                        self._close_position(timestamp, self.position.take_profit, reason="Take profit")
                        continue

            # Process new signals
            if signal == 1 and not self.position:  # Buy signal
                # Check if we should reduce size after losses
                position_size = self._calculate_dynamic_position_size(row['atr'], row['close'])

                if position_size > 0:
                    self._open_position(timestamp, row['close'], 'long', position_size,
                                      row['atr'], use_trailing_stop)

            elif signal == -1:  # Sell signal
                if self.position and self.position.direction == 'long':
                    self._close_position(timestamp, row['close'], reason="Exit signal")

        # Close any remaining position
        if self.position:
            last_price = data.iloc[-1]['close']
            self._close_position(data.index[-1], last_price, reason="End of data")

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

    def _calculate_dynamic_position_size(self, atr: float, price: float) -> float:
        """Calculate position size based on current conditions."""
        if not self.use_risk_management:
            return 0.90  # Default aggressive sizing

        # Base size on ATR
        base_size = self.risk_manager.calculate_position_size_atr(
            self.capital, atr, price, stop_loss_atr_mult=2.5
        )

        # Reduce size after consecutive losses
        if self.consecutive_losses >= 3:
            reduction_factor = 0.6  # Reduce after 3 losses
        elif self.consecutive_losses >= 2:
            reduction_factor = 0.8  # 80% size after 2 losses
        else:
            reduction_factor = 1.0

        # Calculate recent win rate if we have enough trades
        if len(self.recent_trades) >= 10:
            recent_winners = sum(1 for t in self.recent_trades[-10:] if t.pnl and t.pnl > 0)
            recent_win_rate = recent_winners / 10

            # If recent performance is poor, reduce size
            if recent_win_rate < 0.25:
                reduction_factor *= 0.8

        final_size = base_size * reduction_factor

        return min(max(final_size, 0.10), 0.30)  # Between 10% and 30%

    def _calculate_current_equity(self, current_price: float) -> float:
        """Calculate current equity including unrealized P&L."""
        equity = self.capital

        if self.position:
            if self.position.direction == 'long':
                unrealized_pnl = (current_price - self.position.entry_price) * self.position.size
            else:
                unrealized_pnl = (self.position.entry_price - current_price) * self.position.size

            equity += unrealized_pnl

        return equity

    def _open_position(self, timestamp: datetime, price: float, direction: str,
                      position_size: float, atr: float, use_trailing_stop: bool):
        """Open a new position with risk management."""
        # Apply slippage
        if direction == 'long':
            entry_price = price * (1 + self.slippage)
        else:
            entry_price = price * (1 - self.slippage)

        # Calculate position size
        capital_to_use = self.capital * position_size
        commission_cost = capital_to_use * self.commission
        available_capital = capital_to_use - commission_cost
        size = available_capital / entry_price

        # Calculate stop loss and take profit
        stop_loss = self.risk_manager.calculate_optimal_stop_loss(
            entry_price, atr, direction, atr_multiplier=2.0
        )
        take_profit = self.risk_manager.calculate_optimal_take_profit(
            entry_price, stop_loss, direction, risk_reward_ratio=2.5
        )

        # Create trade object
        self.position = Trade(
            entry_date=timestamp,
            exit_date=None,
            entry_price=entry_price,
            exit_price=None,
            size=size,
            direction=direction
        )

        # Add stop loss and take profit to position
        self.position.stop_loss = stop_loss
        self.position.take_profit = take_profit

        # Initialize trailing stop
        if use_trailing_stop:
            self.trailing_stop = TrailingStopManager(
                initial_stop=stop_loss,
                trailing_type='atr',
                atr_mult=2.0
            )
        else:
            self.trailing_stop = None

        # Deduct capital
        self.capital -= capital_to_use

    def _close_position(self, timestamp: datetime, price: float, reason: str = "Signal"):
        """Close the current position."""
        if not self.position:
            return

        # Apply slippage
        if self.position.direction == 'long':
            exit_price = price * (1 - self.slippage)
        else:
            exit_price = price * (1 + self.slippage)

        # Close trade
        self.position.close_trade(timestamp, exit_price)

        # Calculate proceeds
        proceeds = exit_price * self.position.size
        commission_cost = proceeds * self.commission
        net_proceeds = proceeds - commission_cost

        # Update capital
        self.capital += net_proceeds

        # Track consecutive losses
        if self.position.pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        # Store trade
        self.trades.append(self.position)
        self.recent_trades.append(self.position)

        # Keep only recent trades for analysis
        if len(self.recent_trades) > 20:
            self.recent_trades.pop(0)

        self.position = None
        self.trailing_stop = None

    def _calculate_metrics(self, equity_curve: pd.Series) -> Dict:
        """Calculate comprehensive performance metrics."""
        if len(equity_curve) == 0:
            return {}

        returns = equity_curve.pct_change().dropna()

        # Basic metrics
        total_return = ((equity_curve.iloc[-1] - equity_curve.iloc[0]) / equity_curve.iloc[0]) * 100

        # Trade statistics
        winning_trades = [t for t in self.trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl and t.pnl < 0]

        win_rate = len(winning_trades) / len(self.trades) * 100 if self.trades else 0
        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0

        # Profit factor
        total_wins = sum([t.pnl for t in winning_trades]) if winning_trades else 0
        total_losses = abs(sum([t.pnl for t in losing_trades])) if losing_trades else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else 0

        # Sharpe ratio
        if len(returns) > 0 and returns.std() > 0:
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)
        else:
            sharpe_ratio = 0

        # Drawdown analysis
        cummax = equity_curve.expanding().max()
        drawdown = (equity_curve - cummax) / cummax
        max_drawdown = drawdown.min() * 100

        # Sortino ratio (downside deviation)
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() if len(downside_returns) > 0 else 0
        sortino_ratio = (returns.mean() / downside_std) * np.sqrt(252) if downside_std > 0 else 0

        # Calmar ratio
        years = len(equity_curve) / 252
        annualized_return = total_return / years if years > 0 else 0
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0

        # Recovery factor
        recovery_factor = total_return / abs(max_drawdown) if max_drawdown != 0 else 0

        # Expectancy
        expectancy = (win_rate / 100 * avg_win) + ((1 - win_rate / 100) * avg_loss)

        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown': max_drawdown,
            'calmar_ratio': calmar_ratio,
            'recovery_factor': recovery_factor,
            'expectancy': expectancy,
            'final_capital': equity_curve.iloc[-1],
        }


if __name__ == "__main__":
    print("Enhanced backtest engine loaded successfully")
