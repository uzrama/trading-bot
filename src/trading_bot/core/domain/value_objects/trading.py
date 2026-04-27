from enum import StrEnum


class TradeSide(StrEnum):
    LONG = "Buy"
    SHORT = "Sell"

    @property
    def opposite(self) -> TradeSide:
        return TradeSide.SHORT if self == TradeSide.LONG else TradeSide.LONG

    def get_sl_trigger_direction(self) -> int:
        return 2 if self == TradeSide.LONG else 1

    def get_tp_trigger_direction(self) -> int:
        return 1 if self == TradeSide.LONG else 2


class OrderType(StrEnum):
    LIMIT = "Limit"
    MARKET = "Market"
    TAKE_PROFIT = "TakeProfit"
    STOP_LOSS = "StopLoss"
    CONDITIONAL = "Conditional"
    UNKNOWN = "Unknown"


class OrderStatus(StrEnum):
    CREATED = "Created"
    NEW = "New"
    CLOSED = "Closed"
    CANCELED = "Canceled"
    EXPIRED = "Expired"
    REJECTED = "Rejected"
    TRIGGERED = "Triggered"
    UNTRIGGERED = "Untrigged"
    ACTIVE = "Active"
    PARTIALLY_FILLED = "PartiallyFilled"
    UNKNOWN = "Unknown"
    DEACTIVATED = "Deactivated"
    FILLED = "Filled"

    @classmethod
    def from_bybit(cls, value: str) -> OrderStatus:
        try:
            return cls(value)
        except ValueError:
            pass

        mapping = {
            "Created": cls.CREATED,
            "New": cls.NEW,
            "Closed": cls.CLOSED,
            "Canceled": cls.CANCELED,
            "Expired": cls.EXPIRED,
            "Rejected": cls.REJECTED,
            "Triggered": cls.TRIGGERED,
            "Untriggered": cls.UNTRIGGERED,
            "Cancelled": cls.CANCELED,
            "PartiallyFilled": cls.PARTIALLY_FILLED,
            "Deactivated": cls.PARTIALLY_FILLED,
            "Filled": cls.FILLED,
        }

        return mapping.get(value, cls.UNKNOWN)


class StopLossState(StrEnum):
    INITIAL = "initial"
    BREAKEVEN = "breakeven"
    TRAILED_TP1 = "trailed_tp1"
