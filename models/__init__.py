"""
Apex Trading System - Data Models
==================================
Pydantic models for type safety across the system
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class OrderType(str, Enum):
    """Order types."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    STOP_LIMIT = "STOP_LIMIT"


class OrderSide(str, Enum):
    """Order sides."""
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    """Order statuses."""
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class PositionSide(str, Enum):
    """Position sides."""
    LONG = "LONG"
    SHORT = "SHORT"


# ===================
# Order Models
# ===================

class OrderRequest(BaseModel):
    """Order placement request."""
    symbol: str = Field(..., description="Trading symbol, e.g., NIFTY or BTCUSDT")
    quantity: float = Field(..., gt=0, description="Order quantity")
    side: OrderSide = Field(..., description="BUY or SELL")
    order_type: OrderType = Field(default=OrderType.MARKET, description="Order type")
    price: Optional[float] = Field(None, description="Limit price (for LIMIT orders)")
    stop_loss: Optional[float] = Field(None, description="Stop loss price")
    take_profit: Optional[float] = Field(None, description="Take profit price")
    exchange: str = Field(default="dhan", description="Exchange: dhan, binance, forex")
    tag: Optional[str] = Field(None, description="User-defined tag for tracking")


class OrderResponse(BaseModel):
    """Order response from exchange."""
    order_id: str
    symbol: str
    quantity: float
    filled_quantity: float = 0
    side: OrderSide
    order_type: OrderType
    price: Optional[float]
    status: OrderStatus = OrderStatus.PENDING
    filled_price: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    filled_at: Optional[datetime] = None
    exchange_order_id: Optional[str] = None
    tag: Optional[str] = None


class FillInfo(BaseModel):
    """Order fill information."""
    order_id: str
    fill_price: float
    fill_quantity: float
    fill_value: float
    commission: float = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ===================
# Position Models
# ===================

class Position(BaseModel):
    """Trading position."""
    position_id: str
    symbol: str
    side: PositionSide
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float = 0
    realized_pnl: float = 0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    exchange: str
    opened_at: datetime = Field(default_factory=datetime.utcnow)
    tag: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "position_id": self.position_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "pnl_percent": round((self.unrealized_pnl / (self.entry_price * self.quantity)) * 100, 2),
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "exchange": self.exchange,
            "opened_at": self.opened_at.isoformat()
        }


class PositionSummary(BaseModel):
    """Summary of all positions."""
    positions: List[Position] = []
    total_unrealized_pnl: float = 0
    total_realized_pnl: float = 0
    total_value: float = 0
    position_count: int = 0


# ===================
# Account Models
# ===================

class AccountInfo(BaseModel):
    """Account information."""
    exchange: str
    balance: float
    available_balance: float
    unrealized_pnl: float = 0
    realized_pnl: float = 0
    total_pnl: float = 0
    position_count: int = 0
    equity: float = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "exchange": self.exchange,
            "balance": round(self.balance, 2),
            "available_balance": round(self.available_balance, 2),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "total_pnl": round(self.total_pnl, 2),
            "equity": round(self.equity, 2),
            "position_count": self.position_count
        }


# ===================
# Signal Models
# ===================

class TradingSignal(BaseModel):
    """Trading signal."""
    signal_id: str
    symbol: str
    signal_type: str  # BUY, SELL, CLOSE
    confidence: float = Field(ge=0, le=1)
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    timeframe: str = "1D"
    strategy: str = "manual"
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "symbol": self.symbol,
            "signal_type": self.signal_type,
            "confidence": round(self.confidence, 2),
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "timeframe": self.timeframe,
            "strategy": self.strategy,
            "generated_at": self.generenerated_at.isoformat()
        }


# ===================
# Health Check
# ===================

class HealthStatus(BaseModel):
    """System health status."""
    status: str  # healthy, degraded, unhealthy
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: Dict[str, bool] = {}
    exchange_status: Dict[str, str] = {}  # exchange -> status
    paper_mode: bool = True
    uptime_seconds: float = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "timestamp": self.timestamp.isoformat(),
            "services": self.services,
            "exchange_status": self.exchange_status,
            "paper_mode": self.paper_mode,
            "uptime_seconds": round(self.uptime_seconds, 2)
        }