from typing import Any

from google.adk.tools import BaseTool, ToolContext

from .domain import PortfolioError
from .tools import DuplicateTradeError

RECOVERABLE_ERRORS = (PortfolioError, DuplicateTradeError)


def report_tool_error(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    error: Exception,
) -> dict[str, str] | None:
    if not isinstance(error, RECOVERABLE_ERRORS):
        return None
    return {"error": f"{type(error).__name__}: {error}"}
