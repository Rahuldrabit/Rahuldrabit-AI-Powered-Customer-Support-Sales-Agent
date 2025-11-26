"""LangChain tool bindings for agent utilities."""

from typing import Any, Dict, Callable, List

try:
    from langchain_core.tools import tool
    HAVE_LC_TOOLS = True
except Exception:
    HAVE_LC_TOOLS = False
    def tool(fn=None, **kwargs):  # type: ignore
        def _wrap(f):
            return f
        return _wrap(fn) if fn else _wrap

from app.agent.tools import (
    detect_language as _detect_language,
    extract_order_number as _extract_order_number,
    extract_sentiment_indicators as _sentiment,
)


@tool("detect_language", return_direct=False)
def detect_language_tool(text: str) -> str:
    """Detect language code for the given text. Returns codes like 'en', 'es', 'fr', 'de'."""
    return _detect_language(text)


@tool("extract_order_number", return_direct=False)
def extract_order_number_tool(text: str) -> str:
    """Extract order number from text if present; returns empty string when not found."""
    val = _extract_order_number(text)
    return val or ""


@tool("sentiment", return_direct=False)
def sentiment_tool(text: str) -> float:
    """Compute sentiment score in [-1.0, 1.0] from the text."""
    return float(_sentiment(text))


def get_langchain_tools() -> List[Any]:
    """Return list of LangChain Tool objects if available, else empty list."""
    if not HAVE_LC_TOOLS:
        return []
    # The @tool decorator returns Tool instances
    return [detect_language_tool, extract_order_number_tool, sentiment_tool]


# Local registry for manual execution of tool calls
_TOOL_REGISTRY: Dict[str, Callable[..., Any]] = {
    "detect_language": detect_language_tool,  # type: ignore
    "extract_order_number": extract_order_number_tool,  # type: ignore
    "sentiment": sentiment_tool,  # type: ignore
}


def execute_tool_call(name: str, args: Dict[str, Any]) -> Any:
    """Execute a tool call by name using the local registry."""
    fn = _TOOL_REGISTRY.get(name)
    if fn is None:
        raise ValueError(f"Unknown tool: {name}")
    # Decorated functions expect named args
    return fn.invoke(args) if hasattr(fn, "invoke") else fn(**args)
