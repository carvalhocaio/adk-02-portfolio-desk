from decimal import Decimal
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict

from .domain import Portfolio, Position, Side, Trade

PORTFOLIO_KEY = "user:portfolio"
SCENARIO_KEY = "scenario"
RECORDED_TRADES_KEY = "temp:recorded_trades"


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


class TradeLog(_Record):
    trades: tuple[TradeRecord, ...] = ()

    @classmethod
    def of(cls, trades: tuple[Trade, ...]) -> "TradeLog":
        return cls(trades=tuple(TradeRecord.of(trade) for trade in trades))

    def to_trades(self) -> tuple[Trade, ...]:
        return tuple(trade.to_trade() for trade in self.trades)


def load_portfolio(state: StateReader) -> Portfolio:
    raw = state.get(PORTFOLIO_KEY)
    return PortfolioRecord.model_validate(raw).to_portfolio() if raw else Portfolio()


def save_portfolio(state: StateWriter, portfolio: Portfolio) -> None:
    state[PORTFOLIO_KEY] = PortfolioRecord.of(portfolio).model_dump(mode="json")


def load_scenario(state: StateReader) -> tuple[Trade, ...]:
    return _load_trades(state, SCENARIO_KEY)


def save_scenario(state: StateWriter, trades: tuple[Trade, ...]) -> None:
    _save_trades(state, SCENARIO_KEY, trades)


def load_recorded_trades(state: StateReader) -> tuple[Trade, ...]:
    return _load_trades(state, RECORDED_TRADES_KEY)


def save_recorded_trades(state: StateWriter, trades: tuple[Trade, ...]) -> None:
    _save_trades(state, RECORDED_TRADES_KEY, trades)


def _load_trades(state: StateReader, key: str) -> tuple[Trade, ...]:
    raw = state.get(key)
    return TradeLog.model_validate(raw).to_trades() if raw else ()


def _save_trades(state: StateWriter, key: str, trades: tuple[Trade, ...]) -> None:
    state[key] = TradeLog.of(trades).model_dump(mode="json")
