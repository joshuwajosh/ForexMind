# ForexMind 🤖
**AI Hedge Fund for Forex Trading**
Multi-agent system: 4 Analysts + Bull/Bear Debate + Risk Manager + Portfolio Manager

---

## 📁 Folder Structure
```
D:\algotrade\ForexMind\
├── main.py                  ← Run this
├── .env                     ← Your API keys (copy from .env.example)
├── requirements.txt
├── config\
│   └── settings.py          ← All settings (pairs, risk, timeframes)
├── data\
│   ├── fetcher.py           ← MT5 + Alpha Vantage + NewsAPI
│   └── indicators.py        ← RSI, EMA, MACD, BB, ATR etc
├── agents\
│   ├── analysts.py          ← 4 analysts in parallel
│   ├── researchers.py       ← Bull vs Bear debate
│   └── execution.py         ← Trader → Risk → Portfolio Manager
├── memory\
│   ├── manager.py           ← JSON decision log
│   └── data\                ← Auto-created, stores decisions.json
└── utils\
    ├── llm.py               ← Groq API client
    └── telegram.py          ← Telegram notifications
```

---

## 🚀 Setup (One Time)

### Step 1 — Copy to algotrade folder
```
Place this ForexMind folder at: D:\algotrade\ForexMind\
```

### Step 2 — Create .env file
```powershell
cd D:\algotrade\ForexMind
copy .env.example .env
notepad .env
```
Fill in:
- `MT5_LOGIN` — your MT5 demo account number
- `MT5_PASSWORD` — your MT5 demo password
- `MT5_SERVER` — your broker server (e.g. MetaQuotes-Demo)
- `GROQ_API_KEY` — already filled (your existing key)
- `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` — for alerts

### Step 3 — Install dependencies
```powershell
cd D:\algotrade\ForexMind
pip install -r requirements.txt
```

### Step 4 — Make sure MT5 is running
Open MetaTrader 5 on your PC before running the bot.

---

## ▶️ How to Run

```powershell
cd D:\algotrade\ForexMind

# Analyze one pair (interactive)
python main.py

# Analyze specific pair
python main.py --pair EUR_USD

# Analyze with custom settings
python main.py --pair EUR_USD --rounds 3 --tf H1 H4

# Analyze all major pairs
python main.py --all

# View performance stats
python main.py --stats
```

---

## 📊 What Happens When You Run It

```
Step 1: 4 Analysts run in PARALLEL
  ✓ Technical Analyst  — RSI, EMA, MACD, Bollinger Bands
  ✓ Fundamental Analyst — Interest rates, economic strength
  ✓ Sentiment Analyst  — Retail positioning, COT data
  ✓ News Analyst       — Breaking news, economic calendar

Step 2: Bull vs Bear DEBATE (2 rounds default)
  Bull argues FOR buying
  Bear argues AGAINST
  Full transcript saved

Step 3: EXECUTION PIPELINE
  Trader → proposes trade
  Risk Manager → approves/rejects
  Portfolio Manager → final decision

Step 4: RESULT
  Action: BUY / SELL / HOLD
  Confidence: 0-100%
  Stop Loss + Take Profit levels
  Full reasoning saved to memory/data/decisions.json

Step 5: TELEGRAM ALERT sent to your phone
```

---

## ⚙️ Key Settings (config/settings.py)

| Setting | Default | Description |
|---------|---------|-------------|
| MAJOR_PAIRS | EUR_USD, GBP_USD, USD_JPY | Pairs to trade |
| DEFAULT_TIMEFRAMES | H1, H4 | Analysis timeframes |
| DEFAULT_DEBATE_ROUNDS | 2 | Bull/Bear debate rounds |
| RISK_PER_TRADE_PCT | 1.5% | Max risk per trade |
| DEFAULT_LOT_SIZE | 0.01 | Starting lot size (micro) |

---

## 🔗 Integration with Indian Stock Bot

This runs **completely independently** of your Shoonya/OpenAlgo Indian stock system.
- Different broker (MT5 vs Shoonya)
- Different data (MT5 vs Yahoo Finance)
- Different memory folder
- Same Groq API key (shared, no conflict)

Run both simultaneously with no issues!

---

## 📱 Telegram Setup (5 minutes)

1. Open Telegram → search `@BotFather` → `/newbot` → get your token
2. Search `@userinfobot` → start it → it shows your chat_id
3. Add both to `.env`
4. Test: `python main.py --pair EUR_USD`
