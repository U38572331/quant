"""
Donchian Channel Breakout Strategy
Professional quantitative trading system for NQ futures
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class EntryType(Enum):
    TOUCH = 'touch'  # Price touches channel boundary
    CLOSE = 'close'  # Candle closes beyond channel


class ExitType(Enum):
    FIXED_POINTS = 'fixed_points'
    R_MULTIPLE = 'r_multiple'
    TIME_BASED = 'time_based'
    TRAILING = 'trailing'


class StopType(Enum):
    ATR = 'atr'
    FIXED = 'fixed'
    SWING = 'swing'


@dataclass
class StrategyParams:
    """Donchian Breakout Strategy Parameters"""
    channel_period: int  # Lookback period for highs/lows
    entry_type: EntryType
    exit_type: ExitType
    exit_param: float  # Points, R-multiple, minutes, or trailing points
    stop_type: StopType
    stop_param: float  # ATR multiplier or fixed points
    session_filter: str  # 'full_rth', 'morning_only', 'afternoon_only'


@dataclass
class Trade:
    """Individual trade record"""
    date: pd.Timestamp
    direction: str  # 'long' or 'short'
    entry_time: pd.Timestamp
    entry_price: float
    exit_time: Optional[pd.Timestamp]
    exit_price: Optional[float]
    stop_price: float
    target_price: float
    pnl: float
    pnl_points: float
    outcome: str  # 'win', 'loss', 'breakeven'
    exit_reason: str  # 'target', 'stop', 'time', 'eod'
    risk_points: float
    bars_held: int
    atr_at_entry: float  # ATR value at entry time
    vwap_at_entry: float  # VWAP value at entry time
    entry_vs_vwap: float  # Entry price distance from VWAP (positive = above)


@dataclass
class PerformanceMetrics:
    """Strategy performance metrics"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    expectancy: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    avg_bars_held: float
    consecutive_losses_max: int
    recovery_factor: float


