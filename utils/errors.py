"""
Apex Trading System - Error Handling Module
=============================================
Custom exceptions and error handling utilities
"""

from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class TradingError(Exception):
    """Base exception for trading system."""
    
    def __init__(self, message: str, code: str = "TRADING_ERROR", details: Dict = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.timestamp = datetime.utcnow()


class ExchangeError(TradingError):
    """Exchange-specific errors."""
    
    def __init__(self, message: str, exchange: str = "unknown", **kwargs):
        super().__init__(message, code="EXCHANGE_ERROR", **kwargs)
        self.exchange = exchange


class APIError(TradingError):
    """API communication errors."""
    
    def __init__(self, message: str, status_code: int = None, **kwargs):
        super().__init__(message, code="API_ERROR", **kwargs)
        self.status_code = status_code


class AuthenticationError(TradingError):
    """Authentication/authorization errors."""
    
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, code="AUTH_ERROR", **kwargs)


class InsufficientFundsError(TradingError):
    """Insufficient capital for trade."""
    
    def __init__(self, required: float, available: float, **kwargs):
        message = f"Insufficient funds: required {required}, available {available}"
        super().__init__(message, code="INSUFFICIENT_FUNDS", **kwargs)
        self.required = required
        self.available = available


class RiskLimitError(TradingError):
    """Risk limit exceeded."""
    
    def __init__(self, limit_type: str, current: float, limit: float, **kwargs):
        message = f"Risk limit exceeded: {limit_type} - current {current}, limit {limit}"
        super().__init__(message, code="RISK_LIMIT", **kwargs)
        self.limit_type = limit_type
        self.current = current
        self.limit = limit


class OrderError(TradingError):
    """Order placement/rejection errors."""
    
    def __init__(self, message: str, order_id: str = None, **kwargs):
        super().__init__(message, code="ORDER_ERROR", **kwargs)
        self.order_id = order_id


class ValidationError(TradingError):
    """Input validation errors."""
    
    def __init__(self, message: str, field: str = None, **kwargs):
        super().__init__(message, code="VALIDATION_ERROR", **kwargs)
        self.field = field


class ErrorCode(Enum):
    """Standard error codes."""
    # Exchange errors
    EXCHANGE_UNAVAILABLE = "EXCHANGE_001"
    RATE_LIMIT_EXCEEDED = "EXCHANGE_002"
    MARKET_CLOSED = "EXCHANGE_003"
    
    # Order errors
    INVALID_SYMBOL = "ORDER_001"
    INVALID_QUANTITY = "ORDER_002"
    ORDER_REJECTED = "ORDER_003"
    
    # Risk errors
    DAILY_LOSS_LIMIT = "RISK_001"
    POSITION_SIZE_LIMIT = "RISK_002"
    CONCENTRATION_LIMIT = "RISK_003"


class ErrorHandler:
    """Centralized error handling."""
    
    @staticmethod
    def handle_api_error(error: Exception, context: Dict = None) -> Dict[str, Any]:
        """Handle API errors with retry logic."""
        from utils.logging import default_logger as logger
        
        error_type = type(error).__name__
        logger.error(f"API Error: {error_type} - {str(error)}")
        
        # Determine if retryable
        retryable = error_type in [
            "TimeoutError", 
            "ConnectionError",
            "HTTPError"
        ]
        
        return {
            "success": False,
            "error": str(error),
            "error_type": error_type,
            "retryable": retryable,
            "context": context or {}
        }
    
    @staticmethod
    def format_error_response(error: Exception) -> Dict[str, Any]:
        """Format error for API response."""
        if isinstance(error, TradingError):
            return {
                "success": False,
                "error": error.message,
                "code": error.code,
                "details": error.details,
                "timestamp": error.timestamp.isoformat()
            }
        
        return {
            "success": False,
            "error": str(error),
            "code": "UNKNOWN_ERROR",
            "timestamp": datetime.utcnow().isoformat()
        }


def retry_on_error(max_retries: int = 3, delay: float = 1.0):
    """Decorator for retry logic."""
    import functools
    from tenacity import retry, stop_after_attempt, wait_exponential
    
    return retry(
        stop=max_retries,
        wait=wait_exponential(multiplier=1, min=delay, max=10),
        reraise=True
    )