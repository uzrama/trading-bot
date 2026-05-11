from typing import final

from sqlalchemy import Boolean, Enum, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from trading_bot.core.domain.value_objects.trading import StopLossState, TradeSide
from trading_bot.infrastructure.database.models.base import Base
from trading_bot.infrastructure.database.models.mixins.timestamp import TimestampMixin


@final
class PositionModel(Base, TimestampMixin):
    __tablename__ = "positions"
    account_name: Mapped[str] = mapped_column(String, primary_key=True)
    symbol: Mapped[str] = mapped_column(String, primary_key=True)
    side: Mapped[TradeSide] = mapped_column(Enum(TradeSide, native_enum=False))
    entry_price: Mapped[float] = mapped_column(Float)
    size: Mapped[float] = mapped_column(Float)

    sl_state: Mapped[StopLossState] = mapped_column(Enum(StopLossState, native_enum=False), server_default=StopLossState.INITIAL.value)
    current_sl_order_id: Mapped[str | None] = mapped_column(String, nullable=True)
    highest_tp_hit: Mapped[int] = mapped_column(Integer, default=0)

    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)

    is_sl_updated: Mapped[bool] = mapped_column(Boolean, default=False)
