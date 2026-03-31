# clarvia-langchain

LangChain integration for [Clarvia](https://clarvia.art) AEO (Agent Experience Optimization) scoring. Gate your LangChain tool calls based on how agent-friendly the target service is.

## Installation

```bash
pip install clarvia-langchain
```

## Quick Start

```python
from clarvia_langchain import CriteriaGate, GatedTool
from langchain_community.tools import SerpAPIWrapper

# 1. Create a gate with your Clarvia API key
gate = CriteriaGate(
    api_key="clv_xxx",
    min_rating="AGENT_FRIENDLY",  # Block services scoring below 70
)

# 2. Wrap any LangChain tool
search = SerpAPIWrapper()
gated_search = GatedTool(
    tool=search,
    gate=gate,
    service_url="https://serpapi.com",
)

# 3. Use normally — the gate checks AEO score before each call
result = gated_search.invoke({"query": "latest AI news"})
```

## Rating Tiers

| Rating | Score | Meaning |
|--------|-------|---------|
| `AGENT_NATIVE` | 90-100 | Fully optimized for AI agents |
| `AGENT_FRIENDLY` | 70-89 | Usable by agents with minor friction |
| `AGENT_POSSIBLE` | 50-69 | Partially usable, may have issues |
| `AGENT_HOSTILE` | 0-49 | Actively hostile or unusable by agents |

## Configuration

```python
gate = CriteriaGate(
    api_key="clv_xxx",
    min_rating="AGENT_FRIENDLY",  # or ServiceRating enum
    cache_ttl=3600,               # Cache scores for 1 hour (default)
    timeout=10.0,                 # HTTP timeout in seconds
)
```

### Handling Blocked Calls

```python
from clarvia_langchain import GatedTool, GateBlockedError

# Option 1: Raise on block (default)
gated = GatedTool(tool=my_tool, gate=gate, service_url="...")
try:
    result = gated.invoke({"query": "test"})
except GateBlockedError as e:
    print(f"Blocked: {e.gate_result.reason}")
    print(f"Try these instead: {e.gate_result.alternatives}")

# Option 2: Return error string (for agent consumption)
gated = GatedTool(
    tool=my_tool, gate=gate,
    service_url="...",
    raise_on_block=False,
)
result = gated.invoke({"query": "test"})
# result = "BLOCKED: ... | Alternatives: ..."
```

### Direct Gate Usage

```python
gate = CriteriaGate(api_key="clv_xxx")
result = gate.check("https://some-api.com")

print(result.allowed)       # True/False
print(result.score)         # 0-100
print(result.rating)        # ServiceRating enum
print(result.alternatives)  # List of suggested alternatives
```

## CrewAI Integration

`clarvia-langchain` works with any LangChain-compatible framework, including [CrewAI](https://github.com/crewAIInc/crewAI).

```python
from crewai import Agent, Task, Crew
from crewai_tools import SerperDevTool
from clarvia_langchain import CriteriaGate, GatedTool

# 1. Set up the gate
gate = CriteriaGate(api_key="clv_xxx", min_rating="AGENT_FRIENDLY")

# 2. Wrap any CrewAI-compatible tool
search = SerperDevTool()
gated_search = GatedTool(
    tool=search,
    gate=gate,
    service_url="https://serper.dev",
)

# 3. Use with CrewAI agents
researcher = Agent(
    role="Research Analyst",
    goal="Find reliable data from agent-friendly sources",
    tools=[gated_search],
)

task = Task(
    description="Research the latest trends in AI agent tooling",
    agent=researcher,
    expected_output="A summary of key trends",
)

crew = Crew(agents=[researcher], tasks=[task])
result = crew.kickoff()
```

The gate transparently checks AEO scores before each tool call. If a service scores below the threshold, the agent receives a structured error with suggested alternatives, allowing it to adapt its strategy.

## API Behavior

- **Caching**: Scores are cached in-memory with a 1-hour TTL by default. Use `gate.clear_cache()` to reset.
- **Fallback**: If the Clarvia API is unreachable, calls are allowed through with a warning log (fail-open).
- **Async**: Both sync and async paths are supported (`gate.check()` / `gate.acheck()`).

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
