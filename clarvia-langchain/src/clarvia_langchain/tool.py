"""GatedTool — LangChain BaseTool wrapper with Clarvia AEO gating."""

from __future__ import annotations

import logging
from typing import Any, Optional, Type
from urllib.parse import urlparse

from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain_core.tools import BaseTool

from .gate import CriteriaGate
from .models import GateResult

logger = logging.getLogger("clarvia_langchain")


class GateBlockedError(Exception):
    """Raised when a tool invocation is blocked by the Clarvia gate.

    Attributes:
        gate_result: The full ``GateResult`` that caused the block.
    """

    def __init__(self, gate_result: GateResult) -> None:
        self.gate_result = gate_result
        msg = gate_result.reason
        if gate_result.alternatives:
            alts = ", ".join(gate_result.alternatives)
            msg += f" | Suggested alternatives: {alts}"
        super().__init__(msg)


class GatedTool(BaseTool):
    """Wraps an existing LangChain tool with a Clarvia AEO gate.

    Before every invocation the gate checks the target service's AEO score.
    If the score falls below the configured minimum rating, the call is
    blocked and a ``GateBlockedError`` is raised (or a structured error
    string is returned when ``raise_on_block=False``).

    Args:
        tool: The underlying LangChain tool to wrap.
        gate: A configured ``CriteriaGate`` instance.
        service_url: The URL of the service this tool calls. If not
            provided, the tool will attempt to infer it from the tool's
            ``metadata`` dict (key ``"service_url"``).
        raise_on_block: If True (default), raise ``GateBlockedError``
            when blocked. If False, return a descriptive error string.

    Example::

        gate = CriteriaGate(api_key="clv_xxx", min_rating="AGENT_FRIENDLY")
        gated = GatedTool(tool=my_search_tool, gate=gate)
        result = gated.invoke({"query": "hello"})
    """

    name: str = "clarvia_gated"
    description: str = "Clarvia-gated tool"
    tool: Any = None  # BaseTool — typed as Any for Pydantic v2 compatibility
    gate: Any = None  # CriteriaGate
    service_url: Optional[str] = None
    raise_on_block: bool = True

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, **kwargs: Any) -> None:
        # Pre-populate name/description from the wrapped tool before validation
        inner = kwargs.get("tool")
        if inner is not None:
            if "name" not in kwargs:
                kwargs["name"] = getattr(inner, "name", "clarvia_gated")
            if "description" not in kwargs:
                kwargs["description"] = getattr(inner, "description", "Clarvia-gated tool")
        super().__init__(**kwargs)

    @property
    def args_schema(self) -> Optional[Type]:  # type: ignore[override]
        return self.tool.args_schema if self.tool else None

    # ------------------------------------------------------------------
    # Core execution
    # ------------------------------------------------------------------

    def _run(
        self,
        *args: Any,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs: Any,
    ) -> Any:
        url = self._resolve_service_url()
        result = self.gate.check(url)

        logger.info(
            "Gate check for %s: score=%s rating=%s allowed=%s",
            url,
            result.score,
            result.rating.value,
            result.allowed,
        )

        if not result.allowed:
            return self._handle_block(result)

        return self.tool._run(*args, run_manager=run_manager, **kwargs)

    async def _arun(
        self,
        *args: Any,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs: Any,
    ) -> Any:
        url = self._resolve_service_url()
        result = await self.gate.acheck(url)

        logger.info(
            "Gate check for %s: score=%s rating=%s allowed=%s",
            url,
            result.score,
            result.rating.value,
            result.allowed,
        )

        if not result.allowed:
            return self._handle_block(result)

        return await self.tool._arun(*args, run_manager=run_manager, **kwargs)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_service_url(self) -> str:
        """Determine the service URL to check."""
        if self.service_url:
            return self.service_url
        # Try tool metadata
        meta = getattr(self.tool, "metadata", None) or {}
        url = meta.get("service_url")
        if url:
            return url
        raise ValueError(
            f"No service_url configured for GatedTool wrapping '{self.tool.name}'. "
            f"Pass service_url= explicitly or set tool.metadata['service_url']."
        )

    def _handle_block(self, result: GateResult) -> str:
        """Handle a blocked invocation."""
        if self.raise_on_block:
            raise GateBlockedError(result)
        # Return structured error message for agent consumption
        parts = [f"BLOCKED: {result.reason}"]
        if result.alternatives:
            parts.append(f"Alternatives: {', '.join(result.alternatives)}")
        return " | ".join(parts)
