"""
Apex Trading System - Risk Management Module
==============================================
Position sizing, daily limits, and risk controls
"""

from typing import Dict, Optional, List
from datetime import datetime, date
from loguru import logger
from dataclasses import dataclass, field

from models import Position, AccountInfo, OrderRequest


@dataclass
class RiskLimits:
    """Risk limits configuration."""
    max_daily_loss: float = 10000.0      # Maximum daily loss allowed
    max_position_size: float = 50000.0   # Maximum position value
    max_trades_per_day: int = 10         # Maximum trades per day
    max_loss_per_trade: float = 2000.0   # Maximum loss per trade
    max_leverage: float = 1.0            # No leverage by default
    min_trade_size: float = 100.0        # Minimum trade value


class RiskManager:
    """Risk management for trading operations."""
    
    def __init__(self, limits: RiskLimits = None):
        self.limits = limits or RiskLimits()
        self._daily_pnl: float = 0.0
        self._daily_trades: int = 0
        self._last_reset: date = date.today()
        self._trade_losses: Dict[str, float] = {}  # Track per-trade losses
        
    def check_daily_loss(self) -> bool:
        """Check if daily loss limit is hit."""
        if self._daily_pnl <= -self.limits.max_daily_loss:
            logger.warning(f"Daily loss limit hit: ₹{self._daily_pnl:,.2f} / ₹{self.limits.max_daily_loss:,.2f}")
            return False
        return True
    
    def check_position_size(self, order_value: float) -> bool:
        """Check if position size is within limits."""
        if order_value > self.limits.max_position_size:
            logger.warning(f"Position size limit exceeded: ₹{order_value:,.2f} > ₹{self.limits.max_position_size:,.2f}")
            return False
        return True
    
    def check_daily_trades(self) -> bool:
        """Check if daily trade limit is hit."""
        if self._daily_trades >= self.limits.max_trades_per_day:
            logger.warning(f"Daily trade limit hit: {self._daily_trades} / {self.limits.max_trades_per_day}")
            return False
        return True
    
    def calculate_position_size(self, account: AccountInfo, 
                                 risk_per_trade: float,
                                 entry_price: float,
                                 stop_loss: float) -> int:
        """Calculate position size based on risk parameters."""
        if entry_price <= 0 or stop_loss <= 0:
            return 0
            
        risk_amount = min(
            account.balance * risk_per_trade / 100,
            self.limits.max_loss_per_trade
        )
        
        risk_per_share = abs(entry_price - stop_loss)
        if risk_per_share <= 0:
            return 0
            
        quantity = int(risk_amount / risk_per_share)
        
        # Apply position size limit
        max_qty = int(self.limits.max_position_size / entry_price)
        quantity = min(quantity, max_qty)
        
        # Apply minimum trade size
        min_qty = int(self.limits.min_trade_size / entry_price)
        quantity = max(quantity, min_qty)
        
        return max(0, quantity)
    
    def validate_order(self, order: OrderRequest, 
                       account: AccountInfo) -> tuple[bool, str]:
        """Validate an order against all risk rules."""
        order_value = order.price * order.quantity
        
        # Check daily loss
        if not self.check_daily_loss():
            return False, "Daily loss limit exceeded"
        
        # Check position size
        if not self.check_position_size(order_value):
            return False, "Position size limit exceeded"
        
        # Check daily trades
        if not self.check_daily_trades():
            return False, "Daily trade limit exceeded"
        
        # Check balance for buys
        if order.side == "BUY" and order_value > account.available_balance:
            return False, "Insufficient balance"
        
        return True, "Order validated"
    
    def record_trade(self, pnl: float) -> None:
        """Record trade result for daily tracking."""
        self._daily_trades += 1
        self._daily_pnl += pnl
        
        # Reset daily counters if new day
        today = date.today()
        if today != self._last_reset:
            self._daily_pnl = 0.0
            self._daily_trades = 0
            self._last_reset = today
            self._trade_losses = {}
            logger.info("Risk manager daily reset")
    
    def get_daily_stats(self) -> Dict:
        """Get daily risk statistics."""
        return {
            "daily_pnl": self._daily_pnl,
            "daily_trades": self._daily_trades,
            "max_daily_loss": self.limits.max_daily_loss,
            "max_trades_per_day": self.limits.max_trades_per_day,
            "remaining_trades": self.limits.max_trades_per_day - self._daily_trades,
            "loss_remaining": self.limits.max_daily_loss + self._daily_pnl
        }
    
    def update_limits(self, **kwargs) -> None:
        """Update risk limits dynamically."""
        for key, value in kwargs.items():
            if hasattr(self.limits, key):
                setattr(self.limits, key, value)
                logger.info(f"Updated risk limit {key}: {value}")