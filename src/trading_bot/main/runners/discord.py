import logging
from typing import final

from trading_bot.infrastructure.discord.client import DiscordAdapter
from trading_bot.main.config.settings import AppSettings

logger = logging.getLogger(__name__)


@final
class DiscordRunner:
    def __init__(self, discord_client: DiscordAdapter, config: AppSettings):
        self._discord_client = discord_client
        self._config = config
        self._is_running = False

    async def run(self):
        self._is_running = True
        try:
            await self._discord_client.start_client()
        except Exception as e:
            logger.error(f"Discord Runner error: {e}")

    def stop(self):
        self._is_running = False
