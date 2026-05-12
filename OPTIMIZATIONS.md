"""
ForexMind Optimization Report
Changes to improve trade frequency and decision quality
Generated: 2026-05-12
"""

# ============================================================================
# PROBLEM ANALYSIS (from your logs)
# ============================================================================

PROBLEMS_IDENTIFIED = {
    "High HOLD Rate": {
        "issue": "75% of decisions are HOLD due to analyst disagreement",
        "root_cause": "Threshold too high (60%) + risk manager too conservative",
        "impact": "Few trades = limited learning + small profits"
    },
    "Risk Manager Gate": {
        "issue": "Rejecting 50% confidence trades is too strict",
        "root_cause": "MIN_CONFIDENCE = 60%, but analysts rarely reach this",
        "impact": "Good trades blocked"
    },
    "Analyst Conflicts": {
        "issue": "4 analysts often disagree (2 BUY vs 2 SELL vs 2 HOLD)",
        "root_cause": "Equal weighting despite different accuracy rates",
        "impact": "No clear direction = HOLD decision"
    },
    "One-Size-Fits-All": {
        "issue": "All trades use 0.01 lot regardless of confidence",
        "root_cause": "No dynamic position sizing",
        "impact": "High confidence trades under-leveraged"
    }
}

# ============================================================================
# SOLUTIONS IMPLEMENTED (Commits Made)
# ============================================================================

SOLUTIONS = {
    "1. Lower Trade Threshold": {
        "change": "MIN_CONFIDENCE_TO_TRADE: 60% → 55%",
        "file": "config/settings.py",
        "effect": "More trades executed, faster learning",
        "risk": "Lower quality trades, but acceptable for demo"
    },
    
    "2. Dynamic Position Sizing": {
        "change": "Position size now scales with confidence: 55%=0.01, 80%+=0.05",
        "file": "agents/execution.py → get_position_size()",
        "effect": "High confidence trades get better reward",
        "function": """
        55-60% confidence: 0.01 lot (mini)
        60-70% confidence: 0.02 lot (small)
        70-80% confidence: 0.03 lot (medium)
        80%+ confidence: 0.05 lot (normal)
        """
    },
    
    "3. Aggressive Trader Prompts": {
        "change": "LLM told to MINIMIZE HOLDs, be decisive",
        "file": "agents/execution.py → trader_agent()",
        "effect": "Trader pushes for BUY/SELL instead of HOLD",
        "prompt_change": """
        OLD: "Only say HOLD if signals are completely mixed 50/50"
        NEW: "Only say HOLD if signals are completely neutral (rare!)" +
             "Be DECISIVE! Markets reward action."
        """
    },
    
    "4. Analyst Performance Tracking": {
        "change": "New weights file tracks each analyst's historical accuracy",
        "file": "memory/manager.py + utils/analyst_calibrator.py",
        "effect": "Over time, better analysts get higher weight in decisions",
        "mechanism": """
        After each trade closes:
        - Analyst who was RIGHT gets weight boost (up to 1.3x)
        - Analyst who was WRONG gets weight reduction (down to 0.7x)
        - Affects future decision confidence scores
        """
    },
    
    "5. Better Risk Manager Logic": {
        "change": "Risk manager now uses confidence-based approval",
        "file": "agents/execution.py → risk_manager()",
        "effect": "Aligned risk thresholds with trade confidence",
        "logic": "Approve if confidence >= 55% (was 60%)"
    },
    
    "6. Portfolio Manager Override": {
        "change": "Can override risk rejection if confidence >= 75%",
        "file": "agents/execution.py → portfolio_manager()",
        "effect": "High-conviction trades still execute",
        "logic": "confidence >= 75% → execute despite risk objection"
    }
}

# ============================================================================
# EXPECTED IMPROVEMENTS
# ============================================================================

EXPECTED_RESULTS = {
    "Trade Frequency": {
        "before": "20-30% execution rate (mostly HOLDs)",
        "after": "40-50% execution rate",
        "timeline": "Immediate (next run_auto.py)"
    },
    
    "Position Sizing": {
        "before": "All trades: 0.01 lot (limited upside)",
        "after": "High-confidence trades: 0.03-0.05 lots",
        "example": "85% confidence trade now uses 0.05 lot (+5x leverage for conviction)"
    },
    
    "Analyst Calibration": {
        "before": "All analysts weighted equally",
        "after": "Top performer gets 1.3x weight, poor performer gets 0.8x",
        "timeline": "Improves over 20-30 trades as history builds"
    },
    
    "Decision Time": {
        "before": "30-40 seconds per pair",
        "after": "30-40 seconds per pair (no change)",
        "reason": "Logic simplified, no performance impact"
    },
    
    "Win Rate": {
        "estimate": "Should improve 5-15% over baseline",
        "reason": "More informed position sizing + analyst weighting",
        "caveat": "Depends on market conditions"
    }
}

