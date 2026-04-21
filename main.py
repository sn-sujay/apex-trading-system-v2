"""
Apex Trading System - Main FastAPI Application
===============================================
REST API for trading operations
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from loguru import logger

from utils.config import Config
from utils.logging import setup_logging
from utils.errors import TradingError, ExchangeError
from models import OrderRequest, Position, AccountInfo, TradingSignal, OrderResponse
from exchanges.base import ExchangeBase
from exchanges.paper import PaperExchange
from exchanges.dhan import DhanExchange
from exchanges.binance import BinanceExchange
from risk import RiskManager, RiskLimits
from strategies import get_strategy


# Setup logging
setup_logging()
logger.info("Starting Apex Trading System...")

# Global state
app_state = {
    "exchange": None,
    "risk_manager": None,
    "config": None,
    "startup_time": None
}


def get_exchange() -> ExchangeBase:
    """Get or create exchange instance."""
    if app_state["exchange"] is None:
        config = Config
        
        if config.PAPER_MODE:
            app_state["exchange"] = PaperExchange(initial_capital=config.PAPER_INITIAL_CAPITAL)
            logger.info("Using Paper Trading Exchange")
        else:
            # Try to use real exchange based on config
            if config.DHAN_CLIENT_ID and config.DHAN_ACCESS_TOKEN:
                app_state["exchange"] = DhanExchange(
                    client_id=config.DHAN_CLIENT_ID,
                    access_token=config.DHAN_ACCESS_TOKEN
                )
                logger.info("Using Dhan Exchange")
            elif config.BINANCE_API_KEY:
                app_state["exchange"] = BinanceExchange(
                    api_key=config.BINANCE_API_KEY,
                    secret_key=config.BINANCE_SECRET_KEY
                )
                logger.info("Using Binance Exchange")
            else:
                # Fallback to paper
                logger.warning("No real credentials found, using paper trading")
                app_state["exchange"] = PaperExchange()
    
    return app_state["exchange"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Initializing Apex Trading System...")
    
    config = Config()
    app_state["config"] = config
    
    # Initialize exchange
    exchange = get_exchange()
    try:
        await exchange.connect()
    except Exception as e:
        logger.error(f"Exchange connection failed: {e}")
        # Fallback to paper
        app_state["exchange"] = PaperExchange(initial_capital=config.PAPER_INITIAL_CAPITAL)
        await app_state["exchange"].connect()
    
    # Initialize risk manager
    app_state["risk_manager"] = RiskManager(
        limits=RiskLimits(
            max_daily_loss=config.MAX_DAILY_LOSS,
            max_position_size=config.MAX_POSITION_SIZE,
            max_trades_per_day=config.MAX_TRADES_PER_DAY
        )
    )
    
    app_state["startup_time"] = datetime.now()
    logger.info("Apex Trading System initialized successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Apex Trading System...")
    if app_state["exchange"]:
        await app_state["exchange"].disconnect()


# Create FastAPI app
app = FastAPI(
    title="Apex Trading System",
    description="Production-ready algorithmic trading platform",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ Request/Response Models ============

class TradeRequest(BaseModel):
    """Natural language trade request."""
    command: str = Field(..., description="Trading command in natural language")
    # Alternative structured input
    symbol: Optional[str] = None
    side: Optional[str] = None
    quantity: Optional[int] = None
    price: Optional[float] = None
    order_type: str = "MARKET"


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    uptime_seconds: float
    mode: str
    exchange: str


class SignalResponse(BaseModel):
    """Trading signals response."""
    signals: list
    count: int
    timestamp: datetime


# ============ API Endpoints ============

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Apex Trading System",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    exchange = get_exchange()
    uptime = (datetime.now() -app_state["startup_time"]).total_seconds() if app_state["startup_time"] else 0
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        uptime_seconds=uptime,
        mode="paper" if Config.PAPER_MODE else "live",
        exchange=exchange.name
    )


@app.get("/status", response_model=AccountInfo)
async def get_account_status():
    """Get account information and balance."""
    try:
        exchange = get_exchange()
        account = await exchange.get_account_info()
        
        # Add risk manager stats
        risk_stats = app_state["risk_manager"].get_daily_stats()
        
        return account
    
    except Exception as e:
        logger.error(f"Error getting account status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/positions")
async def get_positions():
    """Get all open positions with P&L."""
    try:
        exchange = get_exchange()
        positions = await exchange.get_positions()
        
        return {
            "positions": [p.dict() for p in positions],
            "count": len(positions),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/trade")
async def place_trade(request: TradeRequest):
    """Place a trade order."""
    try:
        exchange = get_exchange()
        risk_manager = app_state["risk_manager"]
        
        # Parse order from request
        if request.command:
            # Natural language parsing
            order = await _parse_trade_command(request.command)
        else:
            # Structured input
            order = OrderRequest(
                symbol=request.symbol,
                side=request.side,
                order_type=request.order_type,
                quantity=request.quantity or 1,
                price=request.price or 0
            )
        
        if not order.symbol:
            raise HTTPException(status_code=400, detail="Symbol is required")
        
        # Get current price if market order
        if order.order_type == "MARKET" and order.price == 0:
            order.price = await exchange.get_current_price(order.symbol)
        
        # Validate with risk manager
        account = await exchange.get_account_info()
        is_valid, message = risk_manager.validate_order(order, account)
        
        if not is_valid:
            raise HTTPException(status_code=400, detail=message)
        
        # Place order
        result = await exchange.place_order(order)
        
        # Record for risk tracking (assume position opened)
        risk_manager.record_trade(0)  # PNL unknown at entry
        
        return {
            "status": "success",
            "order": result.dict(),
            "timestamp": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error placing trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _parse_trade_command(command: str) -> OrderRequest:
    """Parse natural language trading command."""
    command = command.upper()
    
    # Default values
    side = "BUY"
    quantity = 1
    symbol = "NIFTY"
    order_type = "MARKET"
    price = 0.0
    
    # Parse side
    if "SELL" in command:
        side = "SELL"
    if "BUY" in command:
        side = "BUY"
    
    # Parse quantity
    import re
    qty_match = re.search(r'(\d+)\s*(lot|lots|shares?|qty)?', command, re.IGNORECASE)
    if qty_match:
        qty = int(qty_match.group(1))
        if "lot" in qty_match.group(0).lower():
            qty *= 50  # Assume 1 lot = 50 for NIFTY
        quantity = qty
    
    # Parse symbol
    symbols = ["NIFTY", "BANKNIFTY", "RELIANCE", "INFY", "TCS", "BTC", "ETH"]
    for sym in symbols:
        if sym in command:
            symbol = sym
            break
    
    return OrderRequest(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price
    )


@app.get("/signals", response_model=SignalResponse)
async def get_signals(strategy: str = "ma_cross", symbol: str = "NIFTY"):
    """Generate trading signals."""
    try:
        exchange = get_exchange()
        
        # Get market data
        data = await exchange.get_historical_data(symbol, "1min", 100)
        
        if not data:
            return SignalResponse(
                signals=[],
                count=0,
                timestamp=datetime.now()
            )
        
        # Generate signals
        strat = get_strategy(strategy)
        signals = await strat.generate_signals(data)
        
        return SignalResponse(
            signals=[s.dict() for s in signals],
            count=len(signals),
            timestamp=datetime.now()
        )
    
    except Exception as e:
        logger.error(f"Error generating signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/squareoff")
async def square_off_all(background_tasks: BackgroundTasks):
    """Square off all positions."""
    try:
        exchange = get_exchange()
        
        if hasattr(exchange, 'square_off_all'):
            result = await exchange.square_off_all()
            return {
                "status": "success",
                "closed_positions": len(result),
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail="Square off not supported")
    
    except Exception as e:
        logger.error(f"Error squaring off: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/risk/stats")
async def get_risk_stats():
    """Get risk management statistics."""
    try:
        risk_manager = app_state["risk_manager"]
        stats = risk_manager.get_daily_stats()
        
        return {
            "risk_stats": stats,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting risk stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/risk/limits")
async def update_risk_limits(
    max_daily_loss: Optional[float] = None,
    max_position_size: Optional[float] = None,
    max_trades_per_day: Optional[int] = None
):
    """Update risk limits."""
    try:
        risk_manager = app_state["risk_manager"]
        
        updates = {}
        if max_daily_loss is not None:
            updates["max_daily_loss"] = max_daily_loss
        if max_position_size is not None:
            updates["max_position_size"] = max_position_size
        if max_trades_per_day is not None:
            updates["max_trades_per_day"] = max_trades_per_day
        
        risk_manager.update_limits(**updates)
        
        return {
            "status": "success",
            "limits": risk_manager.get_daily_stats(),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error updating limits: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)