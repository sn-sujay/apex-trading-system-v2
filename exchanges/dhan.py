"""
Apex Trading System - Dhan Exchange Adapter
=============================================
Indian stock options trading via Dhan API
"""

import os
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import httpx
from loguru import logger

from exchanges.base import ExchangeBase, PaperExchange
from models import OrderRequest, OrderResponse, OrderStatus, Position, AccountInfo
from utils.errors import ExchangeError, AuthenticationError, APIError
from utils.config import config


class DhanExchange(ExchangeBase):
    """Dhan trading API integration for Indian markets."""
    
    BASE_URL = "https://api.dhan.co/v2"
    
    def __init__(self, paper_mode: bool = None):
        # Use global paper mode if not specified
        if paper_mode is None:
            paper_mode = config.PAPER_MODE
            
        super().__init__("dhan", paper_mode)
        
        self.client_id = config.DHAN_CLIENT_ID
        self.client_secret = config.DHAN_CLIENT_SECRET
        self.access_token = config.DHAN_ACCESS_TOKEN
        self.initial_capital = config.INITIAL_CAPITAL_DHAN
        
        # Use paper exchange if no credentials or paper mode
        if not self.access_token or paper_mode:
            self._delegate = PaperExchange("dhan", self.initial_capital)
            logger.info("Dhan: Using paper trading (no credentials or paper mode)")
        else:
            self._delegate = None
    
    async def connect(self) -> bool:
        """Connect to Dhan API."""
        if self._delegate:
            return await self._delegate.connect()
        
        # Validate credentials
        if not all([self.client_id, self.client_secret, self.access_token]):
            raise AuthenticationError("Dhan credentials not configured")
        
        # Test API connection
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/market/token",
                    headers=self._get_headers(),
                    timeout=10
                )
                if response.status_code == 200:
                    self.connected = True
                    logger.info("Dhan: Connected successfully")
                    return True
                else:
                    raise APIError(f"Dhan API error: {response.status_code}")
        except Exception as e:
            logger.error(f"Dhan connection failed: {e}")
            # Fall back to paper
            self._delegate = PaperExchange("dhan", self.initial_capital)
            await self._delegate.connect()
            return True
    
    async def disconnect(self) -> None:
        """Disconnect from Dhan API."""
        if self._delegate:
            await self._delegate.disconnect()
        self.connected = False
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Dhan API."""
        return {
            "Access-Token": self.access_token,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    async def get_balance(self) -> float:
        """Get account balance."""
        if self._delegate:
            return await self._delegate.get_balance()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/portfolio/positions",
                    headers=self._get_headers(),
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Extract balance from response
                    return data.get("total_balance", 0)
                else:
                    raise APIError(f"Failed to get balance: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Dhan get_balance error: {e}")
            return 0
    
    async def get_market_price(self, symbol: str) -> float:
        """Get current market price."""
        if self._delegate:
            return await self._delegate.get_market_price(symbol)
        
        # Map common symbols to Dhan format
        symbol_map = {
            "NIFTY": "Nifty 50",
            "BANKNIFTY": "Nifty Bank",
            "RELIANCE": "RELIANCE-EQ"
        }
        
        dhan_symbol = symbol_map.get(symbol.upper(), symbol)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/market/quotes",
                    params={"symbol": dhan_symbol},
                    headers=self._get_headers(),
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("last_price", 0)
                else:
                    raise APIError(f"Failed to get price: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Dhan get_market_price error: {e}")
            return 0
    
    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """Place an order on Dhan."""
        if self._delegate:
            return await self._delegate.place_order(order)
        
        # Build order payload
        payload = {
            "exchange": "NSE",
            "symbol": order.symbol,
            "transaction_type": order.side.value,
            "quantity": int(order.quantity),
            "order_type": order.order_type.value,
            "product_type": "INTRADAY",
            "price": order.price or 0
        }
        
        if order.stop_loss:
            payload["stop_loss"] = order.stop_loss
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/orders",
                    json=payload,
                    headers=self._get_headers(),
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return OrderResponse(
                        order_id=data.get("order_id", "UNKNOWN"),
                        symbol=order.symbol,
                        quantity=order.quantity,
                        filled_quantity=data.get("filled_quantity", order.quantity),
                        side=order.side,
                        order_type=order.order_type,
                        price=order.price,
                        status=OrderStatus.FILLED,
                        filled_price=data.get("average_price", order.price),
                        exchange_order_id=data.get("order_id")
                    )
                else:
                    raise APIError(f"Order failed: {response.status_code} - {response.text}")
                    
        except Exception as e:
            logger.error(f"Dhan place_order error: {e}")
            # Fall back to paper
            if not self._delegate:
                self._delegate = PaperExchange("dhan", self.initial_capital)
                await self._delegate.connect()
            return await self._delegate.place_order(order)
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        if self._delegate:
            return await self._delegate.cancel_order(order_id)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.BASE_URL}/orders/{order_id}",
                    headers=self._get_headers(),
                    timeout=10
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Dhan cancel_order error: {e}")
            return False
    
    async def get_order_status(self, order_id: str) -> OrderResponse:
        """Get order status."""
        if self._delegate:
            return await self._delegate.get_order_status(order_id)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/orders/{order_id}",
                    headers=self._get_headers(),
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return OrderResponse(
                        order_id=order_id,
                        symbol=data.get("symbol"),
                        quantity=data.get("quantity"),
                        filled_quantity=data.get("filled_quantity"),
                        side=OrderSide(data.get("transaction_type")),
                        order_type=OrderType(data.get("order_type")),
                        price=data.get("price"),
                        status=OrderStatus(data.get("status")),
                        filled_price=data.get("average_price")
                    )
                else:
                    raise APIError(f"Order not found: {order_id}")
        except Exception as e:
            logger.error(f"Dhan get_order_status error: {e}")
            raise
    
    async def get_positions(self) -> list:
        """Get all positions."""
        if self._delegate:
            return await self._delegate.get_positions()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/portfolio/positions",
                    headers=self._get_headers(),
                    timeout=10
                )
                
                if response.status_code == 200:
                    positions = []
                    for p in response.json():
                        positions.append(Position(
                            position_id=p.get("position_id"),
                            symbol=p.get("symbol"),
                            side=Position.LONG if p.get("quantity", 0) > 0 else Position.SHORT,
                            quantity=abs(p.get("quantity", 0)),
                            entry_price=p.get("average_price"),
                            current_price=p.get("last_price", p.get("average_price")),
                            unrealized_pnl=p.get("unrealized_pnl", 0),
                            exchange="dhan"
                        ))
                    return positions
                return []
        except Exception as e:
            logger.error(f"Dhan get_positions error: {e}")
            return []
    
    async def get_account_info(self) -> AccountInfo:
        """Get account information."""
        if self._delegate:
            return await self._delegate.get_account_info()
        
        try:
            balance = await self.get_balance()
            positions = await self.get_positions()
            
            unrealized = sum(p.unrealized_pnl for p in positions)
            
            return AccountInfo(
                exchange="dhan",
                balance=balance,
                available_balance=balance - sum(p.entry_price * p.quantity for p in positions),
                unrealized_pnl=unrealized,
                realized_pnl=0,
                total_pnl=unrealized,
                position_count=len(positions),
                equity=balance + unrealized
            )
        except Exception as e:
            logger.error(f"Dhan get_account_info error: {e}")
            return AccountInfo(
                exchange="dhan",
                balance=0,
                available_balance=0,
                position_count=0
            )


# For backward compatibility
from models import Position as PosEnum
Position = PosEnum