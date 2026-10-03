from decimal import Decimal
from functools import reduce
from typing import Annotated

from google.adk.tools import ToolContext
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .domain import InvalidTradeError, Portfolio, Side, Trade
from .models import ExposureReport, PortfolioReport, ScenarioReport, TradeReceipt
from .state import (
    load_portfolio,
    load_recorded_trades,
    load_scenario,
    save_portfolio,
    save_recorded_trades,
    save_scenario,
)

Ticker = Annotated[
    str, Field(description="B3 ticker, for example PETR4, VALE3 or TAEE11.")
]
TradeSide = Annotated[Side, Field(description="buy or sell.")]
Quantity = Annotated[int, Field(description="Number of shares, a positive integer.")]
Price = Annotated[
    float,
    Field(description="Price per share in BRL, with at most two decimal places."),
]


class DuplicateTradeError(Exception):
    pass


class _TradeArgs(BaseModel):
    model_config = ConfigDict(frozen=True)

    ticker: str
    side: Side
    quantity: int
    price: Decimal


def record_trade(
    ticker: Ticker,
    side: TradeSide,
    quantity: Quantity,
    price: Price,
    tool_context: ToolContext,
) -> TradeReceipt:
    """Records a trade the user already executed and updates the real portfolio.

    Only call it for trades the user states as done, never for hypotheticals,
    which belong to simulate_trade. Buys raise the position cost; sells release
    cost proportionally, so the average price never changes on a sell. Selling
    more shares than held fails. Identical trades in the same message are
    rejected as duplicates: record several identical trades with one call and
    the combined quantity. The result echoes the normalized trade and the
    resulting position; position is null when the sell closed it.
    """
    trade = _parse_trade(ticker, side, quantity, price)
    recorded = load_recorded_trades(tool_context.state)
    if trade in recorded:
        raise DuplicateTradeError(
            f"{trade.side} {trade.quantity} {trade.ticker} at {trade.price} was "
            "already recorded in this turn"
        )
    portfolio = load_portfolio(tool_context.state).apply(trade)
    save_portfolio(tool_context.state, portfolio)
    save_recorded_trades(tool_context.state, (*recorded, trade))
    return TradeReceipt.of(trade, portfolio)


def get_positions(tool_context: ToolContext) -> PortfolioReport:
    """Returns the user's real portfolio, kept across all their conversations.

    Each position has the ticker, sector, quantity, average price and total
    cost in BRL. Values are at cost: there are no market prices, so never
    present them as current value, profit or loss.
    """
    return PortfolioReport.of(load_portfolio(tool_context.state))


def get_exposure(tool_context: ToolContext) -> ExposureReport:
    """Returns the real portfolio's exposure by sector, measured at cost.

    Sectors are ordered from the largest cost. weight_percent is rounded to
    cents, so the weights may not add up to exactly 100. Tickers outside the
    sector catalog, such as ETFs, are grouped as unclassified.
    """
    return ExposureReport.of(load_portfolio(tool_context.state))


def simulate_trade(
    ticker: Ticker,
    side: TradeSide,
    quantity: Quantity,
    price: Price,
    tool_context: ToolContext,
) -> ScenarioReport:
    """Adds a hypothetical trade to this conversation's what-if scenario.

    Never changes the real portfolio. Trades accumulate until clear_scenario,
    and the whole scenario is replayed on top of the current real portfolio,
    so the result always reflects real trades recorded meanwhile. Fails when a
    simulated sell exceeds the projected position. The result lists the
    scenario trades with the projected positions and sector exposure, at cost.
    """
    trades = (
        *load_scenario(tool_context.state),
        _parse_trade(ticker, side, quantity, price),
    )
    projected = _project(load_portfolio(tool_context.state), trades)
    save_scenario(tool_context.state, trades)
    return ScenarioReport.of(trades, projected)


def clear_scenario(tool_context: ToolContext) -> ScenarioReport:
    """Discards every simulated trade of this conversation's scenario.

    The result has no trades and projects the real portfolio unchanged.
    """
    save_scenario(tool_context.state, ())
    return ScenarioReport.of((), load_portfolio(tool_context.state))


def _parse_trade(
    ticker: object, side: object, quantity: object, price: object
) -> Trade:
    try:
        args = _TradeArgs.model_validate(
            {"ticker": ticker, "side": side, "quantity": quantity, "price": price}
        )
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()
        )
        raise InvalidTradeError(details) from exc
    return Trade(args.ticker.strip().upper(), args.side, args.quantity, args.price)


def _project(portfolio: Portfolio, trades: tuple[Trade, ...]) -> Portfolio:
    return reduce(Portfolio.apply, trades, portfolio)
