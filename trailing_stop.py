"""
ForexMind - Trailing Stop Loss Manager
Moves SL automatically as price moves in profit direction
Runs as background monitor alongside main bot
"""

import time
import json
import os
from datetime import datetime

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

# ── Trailing Stop Settings ────────────────────────────────────────────
TRAIL_PIPS         = 20    # SL trails price by this many pips
BREAKEVEN_PIPS     = 15    # Move SL to breakeven after this many pips profit
MIN_PROFIT_PIPS    = 5     # Lock minimum this many pips profit
CHECK_INTERVAL     = 10    # Check every 10 seconds
MAGIC_NUMBER       = 234000  # Must match mt5_executor.py

# Pip value per symbol
PIP_SIZE = {
    "EURUSD": 0.0001,
    "GBPUSD": 0.0001,
    "USDJPY": 0.01,
    "USDCHF": 0.0001,
    "AUDUSD": 0.0001,
    "NZDUSD": 0.0001,
    "USDCAD": 0.0001,
    "EURGBP": 0.0001,
    "EURJPY": 0.01,
    "GBPJPY": 0.01,
}


def get_pip(symbol):
    return PIP_SIZE.get(symbol, 0.0001)


def connect_mt5():
    if not MT5_AVAILABLE:
        return False
    if not mt5.initialize():
        print(f"[Trail] MT5 init failed: {mt5.last_error()}")
        return False
    print("[Trail] MT5 connected ✓")
    return True


def get_forexmind_positions():
    """Get all open ForexMind positions."""
    if not MT5_AVAILABLE:
        return []
    positions = mt5.positions_get()
    if not positions:
        return []
    return [p for p in positions if p.magic == MAGIC_NUMBER]


def update_trailing_stop(position):
    """
    Update trailing stop for a single position.
    
    Logic:
    1. If price moved TRAIL_PIPS in profit → move SL up by same amount
    2. If profit >= BREAKEVEN_PIPS → move SL to breakeven (entry price)
    3. SL never moves against us (only in profit direction)
    """
    symbol    = position.symbol
    ticket    = position.ticket
    pos_type  = position.type   # 0=BUY, 1=SELL
    entry     = position.price_open
    current_sl = position.sl
    current_tp = position.tp
    pip       = get_pip(symbol)

    # Get current price
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return False

    current_price = tick.bid if pos_type == 0 else tick.ask

    # Calculate profit in pips
    if pos_type == 0:  # BUY
        profit_pips = (current_price - entry) / pip
        new_sl = current_price - (TRAIL_PIPS * pip)
        new_sl = round(new_sl, 5)

        # Only move SL UP (never down for BUY)
        if new_sl <= current_sl:
            return False

        # Breakeven logic
        if profit_pips >= BREAKEVEN_PIPS:
            breakeven_sl = entry + (MIN_PROFIT_PIPS * pip)
            breakeven_sl = round(breakeven_sl, 5)
            new_sl = max(new_sl, breakeven_sl)

    else:  # SELL
        profit_pips = (entry - current_price) / pip
        new_sl = current_price + (TRAIL_PIPS * pip)
        new_sl = round(new_sl, 5)

        # Only move SL DOWN (never up for SELL)
        if new_sl >= current_sl:
            return False

        # Breakeven logic
        if profit_pips >= BREAKEVEN_PIPS:
            breakeven_sl = entry - (MIN_PROFIT_PIPS * pip)
            breakeven_sl = round(breakeven_sl, 5)
            new_sl = min(new_sl, breakeven_sl)

    # Only update if SL has moved meaningfully (at least 1 pip)
    if abs(new_sl - current_sl) < pip:
        return False

    # Send modify order request
    request = {
        "action":   mt5.TRADE_ACTION_SLTP,
        "position": ticket,
        "sl":       new_sl,
        "tp":       current_tp,
    }

    result = mt5.order_send(request)

    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        direction = "BUY" if pos_type == 0 else "SELL"
        print(f"  [Trail] ✅ {symbol} {direction} #{ticket}")
        print(f"         Price: {current_price:.5f}")
        print(f"         Profit: +{profit_pips:.1f} pips")
        print(f"         SL: {current_sl:.5f} → {new_sl:.5f}")
        return True
    else:
        retcode = result.retcode if result else "None"
        print(f"  [Trail] ❌ Failed to update SL: retcode {retcode}")
        return False


def send_telegram(message):
    """Send Telegram notification."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        token   = os.getenv("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        if not token or not chat_id:
            return
        import requests
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
    except Exception:
        pass


def run_trailing_monitor():
    """Main monitoring loop — runs forever."""

    print("""
╔══════════════════════════════════════════════════════╗
║      ForexMind Trailing Stop Monitor                 ║
║   Trails SL automatically as price moves in profit  ║
║   Press Ctrl+C to stop                              ║
╚══════════════════════════════════════════════════════╝
""")
    print(f"  Trail distance : {TRAIL_PIPS} pips")
    print(f"  Breakeven after: {BREAKEVEN_PIPS} pips profit")
    print(f"  Min profit lock: {MIN_PROFIT_PIPS} pips")
    print(f"  Check every   : {CHECK_INTERVAL} seconds")
    print()

    if not connect_mt5():
        print("[Trail] Cannot connect to MT5. Is MT5 running?")
        return

    send_telegram(
        "🔄 <b>Trailing Stop Monitor Started</b>\n"
        f"Trail: {TRAIL_PIPS} pips | Breakeven: {BREAKEVEN_PIPS} pips\n"
        f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )

    check_count = 0

    while True:
        try:
            check_count += 1
            positions = get_forexmind_positions()

            if positions:
                updated = 0
                for pos in positions:
                    result = update_trailing_stop(pos)
                    if result:
                        updated += 1

                if check_count % 6 == 0:  # Print status every minute
                    now = datetime.now().strftime("%H:%M:%S")
                    print(f"\n  [{now}] Monitoring {len(positions)} position(s)...")
                    for pos in positions:
                        tick = mt5.symbol_info_tick(pos.symbol)
                        price = tick.bid if pos.type == 0 else tick.ask
                        pip = get_pip(pos.symbol)
                        if pos.type == 0:
                            pips = (price - pos.price_open) / pip
                        else:
                            pips = (pos.price_open - price) / pip
                        direction = "BUY" if pos.type == 0 else "SELL"
                        pnl_sign = "+" if pos.profit >= 0 else ""
                        print(f"    {pos.symbol} {direction} | "
                              f"P&L: {pnl_sign}{pos.profit:.2f}$ | "
                              f"Pips: {pips:+.1f} | "
                              f"SL: {pos.sl:.5f}")

            else:
                if check_count % 18 == 0:  # Print every 3 min when no positions
                    now = datetime.now().strftime("%H:%M:%S")
                    print(f"  [{now}] No ForexMind positions open. Waiting...")

            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print("\n\n  Trailing stop monitor stopped.")
            send_telegram("⛔ Trailing Stop Monitor stopped.")
            break
        except Exception as e:
            print(f"  [Trail] Error: {e}")
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    run_trailing_monitor()
