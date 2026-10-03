from decimal import Decimal
from typing import cast

import pytest

from adk_02_portfolio_desk.domain import InvalidTradeError, Side, Trade


def test_notional_is_price_times_quantity() -> None:
    trade = Trade("PETR4", Side.BUY, 100, Decimal("38.20"))

    assert trade.notional == Decimal("3820.00")


@pytest.mark.parametrize("ticker", ["PETR4", "TAEE11", "BOVA11"])
def test_accepts_b3_tickers(ticker: str) -> None:
    assert Trade(ticker, Side.BUY, 1, Decimal("10")).ticker == ticker


@pytest.mark.parametrize("ticker", ["petr4", "PETR", "PETR4F", "PETR123", "AAPL"])
def test_rejects_non_b3_tickers(ticker: str) -> None:
    with pytest.raises(InvalidTradeError, match="B3 ticker"):
        Trade(ticker, Side.BUY, 1, Decimal("10"))


@pytest.mark.parametrize("quantity", [0, -100])
def test_rejects_non_positive_quantity(quantity: int) -> None:
    with pytest.raises(InvalidTradeError, match="quantity"):
        Trade("PETR4", Side.BUY, quantity, Decimal("10"))


@pytest.mark.parametrize("price", ["0", "-1", "NaN", "Infinity"])
def test_rejects_invalid_price(price: str) -> None:
    with pytest.raises(InvalidTradeError, match="positive amount"):
        Trade("PETR4", Side.BUY, 1, Decimal(price))


def test_rejects_sub_cent_price() -> None:
    with pytest.raises(InvalidTradeError, match="two decimal places"):
        Trade("PETR4", Side.BUY, 1, Decimal("38.205"))


def test_accepts_trailing_zeros_beyond_cents() -> None:
    assert Trade("PETR4", Side.BUY, 1, Decimal("38.2000")).price == Decimal("38.2")


def test_rejects_a_plain_string_side() -> None:
    with pytest.raises(InvalidTradeError, match="side must be a Side"):
        Trade("PETR4", cast(Side, "buy"), 1, Decimal("10"))
