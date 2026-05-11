"""
ForexMind - Clear pending decisions from memory
Run this once to reset the decision log
"""
import json
import os

DECISION_LOG = "memory/data/decisions.json"

if os.path.exists(DECISION_LOG):
    with open(DECISION_LOG, "r") as f:
        decisions = json.load(f)
    
    print(f"Found {len(decisions)} decisions in memory")
    
    # Keep only last 3 decisions per pair
    from collections import defaultdict
    by_pair = defaultdict(list)
    for d in decisions:
        by_pair[d.get("pair", "UNKNOWN")].append(d)
    
    kept = []
    for pair, trades in by_pair.items():
        last3 = trades[-3:]
        kept.extend(last3)
        print(f"  {pair}: kept last {len(last3)} of {len(trades)}")
    
    # Re-number
    for i, d in enumerate(kept, 1):
        d["id"] = i
    
    with open(DECISION_LOG, "w") as f:
        json.dump(kept, f, indent=2)
    
    print(f"\nDone! Memory reduced from {len(decisions)} to {len(kept)} decisions")
    print("Now run: python run_auto.py")
else:
    print("No memory file found — nothing to clear")
