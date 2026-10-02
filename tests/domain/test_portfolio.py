from decimal import Decimal

import pytest

from adk_02_portfolio_desk.domain import (
    InsufficientPositionError,
    Portfolio,
    Position,
    Side,
    Trade,
)


def buy(ticker: str, quantity: int, price: str) -> Trade:
    return Trade(ticker, Side.BUY, quantity, Decimal(price))


def sell(ticker: str, quantity: int, price: str) -> Trade:
    return Trade(ticker, Side.SELL, quantity, Decimal(price))


def test_first_buy_opens_a_position_at_trade_cost() -> None:
    portfolio = Portfolio().apply(buy("PETR4", 100, "38.20"))

    assert portfolio.positions == (Position("PETR4", 100, Decimal("3820.00")),)


def test_second_buy_blends_the_average_price() -> None:
    portfolio = (
        Portfolio().apply(buy("PETR4", 100, "38.20")).apply(buy("PETR4", 50, "40.15"))
    )

    position = portfolio.position("PETR4")
    assert position == Position("PETR4", 150, Decimal("5827.50"))
    assert position.average_price == Decimal("38.85")


def test_partial_sell_keeps_the_average_price() -> None:
    portfolio = (
        Portfolio()
        .apply(buy("PETR4", 100, "38.20"))
        .apply(buy("PETR4", 50, "40.15"))
        .apply(sell("PETR4", 60, "45.00"))
    )

    position = portfolio.position("PETR4")
    assert position == Position("PETR4", 90, Decimal("3496.50"))
    assert position.average_price == Decimal("38.85")


def test_released_cost_rounds_to_cents() -> None:
    portfolio = (
        Portfolio()
        .apply(buy("VALE3", 3, "10.00"))
        .apply(buy("VALE3", 1, "10.01"))
        .apply(sell("VALE3", 1, "11.00"))
    )

    assert portfolio.position("VALE3") == Position("VALE3", 3, Decimal("30.01"))


def test_selling_everything_closes_the_position() -> None:
    portfolio = (
        Portfolio().apply(buy("PETR4", 100, "38.20")).apply(sell("PETR4", 100, "40"))
    )

    assert portfolio.positions == ()


def test_positions_stay_sorted_by_ticker() -> None:
    portfolio = (
        Portfolio()
        .apply(buy("VALE3", 10, "60"))
        .apply(buy("ITUB4", 10, "30"))
        .apply(buy("PETR4", 10, "38"))
    )

    assert [p.ticker for p in portfolio.positions] == ["ITUB4", "PETR4", "VALE3"]


def test_apply_returns_a_new_portfolio() -> None:
    original = Portfolio().apply(buy("PETR4", 100, "38.20"))

    original.apply(buy("VALE3", 10, "60"))

    assert [p.ticker for p in original.positions] == ["PETR4"]


def test_total_cost_sums_every_position() -> None:
    portfolio = (
        Portfolio().apply(buy("PETR4", 100, "38.20")).apply(buy("VALE3", 10, "60"))
    )

    assert portfolio.total_cost == Decimal("4420.00")


def test_selling_more_than_held_is_rejected() -> None:
    portfolio = Portfolio().apply(buy("PETR4", 100, "38.20"))

    with pytest.raises(InsufficientPositionError, match="holding 100"):
        portfolio.apply(sell("PETR4", 101, "40"))


def test_selling_an_unheld_ticker_is_rejected() -> None:
    with pytest.raises(InsufficientPositionError, match="no position in PETR4"):
        Portfolio().apply(sell("PETR4", 1, "40"))
