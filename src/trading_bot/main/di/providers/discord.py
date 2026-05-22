from collections.abc import AsyncIterable
from typing import final

from dishka import Provider, Scope, provide

from trading_bot.core.application.signal.dto.signal import SignalDTO
from trading_bot.core.application.signal.use_cases.execute_signal import ExecuteSignalUseCase
from trading_bot.core.application.signal.use_cases.update_signal import UpdateSignalUseCase
from trading_bot.infrastructure.discord.client import DiscordAdapter
from trading_bot.infrastructure.discord.parsers.registry import ParserRegistry
from trading_bot.main.config.settings import AppSettings
from trading_bot.main.runners.discord import DiscordRunner


@final
class DiscordProvider(Provider):
    @provide(scope=Scope.APP)
    async def get_discord_client(
        self,
        settings: AppSettings,
        execute_use_case: ExecuteSignalUseCase,
        update_use_case: UpdateSignalUseCase,
        parser_registry: ParserRegistry,
    ) -> AsyncIterable[DiscordAdapter]:
        watched_channel_ids: set[int] = {s.channel_id for s in settings.discord.sources if s.enabled}
        channel_to_source_map: dict[int, str] = {s.channel_id: s.source_name for s in settings.discord.sources if s.enabled}
        token = settings.discord.token.get_secret_value()

        async def on_message_wrapper(dto: SignalDTO):
            await execute_use_case.execute(dto)

        async def on_edit_wrapper(dto: SignalDTO):
            await update_use_case.execute(dto)

        client = DiscordAdapter(
            token=token,
            on_message_callback=on_message_wrapper,
            on_edit_callback=on_edit_wrapper,
            watched_channel_ids=watched_channel_ids,
            channel_to_source_map=channel_to_source_map,
            parser_registry=parser_registry,
        )
        yield client
        await client.stop_client()

    @provide(scope=Scope.APP)
    def get_discord_runner(self, config: AppSettings, discord_client: DiscordAdapter) -> DiscordRunner:
        return DiscordRunner(discord_client=discord_client, config=config)

    @provide(scope=Scope.APP)
    def get_parser_registry(self) -> ParserRegistry:
        return ParserRegistry()
