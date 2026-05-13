"""
ForexMind - Main Orchestrator (ENHANCED)
Analyzes forex pairs and places trades on MT5 demo with dynamic position sizing.

Usage:
  python main.py                        -- runs all pairs
  python main.py --pair EUR_USD         -- single pair
  python main.py --pair EUR_USD --rounds 2
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# -- Add project root to path -------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import MAJOR_PAIRS, DEFAULT_TIMEFRAMES, DEFAULT_LOT_SIZE
from utils.llm import get_llm
from utils.telegram import TelegramNotifier
from utils.mt5_executor import MT5Executor
from data.fetcher import MT5Client as DataFetcher
from data.indicators import get_all_indicators
from agents.analysts import run_analysts
from agents.researchers import run_debate
from agents.execution import run_execution_pipeline
from memory.manager import MemoryManager


def print_header():
    print("")
    print("=" * 60)
    print("  ForexMind AI Trading Bot (Enhanced)")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


def print_separator(title=""):
    print("")
    if title:
        print(f"  --- {title} ---")
    else:
        print("  " + "-" * 40)


async def analyze_pair(pair, rounds, llm, fetcher, executor, telegram, memory):
    """
    Full analysis pipeline for one currency pair.
    Returns the final decision dict or None on failure.
    """
    print_separator(f"Analyzing {pair}")

    # -- Step 1: Check for existing open position -----------------------------
    existing = executor.get_open_positions(pair)
    if existing:
        print(f"  [Main] Position already open for {pair} -- skipping")
        for pos in existing:
            print(f"    Ticket #{pos['ticket']} | {pos['type']} | P&L: ${pos['profit']}")
        return None

    # -- Step 2: Fetch market data --------------------------------------------
    print(f"  [Main] Fetching data for {pair}...")
    data = {}
    for tf in DEFAULT_TIMEFRAMES:
        try:
            ohlcv = fetcher.get_candles(pair, tf)
            if ohlcv:
                data[tf] = ohlcv
                print(f"    Got {len(ohlcv)} bars for {tf}")
        except Exception as e:
            print(f"    WARNING: No data for {pair} {tf}: {e}")

    if not data:
        print(f"  [Main] ERROR: No data at all for {pair} -- skipping")
        return None

    # -- Step 3: Calculate indicators -----------------------------------------
    print(f"  [Main] Calculating indicators...")
    indicators = {}
    current_indicators = None
    for tf, ohlcv in data.items():
        try:
            indicators[tf] = get_all_indicators(ohlcv)
            if tf == DEFAULT_TIMEFRAMES[0]:  # Use first timeframe for market context
                current_indicators = indicators[tf]
        except Exception as e:
            print(f"    WARNING: Indicator error for {tf}: {e}")

    # -- Step 4: Run 4 analysts in parallel -----------------------------------
    print(f"  [Main] Running 4 analysts for {pair}...")
    try:
        analysis = await run_analysts(pair, DEFAULT_TIMEFRAMES, llm)
        analyst_list = list(analysis.items())
        for name, report in analyst_list:
            preview = str(report)[:50] if report else "N/A"
            print(f"    {name}: {preview}...")
    except Exception as e:
        print(f"  [Main] Analysts error: {e}")
        analysis = {}

    # -- Step 5: Bull vs Bear debate with market context ----------------------
    print(f"  [Main] Running Bull vs Bear debate ({rounds} rounds)...")
    try:
        debate_result = await run_debate(pair, analysis, rounds, llm, current_indicators)
        lean = debate_result.get("lean", "NEUTRAL")
        conf = debate_result.get("confidence", 50)
        print(f"    Debate lean: {lean} ({conf}% confidence)")
    except Exception as e:
        print(f"  [Main] Debate error: {e}")
        debate_result = {"lean": "NEUTRAL", "confidence": 50, "transcript": []}

    # -- Step 6: Load trade history for context ------
    history = []
    try:
        history = memory.get_history(pair)[-5:]  # Last 5 trades
    except Exception as e:
        print(f"  [Main] History note: {e}")

    # -- Step 7: Execution pipeline (Trader -> Risk Mgr -> Portfolio Mgr) -----
    print(f"  [Main] Running execution pipeline...")
    try:
        decision = await run_execution_pipeline(pair, analysis, debate_result, history, llm)
        print(f"    Action:     {decision.get('action', 'N/A')}")
        print(f"    Confidence: {decision.get('confidence', 'N/A')}%")
        print(f"    Position:   {decision.get('position_size', 'N/A')} lots")
    except Exception as e:
        print(f"  [Main] Execution error: {e}")
        decision = {"action": "HOLD", "confidence": 0, "position_size": 0}

    # -- Step 8: Place order if BUY or SELL -----------------------------------
    action = decision.get("action", "HOLD").upper()

    if action in ("BUY", "SELL"):
        # Double-check no position opened
        existing_now = executor.get_open_positions(pair)
        if existing_now:
            print(f"  [Main] Position already opened -- skipping")
        else:
            print(f"  [Main] Placing {action} order for {pair}...")
            size = decision.get("position_size", DEFAULT_LOT_SIZE)
            order_result = executor.place_order(
                pair=pair,
                action=action,
                size=size,
                sl=decision.get("sl", 0),
                tp=decision.get("tp", 0),
            )
            decision["order_result"] = order_result
            if order_result.get("success"):
                print(f"  [Main] ✓ Order placed -- Ticket #{order_result.get('ticket')}")
            else:
                print(f"  [Main] ✗ Order failed -- {order_result.get('reason')}")
    else:
        print(f"  [Main] Decision is HOLD -- no order placed")

    # -- Step 9: Send Telegram alert ------------------------------------------
    try:
        telegram.send_signal(
            pair=pair,
            action=action,
            confidence=decision.get("confidence", 0),
            reasoning=decision.get("reasoning", ""),
        )
    except Exception as e:
        print(f"  [Main] Telegram warning: {e}")

    # -- Step 10: Save to memory -----------------------------------------------
    try:
        memory.save_decision(pair, decision, analysis, debate_result.get("transcript", []))
    except Exception as e:
        print(f"  [Main] Memory warning: {e}")

    return decision


async def main():
    # -- Parse arguments ------------------------------------------------------
    parser = argparse.ArgumentParser(description="ForexMind AI Bot")
    parser.add_argument("--pair",   type=str, default=None,
                        help="Single pair to analyze e.g. EUR_USD")
    parser.add_argument("--rounds", type=int, default=2,
                        help="Debate rounds (default: 2)")
    args = parser.parse_args()

    print_header()

    # -- Initialize components ------------------------------------------------
    print_separator("Initializing")

    print("  [Main] Loading LLM client...")
    llm = get_llm()

    print("  [Main] Connecting to MT5...")
    telegram = TelegramNotifier()
    executor = MT5Executor(telegram=telegram)

    print("  [Main] Setting up data fetcher...")
    fetcher = DataFetcher()

    print("  [Main] Loading memory manager...")
    memory = MemoryManager()

    # -- Determine pairs to run -----------------------------------------------
    if args.pair:
        pairs = [args.pair.upper().replace("/", "_")]
    else:
        pairs = MAJOR_PAIRS

    print(f"  [Main] Pairs to analyze: {pairs}")
    print(f"  [Main] Debate rounds: {args.rounds}")

    # -- Run analysis for each pair -------------------------------------------
    results = {}
    for pair in pairs:
        try:
            result = await analyze_pair(
                pair=pair,
                rounds=args.rounds,
                llm=llm,
                fetcher=fetcher,
                executor=executor,
                telegram=telegram,
                memory=memory,
            )
            results[pair] = result
        except Exception as e:
            print(f"  [Main] ERROR for {pair}: {e}")
            results[pair] = None
        time.sleep(2)

    # -- Summary --------------------------------------------------------------
    print_separator("Summary")
    for pair, result in results.items():
        if result is None:
            print(f"  {pair}: ERROR or SKIPPED")
        else:
            action = result.get("action", "N/A")
            conf   = result.get("confidence", 0)
            size   = result.get("position_size", 0)
            print(f"  {pair}: {action} ({conf}%) | {size} lots")

    print(f"\n  Run complete: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
