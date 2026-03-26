"""Clarvia LangChain integration — AEO-gated tool execution.

Works with LangChain, CrewAI, AutoGen, or any Python agent framework.

Quick start (framework-agnostic):
    import clarvia_langchain as clarvia

    # Check a service before using it
    result = clarvia.check("https://api.example.com")
    if result["passed"]:
        # safe to use
        ...

    # Auto-gate all tool calls with a decorator
    @clarvia.before_tool_call(min_score=70)
    def my_tool(url: str):
        return httpx.get(url)

LangChain-specific:
    from clarvia_langchain import CriteriaGate, GatedTool

    gate = CriteriaGate(api_key="clv_xxx")
    gated = GatedTool(tool=my_tool, gate=gate)
"""

from .gate import CriteriaGate
from .middleware import (
    activate,
    before_tool_call,
    check,
    deactivate,
    gate_context,
)
from .models import GateResult, ServiceRating
from .tool import GateBlockedError, GatedTool

__all__ = [
    # Core
    "CriteriaGate",
    "GatedTool",
    "GateBlockedError",
    "GateResult",
    "ServiceRating",
    # Framework-agnostic middleware
    "activate",
    "deactivate",
    "before_tool_call",
    "check",
    "gate_context",
]

__version__ = "0.2.0"
