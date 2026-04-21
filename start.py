#!/usr/bin/env python3
"""
Apex Trading System - Main Entry Point
=======================================
Production-ready algorithmic trading platform

Usage:
    python start.py              # Start server
    python start.py --help       # Show options

Author: Apex Trading Systems
"""

import sys
import os
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from loguru import logger
from uvicorn import run

# Load environment variables
load_dotenv()


def setup_logging():
    """Configure logging for the trading system."""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    
    # Remove default logger
    logger.remove()
    
    # Console output with colors
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True
    )
    
    # File rotation - 10MB max, keep 5 files
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    
    logger.add(
        log_dir / "trading_{time:YYYY-MM-DD}.log",
        rotation="10 MB",
        retention="7 days",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )
    
    return logger


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Apex Trading System - Production Trading Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start.py                    # Start server on default port 8000
  python start.py --host 127.0.0.1  # Bind to localhost
  python start.py --port 9000        # Custom port
  python start.py --reload           # Auto-reload on code changes (dev)
        """
    )
    
    parser.add_argument(
        "--host", 
        default=os.getenv("HOST", "0.0.0.0"),
        help="Server host (default: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port", 
        type=int,
        default=int(os.getenv("PORT", "8000")),
        help="Server port (default: 8000)"
    )
    
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1)"
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    # Setup logging
    setup_logger = logger
    logger.info("=" * 60)
    logger.info("APEX TRADING SYSTEM - Starting")
    logger.info("=" * 60)
    
    # Parse arguments
    args = parse_args()
    
    # Check configuration
    from utils.config import check_config
    config_status = check_config()
    
    if not config_status["is_valid"]:
        logger.warning("Configuration issues detected:")
        for issue in config_status["issues"]:
            logger.warning(f"  - {issue}")
        logger.warning("Running in limited mode...")
    
    # Show status
    paper_mode = os.getenv("PAPER_MODE", "true").lower() == "true"
    logger.info(f"Trading Mode: {'PAPER (Simulation)' if paper_mode else 'LIVE'}")
    
    if paper_mode:
        logger.info("⚠️  PAPER TRADING - No real money at risk")
    else:
        logger.critical("⚠️  LIVE TRADING - Real money at risk!")
    
    # Import and start server
    from main import app
    
    logger.info(f"Starting server on {args.host}:{args.port}")
    logger.info("API Docs available at: http://localhost:8000/docs")
    logger.info("=" * 60)
    
    try:
        run(
            app,
            host=args.host,
            port=args.port,
            reload=args.reload,
            workers=args.workers if not args.reload else 1,
            log_level=os.getenv("LOG_LEVEL", "info").lower()
        )
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()