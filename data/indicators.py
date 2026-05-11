"""
Technical Indicators for ForexMind
Pure Python — no TA-Lib dependency needed
"""

import math
from typing import List


def calculate_rsi(closes: List[float], period: int = 14) -> float:
    """Calculate RSI."""
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains  = [d if d > 0 else 0 for d in deltas[-period:]]
    losses = [-d if d < 0 else 0 for d in deltas[-period:]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def calculate_ema(closes: List[float], period: int) -> float:
    """Calculate EMA."""
    if len(closes) < period:
        return closes[-1] if closes else 0
    k = 2 / (period + 1)
    ema = sum(closes[:period]) / period
    for price in closes[period:]:
        ema = price * k + ema * (1 - k)
    return round(ema, 5)


def calculate_macd(closes: List[float],
                   fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """Calculate MACD, Signal, and Histogram."""
    if len(closes) < slow + signal:
        return {"macd": 0, "signal": 0, "histogram": 0}

    ema_fast   = calculate_ema(closes, fast)
    ema_slow   = calculate_ema(closes, slow)
    macd_line  = round(ema_fast - ema_slow, 6)

    # Signal line = EMA of MACD values
    macd_values = []
    for i in range(signal + 10):
        idx = -(signal + 10 - i)
        subset = closes[:idx] if idx < 0 else closes
        ef = calculate_ema(subset, fast)
        es = calculate_ema(subset, slow)
        macd_values.append(ef - es)

    signal_line = calculate_ema(macd_values, signal)
    histogram   = round(macd_line - signal_line, 6)

    return {
        "macd":      macd_line,
        "signal":    round(signal_line, 6),
        "histogram": histogram,
    }


def calculate_bollinger_bands(closes: List[float],
                               period: int = 20, std_dev: float = 2) -> dict:
    """Calculate Bollinger Bands."""
    if len(closes) < period:
        last = closes[-1] if closes else 0
        return {"upper": last, "middle": last, "lower": last, "width": 0}

    recent = closes[-period:]
    middle = sum(recent) / period
    variance = sum((p - middle) ** 2 for p in recent) / period
    std  = math.sqrt(variance)
    upper = round(middle + std_dev * std, 5)
    lower = round(middle - std_dev * std, 5)
    width = round(upper - lower, 5)

    return {
        "upper":  upper,
        "middle": round(middle, 5),
        "lower":  lower,
        "width":  width,
        "pct_b":  round((closes[-1] - lower) / (width if width > 0 else 1), 3)
    }


def calculate_atr(highs: List[float], lows: List[float],
                  closes: List[float], period: int = 14) -> float:
    """Calculate Average True Range."""
    if len(closes) < period + 1:
        return 0.0
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i]  - closes[i-1])
        )
        trs.append(tr)
    return round(sum(trs[-period:]) / period, 5)


def calculate_support_resistance(highs: List[float],
                                  lows: List[float],
                                  closes: List[float]) -> dict:
    """Find key support and resistance levels."""
    if not closes:
        return {"support": 0, "resistance": 0}

    recent_high = max(highs[-20:]) if len(highs) >= 20 else max(highs)
    recent_low  = min(lows[-20:])  if len(lows)  >= 20 else min(lows)
    current     = closes[-1]

    # Simple pivot points
    pivot      = round((recent_high + recent_low + current) / 3, 5)
    resistance = round(2 * pivot - recent_low,  5)
    support    = round(2 * pivot - recent_high, 5)

    return {
        "pivot":      pivot,
        "resistance": resistance,
        "support":    support,
        "recent_high": round(recent_high, 5),
        "recent_low":  round(recent_low, 5),
    }


def calculate_stochastic(highs: List[float], lows: List[float],
                          closes: List[float], k_period: int = 14) -> dict:
    """Calculate Stochastic Oscillator."""
    if len(closes) < k_period:
        return {"k": 50, "d": 50}

    recent_high = max(highs[-k_period:])
    recent_low  = min(lows[-k_period:])
    rng = recent_high - recent_low

    k = round(((closes[-1] - recent_low) / rng * 100) if rng > 0 else 50, 2)

    # D = 3-period SMA of K
    k_values = []
    for i in range(3):
        idx = -(3 - i)
        h = max(highs[idx-k_period:idx]) if len(highs) >= k_period else recent_high
        l = min(lows[idx-k_period:idx])  if len(lows)  >= k_period else recent_low
        r = h - l
        k_val = ((closes[idx] - l) / r * 100) if r > 0 else 50
        k_values.append(k_val)

    d = round(sum(k_values) / 3, 2)
    return {"k": k, "d": d}


def get_all_indicators(candles: list) -> dict:
    """Calculate all indicators from a candle list."""
    if not candles or len(candles) < 30:
        return {}

    closes = [c["close"] for c in candles]
    highs  = [c["high"]  for c in candles]
    lows   = [c["low"]   for c in candles]

    rsi   = calculate_rsi(closes)
    ema9  = calculate_ema(closes, 9)
    ema21 = calculate_ema(closes, 21)
    ema50 = calculate_ema(closes, 50)
    macd  = calculate_macd(closes)
    bb    = calculate_bollinger_bands(closes)
    atr   = calculate_atr(highs, lows, closes)
    sr    = calculate_support_resistance(highs, lows, closes)
    stoch = calculate_stochastic(highs, lows, closes)

    current = closes[-1]
    trend = "BULLISH" if ema9 > ema21 > ema50 else \
            "BEARISH" if ema9 < ema21 < ema50 else "MIXED"

    return {
        "current_price": current,
        "trend":         trend,
        "rsi":           rsi,
        "ema_9":         ema9,
        "ema_21":        ema21,
        "ema_50":        ema50,
        "macd":          macd,
        "bollinger":     bb,
        "atr":           atr,
        "support_resistance": sr,
        "stochastic":    stoch,
        "price_vs_ema9":  round(((current - ema9) / ema9) * 100, 3),
        "price_vs_ema21": round(((current - ema21) / ema21) * 100, 3),
    }
