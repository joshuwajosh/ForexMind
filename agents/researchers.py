"""
ForexMind — Enhanced Debate Engine with Market Context
Improved: Smarter bull/bear arguments + trend awareness
"""

import time
from typing import Dict, List
from utils.llm import GroqClient


async def run_debate(pair: str, analyst_reports: Dict[str, str],
                     debate_rounds: int, llm: GroqClient,
                     current_indicators: dict = None) -> dict:
    """
    Run intelligent Bull vs Bear debate with market context.
    
    Args:
        pair: Currency pair (e.g., "EUR_USD")
        analyst_reports: Dict of analyst reports
        debate_rounds: Number of debate rounds
        llm: LLM client
        current_indicators: Current market indicators for context
        
    Returns:
        Dict with debate summary, transcript, and lean direction
    """

    print(f"\n  Starting Bull vs Bear debate — {debate_rounds} round(s)")

    # Combine all analyst reports
    combined_reports = "\n\n".join([
        f"=== {name} ===\n{report[:400]}"
        for name, report in analyst_reports.items()
    ])

    # Add market context if available
    market_context = ""
    if current_indicators:
        trend = current_indicators.get("trend", "UNKNOWN")
        rsi = current_indicators.get("rsi", 50)
        price_vs_ema = current_indicators.get("price_vs_ema9", 0)
        
        market_context = f"""
CURRENT MARKET CONTEXT:
- Trend: {trend} {"📈" if trend == "BULLISH" else "📉" if trend == "BEARISH" else "↔️"}
- RSI: {rsi} {"(overbought)" if rsi > 70 else "(oversold)" if rsi < 30 else "(neutral)"}
- Price vs EMA9: {price_vs_ema:+.2f}% {"(above trend)" if price_vs_ema > 0 else "(below trend)"}
"""

    transcript = []
    bull_position = ""
    bear_position = ""
    
    bull_score = 0
    bear_score = 0

    for round_num in range(1, debate_rounds + 1):
        print(f"    Round {round_num}/{debate_rounds}...")

        # ── BULL ARGUMENT ────────────────────────────────────────────────
        if round_num == 1:
            bull_prompt = f"""You are the BULL researcher at a forex hedge fund.
Your job is to make the strongest possible case for going LONG (buying) {pair}.

ANALYST REPORTS:
{combined_reports}

{market_context}

Make your opening argument for a BUY position on {pair}.
- Reference specific data from the analyst reports
- Identify the top 3 reasons to buy
- Quantify potential profit target (pips/percentage)
- Mention timeframe (H1, H4, or D1)
- Rate your conviction: STRONG / MODERATE / WEAK
- Be forceful and specific. Under 250 words."""
        else:
            bull_prompt = f"""You are the BULL researcher. The bear has challenged your position.

BEAR'S ARGUMENT:
{bear_position}

ORIGINAL ANALYST REPORTS:
{combined_reports}

{market_context}

Defend your BUY position on {pair}:
- Counter the bear's specific points with data
- Strengthen your top 3 reasons
- Quantify risk vs reward
- Rate your conviction: STRONG / MODERATE / WEAK
- Be specific. Under 200 words."""

        bull_arg = llm.call(bull_prompt)
        
        # Extract conviction level
        bull_conviction = "MODERATE"
        if "STRONG" in bull_arg.upper():
            bull_conviction = "STRONG"
            bull_score += 2
        elif "WEAK" in bull_arg.upper():
            bull_conviction = "WEAK"
            bull_score += 0
        else:
            bull_score += 1
        
        time.sleep(0.8)  # Rate limit buffer

        # ── BEAR ARGUMENT ────────────────────────────────────────────────
        if round_num == 1:
            bear_prompt = f"""You are the BEAR researcher at a forex hedge fund.
Your job is to make the strongest possible case for going SHORT (selling) {pair}.

ANALYST REPORTS:
{combined_reports}

BULL'S OPENING ARGUMENT:
{bull_arg}

{market_context}

Make your opening argument AGAINST a buy position on {pair}:
- Challenge the bull's specific points with data
- Identify the top 3 risks or reasons NOT to buy
- Quantify potential loss (pips/percentage)
- Mention timeframe (H1, H4, or D1)
- Rate your conviction: STRONG / MODERATE / WEAK
- Be forceful and specific. Under 250 words."""
        else:
            bear_prompt = f"""You are the BEAR researcher. The bull has defended their position.

BULL'S ARGUMENT:
{bull_arg}

ORIGINAL ANALYST REPORTS:
{combined_reports}

{market_context}

Maintain your SELL/SHORT position on {pair}:
- Counter the bull's defense with specific data
- Reinforce your top 3 risk points
- Quantify risk vs reward for shorting
- Rate your conviction: STRONG / MODERATE / WEAK
- Be specific. Under 200 words."""

        bear_arg = llm.call(bear_prompt)
        
        # Extract conviction level
        bear_conviction = "MODERATE"
        if "STRONG" in bear_arg.upper():
            bear_conviction = "STRONG"
            bear_score += 2
        elif "WEAK" in bear_arg.upper():
            bear_conviction = "WEAK"
            bear_score += 0
        else:
            bear_score += 1
        
        time.sleep(0.8)

        # Save round to transcript
        round_data = {
            "round":            round_num,
            "bull_argument":    bull_arg,
            "bear_argument":    bear_arg,
            "bull_conviction":  bull_conviction,
            "bear_conviction":  bear_conviction,
        }
        transcript.append(round_data)

        # Update positions for next round
        bull_position = bull_arg
        bear_position = bear_arg

        print(f"    Round {round_num} complete ✓ (Bull: {bull_conviction}, Bear: {bear_conviction})")

    # ── Determine debate lean ────────────────────────────────────────────
    if bull_score > bear_score:
        lean = "BULLISH"
        confidence = min(80, 50 + (bull_score - bear_score) * 10)
    elif bear_score > bull_score:
        lean = "BEARISH"
        confidence = min(80, 50 + (bear_score - bull_score) * 10)
    else:
        lean = "NEUTRAL"
        confidence = 50

    print(f"  Debate complete — {len(transcript)} round(s) recorded")
    print(f"  Debate lean: {lean} ({confidence}% confidence)")

    return {
        "transcript":   transcript,
        "lean":         lean,
        "confidence":   confidence,
        "bull_score":   bull_score,
        "bear_score":   bear_score,
        "rounds":       debate_rounds,
    }
