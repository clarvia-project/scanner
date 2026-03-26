"""Keep-alive ping to prevent Render cold starts."""
import asyncio
import logging
import aiohttp

logger = logging.getLogger(__name__)
SELF_URL = "https://clarvia-api.onrender.com/v1/stats"
INTERVAL = 840  # 14 minutes (Render spins down after 15min inactivity)

async def keepalive_loop():
    """Background task that pings the API every 14 minutes."""
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(SELF_URL, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    logger.debug("Keep-alive ping: %d", resp.status)
        except Exception as e:
            logger.warning("Keep-alive failed: %s", e)
        await asyncio.sleep(INTERVAL)
