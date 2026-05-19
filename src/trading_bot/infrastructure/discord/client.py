import logging
from collections.abc import Awaitable, Callable
from typing import Any, final

import discord

from trading_bot.core.application.signal.dto.signal import SignalDTO
from trading_bot.infrastructure.discord.parsers.registry import ParserRegistry

logger = logging.getLogger(__name__)


@final
class DiscordAdapter(discord.Client):
    def __init__(
        self,
        token: str,
        on_message_callback: Callable[[SignalDTO], Awaitable[None]],
        on_edit_callback: Callable[[SignalDTO], Awaitable[None]],
        watched_channel_ids: set[int],
        channel_to_source_map: dict[int, str],
        parser_registry: ParserRegistry,
        **options: Any,
    ):
        super().__init__(**options)
        self._token = token
        self._on_message_callback = on_message_callback
        self._on_edit_callback = on_edit_callback
        self._watched_channel_ids = watched_channel_ids
        self._channel_to_source_map = channel_to_source_map
        self._parser_registry = parser_registry

    async def start_client(self):
        await self.start(self._token)

    async def on_ready(self):
        if self.user:
            logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        else:
            logger.info("Logged in as Unknown User")
        logger.info(f"Watching {len(self._watched_channel_ids)} channels:")
        for cid in self._watched_channel_ids:
            channel = self.get_channel(cid)
            name = getattr(channel, "name", "Unknown/Private") if channel else "Unknown/Private"
            logger.info(f"  - {cid} ({name})")

    async def on_message(self, message: discord.Message):
        if message.channel.id not in self._watched_channel_ids:
            return
        text = self._extract_full_text(message)
        source_name = self._channel_to_source_map.get(message.channel.id)
        if not source_name:
            logger.warning(f"Неизвестный канал {message.channel.id}, нет source_name.")
            return
        signal_dto = self._parser_registry.parse_message(source_name=source_name, source_id=message.channel.id, message_id=message.id, text=text)
        if signal_dto:
            await self._on_message_callback(signal_dto)

    async def on_message_edit(self, _before: discord.Message, after: discord.Message):
        if after.channel.id not in self._watched_channel_ids:
            return
        text = self._extract_full_text(after)
        source_name = self._channel_to_source_map.get(after.channel.id)
        signal_dto = self._parser_registry.parse_message(source_name=source_name, source_id=after.channel.id, message_id=after.id, text=text)
        if signal_dto:
            await self._on_edit_callback(signal_dto)

    def _extract_full_text(self, message: discord.Message) -> str:
        parts = []

        # 1. Add message content (contains symbol and side)
        if message.content:
            parts.append(message.content)

        # 2. Process first embed only
        if message.embeds:
            embed = message.embeds[0]

            # Add description (contains signal type and leverage)
            if embed.description:
                parts.append(embed.description)

            # 3. Extract and format fields (contains entry, TP, SL)
            for field in embed.fields:
                field_name = field.name or ""
                field_value = field.value or ""

                # Skip empty fields and separator fields
                if not field_value.strip() or field_value.strip().startswith("━"):
                    continue

                # Add field name and value
                # Format: "ENTRY\n$0.057620 Triggered"
                parts.append(f"{field_name}\n{field_value}")

        extracted_text = "\n".join(parts)
        logger.debug(f"Extracted text from message {message.id}: {extracted_text}")
        return extracted_text

    async def stop_client(self):
        await self.close()
