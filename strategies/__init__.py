"""
Apex Trading System - Trading Strategies
=========================================
Signal generation modules
"""

from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger
import random

from models import TradingSignal, OrderSide


class BaseStrategy:
    """Base class for trading strategies."""
    
    def __init__(self, name: str):
        self.name = name
    
    async def generate_signals(self, data: List[Dict]) -> List[TradingSignal]:
        """Generate trading signals from market data."""
        raise NotImplementedError


class MovingAverageCross(BaseStrategy):
    """MA Crossover strategy."""
    
    def __init__(self, fast_period: int = 20, slow_period: int = 50):
        super().__init__("MA_Cross")
        self.fast_period = fast_period
        self.slow_period = slow_period
    
    async def generate_signals(self, data: List[Dict]) -> List[TradingSignal]:
        """Generate signals based on MA crossover."""
        if len(data) < self.slow_period:
            return []
        
        closes = [d["close"] for d in data]
        
        # Calculate moving averages
        fast_ma = sum(closes[-self.fast_period:]) / self.fast_period
        slow_ma = sum(closes[-self.slow_period:]) / self.slow_period
        
        # Previous MA for direction
        prev_fast = sum(closes[-(self.fast_period+1):-1]) / self.fast_period
        prev_slow = sum(closes[-(self.slow_period+1):-1]) / self.slow_period
        
        signals = []
        
        # Golden cross - BUY signal
        if prev_fast <= prev_slow and fast_ma > slow_ma:
            signals.append(TradingSignal(
                symbol=data[-1].get("symbol", "UNKNOWN"),
                side="BUY",
                strength=0.8,
                strategy=self.name,
                timestamp=datetime.now(),
                metadata={"fast_ma": fast_ma, "slow_ma": slow_ma}
            ))
        
        # Death cross - SELL signal
        elif prev_fast >= prev_slow and fast_ma < slow_ma:
            signals.append(TradingSignal(
                symbol=data[-1].get("symbol", "UNKNOWN"),
                side="SELL",
                strength=0.8,
                strategy=self.name,
                timestamp=datetime.now(),
                metadata={"fast_ma": fast_ma, "slow_ma": slow_ma}
            ))
        
        return signals


class RSIStrategy(BaseStrategy):
    """RSI Overbought/Oversold strategy."""
    
    def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70):
        super().__init__("RSI")
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
    
    async def generate_signals(self, data: List[Dict]) -> List[TradingSignal]:
        """Generate signals based on RSI levels."""
        if len(data) < self.period + 1:
            return []
        
        closes = [d["close"] for d in data]
        
        # Calculate RSI
        gains = []
        losses = []
        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            gains.append(max(change, 0))
            losses.append(max(-change, 0))
        
        avg_gain = sum(gains[-self.period:]) / self.period
        avg_loss = sum(losses[-self.period:]) / self.period
        
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        signals = []
        
        if rsi < self.oversold:
            signals.append(TradingSignal(
                symbol=data[-1].get("symbol", "UNKNOWN"),
                side="BUY",
                strength=(self.oversold - rsi) / self.oversold,
                strategy=self.name,
                timestamp=datetime.now(),
                metadata={"rsi": rsi}
            ))
        elif rsi > self.overbought:
            signals.append(TradingSignal(
                symbol=data[-1].get("symbol", "UNKNOWN"),
                side="SELL",
                strength=(rsi - self.overbought) / (100 - self.overbought),
                strategy=self.name,
                timestamp=datetime.now(),
                metadata={"rsi": rsi}
            ))
        
        return signals


class RandomStrategy(BaseStrategy):
    """Random strategy for paper trading testing."""
    
    def __init__(self):
        super().__init__("Random")
    
    async def generate_signals(self, data: List[Dict]) -> List[TradingSignal]:
        """Generate random signals for testing."""
        if not data:
            return []
        
        # Random signal occasionally
        if random.random() < 0.05:
            side = random.choice(["BUY", "SELL"])
            return [TradingSignal(
                symbol=data[-1].get("symbol", "NIFTY"),
                side=side,
                strength=random.uniform(0.5, 1.0),
                strategy=self.name,
                timestamp=datetime.now(),
                metadata={}
            )]
        
        return []


# Strategy registry
STRATEGIES = {
    "ma_cross": MovingAverageCross,
    "rsi": RSIStrategy,
    "random": RandomStrategy
}


def get_strategy(name: str, **kwargs) -> BaseStrategy:
    """Get strategy instance by name."""
    if name not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGIES.keys())}")
    return STRATEGIES[name](**kwargs)