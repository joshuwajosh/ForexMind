"""
ForexMind — Execution Pipeline (ENHANCED)
Trader Agent → Risk Manager → Portfolio Manager
Features: Dynamic position sizing + debate-aware + aggressive trading
"""

import json
import time
from typing import Dict, List
from utils.llm import GroqClient
from config.settings import RISK_PER_TRADE_PCT, DEFAULT_LOT_SIZE


def get_position_size(confidence: int) -> float:
    """
    Dynamic position sizing based on confidence level.
    Higher confidence = bigger position (leverage conviction).
    
    55-60% confidence → 0.01 lot (minimal)
    60-70% confidence → 0.02 lot (small)
    70-80% confidence → 0.03 lot (medium)
    80%+ confidence → 0.05 lot (full)
    """
    if confidence < 55:
        return 0.01
    elif confidence < 60:
        return 0.01
    elif confidence < 70:
        return 0.02
    elif confidence < 80:
        return 0.03
    elif confidence < 85:
        return 0.04
    else:
        return 0.05


async def trader_agent(pair: str, analyst_reports: Dict[str, str],
                       debate_result: dict, llm: GroqClient) -> dict:
    """Trader reads reports and debate, proposes a trade using debate lean."""

    print("    [Trader] Reading analyst reports and debate...")

    combined_reports = "\n\n".join([
        f"=== {name} ===\n{report[:350]}"
        for name, report in analyst_reports.items()
    ])

    debate_lean = debate_result.get("lean", "NEUTRAL")
    debate_confidence = debate_result.get("confidence", 50)

    prompt = f"""You are an aggressive forex TRADER at a hedge fund.

ANALYST REPORTS:
{combined_reports}

DEBATE RESULT: {debate_lean} ({debate_confidence}% confidence)

Your job: Propose a specific trade for {pair}.

Rules:
- If debate is BULLISH → recommend BUY (with confidence >= 65%)
- If debate is BEARISH → recommend SELL (with confidence >= 65%)
- If debate is NEUTRAL → analyze reports carefully, propose if signals clear
- ALWAYS be more aggressive for high-conviction signals
- Position sizing: 55%=0.01, 70%=0.02, 80%=0.04, 85%+=0.05 lots
- Avoid HOLD — only use if truly uncertain

Respond ONLY with this JSON (no other text):
{{
  "action": "BUY",
  "confidence": 75,
  "position_size": 0.03,
  "reasoning": "Debate BULLISH + strong technical signals"
}}"""

    response = llm.call(prompt)

    try:
        response = response.strip()
        if "```" in response:
            for part in response.split("```"):
                if "{" in part:
                    response = part.replace("json", "").strip()
                    break
        start = response.find("{")
        end   = response.rfind("}") + 1
        if start >= 0 and end > start:
            response = response[start:end]
        trade = json.loads(response)
        
        # Auto-fix position size based on confidence
        trade["position_size"] = get_position_size(trade.get("confidence", 60))
        
    except Exception as e:
        print(f"    [Trader] Parse error: {e}")
        # Fallback: follow debate lean
        if debate_lean == "BULLISH":
            trade = {"action": "BUY", "confidence": debate_confidence, "position_size": get_position_size(debate_confidence), "reasoning": "Debate BULLISH"}
        elif debate_lean == "BEARISH":
            trade = {"action": "SELL", "confidence": debate_confidence, "position_size": get_position_size(debate_confidence), "reasoning": "Debate BEARISH"}
        else:
            trade = {"action": "HOLD", "confidence": 50, "position_size": 0.01, "reasoning": "Debate neutral"}

    print(f"    [Trader] Proposed: {trade.get('action')} with {trade.get('confidence')}% confidence | Size: {trade.get('position_size')} lots")
    return trade


