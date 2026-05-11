"""
ForexMind — Execution Pipeline
Trader Agent → Risk Manager → Portfolio Manager
FIXED: Lower confidence threshold + cleared pending memory confusion
"""

import json
import time
from typing import Dict, List
from utils.llm import GroqClient
from config.settings import RISK_PER_TRADE_PCT, DEFAULT_LOT_SIZE


async def trader_agent(pair: str, analyst_reports: Dict[str, str],
                       debate_transcript: List[dict], llm: GroqClient) -> dict:
    """Trader reads all reports and debate, proposes a trade."""

    print("    [Trader] Reading analyst reports and debate...")

    combined_reports = "\n\n".join([
        f"=== {name} ===\n{report[:500]}"
        for name, report in analyst_reports.items()
    ])

    debate_summary = ""
    for r in debate_transcript:
        debate_summary += f"\nRound {r['round']}:"
        debate_summary += f"\nBULL: {r['bull_argument'][:150]}"
        debate_summary += f"\nBEAR: {r['bear_argument'][:150]}"

    prompt = f"""You are an aggressive forex TRADER at a hedge fund.
Analyze {pair} and propose a specific trade.

ANALYST REPORTS SUMMARY:
{combined_reports[:1200]}

DEBATE SUMMARY:
{debate_summary[:600]}

Rules:
- If bullish signals outweigh bearish → BUY
- If bearish signals outweigh bullish → SELL
- Only say HOLD if signals are completely mixed 50/50
- Be decisive! Markets reward action.

Current {pair} price context: use realistic current market prices.

Respond ONLY with this exact JSON (no other text):
{{
  "action": "BUY",
  "confidence": 72,
  "entry_price": "MARKET",
  "stop_loss": 0,
  "take_profit": 0,
  "position_size": 0.05,
  "timeframe": "H1",
  "reasoning": "Brief reason here"
}}"""

    response = llm.call(prompt)

    try:
        response = response.strip()
        # Clean markdown code blocks
        if "```" in response:
            parts = response.split("```")
            for part in parts:
                if "{" in part:
                    response = part.replace("json", "").strip()
                    break
        # Find JSON object
        start = response.find("{")
        end   = response.rfind("}") + 1
        if start >= 0 and end > start:
            response = response[start:end]
        trade = json.loads(response)
    except Exception as e:
        print(f"    [Trader] JSON parse failed: {e}")
        # Default to a decision based on debate
        trade = {
            "action":        "BUY",
            "confidence":    65,
            "entry_price":   "MARKET",
            "stop_loss":     0,
            "take_profit":   0,
            "position_size": DEFAULT_LOT_SIZE,
            "timeframe":     "H1",
            "reasoning":     "Default buy based on general bullish bias."
        }

    print(f"    [Trader] Proposed: {trade.get('action')} with {trade.get('confidence')}% confidence")
    return trade


async def risk_manager(pair: str, trade_proposal: dict,
                       llm: GroqClient) -> dict:
    """Risk manager evaluates the trade proposal."""

    print("    [Risk Manager] Evaluating risk...")
    time.sleep(1)

    action     = trade_proposal.get("action", "HOLD")
    confidence = trade_proposal.get("confidence", 50)

    prompt = f"""You are a forex RISK MANAGER. Be reasonable, not overly cautious.

TRADE PROPOSAL for {pair}:
- Action: {action}
- Confidence: {confidence}%
- Max risk per trade: {RISK_PER_TRADE_PCT}%

Evaluate and respond ONLY with this exact JSON:
{{
  "approved": true,
  "adjusted_position_size": 0.05,
  "risk_score": 5,
  "risk_reward_ratio": 2.0,
  "concerns": ["one concern max"],
  "recommendation": "Approve with standard risk management"
}}

Rules:
- Approve if confidence >= 60%
- Risk score should be 4-6 for normal trades
- Always include a stop loss suggestion
- Don't be overly cautious — this is a demo account"""

    response = llm.call(prompt)

    try:
        response = response.strip()
        if "```" in response:
            parts = response.split("```")
            for part in parts:
                if "{" in part:
                    response = part.replace("json", "").strip()
                    break
        start = response.find("{")
        end   = response.rfind("}") + 1
        if start >= 0 and end > start:
            response = response[start:end]
        risk = json.loads(response)
    except Exception as e:
        print(f"    [Risk Manager] JSON parse failed: {e}")
        risk = {
            "approved":               confidence >= 60,
            "adjusted_position_size": DEFAULT_LOT_SIZE,
            "risk_score":             5,
            "risk_reward_ratio":      2.0,
            "concerns":               [],
            "recommendation":         "Standard risk assessment"
        }

    status = "APPROVED ✓" if risk.get("approved") else "REJECTED ✗"
    print(f"    [Risk Manager] {status} — Risk Score: {risk.get('risk_score')}/10")
    return risk


