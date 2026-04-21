"""
Apex Trading System - Configuration Module
=============================================
Central configuration management with validation
"""

import os
from pathlib import Path
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load .env file
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")


class Config:
    """Central configuration for the trading system."""
    
    # Trading Mode
    PAPER_MODE = os.getenv("PAPER_MODE", "true").lower() == "true"
    
    # Dhan (Indian Options)
    DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID", "")
    DHAN_CLIENT_SECRET = os.getenv("DHAN_CLIENT_SECRET", "")
    DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN", "")
    
    # Binance (Crypto)
    BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
    BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY", "")
    
    # Alpha Vantage (Market Data)
    ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")
    
    # Capital Settings
    INITIAL_CAPITAL_DHAN = float(os.getenv("INITIAL_CAPITAL_DHAN", "1000000"))
    INITIAL_CAPITAL_BINANCE = float(os.getenv("INITIAL_CAPITAL_BINANCE", "10000"))
    INITIAL_CAPITAL_FOREX = float(os.getenv("INITIAL_CAPITAL_FOREX", "10000"))
    
    # Risk Management
    MAX_DAILY_LOSS_PERCENT = float(os.getenv("MAX_DAILY_LOSS_PERCENT", "5"))
    MAX_PER_TRADE_RISK_PERCENT = float(os.getenv("MAX_PER_TRADE_RISK_PERCENT", "2"))
    MAX_POSITIONS = int(os.getenv("MAX_POSITIONS", "5"))
    
    # Server
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Exchanges
    SUPPORTED_EXCHANGES = ["dhan", "binance", "forex"]
    
    # Trading Hours (IST)
    MARKET_OPEN_TIME = "09:15"
    MARKET_CLOSE_TIME = "15:30"
    

# Global config instance
config = Config()


def check_config() -> Dict[str, Any]:
    """Validate configuration and return status."""
    issues = []
    warnings = []
    
    # Check Dhan credentials
    if not config.DHAN_CLIENT_ID or not config.DHAN_ACCESS_TOKEN:
        warnings.append("Dhan credentials not configured - Indian options disabled")
    
    # Check Binance credentials
    if not config.BINANCE_API_KEY or not config.BINANCE_SECRET_KEY:
        warnings.append("Binance credentials not configured - Crypto disabled")
    
    # Check Alpha Vantage
    if not config.ALPHA_VANTAGE_API_KEY:
        warnings.append("Alpha Vantage not configured - Market data limited")
    
    # Risk checks
    if config.MAX_DAILY_LOSS_PERCENT > 10:
        issues.append("MAX_DAILY_LOSS_PERCENT > 10% is dangerous")
    
    if config.MAX_PER_TRADE_RISK_PERCENT > 5:
        issues.append("MAX_PER_TRADE_RISK_PERCENT > 5% is dangerous")
    
    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "paper_mode": config.PAPER_MODE
    }