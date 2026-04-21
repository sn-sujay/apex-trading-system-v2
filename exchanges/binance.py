"""
Apex Trading System - Binance Exchange Adapter
===============================================
Cryptocurrency trading via Binance API
"""

import os
import hmac
import hashlib
import time
from typing import Dict, Any, Optional
import httpx
from loguru import logger

from exchanges.base import ExchangeBase, PaperExchange
from models import OrderRequest, OrderResponse, OrderStatus, Position, AccountInfo
from utils.errors import ExchangeError, AuthenticationError, APIError
from utils.config import config


class BinanceExchange(ExchangeBase):
    """Binance API integration for crypto trading."""
    
    BASE_URL = "https://api.binance.com"
    
    def __init__(self, paper_mode: bool = None):
        if paper_mode is None:
            paper_mode = config.PAPER_MODE
            
        super().__init__("binance", paper_mode)
        
        self.api_key = config.BINANCE_API_KEY
        self.secret_key = config.BINANCE_SECRET_KEY
        self.initial_capital = config.INITIAL_CAPITAL_BINANCE
        
        # Use paper exchange if no credentials or paper mode
        if not self.api_key or paper_mode:
            self._delegate = PaperExchange("binance", self.initial_capital)
            logger.info("Binance: Using paper trading (no credentials or paper mode)")
        else:
            self._delegate = None
    
    async def connect(self) -> bool:
        """Connect to Binance API."""
        if self._delegate:
            return await self._delegate.connect()
        
        if not all([self.api_key, self.secret_key]):
            raise AuthenticationError("Binance credentials not configured")
        
        # Test connection
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.BASE_URL}/api/v3/ping", timeout=10)
                if response.status_code == 200:
                    self.connected = True
                    logger.info("Binance: Connected successfully")
                    return True
        except Exception as e:
            logger.error(f"Binance connection failed: {e}")
            self._delegate = PaperExchange("binance", self.initial_capital)
            await self._delegate.connect()
            return True
    
    async def disconnect(self) -> None:
        """Disconnect from Binance."""
        if self._delegate:
            await self._delegate.disconnect()
        self.connected = False
    
    def _sign(self, params: Dict) -> str:
        """Generate HMAC signature for Binance."""
        query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Binance API."""
        return {
            "X-MBX-APIKEY": self.api_key,
            "Content-Type": "application/json"
        }
    
    async def get_balance(self) -> float:
        """Get account balance (USDT)."""
        if self._delegate:
            return await self._delegate.get_balance()
        
        try:
            timestamp = int(time.time() * 1000)
            params = {"timestamp": timestamp}
            params["signature"] = self._sign(params)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/api/v3/account",
                    params=params,
                    headers=self._get_headers(),
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Find USDT balance
                    for balance in data.get("balances", []):
                        if balance.get("asset") == "USDT":
                            return float(balance.get("free", 0))
                return 0
        except Exception as e:
            logger.error(f"Binance get_balance error: {e}")
            return 0
    
    async def get_market_price(self, symbol: str) -> float:
        """Get current market price."""
        if self._delegate:
            return await self._delegate.get_market_price(symbol)
        
        try:
            # Normalize symbol (BTCUSDT -> BTCUSDT)
            symbol = symbol.upper().replace("-", "")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/api/v3/ticker/price",
                    params={"symbol": symbol},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return float(data.get("price", 0))
                return 0
        except Exception as e:
            logger.error(f"Binance get_market_price error: {e}")
            return 0
    
    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """Place an order on Binance."""
        if self._delegate:
            return await self._delegate.place_order(order)
        
        # Build order payload
        timestamp = int(time.time() * 1000)
        symbol = order.symbol.upper().replace("-", "")
        
        params = {
            "symbol": symbol,
            "side": order.side.value,
            "quantity": order.quantity,
            "timestamp": timestamp
        }
        
        # Set order type
        if order.order_type.value == "MARKET":
            params["type"] = "MARKET"
        elif order.order_type.value == "LIMIT":
            params["type"] = "LIMIT"
            params["price"] = order.price
            params["timeInForce"] = "GTC"
        else:
            params["type"] = order.order_type.value
        
        params["signature"] = self._sign(params)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/api/v3/order",
                    json=params,
                    headers=self._get_headers(),
                    timeout=10
                )
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    return OrderResponse(
                        order_id=data.get("orderId", "UNKNOWN"),
                        symbol=order.symbol,
                        quantity=order.quantity,
                        filled_quantity=float(data.get("executedQty", 0)),
                        side=order.side,
                        order_type=OrderType(data.get("type", "MARKET")),
                        price=order.price,
                        status=OrderStatus.FILLED if data.get("status") == "FILLED" else OrderStatus.PENDING,
                        filled_price=float(data.get("price", 0) or order.price or 0),
                        exchange_order_id=str(data.get("orderId"))
                    )
                else:
                    raise APIError(f"Order failed: {response.status_code} - {response.text}")
                    
        except Exception as e:
            logger.error(f"Binance place_order error: {e}")
            if not self._delegate:
                self._delegate = PaperExchange("binance", self.initial_capital)
                await self._delegate.connect()
            return await self._delegate.place_order(order)
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        if self._delegate:
            return await self._delegate.cancel_order(order_id)
        
        try:
            timestamp = int(time.time() * 1000)
            params = {"orderId": order_id, "timestamp": timestamp}
            params["signature"] = self._sign(params)
            
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.BASE_URL}/api/v3/order",
                    params=params,
                    headers=self._get_headers(),
                    timeout=10
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Binance cancel_order error: {e}")
            return False
    
    async def get_order_status(self, order_id: str) -> OrderResponse:
        """Get order status."""
        if self._delegate:
            return await self._delegate.get_order_status(order_id)
        
        try:
            timestamp = int(time.time() * 1000)
            params = {"orderId": order_id, "timestamp": timestamp}
            params["signature"] = self._sign(params)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/api/v3/order",
                    params=params,
                    headers=self._get_headers(),
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return OrderResponse(
                        order_id=str(data.get("orderId")),
                        symbol=data.get("symbol"),
                        quantity=float(data.get("quantity")),
                        filled_quantity=float(data.get("executedQty")),
                        side=OrderSide(data.get("side")),
                        order_type=OrderType(data.get("type")),
                        price=float(data.get("price", 0)),
                        status=OrderStatus(data.get("status")),
                        filled_price=float(data.get("price") or 0)
                    )
                raise ExchangeError(f"Order not found: {order_id}")
        except Exception as e:
            logger.error(f"Binance get_order_status error: {e}")
            raise
    
    async def get_positions(self) -> list:
        """Get all positions (open orders)."""
        if self._delegate:
            return await self._delegate.get_positions()
        
        # For Binance, positions are tracked via open orders
        return []
    
    async def get_account_info(self) -> AccountInfo:
        """Get account information."""
        if self._delegate:
            return await self._delegate.get_account_info()
        
        try:
            balance = await self.get_balance()
            
            return AccountInfo(
                exchange="binance",
                balance=balance,
                available_balance=balance,  # Simplified
                unrealized_pnl=0,
                realized_pnl=0,
                total_pnl=0,
                position_count=0,
                equity=balance
            )
        except Exception as e:
            logger.error(f"Binance get_account_info error: {e}")
            return AccountInfo(
                exchange="binance",
                balance=0,
                available_balance=0
            )


from models import Position as PosEnum
Position = PosEnum