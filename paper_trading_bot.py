"""
PAPER TRADING BOT - 24/7 Automated Trading
This runs our strategies in real-time with fake money to PROVE it works before going live!

The FINAL TEST before we make REAL MONEY! 💰
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
from typing import Dict, Optional
import signal
import sys

from binance_client import BinanceClient
from market_regime_detector import MarketRegimeDetector, MarketRegime, recommend_strategy
from mean_reversion_scalper import MeanReversionScalper
from hf_momentum_strategy import HighFrequencyMomentum
from breakout_catcher import BreakoutCatcher
from trend_follower import TrendFollower
from swing_reversal import SwingReversal


class PaperTradingBot:
    """
    24/7 paper trading bot that:
    1. Fetches real-time data from Binance
    2. Detects market regime
    3. Selects best strategy
    4. Executes trades (simulated)
    5. Tracks performance
    6. Adjusts to market conditions
    """

    def __init__(self, symbol: str = 'BTC/USDT', timeframe: str = '5m',
                 initial_capital: float = 10000.0):
        """
        Initialize paper trading bot.

        Args:
            symbol: Trading pair
            timeframe: Candle timeframe ('1m', '5m', '15m', '1h')
            initial_capital: Starting capital (paper money)
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.initial_capital = initial_capital

        # Initialize components
        print("🚀 Initializing Paper Trading Bot...")
        self.client = BinanceClient(paper_trading=True)
        self.client.paper_balance = initial_capital

        self.regime_detector = MarketRegimeDetector(lookback=50)

        # Initialize strategies
        self.strategies = {
            'Mean_Reversion_Scalper': MeanReversionScalper(
                bb_period=15, bb_std=1.8, rsi_oversold=35, vol_spike_mult=1.2
            ),
            'HF_Momentum': HighFrequencyMomentum(
                lookback=5, momentum_threshold=0.3, rsi_min=35, rsi_max=70
            ),
            'Breakout_Catcher': BreakoutCatcher(
                lookback=20, momentum_threshold=1.0, volume_mult=1.5
            ),
            'Trend_Follower': TrendFollower(
                ema_fast=20, ema_slow=50, adx_threshold=25, atr_period=14
            ),
            'Swing_Reversal': SwingReversal(
                rsi_oversold=30, lookback=50
            )
        }

        # State
        self.running = False
        self.current_position = None
        self.current_strategy = None
        self.current_regime = None
        self.data_buffer = None

        # Performance tracking
        self.start_time = datetime.now()
        self.trades_today = 0
        self.daily_pnl = 0
        self.best_daily_return = 0
        self.worst_daily_return = 0

        print("✅ Paper Trading Bot initialized!")
        print(f"   Symbol: {symbol}")
        print(f"   Timeframe: {timeframe}")
        print(f"   Initial Capital: ${initial_capital:,.2f}")

    def fetch_market_data(self, lookback: int = 200) -> pd.DataFrame:
        """Fetch latest market data."""
        try:
            data = self.client.fetch_ohlcv(self.symbol, self.timeframe, limit=lookback)
            return data
        except Exception as e:
            print(f"❌ Error fetching data: {e}")
            return None

    def detect_regime(self, data: pd.DataFrame) -> tuple:
        """Detect current market regime."""
        regime, confidence, metrics = self.regime_detector.detect_regime(data)
        return regime, confidence, metrics

    def select_strategy(self, regime: MarketRegime, confidence: float) -> Optional[str]:
        """Select best strategy based on regime."""
        recommendation = recommend_strategy(regime, confidence)

        if recommendation['action'] != 'TRADE':
            return None

        strategy_name = recommendation['strategy']
        return strategy_name

    def generate_signals(self, data: pd.DataFrame, strategy_name: str) -> pd.Series:
        """Generate trading signals from selected strategy."""
        if strategy_name not in self.strategies:
            return pd.Series(0, index=data.index)

        strategy = self.strategies[strategy_name]
        try:
            signals = strategy.generate_signals(data)
            return signals
        except Exception as e:
            print(f"⚠️  Error generating signals: {e}")
            return pd.Series(0, index=data.index)

    def execute_trading_loop(self):
        """Main trading loop."""
        print("\n" + "="*80)
        print("  📈 STARTING PAPER TRADING!")
        print("="*80)
        print(f"  Symbol: {self.symbol}")
        print(f"  Timeframe: {self.timeframe}")
        print(f"  Starting Balance: ${self.client.paper_balance:,.2f}")
        print(f"  Press Ctrl+C to stop")
        print("="*80 + "\n")

        iteration = 0

        while self.running:
            iteration += 1

            try:
                # 1. Fetch latest data
                data = self.fetch_market_data(lookback=200)
                if data is None or len(data) < 50:
                    print("⚠️  Insufficient data, retrying in 30s...")
                    time.sleep(30)
                    continue

                current_price = data['close'].iloc[-1]

                # 2. Detect regime
                regime, confidence, metrics = self.detect_regime(data)
                self.current_regime = regime

                # 3. Select strategy
                strategy_name = self.select_strategy(regime, confidence)

                # Print status
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iteration {iteration}")
                print(f"  Price: ${current_price:,.2f}")
                print(f"  Regime: {regime.value} ({confidence:.1%})")
                print(f"  Strategy: {strategy_name if strategy_name else 'NONE (waiting)'}")
                print(f"  Balance: ${self.client.paper_balance:,.2f}")
                print(f"  Position: {self.current_position if self.current_position else 'None'}")

                # 4. Check current position
                positions = self.client.get_positions()

                if self.symbol in positions:
                    # Have open position
                    position = positions[self.symbol]
                    entry_price = position['entry_price']
                    unrealized_pnl = (current_price - entry_price) / entry_price * 100 * position['leverage']

                    print(f"  Unrealized PnL: {unrealized_pnl:+.2f}%")

                    # Generate exit signals
                    if strategy_name:
                        signals = self.generate_signals(data, strategy_name)
                        latest_signal = signals.iloc[-1]

                        # Exit signal
                        if latest_signal == -1:
                            print("  🔴 EXIT SIGNAL! Closing position...")
                            self.client.place_market_order(self.symbol, 'sell', amount=1000, leverage=position['leverage'])
                            self.current_position = None
                            self.trades_today += 1
                else:
                    # No position, look for entry
                    if strategy_name:
                        signals = self.generate_signals(data, strategy_name)
                        latest_signal = signals.iloc[-1]

                        # Entry signal
                        if latest_signal == 1:
                            # Get recommended allocation & leverage
                            recommendation = recommend_strategy(regime, confidence)
                            allocation = recommendation['allocation']
                            leverage = recommendation['leverage']

                            amount = self.client.paper_balance * allocation
                            if amount >= 100:  # Minimum trade size
                                print(f"  🟢 ENTRY SIGNAL! Opening position...")
                                print(f"     Amount: ${amount:.2f}")
                                print(f"     Leverage: {leverage}x")
                                self.client.place_market_order(self.symbol, 'buy', amount=amount, leverage=leverage)
                                self.current_position = strategy_name
                                self.current_strategy = strategy_name

                # 5. Print daily stats
                stats = self.client.get_performance_stats()
                total_return = stats.get('total_return', 0)
                win_rate = stats.get('win_rate', 0)
                total_trades = stats.get('total_trades', 0)

                print(f"\n  📊 Performance:")
                print(f"     Total Return: {total_return:+.2f}%")
                print(f"     Total Trades: {total_trades}")
                print(f"     Win Rate: {win_rate:.1f}%")

                # Calculate how far to 10%/month target
                days_running = (datetime.now() - self.start_time).days + 1
                months_running = days_running / 30.0
                monthly_return = total_return / months_running if months_running > 0 else 0

                print(f"     Monthly Rate: {monthly_return:.2f}% (target: 10%)")
                if monthly_return >= 10:
                    print(f"     🚀 TARGET ACHIEVED! WE'RE MAKING IT! 💰")
                elif monthly_return >= 7:
                    print(f"     ⚡ Close to target! Keep going!")
                elif monthly_return >= 5:
                    print(f"     💪 Good progress!")

                # 6. Sleep until next update
                # For 5m timeframe, check every 1 minute
                # For 1m timeframe, check every 10 seconds
                sleep_time = {
                    '1m': 10,
                    '5m': 60,
                    '15m': 180,
                    '1h': 600
                }.get(self.timeframe, 60)

                print(f"\n  💤 Sleeping {sleep_time}s until next check...")
                time.sleep(sleep_time)

            except KeyboardInterrupt:
                print("\n\n⚠️  Keyboard interrupt detected...")
                break
            except Exception as e:
                print(f"\n❌ Error in trading loop: {e}")
                import traceback
                traceback.print_exc()
                print("  Retrying in 30s...")
                time.sleep(30)

    def start(self):
        """Start the bot."""
        self.running = True

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        try:
            self.execute_trading_loop()
        finally:
            self.stop()

    def stop(self):
        """Stop the bot."""
        self.running = False

        print("\n" + "="*80)
        print("  🛑 STOPPING PAPER TRADING BOT")
        print("="*80)

        # Close any open positions
        positions = self.client.get_positions()
        if positions:
            print(f"\n⚠️  Closing {len(positions)} open position(s)...")
            for symbol in positions:
                self.client.place_market_order(symbol, 'sell', amount=1000, leverage=1.0)

        # Print final stats
        stats = self.client.get_performance_stats()
        duration = datetime.now() - self.start_time

        print(f"\n📊 FINAL PERFORMANCE REPORT")
        print(f"="*80)
        print(f"  Duration: {duration}")
        print(f"  Starting Balance: ${self.initial_capital:,.2f}")
        print(f"  Final Balance: ${stats.get('current_balance', 0):,.2f}")
        print(f"  Total Return: {stats.get('total_return', 0):+.2f}%")
        print(f"  Total Trades: {stats.get('total_trades', 0)}")
        print(f"  Wins: {stats.get('wins', 0)}")
        print(f"  Losses: {stats.get('losses', 0)}")
        print(f"  Win Rate: {stats.get('win_rate', 0):.1f}%")
        print(f"  Best Trade: ${stats.get('best_trade', 0):+.2f}")
        print(f"  Worst Trade: ${stats.get('worst_trade', 0):+.2f}")

        # Monthly projection
        days_running = duration.days + (duration.seconds / 86400)
        if days_running > 0:
            monthly_return = stats.get('total_return', 0) / (days_running / 30.0)
            print(f"\n  💰 MONTHLY RETURN RATE: {monthly_return:.2f}%")

            if monthly_return >= 10:
                print(f"  ✅ 10% TARGET ACHIEVED! READY FOR LIVE TRADING! 🚀🚀🚀")
            elif monthly_return >= 7:
                print(f"  ⚠️  Close to target! A few more optimizations needed.")
            elif monthly_return >= 5:
                print(f"  💪 Good progress! Keep tuning parameters.")
            else:
                print(f"  ⚠️  Below target. Consider:")
                print(f"     - Switching to higher frequency data (1m)")
                print(f"     - Adjusting strategy parameters")
                print(f"     - Focusing on best performing regimes")

        print(f"\n{'='*80}")
        print("  ✅ Paper Trading Bot stopped")
        print("="*80)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\n\n⚠️  Received signal {signum}")
        self.stop()
        sys.exit(0)


if __name__ == "__main__":
    print("="*80)
    print("  💎 PAPER TRADING BOT - PATH TO RICHES! 💎")
    print("="*80)
    print("\nThis bot will:")
    print("  1. ✅ Fetch real-time crypto data (5-minute candles)")
    print("  2. ✅ Detect market regime (mean-reverting/trending/breakout)")
    print("  3. ✅ Select best strategy for current market")
    print("  4. ✅ Execute trades (paper money, no risk!)")
    print("  5. ✅ Track performance & adjust to conditions")
    print(f"\nTarget: 10% per month")
    print(f"If we achieve this in paper trading → GO LIVE! 🚀")
    print("\n" + "="*80)

    # Create and start bot
    bot = PaperTradingBot(
        symbol='BTC/USDT',
        timeframe='5m',  # 5-minute candles for decent frequency
        initial_capital=10000.0
    )

    try:
        bot.start()
    except KeyboardInterrupt:
        print("\n\n⚠️  Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
