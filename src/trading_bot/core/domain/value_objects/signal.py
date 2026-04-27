from enum import StrEnum


class SignalStatus(StrEnum):
    ACTIVE = "active"
    LOSS = "loss"
    BREAKEVEN = "breakeven"