# ============================================================================
# TESTING PROCEDURE
# ============================================================================

TESTING_STEPS = """
1. Backup current memory:
   cp -r memory/data memory/data.bak
   
2. Run updated main.py on single pair:
   python main.py --pair EUR_USD
   
3. Check logs for:
   ✓ Trader proposing higher confidence (70%+)
   ✓ More BUY/SELL decisions (fewer HOLDs)
   ✓ Risk Manager approving at 55% threshold
   ✓ Position sizes varying with confidence
   
4. Run auto runner:
   python run_auto.py
   
5. Monitor:
   - Check memory/data/decisions.json for decision details
   - Count BUY/SELL vs HOLD ratio
   - Watch trailing_stop.py to see positions managed
   
6. After 10 trades close:
   - Check analyst_weights.json for performance tracking
   - Compare win rates across analysts
"""

# ============================================================================
# FINE-TUNING PARAMETERS (if still too many HOLDs)
# ============================================================================

TUNING_OPTIONS = {
    "If still >60% HOLDs": {
        "option_1": "Lower MIN_CONFIDENCE_TO_TRADE to 50%",
        "option_2": "Increase TEMPERATURE from 0.3 to 0.5 (more creative LLM)",
        "option_3": "Adjust trader prompt to be even more aggressive"
    },
    
    "If too many losing trades": {
        "option_1": "Raise MIN_CONFIDENCE_TO_TRADE back to 60%",
        "option_2": "Increase risk_score requirement in risk_manager",
        "option_3": "Add position filter: skip if < 3 hours since last trade"
    },
    
    "If high-confidence trades underperforming": {
        "option_1": "Check stop-loss placement (might be too tight)",
        "option_2": "Verify take-profit multiples (risk:reward)",
        "option_3": "Review analyst accuracy — might need analyst weight reset"
    }
}

# ============================================================================
# NEXT PHASE OPTIMIZATIONS (Future)
# ============================================================================

FUTURE_IMPROVEMENTS = """
Phase 2 - Pattern Recognition:
[ ] Track which analyst combinations produce best results (e.g., Tech+Sentiment)
[ ] Learn pair-specific patterns (USD_JPY might need different weightings)
[ ] Add news sentiment scoring to weight News Analyst higher on economic days

Phase 3 - Market Regime Detection:
[ ] Detect trending vs ranging markets
[ ] Adjust confidence thresholds per regime
[ ] Use different analyst weights for different market conditions

Phase 4 - Portfolio Optimization:
[ ] Limit correlated pairs (e.g., EUR_USD + GBP_USD both long)
[ ] Dynamic lot sizing per account equity (Kelly Criterion variant)
[ ] Stop-loss clustering prevention

Phase 5 - Live Trading:
[ ] Reduce lot size from demo levels (0.05 → 0.001)
[ ] Add hard stops for daily loss limits
[ ] Implement Telegram alerts for risk threshold breaches
"""

# ============================================================================
# KEY METRICS TO MONITOR
# ============================================================================

METRICS = {
    "Daily": [
        "Trade count (target: 4-6 per day)",
        "BUY vs SELL ratio (target: roughly balanced)",
        "Hold rate % (target: <40%)",
        "Average confidence % (target: 65-75%)"
    ],
    
    "Weekly": [
        "Win rate % (target: >50%)",
        "Avg win vs avg loss ratio (target: >1.5:1)",
        "Total P&L",
        "Analyst accuracy scores (from analyst_weights.json)"
    ],
    
    "Monthly": [
        "Sharpe ratio approximation",
        "Max drawdown",
        "Analyst weight distribution (see which analysts are improving)",
        "Pair-specific performance (which pairs trade best?)"
    ]
}

print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                  ForexMind Optimization Complete ✓                        ║
║                                                                            ║
║  Key Changes:                                                             ║
║  • Trade threshold: 60% → 55% (increases opportunities)                  ║
║  • Position sizing: Dynamic (higher confidence = bigger position)         ║
║  • Analyst weighting: Tracks historical accuracy                         ║
║  • Decision making: More aggressive, fewer HOLDs                         ║
║                                                                            ║
║  Next step: Run main.py and monitor for improved trade frequency         ║
╚════════════════════════════════════════════════════════════════════════════╝
""")
