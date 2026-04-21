# Apex Trading System 🚀

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green)
![License](https://img.shields.io/badge/License-MIT-orange)

Production-ready algorithmic trading platform with multi-exchange support, paper trading, and risk management.

## ✨ Features

- **Multi-Exchange Support**: Dhan (India), Binance (Crypto), Paper Trading
- **FastAPI Server**: RESTful API for all trading operations
- **Natural Language Trading**: Place orders like "buy 1 lot NIFTY"
- **Paper Trading Engine**: Full simulation with slippage and P&L tracking
- **Risk Management**: Daily loss limits, position sizing, trade limits
- **Trading Strategies**: MA Crossover, RSI, and more
- **Error Handling**: Retry logic, comprehensive logging, health checks

## ⚡ Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/your-repo/apex-trading-system.git
cd apex-trading-system

# 2. Copy environment template
cp .env.example .env

# 3. Edit .env with your credentials (see Configuration below)

# 4. Install dependencies
pip install -r requirements.txt

# 5. Start the server
python start.py
```

That's it! The API server runs at `http://localhost:8000`

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/status` | GET | Account balance & info |
| `/positions` | GET | Open positions with P&L |
| `/trade` | POST | Place order |
| `/signals` | GET | Generate trading signals |
| `/squareoff` | POST | Close all positions |
| `/risk/stats` | GET | Risk management stats |

## 📝 API Examples

### Health Check
```bash
curl http://localhost:8000/health
```

### Get Account Status
```bash
curl http://localhost:8000/status
```

### Place a Trade (Natural Language)
```bash
curl -X POST http://localhost:8000/trade \
  -H "Content-Type: application/json" \
  -d '{"command": "buy 1 lot NIFTY"}'
```

### Place a Trade (Structured)
```bash
curl -X POST http://localhost:8000/trade \
  -H "Content-Type: application/json" \
  -d '{"symbol": "NIFTY", "side": "BUY", "quantity": 50, "price": 23500}'
```

### Get Trading Signals
```bash
curl "http://localhost:8000/signals?strategy=ma_cross&symbol=NIFTY"
```

### Square Off All Positions
```bash
curl -X POST http://localhost:8000/squareoff
```

## ⚙️ Configuration

Edit the `.env` file with your credentials:

```env
# =================
# TRADING MODE
# =================
PAPER_MODE=true

# =================
# DHAN (Indian Stock Options)
# =================
DHAN_CLIENT_ID=your_client_id
DHAN_CLIENT_SECRET=your_client_secret
DHAN_ACCESS_TOKEN=your_access_token

# =================
# BINANCE (Cryptocurrency)
# =================
BINANCE_API_KEY=your_api_key
BINANCE_SECRET_KEY=your_secret_key

# =================
# TRADING PARAMETERS
# =================
PAPER_INITIAL_CAPITAL=100000
MAX_DAILY_LOSS=10000
MAX_POSITION_SIZE=50000
MAX_TRADES_PER_DAY=10
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PAPER_MODE` | Enable paper trading | `true` |
| `DHAN_CLIENT_ID` | Dhan API client ID | - |
| `DHAN_CLIENT_SECRET` | Dhan API secret | - |
| `DHAN_ACCESS_TOKEN` | Dhan access token | - |
| `BINANCE_API_KEY` | Binance API key | - |
| `BINANCE_SECRET_KEY` | Binance secret | - |
| `PAPER_INITIAL_CAPITAL` | Paper trading capital | `100000` |
| `MAX_DAILY_LOSS` | Max daily loss limit | `10000` |
| `MAX_POSITION_SIZE` | Max position value | `50000` |
| `MAX_TRADES_PER_DAY` | Max daily trades | `10` |

## 🏗️ Architecture

```
apex-trading-system/
├── main.py              # FastAPI application
├── start.py             # Entry point
├── requirements.txt     # Dependencies
├── .env.example         # Environment template
├── models/              # Pydantic data models
│   └── __init__.py
├── exchanges/           # Exchange adapters
│   ├── base.py         # Abstract base class
│   ├── dhan.py        # Dhan exchange
│   ├── binance.py     # Binance exchange
│   └── paper.py       # Paper trading engine
├── strategies/         # Trading strategies
│   └── __init__.py
├── risk/               # Risk management
│   └── __init__.py
└── utils/              # Utilities
    ├── config.py      # Configuration
    ├── logging.py    # Logging setup
    └── errors.py     # Error handling
```

## 🔧 Development

### Run in Development Mode
```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Run Tests
```bash
pytest -v
```

### Enable Live Trading

**⚠️ WARNING: Live trading involves real money. Test thoroughly in paper mode first!**

```env
# .env file
PAPER_MODE=false
# Add your exchange credentials
```

## 📚 API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - See LICENSE file for details.

---

**Disclaimer**: This software is for educational purposes. Use at your own risk. Always test thoroughly in paper trading mode before using real money.