from typing import Any

from trading_bot.core.application.trading.dto.order import PlacedOrderDTO, PlaceOrderDTO
from trading_bot.core.domain.value_objects.trading import OrderStatus, OrderType, TradeSide


class BybitOrderMapper:
    @staticmethod
    def to_bybit_request(dto: PlaceOrderDTO) -> dict[str, Any]:
        result = {
            "category": "linear",
            "symbol": dto.symbol,
            "side": dto.side.value,
            "orderType": dto.order_type.value,
            "positionIdx": 0,
            "timeInForce": "GTC",
            "orderLinkId": dto.order_link_id,
        }

        if dto.qty is not None:
            result["qty"] = str(dto.qty)
        if dto.price is not None:
            result["price"] = str(dto.price)
        if dto.reduce_only:
            result["reduceOnly"] = True
        if dto.close_on_trigger:
            result["closeOnTrigger"] = True

        # Bybit-specific logic for CONDITIONAL
        if dto.order_type == OrderType.CONDITIONAL:
            result["orderType"] = "Market"
            result["triggerBy"] = "LastPrice"
            if dto.trigger_direction is not None:
                result["triggerDirection"] = dto.trigger_direction
        # Bybit-specific logic for TP / SL
        if dto.order_type in {OrderType.TAKE_PROFIT, OrderType.STOP_LOSS}:
            result["orderType"] = "Market"
            result["side"] = dto.side.opposite.value
            result["reduceOnly"] = True
            result["triggerBy"] = "LastPrice"

            if dto.order_type == OrderType.TAKE_PROFIT:
                result["triggerDirection"] = 1 if dto.side == TradeSide.LONG else 2
                result["closeOnTrigger"] = True
                if dto.level is not None:
                    result["level"] = dto.level
                if dto.qty == 0 or dto.qty is None:
                    result["qty"] = "0"
            elif dto.order_type == OrderType.STOP_LOSS:
                result["triggerDirection"] = 2 if dto.side == TradeSide.LONG else 1
                result["closeOnTrigger"] = True
                if dto.qty == 0 or dto.qty is None:
                    result["qty"] = "0"
        if dto.trigger_price is not None:
            result["triggerPrice"] = str(dto.trigger_price)
        return result

    @staticmethod
    def from_bybit_response(data: dict[str, Any], request_dto: PlaceOrderDTO | None = None) -> PlacedOrderDTO:
        def get_value(key_bybit: str, attr_req: str, type_func: type | None = None):
            if data.get(key_bybit):
                return type_func(data[key_bybit]) if type_func else data[key_bybit]
            if request_dto and getattr(request_dto, attr_req, None) is not None:
                return getattr(request_dto, attr_req)
            return None

        return PlacedOrderDTO(
            id=data.get("orderId") or data.get("id") or "",
            symbol=data.get("symbol") or (request_dto.symbol if request_dto else ""),
            side=get_value("side", "side", TradeSide),
            order_type=get_value("orderType", "order_type", OrderType) or OrderType.UNKNOWN,
            status=OrderStatus.from_bybit(data["orderStatus"]) if data.get("orderStatus") else None,
            qty=get_value("qty", "qty", float),
            price=float(data["avgPrice"]) if data.get("avgPrice") and float(data["avgPrice"]) > 0 else get_value("price", "price", float),
            trigger_price=get_value("triggerPrice", "trigger_price", float),
            level=get_value("level", "level", int),
            order_link_id=data.get("orderLinkId") or (request_dto.order_link_id if request_dto else None),
            reject_reason=data.get("rejectReason"),
        )
