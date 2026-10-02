import re
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from .errors import InvalidTradeError

TICKER_PATTERN = re.compile(r"[A-Z]{4}\d{1,2}")
PRICE_MAX_DECIMAL_PLACES = 2


class Side(StrEnum):
    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True, slots=True)
class Trade:
    ticker: str
    side: Side
    quantity: int
    price: Decimal

    def __post_init__(self) -> None:
        if not TICKER_PATTERN.fullmatch(self.ticker):
            raise InvalidTradeError(f"'{self.ticker}' is not a B3 ticker")
        if self.quantity <= 0:
            raise InvalidTradeError("quantity must be positive")
        if not self.price.is_finite() or self.price <= 0:
            raise InvalidTradeError("price must be a positive amount")
        if _decimal_places(self.price) > PRICE_MAX_DECIMAL_PLACES:
            raise InvalidTradeError("price must have at most two decimal places")

    @property
    def notional(self) -> Decimal:
        return self.price * self.quantity


def _decimal_places(value: Decimal) -> int:
    exponent = value.normalize().as_tuple().exponent
    return -exponent if isinstance(exponent, int) and exponent < 0 else 0