async def risk_manager(pair: str, trade_proposal: dict, llm: GroqClient) -> dict:
    """Risk manager evaluates proposal with lenient demo-account rules."""

    print("    [Risk Manager] Evaluating risk...")
    time.sleep(0.5)

    action = trade_proposal.get("action", "HOLD")
    confidence = trade_proposal.get("confidence", 50)
    
    if action == "HOLD":
        return {"approved": True, "risk_score": 0, "adjusted_position_size": 0}

    prompt = f"""You are a RISK MANAGER for a DEMO account trading {pair}.

TRADE: {action} with {confidence}% confidence
Position size proposed: {trade_proposal.get('position_size', 0.01)} lots

Respond ONLY with this JSON:
{{
  "approved": true,
  "risk_score": 5,
  "adjusted_position_size": 0.02
}}

Rules for DEMO account:
- Approve any trade with confidence >= 55%
- Confidence >= 75% → auto-approve regardless
- Risk score: 1-10 (higher = riskier)
- Adjust position size if unrealistic
- DEMO = learning environment, take reasonable risks"""

    response = llm.call(prompt)

    try:
        response = response.strip()
        if "```" in response:
            for part in response.split("```"):
                if "{" in part:
                    response = part.replace("json", "").strip()
                    break
        start = response.find("{")
        end   = response.rfind("}") + 1
        if start >= 0 and end > start:
            response = response[start:end]
        risk = json.loads(response)
    except Exception as e:
        print(f"    [Risk Manager] Parse error: {e}")
        risk = {
            "approved": confidence >= 55,
            "risk_score": 5,
            "adjusted_position_size": trade_proposal.get("position_size", 0.01)
        }

    status = "✓ APPROVED" if risk.get("approved") else "✗ REJECTED"
    print(f"    [Risk Manager] {status} | Risk Score: {risk.get('risk_score')}/10")
    return risk


async def portfolio_manager(pair: str, analyst_reports: Dict[str, str],
                             debate_result: dict,
                             trade_proposal: dict, risk_assessment: dict,
                             history: list, llm: GroqClient) -> dict:
    """Portfolio Manager makes final decision."""

    print("    [Portfolio Manager] Making final decision...")
    time.sleep(0.5)

    action = trade_proposal.get("action", "HOLD")
    confidence = trade_proposal.get("confidence", 50)
    risk_approved = risk_assessment.get("approved", False)
    debate_lean = debate_result.get("lean", "NEUTRAL")

    prompt = f"""You are PORTFOLIO MANAGER for {pair}.

SITUATION:
- Trader proposes: {action} ({confidence}% confidence)
- Risk Manager: {"APPROVED ✓" if risk_approved else "REJECTED ✗"}
- Debate lean: {debate_lean}

FINAL DECISION (respond with JSON only):
{{
  "action": "{action}",
  "confidence": {confidence},
  "position_size": 0.02
}}

RULES:
- If action=BUY/SELL AND confidence>=55% AND risk approved → EXECUTE
- If confidence>=75% → EXECUTE even if risk rejected
- If action=HOLD → approve as-is
- DEMO account → be aggressive but not reckless
- Only HOLD if truly uncertain"""

    response = llm.call(prompt)

    try:
        response = response.strip()
        if "```" in response:
            for part in response.split("```"):
                if "{" in part:
                    response = part.replace("json", "").strip()
                    break
        start = response.find("{")
        end   = response.rfind("}") + 1
        if start >= 0 and end > start:
            response = response[start:end]
        final = json.loads(response)
    except Exception as e:
        print(f"    [Portfolio Manager] Parse error: {e}")
        # Fallback logic
        if (risk_approved and confidence >= 55 and action != "HOLD") or confidence >= 75:
            final = {
                "action": action,
                "confidence": confidence,
                "position_size": trade_proposal.get("position_size", 0.01)
            }
        else:
            final = {
                "action": "HOLD",
                "confidence": confidence,
                "position_size": 0
            }

    action_out = final.get("action", "HOLD")
    emoji = "🟢 BUY" if action_out == "BUY" else "🔴 SELL" if action_out == "SELL" else "⚪ HOLD"
    size = final.get("position_size", 0)
    print(f"    [Portfolio Manager] FINAL: {emoji} ({final.get('confidence')}%) | Size: {size} lots")
    return final


async def run_execution_pipeline(pair: str, analyst_reports: Dict[str, str],
                                  debate_result: dict,
                                  history: list, llm: GroqClient) -> dict:
    """Run Trader → Risk Manager → Portfolio Manager pipeline."""

    trade_proposal = await trader_agent(pair, analyst_reports, debate_result, llm)
    risk_assessment = await risk_manager(pair, trade_proposal, llm)
    final_decision = await portfolio_manager(
        pair=pair,
        analyst_reports=analyst_reports,
        debate_result=debate_result,
        trade_proposal=trade_proposal,
        risk_assessment=risk_assessment,
        history=history,
        llm=llm
    )

    final_decision["pair"] = pair
    final_decision["trade_proposal"] = trade_proposal
    final_decision["risk_assessment"] = risk_assessment
    final_decision["debate_result"] = debate_result

    return final_decision
