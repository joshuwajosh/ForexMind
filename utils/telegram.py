"""
ForexMind — Telegram Notifier (Fixed)
"""

import requests
from datetime import datetime
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


class TelegramNotifier:
    API_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self):
        self.token   = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.enabled = bool(self.token and self.chat_id)

        if self.enabled:
            print("  [Telegram] Notifications enabled ✓")
        else:
            print("  [Telegram] Not configured")

    def send(self, message: str) -> bool:
        """Send a message to Telegram."""
        if not self.enabled:
            return False
        try:
            url = self.API_URL.format(token=self.token)
            payload = {
                "chat_id":    self.chat_id,
                "text":       message,
                "parse_mode": "HTML"
            }
            r = requests.post(url, json=payload, timeout=10)
            return r.status_code == 200
        except Exception as e:
            print(f"  [Telegram] Send failed: {e}")
            return False

    # Fixed — no longer async, works everywhere
    def send_signal(self, pair: str, decision: dict,
                    analyst_reports: dict = None) -> bool:
        """Send formatted trade signal."""
        action     = decision.get("action", "HOLD")
        confidence = decision.get("confidence", 0)
        sl         = decision.get("stop_loss", "N/A")
        tp         = decision.get("take_profit", "N/A")
        size       = decision.get("position_size", 0.01)
        reasoning  = decision.get("reasoning", "")
        now        = datetime.now().strftime("%Y-%m-%d %H:%M")

        emoji = "🟢" if action == "BUY" else "🔴" if action == "SELL" else "⚪"

        message = f"""{emoji} <b>ForexMind Signal</b>

📊 <b>Pair:</b> {pair.replace('_', '/')}
🎯 <b>Action:</b> {action}
📈 <b>Confidence:</b> {confidence}%
📏 <b>Lot Size:</b> {size}
🛑 <b>Stop Loss:</b> {sl}
✅ <b>Take Profit:</b> {tp}

💬 <b>Reasoning:</b>
{str(reasoning)[:300]}

⏰ {now}
🤖 ForexMind AI Bot"""

        return self.send(message)

    def send_order(self, pair: str, action: str, price: float,
                   sl: float, tp: float, size: float, ticket: int) -> bool:
        """Send order placement notification."""
        emoji = "🟢" if action == "BUY" else "🔴"
        message = f"""{emoji} <b>Order Placed on MT5 Demo!</b>

📊 <b>Pair:</b> {pair.replace('_', '/')}
🎯 <b>Action:</b> {action}
💰 <b>Entry Price:</b> {price}
📏 <b>Lot Size:</b> {size}
🛑 <b>Stop Loss:</b> {sl}
✅ <b>Take Profit:</b> {tp}
🎫 <b>Ticket #:</b> {ticket}

⏰ {datetime.now().strftime("%Y-%m-%d %H:%M")}
🤖 ForexMind AI Bot"""
        return self.send(message)

    def send_order_closed(self, pair: str, ticket: int,
                          pnl: float, reason: str) -> bool:
        """Send order closed notification."""
        emoji = "💰" if pnl >= 0 else "📉"
        message = f"""{emoji} <b>Order Closed!</b>

📊 <b>Pair:</b> {pair.replace('_', '/')}
🎫 <b>Ticket #:</b> {ticket}
💵 <b>P&L:</b> {'+'if pnl>=0 else ''}{pnl:.2f} USD
📝 <b>Reason:</b> {reason}

⏰ {datetime.now().strftime("%Y-%m-%d %H:%M")}
🤖 ForexMind AI Bot"""
        return self.send(message)

    def send_startup(self, pairs: list):
        pairs_str = ", ".join([p.replace("_", "/") for p in pairs])
        msg = f"""🚀 <b>ForexMind Started</b>

Monitoring: {pairs_str}
Time: {datetime.now().strftime("%Y-%m-%d %H:%M")}
Status: Running ✓"""
        self.send(msg)

    def send_error(self, pair: str, error: str):
        msg = f"""⚠️ <b>ForexMind Error</b>

Pair: {pair}
Error: {error[:200]}
Time: {datetime.now().strftime("%Y-%m-%d %H:%M")}"""
        self.send(msg)