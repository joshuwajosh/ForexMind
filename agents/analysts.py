"""
ForexMind — 4 Analyst Agents (run in parallel)
Technical | Fundamental | Sentiment | News
"""

import asyncio
import time
from typing import Dict

from data.fetcher import MT5Client, AlphaVantageClient, NewsClient
from data.indicators import get_all_indicators
from utils.llm import GroqClient
from config.settings import DEFAULT_TIMEFRAMES


# Shared data fetcher instances
_mt5    = None
_av     = None
_news   = None


def get_mt5():
    global _mt5
    if _mt5 is None:
        _mt5 = MT5Client()
    return _mt5


def get_av():
    global _av
    if _av is None:
        _av = AlphaVantageClient()
    return _av


def get_news_client():
    global _news
    if _news is None:
        _news = NewsClient()
    return _news


async def technical_analyst(pair: str, timeframes: list, llm: GroqClient) -> str:
    """Analyzes chart patterns and technical indicators."""
    print(f"    [Technical Analyst] Fetching candles for {pair}...")

    mt5 = get_mt5()
    all_tf_data = {}

    for tf in timeframes:
        candles = mt5.get_candles(pair, tf, count=100)
        indicators = get_all_indicators(candles)
        all_tf_data[tf] = {
            "candle_count": len(candles),
            "indicators":   indicators
        }
        time.sleep(0.5)

    # Build prompt
    tf_summary = ""
    for tf, data in all_tf_data.items():
        ind = data["indicators"]
        if not ind:
            continue
        tf_summary += f"""
Timeframe {tf}:
  Price: {ind.get('current_price')}
  Trend: {ind.get('trend')}
  RSI: {ind.get('rsi')} (>70=overbought, <30=oversold)
  EMA9: {ind.get('ema_9')}, EMA21: {ind.get('ema_21')}, EMA50: {ind.get('ema_50')}
  MACD: {ind.get('macd', {}).get('macd')} | Signal: {ind.get('macd', {}).get('signal')} | Hist: {ind.get('macd', {}).get('histogram')}
  Bollinger: Upper={ind.get('bollinger', {}).get('upper')} Mid={ind.get('bollinger', {}).get('middle')} Lower={ind.get('bollinger', {}).get('lower')}
  ATR: {ind.get('atr')}
  Support: {ind.get('support_resistance', {}).get('support')} | Resistance: {ind.get('support_resistance', {}).get('resistance')}
  Stochastic K: {ind.get('stochastic', {}).get('k')} D: {ind.get('stochastic', {}).get('d')}
"""

    prompt = f"""You are a professional forex technical analyst at a hedge fund.

Analyze {pair} across multiple timeframes and provide a structured report.

TECHNICAL DATA:
{tf_summary}

Provide your analysis covering:
1. Overall trend direction (bullish/bearish/ranging)
2. Key support and resistance levels
3. Momentum signals (RSI, MACD, Stochastic)
4. Entry/exit zones
5. Your technical BIAS: BUY / SELL / HOLD with confidence (0-100%)

Be specific with numbers. Keep your report under 300 words."""

    report = llm.call(prompt)
    return report


async def fundamental_analyst(pair: str, timeframes: list, llm: GroqClient) -> str:
    """Analyzes macroeconomic fundamentals for the currency pair."""
    print(f"    [Fundamental Analyst] Analyzing fundamentals for {pair}...")

    av = get_av()

    # Get current rate from Alpha Vantage
    parts = pair.split("_")
    from_currency = parts[0] if len(parts) >= 1 else "EUR"
    to_currency   = parts[1] if len(parts) >= 2 else "USD"

    rate_data = av.get_exchange_rate(from_currency, to_currency)

    prompt = f"""You are a professional forex fundamental analyst at a hedge fund.

Analyze {pair} ({from_currency}/{to_currency}) from a macroeconomic perspective.

CURRENT MARKET DATA:
- Exchange Rate: {rate_data.get('rate', 'N/A')}
- Bid: {rate_data.get('bid', 'N/A')}
- Ask: {rate_data.get('ask', 'N/A')}
- Last Update: {rate_data.get('last_update', 'N/A')}

Based on current macroeconomic context, analyze:
1. Interest rate differential between {from_currency} and {to_currency} central banks
2. Relative economic strength (GDP, employment, inflation)
3. Trade balance and current account factors
4. Central bank policy stance (hawkish/dovish)
5. Your fundamental BIAS: BUY / SELL / HOLD with confidence (0-100%)

Reference general knowledge about these currencies' economic fundamentals.
Be specific and professional. Keep under 300 words."""

    report = llm.call(prompt)
    return report


