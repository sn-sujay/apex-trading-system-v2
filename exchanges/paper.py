"""
Apex Trading System - Paper Trading Engine
===========================================
Simulates order execution with realistic fills
"""

import asyncio
from typing import Dict, Optional, List
from datetime import datetime, time
from loguru import logger
import random

from models import (
    OrderRequest, OrderResponse, OrderStatus, OrderSide,
    Position, AccountInfo, TradingSignal
)
from utils.config import Config


class PaperExchange(ExchangeBase):
    """Paper trading simulator with realistic fills."""
    
    def __init__(self, initial_capital: float = 100000.0):
        super().__init__("PAPER")
        self.initial_capital = initial_capital
        self._balance = initial_capital
        self._positions: Dict[str, Position] = {}
        self._orders: Dict[str, OrderResponse] = {}
        self._order_id = 1
        self._slippage_pct = 0.001  # 0.1% slippage
        self._market_open = time(9, 15)
        self._market_close = time(15, 30)
        
    @property
    def name(self) -> str:
        return "PAPER"
    
    async def connect(self) -> bool:
        logger.info(f"Paper trading initialized with capital: ₹{self._balance:,.2f}")
        self._connected = True
        return True
    
    async def disconnect(self) -> None:
        self._connected = False
        logger.info("Paper trading session ended")
    
    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """Simulate order placement with slippage."""
        if not self._connected:
            raise ExchangeError("Not connected to paper exchange")
        
        order_id = f"PAPER_{self._order_id}"
        self._order_id += 1
        
        # Apply slippage for market orders
        fill_price = order.price
        if order.order_type == "MARKET":
            slippage = random.uniform(-self._slippage_pct, self._slippage_pct)
            fill_price *= (1 + slippage)
        
        # Calculate quantity and value
        quantity = order.quantity
        order_value = fill_price * quantity
        
        # Check balance for buys
        if order.side == "BUY":
            if order_value > self._balance:
                raise ExchangeError(f"Insufficient balance: ₹{self._balance:,.2f}")
            self._balance -= order_value
        else:  # SELL
            # Check position exists
            symbol = order.symbol
            if symbol not in self._positions:
                raise ExchangeError(f"No position to sell: {symbol}")
            pos = self._positions[symbol]
            if pos.quantity < quantity:
                raise ExchangeError(f"Insufficient quantity: {pos.quantity}")
        
        # Create response
        response = OrderResponse(
            order_id=order_id,
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            quantity=quantity,
            price=fill_price,
            status="FILLED",
            filled_quantity=quantity,
            average_price=fill_price,
            timestamp=datetime.now()
        )
        
        self._orders[order_id] = response
        
        # Update positions
        await self._update_position(order, fill_price)
        
        logger.info(f"Paper order filled: {order.side} {quantity} {order.symbol} @ ₹{fill_price:.2f}")
        return response
    
    async def _update_position(self, order: OrderRequest, fill_price: float) -> None:
        """Update position after trade."""
        symbol = order.symbol
        
        if order.side == "BUY":
            if symbol in self._positions:
                pos = self._positions[symbol]
                total_qty = pos.quantity + order.quantity
                avg_price = ((pos.quantity * pos.average_price) + 
                            (order.quantity * fill_price)) / total_qty
                pos.quantity = total_qty
                pos.average_price = avg_price
                pos.entry_time = datetime.now()
            else:
                self._positions[symbol] = Position(
                    symbol=symbol,
                    side="LONG",
                    quantity=order.quantity,
                    average_price=fill_price,
                    current_price=fill_price,
                    entry_time=datetime.now(),
                    unrealized_pnl=0.0,
                    realized_pnl=0.0
                )
        else:  # SELL
            if symbol in self._positions:
                pos = self._positions[symbol]
                pnl = (fill_price - pos.average_price) * order.quantity
                pos.realized_pnl += pnl
                pos.quantity -= order.quantity
                
                if pos.quantity <= 0:
                    del self._positions[symbol]
    
    async def get_positions(self) -> List[Position]:
        """Get all open positions."""
        # Update current prices and P&L
        for symbol, pos in self._positions.items():
            pos.unrealized_pnl = (pos.current_price - pos.average_price) * pos.quantity
        return list(self._positions.values())
    
    async def get_account_info(self) -> AccountInfo:
        """Get account information."""
        positions = await self.get_positions()
        total_unrealized = sum(p.unrealized_pnl for p in positions)
        total_realized = sum(p.realized_pnl for p in positions)
        
        return AccountInfo(
            account_id="PAPER_001",
            balance=self._balance,
            available_balance=self._balance,
            unrealized_pnl=total_unrealized,
            realized_pnl=total_realized,
            total_pnl=total_unrealized + total_realized,
            margin_used=0.0,
            timestamp=datetime.now()
        )
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        if order_id in self._orders:
            order = self._orders[order_id]
            if order.status == "FILLED":
                raise ExchangeError("Cannot cancel filled order")
            order.status = "CANCELLED"
            return True
        return False
    
    async def get_order_status(self, order_id: str) -> Optional[OrderResponse]:
        """Get order status."""
        return self._orders.get(order_id)
    
    async def get_historical_data(self, symbol: str, interval: str, 
                                  limit: int = 100) -> List[Dict]:
        """Generate mock historical data."""
        import random
        data = []
        base_price = 100.0
        
        for i in range(limit):
            timestamp = datetime.now().timestamp() - (limit - i) * 60
            open_price = base_price + random.uniform(-2, 2)
            close_price = open_price + random.uniform(-1, 1)
            high_price = max(open_price, close_price) + random.uniform(0, 1)
            low_price = min(open_price, close_price) - random.uniform(0, 1)
            
            data.append({
                "timestamp": timestamp,
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "volume": random.randint(1000, 10000)
            })
            base_price = close_price
        
        return data
    
    async def get_current_price(self, symbol: str) -> float:
        """Get current price (mock)."""
        return 100.0 + random.uniform(-5, 5)
    
    async def square_off_all(self) -> List[OrderResponse]:
        """Square off all positions at market close."""
        closed = []
        for symbol, pos in list(self._positions.items()):
            order = OrderRequest(
                symbol=symbol,
                side="SELL" if pos.side == "LONG" else "BUY",
                order_type="MARKET",
                quantity=pos.quantity,
                price=pos.current_price
            )
            try:
                result = await self.place_order(order)
                closed.append(result)
                logger.info(f"Squared off position: {symbol}")
            except Exception as e:
                logger.error(f"Error squaring off {symbol}: {e}")
        
        return closed