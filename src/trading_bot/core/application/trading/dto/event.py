import msgspec

from trading_bot.core.application.trading.dto.order import PlacedOrderDTO
from trading_bot.core.domain.value_objects.event import EventType


class EventDTO(msgspec.Struct, frozen=True, kw_only=True):
    event_type: EventType
    symbol: str
    order: PlacedOrderDTO | None = None
    account_name: str
