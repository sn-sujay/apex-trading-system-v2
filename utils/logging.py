"""
Apex Trading System - Logging Module
=====================================
Centralized logging with structured output
"""

import sys
import logging
from pathlib import Path
from loguru import logger
from datetime import datetime


def setup_logging(name: str = "apex-trading", log_dir: str = "logs") -> None:
    """Setup logging for the trading system."""
    
    # Remove default handler
    logger.remove()
    
    # Create logs directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Console handler with colors
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True
    )
    
    # File handler - daily rotation
    logger.add(
        log_path / f"{name}_{{time:YYYY-MM-DD}}.log",
        rotation="00:00",  # New file at midnight
        retention="30 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG"
    )
    
    # Error file - only errors
    logger.add(
        log_path / "errors.log",
        rotation="10 MB",
        retention="90 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}",
        level="ERROR",
        filter=lambda record: record["level"].name == "ERROR"
    )
    
    return logger


class TradeLogger:
    """Specialized logger for trade operations."""
    
    def __init__(self, exchange: str = "GENERAL"):
        self.exchange = exchange
        self.logger = logger.bind(exchange=exchange)
    
    def log_order(self, order_type: str, symbol: str, quantity: float, 
                  price: float, status: str = "PENDING") -> None:
        """Log order placement."""
        self.logger.info(
            f"ORDER | {order_type} | {symbol} | Qty: {quantity} | "
            f"Price: {price} | Status: {status}"
        )
    
    def log_fill(self, order_id: str, fill_price: float, quantity: float) -> None:
        """Log order fill."""
        self.logger.info(
            f"FILL | Order: {order_id} | Fill Price: {fill_price} | "
            f"Qty: {quantity}"
        )
    
    def log_pnl(self, realized_pnl: float, unrealized_pnl: float) -> None:
        """Log P&L update."""
        self.logger.info(
            f"P&L | Realized: {realized_pnl:.2f} | Unrealized: {unrealized_pnl:.2f}"
        )
    
    def log_error(self, operation: str, error: Exception) -> None:
        """Log error with context."""
        self.logger.error(
            f"ERROR in {operation}: {type(error).__name__}: {str(error)}"
        )
    
    def log_signal(self, signal_type: str, symbol: str, confidence: float,
                   entry: float = None, stop_loss: float = None) -> None:
        """Log trading signal."""
        self.logger.info(
            f"SIGNAL | {signal_type} | {symbol} | Confidence: {confidence:.1%} | "
            f"Entry: {entry} | SL:{stop_loss}"
        )


# Default logger instance
default_logger = logger