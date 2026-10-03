from collections.abc import AsyncGenerator
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.events import Event
from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from google.adk.runners import InMemoryRunner
from google.genai import types

from adk_02_portfolio_desk.state import PORTFOLIO_KEY, RECORDED_TRADES_KEY
from adk_02_portfolio_desk.tool_errors import report_tool_error
from adk_02_portfolio_desk.tools import record_trade

APP_NAME = "tool_flow_probe"
USER_ID = "caio"
PETR4_BUY = {"ticker": "PETR4", "side": "buy", "quantity": 100, "price": 38.2}
VALE3_BUY = {"ticker": "VALE3", "side": "buy", "quantity": 10, "price": 60.15}


class ScriptedLlm(BaseLlm):
    turns: list[list[types.Part]]

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse]:
        yield LlmResponse(content=types.Content(role="model", parts=self.turns.pop(0)))


def calls(*args: dict[str, Any]) -> list[types.Part]:
    return [
        types.Part(function_call=types.FunctionCall(name="record_trade", args=a))
        for a in args
    ]


def done() -> list[types.Part]:
    return [types.Part(text="Done.")]


def runner_for(*turns: list[types.Part]) -> InMemoryRunner:
    agent = LlmAgent(
        name="tool_flow_probe",
        model=ScriptedLlm(model="scripted", turns=list(turns)),
        tools=[record_trade],
        on_tool_error_callback=report_tool_error,
    )
    return InMemoryRunner(agent=agent, app_name=APP_NAME)


async def send(runner: InMemoryRunner, session_id: str) -> list[Event]:
    message = types.Content(role="user", parts=[types.Part(text="record it")])
    return [
        event
        async for event in runner.run_async(
            user_id=USER_ID, session_id=session_id, new_message=message
        )
    ]


async def stored_state(runner: InMemoryRunner, session_id: str) -> dict[str, Any]:
    session = await runner.session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )
    assert session is not None
    return session.state


def responses(events: list[Event]) -> list[dict[str, Any]]:
    return [
        response.response or {}
        for event in events
        for response in event.get_function_responses()
    ]


def held(state: dict[str, Any]) -> dict[str, int]:
    return {p["ticker"]: p["quantity"] for p in state[PORTFOLIO_KEY]["positions"]}


async def new_session(runner: InMemoryRunner) -> str:
    session = await runner.session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID
    )
    return session.id


async def test_duplicate_parallel_calls_record_the_trade_once() -> None:
    runner = runner_for(calls(PETR4_BUY, PETR4_BUY), done())
    session_id = await new_session(runner)

    events = await send(runner, session_id)

    errors = [r["error"] for r in responses(events) if "error" in r]
    assert len(errors) == 1
    assert errors[0].startswith("DuplicateTradeError")
    assert held(await stored_state(runner, session_id)) == {"PETR4": 100}


async def test_distinct_parallel_calls_both_persist() -> None:
    runner = runner_for(calls(PETR4_BUY, VALE3_BUY), done())
    session_id = await new_session(runner)

    await send(runner, session_id)

    assert held(await stored_state(runner, session_id)) == {"PETR4": 100, "VALE3": 10}


async def test_same_trade_in_a_later_turn_is_recorded_again() -> None:
    runner = runner_for(calls(PETR4_BUY), done(), calls(PETR4_BUY), done())
    session_id = await new_session(runner)

    await send(runner, session_id)
    await send(runner, session_id)

    state = await stored_state(runner, session_id)
    assert held(state) == {"PETR4": 200}
    assert RECORDED_TRADES_KEY not in state
