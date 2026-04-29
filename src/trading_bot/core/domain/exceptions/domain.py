from .base import DomainException


class InvalidTradeSetupException(DomainException):
    pass


class InvalidVolumeException(DomainException):
    pass


class OrderValidationException(DomainException):
    pass
