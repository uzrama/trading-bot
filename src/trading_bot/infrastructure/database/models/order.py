from typing import final

from sqlalchemy import Enum, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from trading_bot.core.domain.value_objects.trading import OrderStatus, OrderType, TradeSide
from trading_bot.infrastructure.database.models.mixins.timestamp import TimestampMixin

from .base import Base


@final
class OrderModel(Base, TimestampMixin):
    __tablename__ = "orders"
    # Order ID from exchange
    id: Mapped[str] = mapped_column(String, primary_key=True)

    # References
    account_name: Mapped[str] = mapped_column(String, index=True, nullable=True)
    message_id: Mapped[str | None] = mapped_column(String, index=True, nullable=True)

    # Main data
    symbol: Mapped[str] = mapped_column(String, index=True, nullable=True)
    side: Mapped[TradeSide] = mapped_column(Enum(TradeSide), nullable=True)
    order_type: Mapped[OrderType] = mapped_column(Enum(OrderType), index=True, nullable=True)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), index=True, nullable=True)

    # Numeric values (can be NULL)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    trigger_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    qty: Mapped[float | None] = mapped_column(Float, nullable=True)
    filled: Mapped[float | None] = mapped_column(Float, nullable=True)
    level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    order_link_id: Mapped[str | None] = mapped_column(String, nullable=True)
