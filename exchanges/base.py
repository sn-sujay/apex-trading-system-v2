"""
Apex Trading System - Exchange Base Class
===========================================
Abstract base for all exchange adapters
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
from loguru import logger

from models import (
    OrderRequest, OrderResponse, OrderStatus,
    Position, AccountInfo, TradingSignal
)
from utils.errors import ExchangeError, AuthenticationError


class ExchangeBase(ABC):
    """Base class for all exchange adapters."""
    
    def __init__(self, name: str, paper_mode: bool = True):
        self.name = name
        self.paper_mode = paper_mode
        self.connected = False
        self._orders = {}  # order_id -> OrderResponse
        self._positions = {}  # symbol -> Position
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to exchange."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to exchange."""
        pass
    
    @abstractmethod
    async def get_balance(self) -> float:
        """Get account balance."""
        pass
    
    @abstractmethod
    async def get_market_price(self, symbol: str) -> float:
        """Get current market price for symbol."""
        pass
    
    @abstractmethod
    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """Place an order."""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> OrderResponse:
        """Get order status."""
        pass
    
    async def get_positions(self) -> List[Position]:
        """Get all open positions."""
        return list(self._positions.values())
    
    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol."""
        return self._positions.get(symbol)
    
    def _generate_order_id(self) -> str:
        """Generate unique order ID."""
        return f"{self.name}_{uuid.uuid4().hex[:8].upper()}"
    
    def _generate_position_id(self) -> str:
        """Generate unique position ID."""
        return f"POS_{uuid.uuid4().hex[:8].upper()}"
    
    async def health_check(self) -> Dict[str, Any]:
        """Check exchange health."""
        try:
            balance = await self.get_balance()
            return {
                "exchange": self.name,
                "status": "healthy" if self.connected else "disconnected",
                "balance": balance,
                "latency_ms": 0
            }
        except Exception as e:
            return {
                "exchange": self.name,
                "status": "unhealthy",
                "error": str(e)
            }


class PaperExchange(ExchangeBase):
    """Paper trading simulation exchange."""
    
    def __init__(self, name: str, initial_capital: float):
        super().__init__(name, paper_mode=True)
        self.initial_capital = initial_capital
        self.balance = initial_capital
        self.available_balance = initial_capital
        self.orders = {}
        self.positions = {}
        self.order_fills = {}
        self._slippage = 0.001  # 0.1% slippage
        self._commission = 0.001  # 0.1% commission
        
    async def connect(self) -> bool:
        """Simulate connection."""
        self.connected = True
        logger.info(f"[{self.name}] Paper exchange connected. Capital: {self.balance}")
        return True
    
    async def disconnect(self) -> None:
        """Simulate disconnection."""
        self.connected = False
        logger.info(f"[{self.name}] Paper exchange disconnected")
    
    async def get_balance(self) -> float:
        """Get paper balance."""
        return self.balance
    
    async def get_market_price(self, symbol: str) -> float:
        """Simulate market price (base price + random variation)."""
        import random
        # Base prices for common symbols
        base_prices = {
            "NIFTY": 23500,
            "BANKNIFTY": 50000,
            "RELIANCE": 3000,
            "BTCUSDT": 67000,
            "ETHUSDT": 3500,
            "SOLUSDT": 180
        }
        base = base_prices.get(symbol.upper(), 1000)
        # Add ±2% random variation
        variation = base * random.uniform(-0.02, 0.02)
        return base + variation
    
    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """Simulate order placement with slippage."""
        if not self.connected:
            raise ExchangeError("Exchange not connected", self.name)
        
        # Get current market price
        market_price = await self.get_market_price(order.symbol)
        
        # Apply slippage
        if order.side.value == "BUY":
            fill_price = market_price * (1 + self._slippage)
        else:
            fill_price = market_price * (1 - self._slippage)
        
        # Use limit price if specified and better
        if order.price and order.order_type.value == "LIMIT":
            if order.side.value == "BUY" and order.price < fill_price:
                fill_price = order.price
            elif order.side.value == "SELL" and order.price > fill_price:
                fill_price = order.price
        
        # Calculate fill value
        fill_value = fill_price * order.quantity
        commission = fill_value * self._commission
        
        # Check balance for BUY orders
        if order.side.value == "BUY" and fill_value + commission > self.available_balance:
            raise ExchangeError(
                f"Insufficient balance: need {fill_value + commission}, have {self.available_balance}",
                self.name
            )
        
        # Create order response
        order_id = self._generate_order_id()
        response = OrderResponse(
            order_id=order_id,
            symbol=order.symbol,
            quantity=order.quantity,
            filled_quantity=order.quantity,
            side=order.side,
            order_type=order.order_type,
            price=order.price,
            status=OrderStatus.FILLED,
            filled_price=fill_price,
            filled_at=datetime.utcnow(),
            tag=order.tag
        )
        
        # Deduct from balance for BUY
        if order.side.value == "BUY":
            self.available_balance -= (fill_value + commission)
        
        # Store order
        self.orders[order_id] = response
        self.order_fills[order_id] = {
            "fill_price": fill_price,
            "fill_quantity": order.quantity,
            "commission": commission
        }
        
        # Update position
        await self._update_position(response)
        
        logger.info(
            f"[{self.name}] ORDER FILLED: {order.side.value} {order.quantity} "
            f"{order.symbol} @ {fill_price:.2f}"
        )
        
        return response
    
    async def _update_position(self, order: OrderResponse) -> None:
        """Update position after order fill."""
        symbol = order.symbol
        
        if symbol not in self.positions:
            # Create new position
            from models import PositionSide
            side = PositionSide.LONG if order.side.value == "BUY" else PositionSide.SHORT
            
            position = Position(
                position_id=self._generate_position_id(),
                symbol=symbol,
                side=side,
                quantity=order.filled_quantity,
                entry_price=order.filled_price,
                current_price=order.filled_price,
                unrealized_pnl=0,
                exchange=self.name,
                opened_at=datetime.utcnow(),
                tag=order.tag
            )
            self.positions[symbol] = position
        else:
            # Update existing position
            pos = self.positions[symbol]
            
            if order.side.value == "BUY":
                # Average up
                total_cost = (pos.entry_price * pos.quantity) + (order.filled_price * order.filled_quantity)
                pos.quantity += order.filled_quantity
                pos.entry_price = total_cost / pos.quantity
            else:
                # Reduce or close
                pos.quantity -= order.filled_quantity
                if pos.quantity <= 0:
                    del self.positions[symbol]
                    return
            
            pos.current_price = order.filled_price
        
        # Update unrealized P&L
        await self._update_pnl()
    
    async def _update_pnl(self) -> None:
        """Update unrealized P&L for all positions."""
        for symbol, position in self.positions.items():
            current_price = await self.get_market_price(symbol)
            position.current_price = current_price
            
            if position.side.value == "LONG":
                position.unrealized_pnl = (current_price - position.entry_price) * position.quantity
            else:
                position.unrealized_pnl = (position.entry_price - current_price) * position.quantity
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order (simulated)."""
        if order_id in self.orders:
            order = self.orders[order_id]
            if order.status == OrderStatus.PENDING:
                order.status = OrderStatus.CANCELLED
                return True
        return False
    
    async def get_order_status(self, order_id: str) -> OrderResponse:
        """Get order status."""
        if order_id in self.orders:
            return self.orders[order_id]
        raise ExchangeError(f"Order not found: {order_id}", self.name)
    
    async def get_account_info(self) -> AccountInfo:
        """Get account info for paper trading."""
        await self._update_pnl()
        
        total_pnl = sum(p.unrealized_pnl for p in self.positions.values())
        
        return AccountInfo(
            exchange=self.name,
            balance=self.balance,
            available_balance=self.available_balance,
            unrealized_pnl=total_pnl,
            realized_pnl=0,
            total_pnl=total_pnl,
            position_count=len(self.positions),
            equity=self.balance + total_pnl
        )
    
    async def close_all_positions(self) -> List[OrderResponse]:
        """Close all open positions (for end of day)."""
        closed = []
        
        for symbol, position in list(self.positions.items()):
            from models import OrderRequest, OrderSide
            
            # Create closing order
            close_side = OrderSide.SELL if position.side.value == "LONG" else OrderSide.BUY
            
            order = OrderRequest(
                symbol=symbol,
                quantity=position.quantity,
                side=close_side,
                order_type=OrderType.MARKET,
                exchange=self.name,
                tag="auto_square_off"
            )
            
            try:
                response = await self.place_order(order)
                closed.append(response)
            except Exception as e:
                logger.error(f"Failed to close position {symbol}: {e}")
        
        return closed