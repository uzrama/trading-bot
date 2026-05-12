from typing import final, override

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from trading_bot.core.application.database.dto.order import OrderDTO
from trading_bot.core.application.database.interfaces.repositories.orders import OrderRepositoryProtocol
from trading_bot.core.domain.value_objects.trading import OrderType
from trading_bot.infrastructure.database.models.order import OrderModel


@final
class SQLAlchemyOrderRepository(OrderRepositoryProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    @override
    async def upsert(self, order: OrderDTO) -> None:
        values = {
            "id": order.id,
            "symbol": order.symbol,
            "status": order.status,
            "qty": order.qty,
            "account_name": order.account_name,
            "message_id": str(order.message_id) if order.message_id else None,
            "price": order.price,
            "trigger_price": order.trigger_price,
            "side": order.side,
            "order_type": order.order_type,
            "level": order.level,
            "order_link_id": order.order_link_id,
        }

        stmt = insert(OrderModel).values(**values)
        update_dict = {c.name: c for c in stmt.excluded if c.name not in ("id", "created_at")}

        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_=update_dict,
        )
        await self._session.execute(stmt)

    @override
    async def get_by_id(self, order_id: str) -> OrderDTO | None:
        stmt = select(OrderModel).where(OrderModel.id == order_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        order = OrderDTO(
            id=model.id,
            symbol=model.symbol,
            side=model.side,
            status=model.status,
            qty=model.qty,
            price=model.price,
            order_type=model.order_type,
            trigger_price=model.trigger_price,
            level=model.level,
            account_name=model.account_name,
            message_id=model.message_id,
        )
        return order

    @override
    async def get_takeprofits_by_symbol(self, symbol: str) -> list[OrderDTO] | None:
        stmt = select(OrderModel).where((OrderModel.symbol == symbol) & (OrderModel.order_type == OrderType.TAKE_PROFIT))
        result = await self._session.execute(stmt)

        models = result.scalars().all()

        return [
            OrderDTO(
                id=model.id,
                symbol=model.symbol,
                side=model.side,
                status=model.status,
                qty=model.qty,
                price=model.price,
                order_type=model.order_type,
                trigger_price=model.trigger_price,
                level=model.level,
                account_name=model.account_name,
                message_id=model.message_id,
            )
            for model in models  # Map each model to DTO
        ]

    @override
    async def get_stop_loss_by_symbol(self, symbol: str) -> OrderDTO | None:

        stmt = select(OrderModel).where((OrderModel.symbol == symbol) & (OrderModel.order_type == OrderType.STOP_LOSS))
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_dto(model) if model else None

    @override
    async def get_active_orders(self, symbol: str | None = None) -> list[OrderDTO]: ...

    @override
    async def delete_by_symbol(self, symbol: str) -> bool:
        stmt = delete(OrderModel).where(OrderModel.symbol == symbol)
        await self._session.execute(stmt)
        return True

    @override
    async def get_by_link_id(self, order_link_id: str) -> OrderDTO | None:
        stmt = select(OrderModel).where(OrderModel.order_link_id == order_link_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._to_dto(model)

    @override
    async def get_stop_loss_by_signal(self, account_name: str, message_id: str) -> OrderDTO | None:
        stmt = select(OrderModel).where(
            (OrderModel.account_name == account_name) & (OrderModel.message_id == message_id) & (OrderModel.order_type == OrderType.STOP_LOSS),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_dto(model) if model else None

    @override
    async def get_takeprofits_by_signal(self, account_name: str, message_id: str) -> list[OrderDTO]:
        stmt = select(OrderModel).where(
            (OrderModel.account_name == account_name) & (OrderModel.message_id == message_id) & (OrderModel.order_type == OrderType.TAKE_PROFIT),
        )
        result = await self._session.execute(stmt)
        return [self._to_dto(model) for model in result.scalars().all()]

    @override
    async def delete_by_link_id(self, order_link_id: str) -> bool:
        stmt = delete(OrderModel).where(OrderModel.order_link_id == order_link_id)
        await self._session.execute(stmt)
        return True

    @override
    async def delete_by_id(self, order_id: str) -> bool:
        stmt = delete(OrderModel).where(OrderModel.id == order_id)
        await self._session.execute(stmt)
        return True

    @override
    async def delete_by_symbol_and_account(self, account_name: str, symbol: str) -> bool:
        stmt = delete(OrderModel).where((OrderModel.account_name == account_name) & (OrderModel.symbol == symbol))
        await self._session.execute(stmt)
        return True

    def _to_dto(self, model: OrderModel) -> OrderDTO:
        return OrderDTO(
            id=model.id,
            symbol=model.symbol,
            side=model.side,
            status=model.status,
            qty=float(model.qty) if model.qty is not None else None,
            price=float(model.price) if model.price is not None else None,
            order_type=model.order_type,
            trigger_price=float(model.trigger_price) if model.trigger_price is not None else None,
            level=model.level,
            account_name=model.account_name,
            message_id=model.message_id,
            order_link_id=model.order_link_id,
        )
