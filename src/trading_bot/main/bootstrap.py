import asyncio
import logging
from typing import Protocol

from trading_bot.main.config.logging import setup_logging
from trading_bot.main.di.setup import setup_di

logger = logging.getLogger(__name__)


class ApplicationRunner(Protocol):
    async def run(self) -> None: ...


async def run_application[TRunner: ApplicationRunner](runner_type: type[TRunner], process_name: str) -> None:
    setup_logging()
    container = setup_di()
    try:
        # Resolve the requested runner (Discord or Tracker) from the container
        runner: ApplicationRunner = await container.get(runner_type)
        logger.info(f"🟢 Starting: {process_name}...")
        await runner.run()
    except asyncio.CancelledError:
        logger.info(f"🛑 Stopping: {process_name} (Cancelled)...")
    except Exception as e:
        logger.exception(f"❌ Fatal error in {process_name}: {e}")
    finally:
        logger.info(f"🧹 Cleaning up resources for {process_name}...")
        await container.close()
