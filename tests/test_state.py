import json
from decimal import Decimal

import pytest
from google.adk.sessions.state import State
from pydantic import ValidationError

from adk_02_portfolio_desk.domain import Portfolio, Side, Trade
from adk_02_portfolio_desk.state import (
    PORTFOLIO_KEY,
    RECORDED_TRADES_KEY,
    SCENARIO_KEY,
    load_portfolio,
    load_recorded_trades,
    load_scenario,
    save_portfolio,
    save_recorded_trades,
    save_scenario,
)


def empty_state() -> State:
    return State(value={}, delta={})


def sample_portfolio() -> Portfolio:
    return (
        Portfolio()
        .apply(Trade("PETR4", Side.BUY, 100, Decimal("38.20")))
        .apply(Trade("VALE3", Side.BUY, 10, Decimal("60.15")))
    )


def test_missing_keys_load_as_empty() -> None:
    state = empty_state()

    assert load_portfolio(state) == Portfolio()
    assert load_scenario(state) == ()
    assert load_recorded_trades(state) == ()


def test_portfolio_round_trips_through_state() -> None:
    state = empty_state()

    save_portfolio(state, sample_portfolio())

    assert load_portfolio(state) == sample_portfolio()


def test_saving_records_a_json_native_delta() -> None:
    state = empty_state()

    save_portfolio(state, sample_portfolio())

    assert state.has_delta()
    assert json.loads(json.dumps(state.to_dict()))[PORTFOLIO_KEY] == {
        "positions": [
            {"ticker": "PETR4", "quantity": 100, "cost": "3820.00"},
            {"ticker": "VALE3", "quantity": 10, "cost": "601.50"},
        ]
    }


def test_each_save_replaces_the_whole_value() -> None:
    state = empty_state()
    save_portfolio(state, sample_portfolio())
    first_value = state[PORTFOLIO_KEY]

    save_portfolio(state, Portfolio())

    assert state[PORTFOLIO_KEY] is not first_value
    assert first_value["positions"]


def test_scenario_round_trips_through_state() -> None:
    state = empty_state()
    trades = (
        Trade("PETR4", Side.SELL, 50, Decimal("41.00")),
        Trade("ITUB4", Side.BUY, 100, Decimal("33.10")),
    )

    save_scenario(state, trades)

    assert load_scenario(state) == trades
    assert state[SCENARIO_KEY]["trades"][0]["side"] == "sell"


def test_recorded_trades_live_in_temp_scope() -> None:
    state = empty_state()
    trades = (Trade("PETR4", Side.BUY, 100, Decimal("38.20")),)

    save_recorded_trades(state, trades)

    assert RECORDED_TRADES_KEY.startswith(State.TEMP_PREFIX)
    assert load_recorded_trades(state) == trades


def test_corrupted_state_fails_loudly() -> None:
    state = State(value={PORTFOLIO_KEY: {"positions": [{"ticker": "PETR4"}]}}, delta={})

    with pytest.raises(ValidationError):
        load_portfolio(state)


def test_in_place_mutation_never_reaches_the_delta() -> None:
    state = State(value={PORTFOLIO_KEY: {"positions": []}}, delta={})

    state[PORTFOLIO_KEY]["positions"].append({"ticker": "PETR4"})

    assert not state.has_delta()
