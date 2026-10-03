from decimal import Decimal
from types import SimpleNamespace
from typing import cast

import pytest
from google.adk.sessions.state import State
from google.adk.tools import ToolContext

from adk_02_portfolio_desk.domain import (
    InsufficientPositionError,
    InvalidTradeError,
    Sector,
    Side,
)
from adk_02_portfolio_desk.state import PORTFOLIO_KEY, SCENARIO_KEY
from adk_02_portfolio_desk.tools import (
    DuplicateTradeError,
    clear_scenario,
    get_exposure,
    get_positions,
    record_trade,
    simulate_trade,
)


def tool_context() -> ToolContext:
    return cast(ToolContext, SimpleNamespace(state=State(value={}, delta={})))


def test_record_trade_normalizes_the_ticker_and_price() -> None:
    receipt = record_trade(" petr4 ", Side.BUY, 100, 38.2, tool_context())

    assert receipt.trade.ticker == "PETR4"
    assert receipt.trade.price == Decimal("38.2")
    assert receipt.trade.notional == Decimal("3820.0")
    assert receipt.position is not None
    assert receipt.position.average_price == Decimal("38.20")


def test_record_trade_persists_the_portfolio_in_user_state() -> None:
    context = tool_context()

    record_trade("PETR4", Side.BUY, 100, 38.2, context)

    assert context.state[PORTFOLIO_KEY]["positions"][0]["ticker"] == "PETR4"
    assert get_positions(context).total_cost == Decimal("3820.00")


def test_record_trade_reports_a_closed_position_as_none() -> None:
    context = tool_context()
    record_trade("PETR4", Side.BUY, 100, 38.2, context)

    receipt = record_trade("PETR4", Side.SELL, 100, 41.0, context)

    assert receipt.position is None
    assert get_positions(context).positions == []


def test_record_trade_rejects_a_duplicate_in_the_same_turn() -> None:
    context = tool_context()
    record_trade("PETR4", Side.BUY, 100, 38.2, context)

    with pytest.raises(DuplicateTradeError, match="already recorded"):
        record_trade("PETR4", Side.BUY, 100, 38.2, context)

    assert get_positions(context).positions[0].quantity == 100


def test_failed_trade_leaves_state_untouched() -> None:
    context = tool_context()

    with pytest.raises(InsufficientPositionError):
        record_trade("PETR4", Side.SELL, 1, 38.2, context)

    assert not context.state.has_delta()


def test_record_trade_rejects_sub_cent_prices() -> None:
    with pytest.raises(InvalidTradeError, match="two decimal places"):
        record_trade("PETR4", Side.BUY, 1, 38.205, tool_context())


def test_record_trade_coerces_raw_model_arguments() -> None:
    receipt = record_trade(
        "PETR4",
        cast(Side, "buy"),
        cast(int, 100.0),
        38.2,
        tool_context(),
    )

    assert receipt.trade.side is Side.BUY
    assert receipt.trade.quantity == 100


@pytest.mark.parametrize(
    ("side", "quantity", "field"),
    [("hold", 100, "side"), ("buy", 100.5, "quantity")],
)
def test_record_trade_rejects_malformed_arguments(
    side: str, quantity: float, field: str
) -> None:
    with pytest.raises(InvalidTradeError, match=f"^{field}: "):
        record_trade(
            "PETR4", cast(Side, side), cast(int, quantity), 38.2, tool_context()
        )


def test_get_exposure_groups_by_sector() -> None:
    context = tool_context()
    record_trade("PETR4", Side.BUY, 100, 38.2, context)
    record_trade("ITUB4", Side.BUY, 100, 33.1, context)

    report = get_exposure(context)

    assert [s.sector for s in report.sectors] == [Sector.OIL_AND_GAS, Sector.BANKS]


def test_simulation_never_touches_the_real_portfolio() -> None:
    context = tool_context()
    record_trade("PETR4", Side.BUY, 100, 38.2, context)

    report = simulate_trade("PETR4", Side.SELL, 50, 41.0, context)

    assert report.projected.positions[0].quantity == 50
    assert get_positions(context).positions[0].quantity == 100


def test_simulated_trades_accumulate_until_cleared() -> None:
    context = tool_context()
    record_trade("PETR4", Side.BUY, 100, 38.2, context)
    simulate_trade("PETR4", Side.SELL, 50, 41.0, context)

    report = simulate_trade("ITUB4", Side.BUY, 100, 33.1, context)

    assert len(report.trades) == 2
    assert [p.ticker for p in report.projected.positions] == ["ITUB4", "PETR4"]

    cleared = clear_scenario(context)

    assert cleared.trades == []
    assert cleared.projected == get_positions(context)


def test_scenario_replays_on_top_of_later_real_trades() -> None:
    context = tool_context()
    record_trade("PETR4", Side.BUY, 100, 38.2, context)
    simulate_trade("PETR4", Side.SELL, 50, 41.0, context)
    record_trade("PETR4", Side.BUY, 100, 40.0, context)

    report = simulate_trade("VALE3", Side.BUY, 10, 60.0, context)

    assert report.projected.positions[0].quantity == 150


def test_invalid_simulation_keeps_the_previous_scenario() -> None:
    context = tool_context()
    record_trade("PETR4", Side.BUY, 100, 38.2, context)
    simulate_trade("PETR4", Side.SELL, 50, 41.0, context)

    with pytest.raises(InsufficientPositionError):
        simulate_trade("PETR4", Side.SELL, 51, 41.0, context)

    assert len(context.state[SCENARIO_KEY]["trades"]) == 1
