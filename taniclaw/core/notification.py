"""TaniClaw Notification Service — send alerts via WhatsApp/Telegram/log."""

import logging

import httpx

from taniclaw.core.config import Settings

logger = logging.getLogger("taniclaw.notification")


class NotificationService:
    """Send notifications via multiple channels.

    All notifications are optional and configurable.
    Gracefully degrades to logging if channels not configured.
    """

    def __init__(self, settings: Settings):
        self.settings = settings

    async def send(self, message: str, priority: str = "normal") -> bool:
        """Send notification via all configured channels.

        Priority: "normal", "high", "critical"
        Returns True if at least one channel succeeded.
        """
        if not self.settings.notification_enabled:
            logger.info(f"[NOTIFICATION] {priority.upper()}: {message}")
            return True

        results = []

        if self.settings.telegram_bot_token and self.settings.telegram_chat_id:
            results.append(await self.send_telegram(message))

        if self.settings.whatsapp_api_url and self.settings.whatsapp_api_key:
            results.append(await self.send_whatsapp(message))

        if not results:
            logger.info(f"[NOTIFICATION — no channels configured] {message}")
            return True

        success = any(results)
        if not success:
            logger.error(f"All notification channels failed for message: {message[:50]}")
        return success

    async def send_telegram(self, message: str) -> bool:
        """Send via Telegram Bot API."""
        try:
            url = f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/sendMessage"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json={
                    "chat_id": self.settings.telegram_chat_id,
                    "text": f"🌱 TaniClaw\n\n{message}",
                    "parse_mode": "HTML",
                })
                resp.raise_for_status()
                logger.info("Telegram notification sent")
                return True
        except Exception as e:
            logger.error(f"Telegram notification failed: {e}")
            return False

    async def send_whatsapp(self, message: str) -> bool:
        """Send via WhatsApp API (Fonnte/WA Business)."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    self.settings.whatsapp_api_url,
                    headers={"Authorization": self.settings.whatsapp_api_key},
                    json={"message": f"🌱 TaniClaw\n\n{message}"},
                )
                resp.raise_for_status()
                logger.info("WhatsApp notification sent")
                return True
        except Exception as e:
            logger.error(f"WhatsApp notification failed: {e}")
            return False

    def format_daily_summary(self, plant_name: str, actions: list[dict]) -> str:
        """Format a daily summary message from action results."""
        lines = [f"📋 Ringkasan Harian — {plant_name}", ""]
        if not actions:
            lines.append("✅ Tidak ada tindakan diperlukan hari ini.")
        else:
            for action in actions:
                action_type = action.get("type", "")
                description = action.get("description", "")
                emoji = {
                    "water": "💧",
                    "skip_water": "⏭️",
                    "fertilize": "🌿",
                    "harvest": "🌾",
                    "notify": "🔔",
                    "alert": "⚠️",
                    "log": "📝",
                }.get(action_type, "•")
                lines.append(f"{emoji} {description}")
        return "\n".join(lines)

    def format_alert(self, alert: dict) -> str:
        """Format an alert message."""
        return f"⚠️ PERINGATAN TANICLAW\n\n{alert.get('description', 'Peringatan tidak diketahui')}"
