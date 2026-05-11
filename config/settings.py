"""
ForexMind Configuration
Edit this file to change pairs, risk settings, and API keys
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Forex Pairs ──────────────────────────────────────────────────────
MAJOR_PAIRS = [
    "EUR_USD",
    "GBP_USD",
    "USD_JPY",
]

# ── Timeframes ────────────────────────────────────────────────────────
DEFAULT_TIMEFRAMES = ["H1", "H4"]   # H1=1hour, H4=4hour, D1=daily
ALL_TIMEFRAMES     = ["M15", "H1", "H4", "D1"]

# ── Debate Settings ───────────────────────────────────────────────────
DEFAULT_DEBATE_ROUNDS = 2    # 1-5 rounds between Bull and Bear
MAX_DEBATE_ROUNDS     = 5

# ── Risk Management ───────────────────────────────────────────────────
RISK_PER_TRADE_PCT  = 1.5    # 1-2% conservative risk per trade
MAX_OPEN_POSITIONS  = 3      # max simultaneous positions
DEFAULT_LOT_SIZE    = 0.01   # micro lot — safe for demo

# ── MT5 Settings ─────────────────────────────────────────────────────
MT5_LOGIN    = int(os.getenv("MT5_LOGIN", "0"))
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER   = os.getenv("MT5_SERVER", "MetaQuotes-Demo")

# MT5 timeframe mapping
MT5_TIMEFRAME_MAP = {
    "M1":  1,
    "M5":  5,
    "M15": 15,
    "M30": 30,
    "H1":  16385,
    "H4":  16388,
    "D1":  16408,
}

# ── API Keys ──────────────────────────────────────────────────────────
GROQ_API_KEY          = os.getenv("GROQ_API_KEY", "")
ALPHA_VANTAGE_KEY     = os.getenv("ALPHA_VANTAGE_KEY", "")
NEWS_API_KEY          = os.getenv("NEWS_API_KEY", "")
TELEGRAM_BOT_TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID      = os.getenv("TELEGRAM_CHAT_ID", "")

# ── LLM Settings ─────────────────────────────────────────────────────
GROQ_MODEL      = "llama-3.3-70b-versatile"
MAX_TOKENS      = 1000
TEMPERATURE     = 0.3          # lower = more consistent/conservative
RETRY_ATTEMPTS  = 3
RETRY_DELAY     = 2            # seconds between retries

# ── Memory / Logging ──────────────────────────────────────────────────
MEMORY_DIR      = "memory/data"
LOG_DIR         = "logs"
DECISION_LOG    = f"{MEMORY_DIR}/decisions.json"
TRADE_HISTORY   = f"{MEMORY_DIR}/trade_history.json"

# ── Technical Analysis Settings ───────────────────────────────────────
CANDLES_LOOKBACK = 200         # how many candles to fetch
RSI_PERIOD       = 14
EMA_FAST         = 9
EMA_SLOW         = 21
MACD_FAST        = 12
MACD_SLOW        = 26
MACD_SIGNAL      = 9
BB_PERIOD        = 20
BB_STD           = 2
ATR_PERIOD       = 14
