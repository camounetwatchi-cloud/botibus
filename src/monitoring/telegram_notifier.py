"""
Telegram Notifier for Trading Bot.

Sends notifications for:
- Trade opened/closed
- Daily summaries
- Critical alerts (errors, daily loss limit, etc.)
"""
import asyncio
from datetime import datetime
from typing import Dict, Optional
from loguru import logger

try:
    from telegram import Bot
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.debug("python-telegram-bot not installed - notifications disabled")

from src.config.settings import settings


class TelegramNotifier:
    """
    Telegram notification sender for trading events.
    
    Handles rate limiting and message formatting.
    """
    
    MAX_MESSAGES_PER_MINUTE = 20
    
    def __init__(self, bot_token: str = None, chat_id: str = None):
        """
        Initialize Telegram notifier.
        
        Args:
            bot_token: Telegram bot token (from BotFather)
            chat_id: Chat ID to send messages to
        """
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or settings.TELEGRAM_CHAT_ID
        self.enabled = bool(self.bot_token and self.chat_id and TELEGRAM_AVAILABLE)
        self.message_count = 0
        self.last_reset = datetime.now()
        
        if self.enabled:
            self.bot = Bot(token=self.bot_token)
            logger.info("✅ Telegram notifications enabled")
        else:
            self.bot = None
            if not TELEGRAM_AVAILABLE:
                logger.debug("Telegram disabled: python-telegram-bot not installed")
            elif not self.bot_token:
                logger.debug("Telegram disabled: TELEGRAM_BOT_TOKEN not set")
            elif not self.chat_id:
                logger.debug("Telegram disabled: TELEGRAM_CHAT_ID not set")
    
    async def _send(self, text: str, parse_mode: str = "HTML") -> bool:
        """
        Send a message with rate limiting.
        
        Args:
            text: Message text
            parse_mode: 'HTML' or 'Markdown'
            
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            return False
        
        # Rate limiting
        now = datetime.now()
        if (now - self.last_reset).seconds >= 60:
            self.message_count = 0
            self.last_reset = now
        
        if self.message_count >= self.MAX_MESSAGES_PER_MINUTE:
            logger.warning("Telegram rate limit reached")
            return False
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=parse_mode
            )
            self.message_count += 1
            return True
        except TelegramError as e:
            logger.error(f"Telegram send failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Telegram error: {e}")
            return False
    
    async def notify_trade_opened(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        confidence: float = 0
    ):
        """
        Send notification when a trade is opened.
        
        Args:
            symbol: Trading pair
            side: 'BUY' or 'SELL'
            amount: Position size
            price: Entry price
            confidence: Signal confidence
        """
        emoji = "🟢" if side.upper() == "BUY" else "🔴"
        side_text = "ACHAT" if side.upper() == "BUY" else "VENTE"
        value = amount * price
        
        message = f"""
{emoji} <b>{side_text}</b> {symbol}

💰 Montant: <code>{amount:.6f}</code>
📊 Prix: <code>€{price:,.2f}</code>
💵 Valeur: <code>€{value:,.2f}</code>
📈 Confiance: <code>{confidence:.0%}</code>
🕐 {datetime.now().strftime('%H:%M:%S')}
"""
        await self._send(message.strip())
    
    async def notify_trade_closed(
        self,
        symbol: str,
        side: str,
        pnl: float,
        pnl_pct: float,
        reason: str,
        duration_hours: float = 0
    ):
        """
        Send notification when a trade is closed.
        
        Args:
            symbol: Trading pair
            side: Original position side
            pnl: Realized PnL in EUR
            pnl_pct: PnL percentage
            reason: Close reason (TP, SL, etc.)
            duration_hours: Trade duration
        """
        if pnl >= 0:
            emoji = "✅"
            pnl_text = f"+€{pnl:.2f}"
        else:
            emoji = "❌"
            pnl_text = f"-€{abs(pnl):.2f}"
        
        reason_emoji = {
            'take_profit': '🎯',
            'stop_loss': '🛑',
            'trailing_stop': '📉',
            'signal_reversal': '🔄',
            'manual': '✋'
        }.get(reason.lower(), '📊')
        
        message = f"""
{emoji} <b>CLOTURE</b> {symbol}

💰 PnL: <code>{pnl_text}</code> ({pnl_pct:+.2f}%)
{reason_emoji} Raison: {reason.replace('_', ' ').title()}
⏱️ Durée: {duration_hours:.1f}h
🕐 {datetime.now().strftime('%H:%M:%S')}
"""
        await self._send(message.strip())
    
    async def daily_summary(
        self,
        total_pnl: float,
        total_trades: int,
        win_rate: float,
        balance: float,
        top_winner: Optional[Dict] = None,
        worst_loser: Optional[Dict] = None
    ):
        """
        Send daily performance summary.
        
        Args:
            total_pnl: Total PnL for the day
            total_trades: Number of trades
            win_rate: Win rate percentage
            balance: Current balance
            top_winner: Best trade of the day
            worst_loser: Worst trade of the day
        """
        pnl_emoji = "📈" if total_pnl >= 0 else "📉"
        pnl_text = f"+€{total_pnl:.2f}" if total_pnl >= 0 else f"-€{abs(total_pnl):.2f}"
        
        message = f"""
📊 <b>RÉSUMÉ JOURNALIER</b>

{pnl_emoji} PnL: <code>{pnl_text}</code>
💼 Balance: <code>€{balance:,.2f}</code>
📈 Trades: {total_trades}
🎯 Win Rate: {win_rate:.0%}
"""
        
        if top_winner:
            message += f"\n🏆 Meilleur: {top_winner['symbol']} (+€{top_winner['pnl']:.2f})"
        
        if worst_loser and worst_loser['pnl'] < 0:
            message += f"\n😓 Pire: {worst_loser['symbol']} (-€{abs(worst_loser['pnl']):.2f})"
        
        message += f"\n\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        await self._send(message.strip())
    
    async def alert_critical(self, message: str, alert_type: str = "error"):
        """
        Send critical alert.
        
        Args:
            message: Alert message
            alert_type: 'error', 'warning', 'limit_reached'
        """
        emoji = {
            'error': '🚨',
            'warning': '⚠️',
            'limit_reached': '🛑',
            'connection': '📡'
        }.get(alert_type, '❗')
        
        text = f"""
{emoji} <b>ALERTE CRITIQUE</b>

{message}

🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        await self._send(text.strip())
    
    async def alert_daily_loss_limit(self, current_loss: float, limit: float):
        """Send alert when daily loss limit is reached."""
        await self.alert_critical(
            f"Daily loss limit reached!\n"
            f"Perte: €{abs(current_loss):.2f}\n"
            f"Limite: €{limit:.2f}\n"
            f"Trading suspendu pour aujourd'hui.",
            alert_type='limit_reached'
        )
    
    async def test_connection(self) -> bool:
        """
        Test Telegram connection with a simple message.
        
        Returns:
            True if message was sent successfully
        """
        return await self._send("🤖 Trading bot connected!")


# Convenience function
def create_notifier() -> TelegramNotifier:
    """Create TelegramNotifier with settings from environment."""
    return TelegramNotifier()


# CLI test
if __name__ == "__main__":
    async def test():
        notifier = TelegramNotifier()
        if notifier.enabled:
            success = await notifier.test_connection()
            print(f"Connection test: {'✅ Success' if success else '❌ Failed'}")
        else:
            print("Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
    
    asyncio.run(test())
