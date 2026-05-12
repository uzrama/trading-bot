from typing import final, override

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from trading_bot.core.application.database.dto import PositionDTO
from trading_bot.core.application.database.interfaces.repositories import PositionRepositoryProtocol
from trading_bot.infrastructure.database.models import PositionModel


@final
class SQLAlchemyPositionRepository(PositionRepositoryProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    @override
    async def upsert(self, position: PositionDTO) -> None:
        values = {
            "account_name": position.account_name,
            "symbol": position.symbol,
            "side": position.side,
            "entry_price": position.entry_price,
            "size": position.size,
            "sl_state": position.sl_state,
            "current_sl_order_id": position.current_sl_order_id,
            "highest_tp_hit": position.highest_tp_hit,
            "is_closed": position.is_closed,
            "is_sl_updated": position.is_sl_updated,
        }
        stmt = insert(PositionModel).values(**values)
        update_dict = {c.name: c for c in stmt.excluded if c.name not in ("account_name", "symbol", "created_at")}

        # Conflict by composite key (account_name, symbol)
        stmt = stmt.on_conflict_do_update(
            index_elements=["account_name", "symbol"],
            set_=update_dict,
        )
        await self._session.execute(stmt)

    @override
    async def get_by_id(self, account_name: str, symbol: str) -> PositionDTO | None:
        stmt = select(PositionModel).where(PositionModel.account_name == account_name, PositionModel.symbol == symbol)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_dto(model) if model else None

    @override
    async def get_active_by_symbol(self, account_name: str, symbol: str) -> PositionDTO | None:
        stmt = select(PositionModel).where(PositionModel.account_name == account_name, PositionModel.symbol == symbol, PositionModel.is_closed == False)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_dto(model) if model else None

    def _to_dto(self, model: PositionModel) -> PositionDTO:
        return PositionDTO(
            account_name=model.account_name,
            symbol=model.symbol,
            side=model.side,
            entry_price=model.entry_price,
            size=model.size,
            sl_state=model.sl_state,
            current_sl_order_id=model.current_sl_order_id,
            highest_tp_hit=model.highest_tp_hit,
            is_closed=model.is_closed,
            is_sl_updated=model.is_sl_updated,
        )
