from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal

from .errors import InsufficientPositionError
from .trade import Side, Trade

CENT = Decimal("0.01")


def to_cents(amount: Decimal) -> Decimal:
    return amount.quantize(CENT, rounding=ROUND_HALF_EVEN)


@dataclass(frozen=True, slots=True)
class Position:
    ticker: str
    quantity: int
    cost: Decimal

    @property
    def average_price(self) -> Decimal:
        return to_cents(self.cost / self.quantity)

    def bought(self, quantity: int, notional: Decimal) -> "Position":
        return Position(self.ticker, self.quantity + quantity, self.cost + notional)

    def sold(self, quantity: int) -> "Position | None":
        if quantity > self.quantity:
            raise InsufficientPositionError(
                f"cannot sell {quantity} {self.ticker}, holding {self.quantity}"
            )
        remaining = self.quantity - quantity
        if remaining == 0:
            return None
        released_cost = to_cents(self.cost * quantity / self.quantity)
        return Position(self.ticker, remaining, self.cost - released_cost)


@dataclass(frozen=True, slots=True)
class Portfolio:
    positions: tuple[Position, ...] = ()

    @property
    def total_cost(self) -> Decimal:
        return sum((position.cost for position in self.positions), Decimal(0))

    def position(self, ticker: str) -> Position | None:
        return next((p for p in self.positions if p.ticker == ticker), None)

    def apply(self, trade: Trade) -> "Portfolio":
        current = self.position(trade.ticker)
        if trade.side is Side.BUY:
            updated = (
                current.bought(trade.quantity, trade.notional)
                if current
                else Position(trade.ticker, trade.quantity, trade.notional)
            )
        elif current is None:
            raise InsufficientPositionError(f"no position in {trade.ticker} to sell")
        else:
            updated = current.sold(trade.quantity)
        return self._replace(trade.ticker, updated)

    def _replace(self, ticker: str, position: Position | None) -> "Portfolio":
        others = (p for p in self.positions if p.ticker != ticker)
        kept = (*others, position) if position else tuple(others)
        return Portfolio(tuple(sorted(kept, key=lambda p: p.ticker)))
