"""
Advanced risk management module for position sizing and risk control.
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional


class RiskManager:
    """Advanced risk management for trading strategies."""

    def __init__(self, initial_capital: float, max_risk_per_trade: float = 0.02,
                 max_portfolio_risk: float = 0.06, max_drawdown_limit: float = 0.20):
        """
        Initialize risk manager.

        Args:
            initial_capital: Starting capital
            max_risk_per_trade: Max % of capital to risk per trade (default 2%)
            max_portfolio_risk: Max total portfolio risk (default 6%)
            max_drawdown_limit: Circuit breaker - stop trading if DD exceeds this
        """
        self.initial_capital = initial_capital
        self.max_risk_per_trade = max_risk_per_trade
        self.max_portfolio_risk = max_portfolio_risk
        self.max_drawdown_limit = max_drawdown_limit
        self.peak_capital = initial_capital

    def calculate_position_size_atr(self, current_capital: float, atr: float,
                                    entry_price: float, stop_loss_atr_mult: float = 2.0) -> float:
        """
        Calculate position size based on ATR (volatility-adjusted).

        Args:
            current_capital: Current account capital
            atr: Average True Range value
            entry_price: Entry price for the trade
            stop_loss_atr_mult: Stop loss distance in ATR multiples

        Returns:
            Position size as fraction of capital (0-1)
        """
        # Calculate risk amount
        risk_amount = current_capital * self.max_risk_per_trade

        # Calculate stop loss distance
        stop_distance = atr * stop_loss_atr_mult

        # Position size based on risk
        if stop_distance > 0 and entry_price > 0:
            shares = risk_amount / stop_distance
            position_value = shares * entry_price
            position_fraction = position_value / current_capital

            # Cap at reasonable limits
            return min(position_fraction, 0.25)  # Max 25% per position

        return 0.10  # Default conservative size

    def calculate_position_size_kelly(self, win_rate: float, avg_win: float,
                                      avg_loss: float, fraction: float = 0.25) -> float:
        """
        Calculate position size using Kelly Criterion (fractional).

        Args:
            win_rate: Win rate (0-1)
            avg_win: Average win amount
            avg_loss: Average loss amount
            fraction: Fraction of Kelly to use (0.25 = quarter Kelly, conservative)

        Returns:
            Position size fraction
        """
        if win_rate <= 0 or win_rate >= 1 or avg_loss >= 0:
            return 0.10  # Default if invalid inputs

        # Kelly formula: f = (p*b - q) / b
        # where p = win rate, q = loss rate, b = avg_win / abs(avg_loss)
        q = 1 - win_rate
        b = avg_win / abs(avg_loss) if avg_loss != 0 else 1

        kelly = (win_rate * b - q) / b

        # Use fractional Kelly for safety
        kelly_fraction = kelly * fraction

        # Bound between reasonable limits
        return np.clip(kelly_fraction, 0.05, 0.25)

    def calculate_position_size_volatility(self, current_capital: float,
                                          recent_volatility: float,
                                          target_volatility: float = 0.15) -> float:
        """
        Calculate position size to target a specific portfolio volatility.

        Args:
            current_capital: Current capital
            recent_volatility: Recent realized volatility
            target_volatility: Target portfolio volatility

        Returns:
            Position size fraction
        """
        if recent_volatility <= 0:
            return 0.10

        # Scale position inversely with volatility
        position_size = (target_volatility / recent_volatility) * 0.20

        return np.clip(position_size, 0.05, 0.30)

    def check_drawdown_limit(self, current_capital: float) -> bool:
        """
        Check if drawdown limit has been exceeded.

        Returns:
            True if trading should continue, False if should stop
        """
        # Update peak
        if current_capital > self.peak_capital:
            self.peak_capital = current_capital

        # Calculate current drawdown
        drawdown = (self.peak_capital - current_capital) / self.peak_capital

        # Stop trading if drawdown exceeds limit
        return drawdown < self.max_drawdown_limit

    def calculate_optimal_stop_loss(self, entry_price: float, atr: float,
                                   direction: str = 'long',
                                   atr_multiplier: float = 2.0) -> float:
        """
        Calculate optimal stop loss based on ATR.

        Args:
            entry_price: Entry price
            atr: Average True Range
            direction: 'long' or 'short'
            atr_multiplier: ATR multiplier for stop distance

        Returns:
            Stop loss price
        """
        stop_distance = atr * atr_multiplier

        if direction == 'long':
            return entry_price - stop_distance
        else:
            return entry_price + stop_distance

    def calculate_optimal_take_profit(self, entry_price: float, stop_loss: float,
                                      direction: str = 'long',
                                      risk_reward_ratio: float = 2.5) -> float:
        """
        Calculate take profit based on risk-reward ratio.

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            direction: 'long' or 'short'
            risk_reward_ratio: Target risk:reward ratio

        Returns:
            Take profit price
        """
        risk = abs(entry_price - stop_loss)
        reward = risk * risk_reward_ratio

        if direction == 'long':
            return entry_price + reward
        else:
            return entry_price - reward


class TrailingStopManager:
    """Manage trailing stops for open positions."""

    def __init__(self, initial_stop: float, trailing_type: str = 'atr',
                 trail_percent: float = 0.02, atr_mult: float = 2.0):
        """
        Initialize trailing stop manager.

        Args:
            initial_stop: Initial stop loss price
            trailing_type: 'percent' or 'atr'
            trail_percent: Trailing percentage (for percent type)
            atr_mult: ATR multiplier (for atr type)
        """
        self.current_stop = initial_stop
        self.trailing_type = trailing_type
        self.trail_percent = trail_percent
        self.atr_mult = atr_mult
        self.highest_price = None
        self.lowest_price = None

    def update(self, current_price: float, direction: str, atr: Optional[float] = None) -> float:
        """
        Update trailing stop based on current price.

        Args:
            current_price: Current market price
            direction: 'long' or 'short'
            atr: Current ATR (for atr-based trailing)

        Returns:
            Updated stop loss price
        """
        if direction == 'long':
            # Track highest price
            if self.highest_price is None or current_price > self.highest_price:
                self.highest_price = current_price

                # Update trailing stop
                if self.trailing_type == 'percent':
                    new_stop = self.highest_price * (1 - self.trail_percent)
                elif self.trailing_type == 'atr' and atr:
                    new_stop = self.highest_price - (atr * self.atr_mult)
                else:
                    new_stop = self.current_stop

                # Only move stop up, never down
                self.current_stop = max(self.current_stop, new_stop)

        else:  # short
            # Track lowest price
            if self.lowest_price is None or current_price < self.lowest_price:
                self.lowest_price = current_price

                # Update trailing stop
                if self.trailing_type == 'percent':
                    new_stop = self.lowest_price * (1 + self.trail_percent)
                elif self.trailing_type == 'atr' and atr:
                    new_stop = self.lowest_price + (atr * self.atr_mult)
                else:
                    new_stop = self.current_stop

                # Only move stop down, never up
                self.current_stop = min(self.current_stop, new_stop)

        return self.current_stop

    def is_stopped_out(self, current_price: float, direction: str) -> bool:
        """Check if position should be stopped out."""
        if direction == 'long':
            return current_price <= self.current_stop
        else:
            return current_price >= self.current_stop


if __name__ == "__main__":
    # Test risk manager
    rm = RiskManager(initial_capital=10000, max_risk_per_trade=0.02)

    # Test ATR-based sizing
    pos_size = rm.calculate_position_size_atr(
        current_capital=10000,
        atr=5.0,
        entry_price=100.0,
        stop_loss_atr_mult=2.0
    )
    print(f"ATR-based position size: {pos_size:.2%}")

    # Test Kelly sizing
    kelly_size = rm.calculate_position_size_kelly(
        win_rate=0.40,
        avg_win=200,
        avg_loss=-100,
        fraction=0.25
    )
    print(f"Kelly position size: {kelly_size:.2%}")

    # Test trailing stop
    ts = TrailingStopManager(initial_stop=95.0, trailing_type='percent', trail_percent=0.02)

    prices = [100, 105, 110, 108, 112, 109]
    for price in prices:
        stop = ts.update(price, 'long')
        stopped = ts.is_stopped_out(price, 'long')
        print(f"Price: ${price:.2f}, Stop: ${stop:.2f}, Stopped: {stopped}")
