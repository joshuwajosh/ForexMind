"""
ForexMind Data Fetcher
Pulls candles from MT5 + news from Alpha Vantage + NewsAPI
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Optional

from config.settings import (
    MT5_LOGIN, MT5_PASSWORD, MT5_SERVER,
    ALPHA_VANTAGE_KEY, NEWS_API_KEY,
    MT5_TIMEFRAME_MAP, CANDLES_LOOKBACK
)

# Try importing MT5 — only works on Windows with MT5 installed
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    print("  [WARN] MetaTrader5 not installed — using dummy data for testing")


class MT5Client:
    """Connects to MetaTrader 5 and fetches real forex data."""

    def __init__(self):
        self.connected = False
        self._connect()

    def _connect(self):
        if not MT5_AVAILABLE:
            print("  [MT5] MetaTrader5 library not available")
            return

        if not mt5.initialize():
            print(f"  [MT5] initialize() failed: {mt5.last_error()}")
            return

        # Login if credentials provided
        if MT5_LOGIN and MT5_PASSWORD:
            authorized = mt5.login(
                login=MT5_LOGIN,
                password=MT5_PASSWORD,
                server=MT5_SERVER
            )
            if not authorized:
                print(f"  [MT5] Login failed: {mt5.last_error()}")
                return
            print(f"  [MT5] Logged in as {MT5_LOGIN} on {MT5_SERVER}")
        else:
            print("  [MT5] Using active MT5 session (no login credentials in .env)")

        self.connected = True
        info = mt5.terminal_info()
        if info:
            print(f"  [MT5] Connected — Build {info.build}")

    def get_candles(self, pair: str, timeframe: str, count: int = CANDLES_LOOKBACK) -> list:
        """Fetch OHLCV candles from MT5."""
        if not self.connected or not MT5_AVAILABLE:
            return self._dummy_candles(pair, timeframe, count)

        # Convert pair format EUR_USD → EURUSD
        symbol = pair.replace("_", "")

        tf_code = MT5_TIMEFRAME_MAP.get(timeframe, 16385)  # default H1

        rates = mt5.copy_rates_from_pos(symbol, tf_code, 0, count)
        if rates is None:
            print(f"  [MT5] No data for {symbol} {timeframe}: {mt5.last_error()}")
            return self._dummy_candles(pair, timeframe, count)

        candles = []
        for r in rates:
            candles.append({
                "time":   datetime.fromtimestamp(r['time']).strftime('%Y-%m-%d %H:%M'),
                "open":   round(float(r['open']),  5),
                "high":   round(float(r['high']),  5),
                "low":    round(float(r['low']),   5),
                "close":  round(float(r['close']), 5),
                "volume": int(r['tick_volume']),
            })
        return candles

    def get_current_price(self, pair: str) -> dict:
        """Get current bid/ask for a pair."""
        if not self.connected or not MT5_AVAILABLE:
            return {"bid": 1.0850, "ask": 1.0852, "spread": 2}

        symbol = pair.replace("_", "")
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return {"bid": 0, "ask": 0, "spread": 0}

        return {
            "bid":    round(tick.bid, 5),
            "ask":    round(tick.ask, 5),
            "spread": round((tick.ask - tick.bid) * 10000, 1)
        }

    def get_account_info(self) -> dict:
        """Get demo account balance and margin info."""
        if not self.connected or not MT5_AVAILABLE:
            return {"balance": 10000, "equity": 10000, "margin_free": 10000}

        info = mt5.account_info()
        if not info:
            return {}

        return {
            "balance":     round(info.balance, 2),
            "equity":      round(info.equity, 2),
            "margin":      round(info.margin, 2),
            "margin_free": round(info.margin_free, 2),
            "profit":      round(info.profit, 2),
            "currency":    info.currency,
            "leverage":    info.leverage,
        }

    def _dummy_candles(self, pair: str, timeframe: str, count: int) -> list:
        """Generate dummy candles when MT5 is not available (for testing)."""
        import random
        base = 1.0850 if "EUR" in pair else 1.2650 if "GBP" in pair else 149.50
        candles = []
        price = base
        for i in range(count):
            change = random.uniform(-0.0020, 0.0020)
            open_p  = round(price, 5)
            close_p = round(price + change, 5)
            high_p  = round(max(open_p, close_p) + abs(random.uniform(0, 0.0010)), 5)
            low_p   = round(min(open_p, close_p) - abs(random.uniform(0, 0.0010)), 5)
            candles.append({
                "time":   (datetime.now() - timedelta(hours=count - i)).strftime('%Y-%m-%d %H:%M'),
                "open":   open_p,
                "high":   high_p,
                "low":    low_p,
                "close":  close_p,
                "volume": random.randint(100, 5000)
            })
            price = close_p
        return candles

    def disconnect(self):
        if MT5_AVAILABLE and self.connected:
            mt5.shutdown()


class AlphaVantageClient:
    """Fetches forex data and economic indicators from Alpha Vantage (free)."""

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self):
        self.key = ALPHA_VANTAGE_KEY

    def get_exchange_rate(self, from_currency: str, to_currency: str) -> dict:
        """Get current exchange rate."""
        if not self.key:
            return {}
        try:
            params = {
                "function":      "CURRENCY_EXCHANGE_RATE",
                "from_currency": from_currency,
                "to_currency":   to_currency,
                "apikey":        self.key
            }
            r = requests.get(self.BASE_URL, params=params, timeout=10)
            data = r.json()
            rate_data = data.get("Realtime Currency Exchange Rate", {})
            return {
                "rate":       rate_data.get("5. Exchange Rate", "N/A"),
                "bid":        rate_data.get("8. Bid Price", "N/A"),
                "ask":        rate_data.get("9. Ask Price", "N/A"),
                "last_update": rate_data.get("6. Last Refreshed", "N/A"),
            }
        except Exception as e:
            return {"error": str(e)}

    def get_forex_intraday(self, from_currency: str, to_currency: str,
                           interval: str = "60min") -> list:
        """Get intraday forex candles."""
        if not self.key:
            return []
        try:
            params = {
                "function":      "FX_INTRADAY",
                "from_symbol":   from_currency,
                "to_symbol":     to_currency,
                "interval":      interval,
                "outputsize":    "compact",
                "apikey":        self.key
            }
            r = requests.get(self.BASE_URL, params=params, timeout=10)
            data = r.json()
            series = data.get(f"Time Series FX ({interval})", {})
            candles = []
            for ts, values in list(series.items())[:50]:
                candles.append({
                    "time":  ts,
                    "open":  float(values["1. open"]),
                    "high":  float(values["2. high"]),
                    "low":   float(values["3. low"]),
                    "close": float(values["4. close"]),
                })
            return candles
        except Exception as e:
            return []


class NewsClient:
    """Fetches forex-relevant news from NewsAPI."""

    def __init__(self):
        self.key = NEWS_API_KEY

    def get_forex_news(self, pair: str, limit: int = 10) -> list:
        """Fetch recent news for a currency pair."""
        if not self.key:
            return self._dummy_news(pair)

        # Build search query from pair
        currencies = pair.replace("_", "/")
        currency_names = {
            "EUR": "Euro",
            "USD": "Dollar Federal Reserve",
            "GBP": "British Pound Sterling",
            "JPY": "Japanese Yen Bank of Japan",
        }
        parts = pair.split("_")
        query_terms = []
        for p in parts:
            query_terms.append(currency_names.get(p, p))
        query = " OR ".join(query_terms) + " OR forex"

        try:
            params = {
                "q":        query,
                "language": "en",
                "sortBy":   "publishedAt",
                "pageSize": limit,
                "apiKey":   self.key
            }
            r = requests.get(
                "https://newsapi.org/v2/everything",
                params=params,
                timeout=10
            )
            data = r.json()
            articles = data.get("articles", [])
            news = []
            for a in articles:
                news.append({
                    "title":       a.get("title", ""),
                    "description": a.get("description", ""),
                    "source":      a.get("source", {}).get("name", ""),
                    "published":   a.get("publishedAt", ""),
                    "url":         a.get("url", ""),
                })
            return news
        except Exception as e:
            return self._dummy_news(pair)

    def _dummy_news(self, pair: str) -> list:
        return [
            {
                "title":       f"Central bank policy update affecting {pair}",
                "description": "Markets await Fed decision on interest rates amid inflation concerns",
                "source":      "Reuters",
                "published":   datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
            {
                "title":       "Global risk sentiment improves on trade data",
                "description": "Positive economic indicators support risk-on currencies",
                "source":      "Bloomberg",
                "published":   datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        ]
