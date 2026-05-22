import logging

from dishka import AsyncContainer, make_async_container

from trading_bot.main.di.providers.database import DatabaseProvider
from trading_bot.main.di.providers.discord import DiscordProvider
from trading_bot.main.di.providers.tracker import TrackerProvider
from trading_bot.main.di.providers.trading import TradingProvider

from .providers.settings import SettingsProvide

logger = logging.getLogger(__name__)


def setup_di() -> AsyncContainer:
    logger.debug("Initializing DI Container...")
    _container = make_async_container(
        SettingsProvide(),
        TradingProvider(),
        DatabaseProvider(),
        DiscordProvider(),
        TrackerProvider(),
    )

    return _container
