"""
ForexMind — Bull vs Bear Debate Engine
Configurable rounds of structured disagreement
"""

import time
from typing import Dict, List
from utils.llm import GroqClient


async def run_debate(pair: str, analyst_reports: Dict[str, str],
                     rounds: int, llm: GroqClient) -> List[dict]:
    """
    Run Bull vs Bear debate for configured number of rounds.
    Returns full transcript of all rounds.
    """

    print(f"\n  Starting Bull vs Bear debate — {rounds} round(s)")

    # Combine all analyst reports
    combined_reports = "\n\n".join([
        f"=== {name} ===\n{report}"
        for name, report in analyst_reports.items()
    ])

    transcript = []

    bull_position = ""
    bear_position = ""

    for round_num in range(1, rounds + 1):
        print(f"    Round {round_num}/{rounds}...")

        # ── BULL makes case ──────────────────────────────────────────
        if round_num == 1:
            bull_prompt = f"""You are the BULL researcher at a forex hedge fund.
Your job is to make the strongest possible case for going LONG (buying) {pair}.

ANALYST REPORTS:
{combined_reports}

Make your opening argument for a BUY position on {pair}.
- Reference specific data from the analyst reports
- Identify the top 3 reasons to buy
- Estimate potential profit target and timeframe
- Be forceful and specific. Under 250 words."""
        else:
            bull_prompt = f"""You are the BULL researcher. The bear has challenged your position.

BEAR'S ARGUMENT:
{bear_position}

ORIGINAL ANALYST REPORTS:
{combined_reports}

Defend your BUY position on {pair} and counter the bear's specific points.
Be specific, cite data, and strengthen your case. Under 200 words."""

        bull_arg = llm.call(bull_prompt)
        time.sleep(1)  # Rate limit buffer

        # ── BEAR makes case ──────────────────────────────────────────
        if round_num == 1:
            bear_prompt = f"""You are the BEAR researcher at a forex hedge fund.
Your job is to make the strongest possible case for going SHORT (selling) {pair}.

ANALYST REPORTS:
{combined_reports}

BULL'S OPENING ARGUMENT:
{bull_arg}

Make your opening argument AGAINST a buy position on {pair}.
- Challenge the bull's specific points
- Identify the top 3 risks/reasons NOT to buy
- Estimate downside risk
- Be forceful and specific. Under 250 words."""
        else:
            bear_prompt = f"""You are the BEAR researcher. The bull has defended their position.

BULL'S ARGUMENT:
{bull_arg}

ORIGINAL ANALYST REPORTS:
{combined_reports}

Maintain your SELL/SHORT position on {pair} and counter the bull's specific points.
Be specific, cite risks, and reinforce your bearish case. Under 200 words."""

        bear_arg = llm.call(bear_prompt)
        time.sleep(1)

        # Save round to transcript
        round_data = {
            "round":        round_num,
            "bull_argument": bull_arg,
            "bear_argument": bear_arg,
        }
        transcript.append(round_data)

        # Update positions for next round
        bull_position = bull_arg
        bear_position = bear_arg

        print(f"    Round {round_num} complete ✓")

    print(f"  Debate complete — {len(transcript)} round(s) recorded")
    return transcript