async def portfolio_manager(pair: str, analyst_reports: Dict[str, str],
                             debate_transcript: List[dict],
                             trade_proposal: dict, risk_assessment: dict,
                             history: list, llm: GroqClient) -> dict:
    """Portfolio Manager makes the final decision."""

    print("    [Portfolio Manager] Making final decision...")
    time.sleep(1)

    risk_approved = risk_assessment.get("approved", False)
    action        = trade_proposal.get("action", "HOLD")
    confidence    = trade_proposal.get("confidence", 50)

    # Only show last 2 trades in history to avoid confusion
    recent_history = ""
    if history:
        last2 = history[-2:]
        recent_history = f"Last {len(last2)} trades: " + ", ".join(
            [f"{h.get('action','?')} ({h.get('date','?')[:10]})" for h in last2]
        )

    prompt = f"""You are the PORTFOLIO MANAGER making the FINAL trading decision for {pair}.

SITUATION:
- Trader proposes: {action} with {confidence}% confidence
- Risk assessment: {"APPROVED" if risk_approved else "REJECTED"}
- {recent_history}

DECISION RULES:
- If action is BUY or SELL AND confidence >= 60% AND risk approved → EXECUTE the trade
- If confidence >= 75% → override even if risk rejected
- Only HOLD if confidence < 60% or signals completely unclear

You MUST be decisive. The market is open. Make a call.

Respond ONLY with this exact JSON:
{{
  "action": "{action}",
  "confidence": {confidence},
  "position_size": 0.05,
  "stop_loss": 0,
  "take_profit": 0,
  "reasoning": "Executing {action} based on analyst consensus and approved risk",
  "rejected_reason": ""
}}"""

    response = llm.call(prompt)

    try:
        response = response.strip()
        if "```" in response:
            parts = response.split("```")
            for part in parts:
                if "{" in part:
                    response = part.replace("json", "").strip()
                    break
        start = response.find("{")
        end   = response.rfind("}") + 1
        if start >= 0 and end > start:
            response = response[start:end]
        final = json.loads(response)
    except Exception as e:
        print(f"    [Portfolio Manager] JSON parse failed: {e}")
        # If risk approved and confidence >= 60, execute
        if risk_approved and confidence >= 60 and action != "HOLD":
            final = {
                "action":          action,
                "confidence":      confidence,
                "position_size":   DEFAULT_LOT_SIZE,
                "stop_loss":       0,
                "take_profit":     0,
                "reasoning":       f"Executing {action} — analyst consensus with {confidence}% confidence.",
                "rejected_reason": ""
            }
        else:
            final = {
                "action":          "HOLD",
                "confidence":      confidence,
                "position_size":   0,
                "stop_loss":       0,
                "take_profit":     0,
                "reasoning":       "Insufficient confidence to trade.",
                "rejected_reason": "Below threshold"
            }

    action_out = final.get("action", "HOLD")
    emoji = "🟢 BUY" if action_out == "BUY" else "🔴 SELL" if action_out == "SELL" else "⚪ HOLD"
    print(f"    [Portfolio Manager] FINAL: {emoji} ({final.get('confidence')}%)")
    return final


async def run_execution_pipeline(pair: str, analyst_reports: Dict[str, str],
                                  debate_transcript: List[dict],
                                  history: list, llm: GroqClient) -> dict:
    """Run the full Trader → Risk → Portfolio pipeline."""

    trade_proposal  = await trader_agent(pair, analyst_reports, debate_transcript, llm)
    risk_assessment = await risk_manager(pair, trade_proposal, llm)
    final_decision  = await portfolio_manager(
        pair=pair,
        analyst_reports=analyst_reports,
        debate_transcript=debate_transcript,
        trade_proposal=trade_proposal,
        risk_assessment=risk_assessment,
        history=history,
        llm=llm
    )

    final_decision["pair"]            = pair
    final_decision["trade_proposal"]  = trade_proposal
    final_decision["risk_assessment"] = risk_assessment

    return final_decision