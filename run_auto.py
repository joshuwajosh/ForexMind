"""
ForexMind Auto Runner
Runs analysis every 15 minutes automatically
Press Ctrl+C to stop
"""

import subprocess
import time
from datetime import datetime

PAIRS    = ["EUR_USD", "GBP_USD", "USD_JPY"]
INTERVAL = 1 * 60  # 15 minutes in seconds

print("""
╔══════════════════════════════════════════════════════╗
║         ForexMind Auto Runner                        ║
║   Runs every 15 minutes — Press Ctrl+C to stop      ║
╚══════════════════════════════════════════════════════╝
""")

run_count = 0

while True:
    run_count += 1
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*54}")
    print(f"  AUTO RUN #{run_count} — {now}")
    print(f"{'='*54}")

    for pair in PAIRS:
        print(f"\n  Running {pair}...")
        subprocess.run([
            "python", "main.py",
            "--pair", pair,
            "--rounds", "2"
        ])
        time.sleep(10)  # 10 sec between pairs

    next_run = datetime.now().strftime("%H:%M:%S")
    print(f"\n  ✅ Run #{run_count} complete!")
    print(f"  ⏰ Next run in 15 minutes...")
    print(f"  💤 Sleeping until next cycle...")

    time.sleep(INTERVAL)