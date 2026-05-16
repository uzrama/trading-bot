import logging
from typing import Any, final, override

from trading_bot.core.application.database.dto import PositionDTO
from trading_bot.core.application.trading.dto.order import PlacedOrderDTO, PlaceOrderDTO
from trading_bot.core.application.trading.interfaces.exchange import ExchangeGatewayProtocol
from trading_bot.core.domain.exceptions.trading import SymbolNotFoundException
from trading_bot.core.domain.value_objects.symbol import SymbolInfo
from trading_bot.core.domain.value_objects.trading import OrderType, StopLossState, TradeSide
from trading_bot.infrastructure.exchanges.bybit.mapper import BybitOrderMapper

from .base import BaseBybitAdapter

type WSMessageData = dict[str, Any]

logger = logging.getLogger()


@final
class BybitAdapter(BaseBybitAdapter, ExchangeGatewayProtocol):
    @property
    @override
    def name(self) -> str:
        return "Bybit"

    @override
    async def get_last_price(self, symbol: str) -> float:
        params = {"category": "linear", "symbol": symbol}
        result = await self._request("GET", "/v5/market/tickers", params=params, signed=False)

        ticker_list = result.get("result", {}).get("list", [])
        if not ticker_list:
            raise SymbolNotFoundException(symbol=symbol, exchange_name=self.name)

        return float(ticker_list[0]["lastPrice"])

    @override
    async def get_balance(self) -> float:
        params = {"accountType": "UNIFIED", "coin": "USDT"}
        result = await self._request("GET", "/v5/account/wallet-balance", params=params, signed=True)
        balance_list = result["result"]["list"]
        if not balance_list:
            return 0.0

        total_balance = balance_list[0].get("totalAvailableBalance", [])
        return float(total_balance)

    @override
    async def get_position(self, symbol: str) -> PositionDTO | None:
        params = {"category": "linear", "symbol": symbol}
        result = await self._request("GET", "/v5/position/list", params=params, signed=True)
        position = result["result"]["list"][0]
        size = float(position.get("size", 0.0))
        if size > 0:
            raw_side = position.get("side", "Buy")
            side = TradeSide.LONG if raw_side == "Buy" else TradeSide.SHORT

            return PositionDTO(
                account_name=self.account_name,
                symbol=position.get("symbol", symbol),
                side=side,
                entry_price=float(position.get("avgPrice", 0.0)),
                size=size,
                # Exchange doesn't know these fields, use defaults
                sl_state=StopLossState.INITIAL,
                current_sl_order_id=None,
                highest_tp_hit=0,
                is_closed=False,
            )
        return None

    @override
    async def get_orders(self, symbol: str) -> list[PlacedOrderDTO] | None:
        params = {"category": "linear", "symbol": symbol}
        result = await self._request("GET", "/v5/order/realtime", params=params, signed=True)
        orders = result["result"]["list"]
        if not orders:
            return None

        return [BybitOrderMapper.from_bybit_response(order) for order in orders]

    @override
    async def get_symbol_info(self, symbol: str) -> SymbolInfo:
        params = {"category": "linear", "symbol": symbol}
        result = await self._request("GET", "/v5/market/instruments-info", params=params, signed=False)
        instruments = result.get("result", {}).get("list", [])
        if not instruments:
            raise SymbolNotFoundException(symbol=symbol, exchange_name=self.name)

        return SymbolInfo.from_bybit(instruments[0])

    @override
    async def place_order(self, request: PlaceOrderDTO) -> PlacedOrderDTO:
        params = BybitOrderMapper.to_bybit_request(request)
        result = await self._request("POST", "/v5/order/create", params=params, signed=True)

        return BybitOrderMapper.from_bybit_response(result["result"], request_dto=request)

    @override
    async def place_orders(self, requests: list[PlaceOrderDTO]) -> list[PlacedOrderDTO]:
        params = {
            "category": "linear",
            "request": [BybitOrderMapper.to_bybit_request(r) for r in requests],
        }
        palced_orders = []
        result = await self._request("POST", "/v5/order/create-batch", params=params, signed=True)

        for request_dto, response_json in zip(requests, result["result"]["list"]):
            palced_orders.append(BybitOrderMapper.from_bybit_response(response_json, request_dto=request_dto))
        return palced_orders

    @override
    async def place_market_order(self, symbol: str, side: TradeSide, qty: float | str) -> PlacedOrderDTO:
        # Create clean DTO
        request = PlaceOrderDTO(symbol=symbol, side=side, order_type=OrderType.MARKET, qty=float(qty))
        return await self.place_order(request)

    @override
    async def place_limit_order(self, symbol: str, price: float, side: TradeSide, qty: float | str) -> PlacedOrderDTO:
        request = PlaceOrderDTO(symbol=symbol, side=side, order_type=OrderType.LIMIT, qty=float(qty), price=price)
        return await self.place_order(request)

    @override
    async def place_stop_loss_order(self, symbol: str, side: TradeSide, stop_price: float, link_id: str | None = None) -> PlacedOrderDTO:
        request = PlaceOrderDTO(symbol=symbol, side=side, order_type=OrderType.STOP_LOSS, trigger_price=stop_price, close_on_trigger=True, reduce_only=True, order_link_id=link_id)
        return await self.place_order(request)

    @override
    async def place_conditional_market_order(self, symbol: str, side: TradeSide, qty: float | str, trigger_price: float) -> PlacedOrderDTO:
        request = PlaceOrderDTO(symbol=symbol, side=side, order_type=OrderType.CONDITIONAL, qty=float(qty), trigger_price=trigger_price)
        return await self.place_order(request)

    @override
    async def place_trade_setup(self, orders: list[PlaceOrderDTO]) -> list[PlacedOrderDTO]:
        params = {
            "category": "linear",
            "request": [BybitOrderMapper.to_bybit_request(r) for r in orders],
        }
        placed_orders = []
        result = await self._request("POST", "/v5/order/create-batch", params=params, signed=True)

        order_results = result.get("result", {}).get("list", [])
        error_results = result.get("retExtInfo", {}).get("list", [])

        for request_dto, response_data, error_info in zip(orders, order_results, error_results):
            code = error_info.get("code")

            if code != 0:
                msg = error_info.get("msg")
                logger.error(f"❌ Ошибка Bybit (batch) при выставлении {request_dto.order_type.value}: {msg} (code: {code})")
                continue
            merged_data = {"symbol": request_dto.symbol, **response_data}
            placed_orders.append(BybitOrderMapper.from_bybit_response(merged_data, request_dto=request_dto))
        return placed_orders

    @override
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        params = {"category": "linear", "symbol": symbol, "orderLinkId": order_id}

        result = await self._request("POST", "/v5/order/cancel", params=params, signed=True)
        return result["retCode"] == 0

    @override
    async def cancel_order_by_link_id(self, symbol: str, order_link_id: str) -> bool:
        params = {"category": "linear", "symbol": symbol, "orderLinkId": order_link_id}

        result = await self._request("POST", "/v5/order/cancel", params=params, signed=True)
        return result["retCode"] == 0

    @override
    async def cancel_all_orders(self, symbol: str) -> bool:
        params: dict[str, Any] = {"category": "linear"}
        if symbol:
            params["symbol"] = symbol

        result = await self._request("POST", "/v5/order/cancel-all", params=params, signed=True)
        return result["retCode"] == 0

    @override
    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    @override
    async def cancel_position(self, symbol: str, side: TradeSide, qty: float):
        request = PlaceOrderDTO(symbol=symbol, side=side.opposite, order_type=OrderType.MARKET, qty=qty, reduce_only=True)
        await self.place_order(request)
