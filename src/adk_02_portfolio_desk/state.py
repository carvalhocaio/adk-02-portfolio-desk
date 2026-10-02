from decimal import Decimal
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict

from .domain import Portfolio, Position, Side, Trade

PORTFOLIO_KEY = "user:portfolio"
SCENARIO_KEY = "scenario"


class StateReader(Protocol):
    def get(self, key: str, default: Any = None) -> Any: ...


class StateWriter(StateReader, Protocol):
    def __setitem__(self, key: str, value: Any) -> None: ...


class _Record(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TradeRecord(_Record):
    ticker: str
    side: Side
    quantity: int
    price: Decimal

    @classmethod
    def of(cls, trade: Trade) -> "TradeRecord":
        return cls(
            ticker=trade.ticker,
            side=trade.side,
            quantity=trade.quantity,
            price=trade.price,
        )

    def to_trade(self) -> Trade:
        return Trade(self.ticker, self.side, self.quantity, self.price)


class PositionRecord(_Record):
    ticker: str
    quantity: int
    cost: Decimal


class PortfolioRecord(_Record):
    positions: tuple[PositionRecord, ...] = ()

    @classmethod
    def of(cls, portfolio: Portfolio) -> "PortfolioRecord":
        return cls(
            positions=tuple(
                PositionRecord(ticker=p.ticker, quantity=p.quantity, cost=p.cost)
                for p in portfolio.positions
            )
        )

    def to_portfolio(self) -> Portfolio:
        return Portfolio(
            tuple(Position(p.ticker, p.quantity, p.cost) for p in self.positions)
        )


class ScenarioRecord(_Record):
    trades: tuple[TradeRecord, ...] = ()


def load_portfolio(state: StateReader) -> Portfolio:
    raw = state.get(PORTFOLIO_KEY)
    return PortfolioRecord.model_validate(raw).to_portfolio() if raw else Portfolio()


def save_portfolio(state: StateWriter, portfolio: Portfolio) -> None:
    state[PORTFOLIO_KEY] = PortfolioRecord.of(portfolio).model_dump(mode="json")


def load_scenario(state: StateReader) -> tuple[Trade, ...]:
    raw = state.get(SCENARIO_KEY)
    record = ScenarioRecord.model_validate(raw) if raw else ScenarioRecord()
    return tuple(trade.to_trade() for trade in record.trades)


def save_scenario(state: StateWriter, trades: tuple[Trade, ...]) -> None:
    record = ScenarioRecord(trades=tuple(TradeRecord.of(t) for t in trades))
    state[SCENARIO_KEY] = record.model_dump(mode="json")
