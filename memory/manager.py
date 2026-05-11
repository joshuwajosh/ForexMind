"""
ForexMind — Memory Manager
Persistent JSON decision log + trade history + reflections
"""

import json
import os
from datetime import datetime
from typing import Optional

from config.settings import MEMORY_DIR, DECISION_LOG, TRADE_HISTORY


class MemoryManager:
    def __init__(self):
        os.makedirs(MEMORY_DIR, exist_ok=True)
        self._init_files()

    def _init_files(self):
        for filepath in [DECISION_LOG, TRADE_HISTORY]:
            if not os.path.exists(filepath):
                with open(filepath, "w") as f:
                    json.dump([], f)

    def _load(self, filepath: str) -> list:
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except Exception:
            return []

    def _save(self, filepath: str, data: list):
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def save_decision(self, pair: str, decision: dict,
                      analyst_reports: dict, debate_transcript: list):
        """Save a completed decision to the log."""
        decisions = self._load(DECISION_LOG)

        record = {
            "id":               len(decisions) + 1,
            "date":             datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "pair":             pair,
            "action":           decision.get("action", "HOLD"),
            "confidence":       decision.get("confidence", 0),
            "stop_loss":        decision.get("stop_loss", "N/A"),
            "take_profit":      decision.get("take_profit", "N/A"),
            "position_size":    decision.get("position_size", 0.01),
            "reasoning":        decision.get("reasoning", ""),
            "analyst_summary": {
                name: report[:200] for name, report in analyst_reports.items()
            },
            "debate_rounds":    len(debate_transcript),
            "outcome":          "pending",
            "reflection":       "",
        }

        decisions.append(record)
        self._save(DECISION_LOG, decisions)
        print(f"\n  Memory saved — Decision #{record['id']} logged")

    def get_history(self, pair: str) -> list:
        """Get all prior decisions for a specific pair."""
        decisions = self._load(DECISION_LOG)
        return [d for d in decisions if d.get("pair") == pair]

    def update_outcome(self, decision_id: int, outcome: str,
                       pnl: float, reflection: str = ""):
        """Update a decision with its actual outcome (call manually after trade closes)."""
        decisions = self._load(DECISION_LOG)
        for d in decisions:
            if d.get("id") == decision_id:
                d["outcome"]    = outcome
                d["pnl"]        = pnl
                d["reflection"] = reflection
                d["closed_at"]  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                break
        self._save(DECISION_LOG, decisions)

    def get_stats(self) -> dict:
        """Get overall portfolio statistics."""
        decisions = self._load(DECISION_LOG)
        if not decisions:
            return {}

        buys  = sum(1 for d in decisions if d.get("action") == "BUY")
        sells = sum(1 for d in decisions if d.get("action") == "SELL")
        holds = sum(1 for d in decisions if d.get("action") == "HOLD")

        by_pair = {}
        for d in decisions:
            p = d.get("pair", "UNKNOWN")
            by_pair[p] = by_pair.get(p, 0) + 1

        # PnL stats for closed trades
        closed = [d for d in decisions if d.get("outcome") != "pending"]
        total_pnl = sum(d.get("pnl", 0) for d in closed)

        return {
            "total":    len(decisions),
            "buys":     buys,
            "sells":    sells,
            "holds":    holds,
            "by_pair":  by_pair,
            "closed":   len(closed),
            "total_pnl": round(total_pnl, 2),
        }

    def get_recent(self, n: int = 5) -> list:
        """Get n most recent decisions."""
        decisions = self._load(DECISION_LOG)
        return decisions[-n:]