async def sentiment_analyst(pair: str, timeframes: list, llm: GroqClient) -> str:
    """Analyzes market sentiment and positioning."""
    print(f"    [Sentiment Analyst] Gauging sentiment for {pair}...")

    prompt = f"""You are a professional forex sentiment analyst at a hedge fund.

Analyze current market sentiment for {pair}.

Evaluate:
1. Retail trader positioning (typically contrarian signal — if 70% retail are long, consider bearish)
2. COT (Commitment of Traders) report implications for institutional positioning
3. Risk-on vs risk-off environment (affects JPY, CHF as safe havens)
4. Market fear/greed indicators
5. Key psychological price levels and round numbers traders are watching
6. Seasonal and time-of-day patterns for this pair
7. Your sentiment BIAS: BUY / SELL / HOLD with confidence (0-100%)

Note any contrarian signals where retail crowd is heavily positioned one way.
Be specific. Keep under 300 words."""

    report = llm.call(prompt)
    return report


async def news_analyst(pair: str, timeframes: list, llm: GroqClient) -> str:
    """Analyzes recent news and upcoming economic events."""
    print(f"    [News Analyst] Scanning news for {pair}...")

    news_client = get_news_client()
    articles = news_client.get_forex_news(pair, limit=8)

    news_text = ""
    for i, article in enumerate(articles[:5], 1):
        news_text += f"\n{i}. [{article.get('source', 'Unknown')}] {article.get('title', '')}"
        if article.get('description'):
            news_text += f"\n   {article.get('description', '')[:150]}"

    parts = pair.split("_")
    from_currency = parts[0] if len(parts) >= 1 else "EUR"
    to_currency   = parts[1] if len(parts) >= 2 else "USD"

    prompt = f"""You are a professional forex news analyst at a hedge fund.

Analyze recent news and events affecting {pair} ({from_currency}/{to_currency}).

RECENT NEWS HEADLINES:
{news_text if news_text else "No recent news fetched — use your knowledge of current macro events."}

Analyze:
1. Immediate market-moving events (rate decisions, NFP, CPI, GDP releases)
2. Geopolitical risks affecting these currencies
3. Central bank communications and forward guidance
4. Upcoming high-impact economic calendar events this week
5. How this news SHIFTS the bias for {pair}
6. Your news-based BIAS: BUY / SELL / HOLD with confidence (0-100%)

Be specific about event dates and expected impacts. Keep under 300 words."""

    report = llm.call(prompt)
    return report


async def run_analysts(pair: str, timeframes: list,
                       llm: GroqClient) -> Dict[str, str]:
    """Run all 4 analysts in parallel and return their reports."""

    print(f"\n  Running 4 analysts for {pair}...")

    # Run all 4 in parallel with asyncio
    results = await asyncio.gather(
        technical_analyst(pair, timeframes, llm),
        fundamental_analyst(pair, timeframes, llm),
        sentiment_analyst(pair, timeframes, llm),
        news_analyst(pair, timeframes, llm),
        return_exceptions=True
    )

    reports = {}
    names = ["Technical Analyst", "Fundamental Analyst",
             "Sentiment Analyst", "News Analyst"]

    for name, result in zip(names, results):
        if isinstance(result, Exception):
            print(f"    [WARN] {name} failed: {result}")
            reports[name] = f"Analysis failed: {result}"
        else:
            reports[name] = result

    return reports
