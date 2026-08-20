import asyncio
import logging
import aiohttp

logger = logging.getLogger("KeepAliveMeshTuring")

PORTFOLIO_URLS = [
    "https://crypto-trading-bot-1-iz21.onrender.com/api/status",
    "https://crypto-trading-bot-turbo.onrender.com/api/status",
    "https://crypto-trading-bot-apex.onrender.com/api/status",
    "https://crypto-trading-bot-bare.onrender.com/api/status",
    "https://crypto-trading-bot-nexus.onrender.com/api/status",
    "https://crypto-trading-bot-turing.onrender.com/api/status"
]

class KeepAliveMesh:
    def __init__(self, interval_seconds: int = 120):
        self.interval_seconds = interval_seconds
        self.is_running = False
        self._task = None

    async def _ping_all_endpoints(self):
        async with aiohttp.ClientSession() as session:
            for url in PORTFOLIO_URLS:
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        if resp.status == 200:
                            logger.debug(f"🏓 [KEEP-ALIVE OK] Ping a {url}")
                except Exception:
                    pass

    async def _loop(self):
        logger.info("🌐 Malla de Resiliencia TURING Keep-Alive Activa (Auto-Ping cruzado a los 6 bots)")
        while self.is_running:
            await asyncio.sleep(self.interval_seconds)
            try:
                await self._ping_all_endpoints()
            except Exception as e:
                logger.error(f"Error en bucle Keep-Alive TURING: {e}")

    def start(self):
        self.is_running = True
        self._task = asyncio.create_task(self._loop())

    def stop(self):
        self.is_running = False
        if self._task:
            self._task.cancel()