class DonchianBreakout:
    """
    Donchian Channel Breakout Strategy Implementation
    
    Enters long when price breaks above N-period high
    Enters short when price breaks below N-period low
    Exits based on configurable exit logic
    """
    
    def __init__(self, params: StrategyParams):
        self.params = params
        self.trades: List[Trade] = []
        
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr
    
    def calculate_vwap(self, df: pd.DataFrame) -> pd.Series:
        """Calculate Volume Weighted Average Price from session start"""
        # Typical price (H+L+C)/3
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        
        # Cumulative (Price * Volume) and cumulative Volume
        pv = typical_price * df['volume']
        cum_pv = pv.cumsum()
        cum_vol = df['volume'].cumsum()
        
        # VWAP = Cumulative(Price*Volume) / Cumulative(Volume)
        vwap = cum_pv / cum_vol
        return vwap
    
    def calculate_channels(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        """Calculate Donchian Channel upper and lower bands"""
        period = self.params.channel_period
        
        upper_channel = df['high'].rolling(window=period).max().shift(1)
        lower_channel = df['low'].rolling(window=period).min().shift(1)
        
        return upper_channel, lower_channel
    
    def get_session_data(self, df: pd.DataFrame, session_filter: str) -> pd.DataFrame:
        """Filter data based on session"""
        df = df.copy()
        df['hour'] = df.index.hour
        df['minute'] = df.index.minute
        
        if session_filter == 'morning_only':
            # 09:30 - 12:00
            mask = (df['hour'] < 12) | ((df['hour'] == 12) & (df['minute'] == 0))
            return df[mask]
        elif session_filter == 'afternoon_only':
            # 12:00 - 16:00
            mask = df['hour'] >= 12
            return df[mask]
        else:  # full_rth
            return df
    
    def detect_entry_signal(self, row: pd.Series, prev_high: float, prev_low: float, 
                           upper_channel: float, lower_channel: float) -> Optional[str]:
        """Detect entry signal for current bar"""
        if pd.isna(upper_channel) or pd.isna(lower_channel):
            return None
            
        # Avoid re-entry using previous bar's highs/lows
        if self.params.entry_type == EntryType.TOUCH:
            # Long: current high breaks above channel
            if row['high'] > upper_channel and prev_high <= upper_channel:
                return 'long'
            # Short: current low breaks below channel
            elif row['low'] < lower_channel and prev_low >= lower_channel:
                return 'short'
        else:  # CLOSE
            # Long: candle closes above channel
            if row['close'] > upper_channel:
                return 'long'
            # Short: candle closes below channel
            elif row['close'] < lower_channel:
                return 'short'
                
        return None
    
    def calculate_stop_loss(self, df: pd.DataFrame, idx: int, direction: str, 
                           entry_price: float) -> float:
        """Calculate stop loss price"""
        if self.params.stop_type == StopType.ATR:
            atr = self.calculate_atr(df.iloc[:idx+1])
            atr_value = atr.iloc[-1]
            if pd.isna(atr_value):
                atr_value = 20  # Default fallback
            
            if direction == 'long':
                stop = entry_price - (self.params.stop_param * atr_value)
            else:
                stop = entry_price + (self.params.stop_param * atr_value)
                
        elif self.params.stop_type == StopType.FIXED:
            if direction == 'long':
                stop = entry_price - self.params.stop_param
            else:
                stop = entry_price + self.params.stop_param
                
        else:  # SWING (use channel low/high)
            period = self.params.channel_period
            if direction == 'long':
                stop = df['low'].iloc[max(0, idx-period):idx+1].min()
            else:
                stop = df['high'].iloc[max(0, idx-period):idx+1].max()
                
        return stop
    
    def calculate_target(self, entry_price: float, stop_price: float, direction: str) -> float:
        """Calculate target price"""
        risk = abs(entry_price - stop_price)
        
        if self.params.exit_type == ExitType.FIXED_POINTS:
            if direction == 'long':
                target = entry_price + self.params.exit_param
            else:
                target = entry_price - self.params.exit_param
                
        elif self.params.exit_type == ExitType.R_MULTIPLE:
            if direction == 'long':
                target = entry_price + (risk * self.params.exit_param)
            else:
                target = entry_price - (risk * self.params.exit_param)
        else:
            # For time-based and trailing, no fixed target
            target = np.inf if direction == 'long' else -np.inf
            
        return target
    
    def check_exit(self, row: pd.Series, trade_bars: int, direction: str,
                   entry_price: float, stop_price: float, target_price: float,
                   highest_since_entry: float, lowest_since_entry: float) -> Tuple[bool, str, float]:
        """
        Check if trade should exit
        Returns: (should_exit, exit_reason, exit_price)
        """
        # Check stop loss first (conservative)
        if direction == 'long':
            if row['low'] <= stop_price:
                return True, 'stop', stop_price
        else:
            if row['high'] >= stop_price:
                return True, 'stop', stop_price
        
        # Check target
        if self.params.exit_type in [ExitType.FIXED_POINTS, ExitType.R_MULTIPLE]:
            if direction == 'long':
                if row['high'] >= target_price:
                    return True, 'target', target_price
            else:
                if row['low'] <= target_price:
                    return True, 'target', target_price
        
        # Trailing stop
        elif self.params.exit_type == ExitType.TRAILING:
            trail_dist = self.params.exit_param
            if direction == 'long':
                trail_stop = highest_since_entry - trail_dist
                if row['low'] <= trail_stop:
                    return True, 'trailing_stop', trail_stop
            else:
                trail_stop = lowest_since_entry + trail_dist
                if row['high'] >= trail_stop:
                    return True, 'trailing_stop', trail_stop
        
        # Time-based exit
        elif self.params.exit_type == ExitType.TIME_BASED:
            if trade_bars >= int(self.params.exit_param):
                exit_price = row['close']
                return True, 'time', exit_price
        
        return False, '', 0.0
    
    def backtest_day(self, day_df: pd.DataFrame, date: pd.Timestamp) -> Optional[Trade]:
        """Backtest single day, return first trade if any"""
        if len(day_df) < self.params.channel_period + 1:
            return None
        
        # Filter by session
        day_df = self.get_session_data(day_df, self.params.session_filter)
        if len(day_df) < self.params.channel_period + 1:
            return None
        
        # Calculate channels
        upper_channel, lower_channel = self.calculate_channels(day_df)
        
        # Calculate ATR and VWAP for the day
        atr_series = self.calculate_atr(day_df)
        vwap_series = self.calculate_vwap(day_df)
        
        # Find first entry signal
        entry_idx = None
        direction = None
        
        for i in range(self.params.channel_period, len(day_df)):
            prev_high = day_df['high'].iloc[i-1] if i > 0 else 0
            prev_low = day_df['low'].iloc[i-1] if i > 0 else 999999
            
            signal = self.detect_entry_signal(
                day_df.iloc[i],
                prev_high,
                prev_low,
                upper_channel.iloc[i],
                lower_channel.iloc[i]
            )
            
            if signal:
                entry_idx = i
                direction = signal
                break
        
        if entry_idx is None:
            return None
        
        # Entry details
        entry_row = day_df.iloc[entry_idx]
        entry_time = entry_row.name
        
        if self.params.entry_type == EntryType.TOUCH:
            if direction == 'long':
                entry_price = upper_channel.iloc[entry_idx]
            else:
                entry_price = lower_channel.iloc[entry_idx]
        else:  # CLOSE
            entry_price = entry_row['close']
        
        # Calculate stop and target
        stop_price = self.calculate_stop_loss(day_df, entry_idx, direction, entry_price)
        target_price = self.calculate_target(entry_price, stop_price, direction)
        risk_points = abs(entry_price - stop_price)
        
        # Get ATR and VWAP at entry
        atr_at_entry = atr_series.iloc[entry_idx] if not pd.isna(atr_series.iloc[entry_idx]) else 0.0
        vwap_at_entry = vwap_series.iloc[entry_idx] if not pd.isna(vwap_series.iloc[entry_idx]) else entry_price
        entry_vs_vwap = entry_price - vwap_at_entry
        
        # Simulate trade execution
        highest_since_entry = entry_price
        lowest_since_entry = entry_price
        
        for i in range(entry_idx + 1, len(day_df)):
            row = day_df.iloc[i]
            trade_bars = i - entry_idx
            
            # Update highest/lowest
            highest_since_entry = max(highest_since_entry, row['high'])
            lowest_since_entry = min(lowest_since_entry, row['low'])
            
            should_exit, exit_reason, exit_price = self.check_exit(
                row, trade_bars, direction, entry_price, stop_price, target_price,
                highest_since_entry, lowest_since_entry
            )
            
            if should_exit:
                # Calculate P&L
                if direction == 'long':
                    pnl_points = exit_price - entry_price
                else:
                    pnl_points = entry_price - exit_price
                
                pnl = pnl_points * 20  # NQ point value = $20
                outcome = 'win' if pnl > 0 else ('loss' if pnl < 0 else 'breakeven')
                
                trade = Trade(
                    date=date,
                    direction=direction,
                    entry_time=entry_time,
                    entry_price=entry_price,
                    exit_time=row.name,
                    exit_price=exit_price,
                    stop_price=stop_price,
                    target_price=target_price,
                    pnl=pnl,
                    pnl_points=pnl_points,
                    outcome=outcome,
                    exit_reason=exit_reason,
                    risk_points=risk_points,
                    bars_held=trade_bars,
                    atr_at_entry=atr_at_entry,
                    vwap_at_entry=vwap_at_entry,
                    entry_vs_vwap=entry_vs_vwap
                )
                
                return trade
        
        # End of day exit
        last_row = day_df.iloc[-1]
        exit_price = last_row['close']
        
        if direction == 'long':
            pnl_points = exit_price - entry_price
        else:
            pnl_points = entry_price - exit_price
        
        pnl = pnl_points * 20
        outcome = 'win' if pnl > 0 else ('loss' if pnl < 0 else 'breakeven')
        
        trade = Trade(
            date=date,
            direction=direction,
            entry_time=entry_time,
            entry_price=entry_price,
            exit_time=last_row.name,
            exit_price=exit_price,
            stop_price=stop_price,
            target_price=target_price,
            pnl=pnl,
            pnl_points=pnl_points,
            outcome=outcome,
            exit_reason='eod',
            risk_points=risk_points,
            bars_held=len(day_df) - entry_idx - 1,
            atr_at_entry=atr_at_entry,
            vwap_at_entry=vwap_at_entry,
            entry_vs_vwap=entry_vs_vwap
        )
        
        return trade
    
    def run_backtest(self, df: pd.DataFrame) -> List[Trade]:
        """Run backtest on entire dataset"""
        self.trades = []
        
        # Group by date
        df = df.copy()
        
        # Ensure index is datetime and creating time columns for filtering
        if not isinstance(df.index, pd.DatetimeIndex):
             # Try to convert if failed? or assume done?
             # donchian_main.py sets index but ML optimizer passes passed df.
             # ML optimizer passes self.df.
             pass

        df['hour'] = df.index.hour
        df['minute'] = df.index.minute
        
        df['date_group'] = df.index.date
        grouped = df.groupby('date_group')
        
        for date, day_df in grouped:
            trade = self.backtest_day(day_df, pd.Timestamp(date))
            if trade:
                self.trades.append(trade)
        
        return self.trades
    
    def calculate_metrics(self) -> PerformanceMetrics:
        """Calculate performance metrics from trades"""
        if not self.trades:
            return PerformanceMetrics(
                total_trades=0, winning_trades=0, losing_trades=0,
                win_rate=0, total_pnl=0, avg_win=0, avg_loss=0,
                profit_factor=0, expectancy=0, sharpe_ratio=0,
                max_drawdown=0, max_drawdown_pct=0, avg_bars_held=0,
                consecutive_losses_max=0, recovery_factor=0
            )
        
        total_trades = len(self.trades)
        wins = [t for t in self.trades if t.outcome == 'win']
        losses = [t for t in self.trades if t.outcome == 'loss']
        
        winning_trades = len(wins)
        losing_trades = len(losses)
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        total_pnl = sum(t.pnl for t in self.trades)
        avg_win = np.mean([t.pnl for t in wins]) if wins else 0
        avg_loss = np.mean([t.pnl for t in losses]) if losses else 0
        
        gross_profit = sum(t.pnl for t in wins)
        gross_loss = abs(sum(t.pnl for t in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        expectancy = total_pnl / total_trades if total_trades > 0 else 0
        
        # Calculate Sharpe ratio
        returns = [t.pnl for t in self.trades]
        if len(returns) > 1 and np.std(returns) > 0:
            sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(252)  # Annualized
        else:
            sharpe_ratio = 0
        
        # Calculate max drawdown
        cumulative_pnl = np.cumsum([t.pnl for t in self.trades])
        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdown = running_max - cumulative_pnl
        max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0
        max_drawdown_pct = (max_drawdown / running_max[np.argmax(drawdown)]) * 100 if np.argmax(drawdown) > 0 and running_max[np.argmax(drawdown)] > 0 else 0
        
        # Average bars held
        avg_bars_held = np.mean([t.bars_held for t in self.trades])
        
        # Max consecutive losses
        consecutive_losses = 0
        max_consecutive_losses = 0
        for t in self.trades:
            if t.outcome == 'loss':
                consecutive_losses += 1
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
            else:
                consecutive_losses = 0
        
        # Recovery factor
        recovery_factor = total_pnl / max_drawdown if max_drawdown > 0 else 0
        
        return PerformanceMetrics(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            expectancy=expectancy,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            avg_bars_held=avg_bars_held,
            consecutive_losses_max=max_consecutive_losses,
            recovery_factor=recovery_factor
        )
