"""Continuous monitoring service for registered Clarvia profiles.

Periodically re-scans registered profiles and detects score changes.
Supports webhook and email notification stubs.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Default re-scan interval: 24 hours
DEFAULT_INTERVAL_SECONDS = 86400

# Score change threshold for triggering notifications
SCORE_CHANGE_THRESHOLD = 5


class MonitorService:
    """Watches registered profiles and re-scans them periodically."""

    def __init__(
        self,
        interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
        webhook_url: str | None = None,
        email_config: dict[str, Any] | None = None,
    ):
        self.interval = interval_seconds
        self.webhook_url = webhook_url
        self.email_config = email_config
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the monitoring loop."""
        if self._running:
            logger.warning("Monitor is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(
            "Monitor started — interval=%ds, webhook=%s",
            self.interval,
            bool(self.webhook_url),
        )

    async def stop(self) -> None:
        """Stop the monitoring loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Monitor stopped")

    async def _loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                await self._run_cycle()
            except Exception:
                logger.exception("Monitor cycle failed")

            await asyncio.sleep(self.interval)

    async def _run_cycle(self) -> None:
        """Execute one monitoring cycle: re-scan all registered profiles."""
        from ..routes.profile_routes import get_all_profiles
        from ..scanner import run_scan

        profiles = get_all_profiles()
        if not profiles:
            logger.info("No profiles to monitor")
            return

        logger.info("Monitor cycle: scanning %d profiles", len(profiles))
        changes: list[dict[str, Any]] = []

        for profile in profiles:
            url = profile.get("url")
            if not url:
                continue

            old_score = profile.get("clarvia_score")
            profile_id = profile.get("profile_id", "unknown")

            try:
                result = await run_scan(url)
                new_score = result.clarvia_score

                # Detect meaningful change
                if old_score is not None and abs(new_score - old_score) >= SCORE_CHANGE_THRESHOLD:
                    change = {
                        "profile_id": profile_id,
                        "name": profile.get("name", url),
                        "url": url,
                        "old_score": old_score,
                        "new_score": new_score,
                        "delta": new_score - old_score,
                        "rating": result.rating,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    changes.append(change)
                    logger.info(
                        "Score change detected: %s %d -> %d (%+d)",
                        url, old_score, new_score, new_score - old_score,
                    )

                # Update profile in-memory (profile_routes handles persistence)
                profile["clarvia_score"] = new_score
                profile["status"] = "scanned"
                profile["last_scanned_at"] = datetime.now(timezone.utc).isoformat()
                profile["scan_result"] = {
                    "scan_id": result.scan_id,
                    "rating": result.rating,
                    "clarvia_score": result.clarvia_score,
                    "dimensions": {
                        k: {"score": v.score, "max": v.max}
                        for k, v in result.dimensions.items()
                    },
                    "top_recommendations": result.top_recommendations,
                    "scanned_at": result.scanned_at.isoformat(),
                }

                # Persist to Supabase
                try:
                    from .supabase_client import save_scan
                    await save_scan(result)
                except Exception:
                    pass

            except Exception as e:
                logger.warning("Monitor scan failed for %s: %s", url, e)

            # Rate limit between scans
            await asyncio.sleep(2)

        # Send notifications if there were changes
        if changes:
            await self._notify(changes)

        logger.info(
            "Monitor cycle complete: %d profiles scanned, %d changes",
            len(profiles), len(changes),
        )

    async def _notify(self, changes: list[dict[str, Any]]) -> None:
        """Send notifications for score changes."""
        if self.webhook_url:
            await self._notify_webhook(changes)

        if self.email_config:
            await self._notify_email(changes)

    async def _notify_webhook(self, changes: list[dict[str, Any]]) -> None:
        """Send score changes to a webhook URL."""
        try:
            import aiohttp

            payload = {
                "event": "score_change",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "changes": changes,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status < 300:
                        logger.info("Webhook notification sent: %d changes", len(changes))
                    else:
                        logger.warning(
                            "Webhook returned %d: %s",
                            resp.status, await resp.text(),
                        )
        except Exception as e:
            logger.error("Webhook notification failed: %s", e)

    async def _notify_email(self, changes: list[dict[str, Any]]) -> None:
        """Send score change email notification (stub).

        To implement: integrate with Resend, SendGrid, or SES.
        Config expected: {"to": "user@example.com", "api_key": "..."}
        """
        to_email = self.email_config.get("to", "")
        logger.info(
            "Email notification stub: would send %d changes to %s",
            len(changes), to_email,
        )

        # Build email body for logging
        lines = ["Clarvia Score Changes Detected:\n"]
        for c in changes:
            direction = "improved" if c["delta"] > 0 else "declined"
            lines.append(
                f"  {c['name']} ({c['url']}): "
                f"{c['old_score']} -> {c['new_score']} ({direction} by {abs(c['delta'])})"
            )
        logger.info("\n".join(lines))


# Singleton instance
_monitor: MonitorService | None = None


def get_monitor(
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
    webhook_url: str | None = None,
    email_config: dict[str, Any] | None = None,
) -> MonitorService:
    """Get or create the singleton monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = MonitorService(
            interval_seconds=interval_seconds,
            webhook_url=webhook_url,
            email_config=email_config,
        )
    return _monitor
