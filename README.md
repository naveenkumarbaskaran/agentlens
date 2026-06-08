# AgentLens

**Runtime profiler and optimization engine for AI agents using MCP.**

AgentLens sits between your agent and its tools — observing every MCP schema load, tool call, and LLM call, then using that history to automatically pre-select the minimal tool set for future runs. The result: **80–95% reduction in schema token overhead**, zero code changes in the agent.

```bash
pip install agentlens
```

---

## The Problem

Every agent connecting to an MCP server loads **all** tool schemas on every call — even tools it will never use. A 50-tool server dumps 8,000–15,000 tokens of schema into every LLM call. No existing observability tool (LangSmith, Arize, Helicone) measures or optimizes this.

## The Solution

```
Before AgentLens                    After AgentLens
─────────────────                   ───────────────
Agent → 50 tool schemas             Agent → 6 tool schemas (snapshot)
        ↓ 12,000 tokens                     ↓ 800 tokens
        LLM picks 6 tools                   LLM calls correct tools
        Cost: $0.036/call                   Cost: $0.0024/call  (93% saving)
```

AgentLens **profiles** your agent, builds a **snapshot** of the tools it actually uses per task type, and on the next run pre-loads only those tools.

---

## Installation

```bash
# Core
pip install agentlens

# With Postgres support
pip install "agentlens[postgres]"

# With LangChain support
pip install "agentlens[langchain]"

# With OpenAI support
pip install "agentlens[openai]"

# Everything
pip install "agentlens[postgres,langchain,openai]"
```

Requires Python 3.11+.

---

## Quick Start

### 1. Wrap your Anthropic client (10 lines)

```python
import anthropic
from agentlens import AgentLens

lens = AgentLens(store="sqlite:///agentlens.db")
await lens.init()

raw = anthropic.Anthropic()

async with lens.session(agent_id="my-agent", task_type="code-review") as sess:
    client = lens.wrap_anthropic(session=sess)
    # client records every call — token counts, cost, latency
```

### 2. Wrap your MCP client (zero code in the agent)

```bash
# Start AgentLens as a transparent proxy in front of your MCP server
agentlens proxy start --upstream "uvx mcp-server-filesystem /tmp"

# Your agent now points to this proxy instead of the real server
# All tool calls are profiled automatically
```

### 3. Build a snapshot after enough sessions

```bash
agentlens snapshot build code-review --min-sessions 5
```

### 4. Use the snapshot — agent loads only 6 tools instead of 50

```bash
agentlens proxy start --upstream "uvx mcp-server-filesystem /tmp" --task-type code-review
```

### 5. View your savings

```bash
agentlens stats show --last 7d
agentlens dashboard show        # live terminal UI
```

---

## Architecture

```
┌────────────────────────────────────────────────────────┐
│                     Agent / LLM App                     │
└──────────────┬───────────────────────────┬─────────────┘
               │ SDK wrapper               │ MCP proxy
     ┌─────────▼──────────┐     ┌──────────▼──────────┐
     │   AgentLens SDK     │     │  AgentLens Proxy     │
     │  wrap_anthropic()   │     │  (zero code change)  │
     │  wrap_openai()      │     │  stdio / HTTP        │
     └─────────┬──────────┘     └──────────┬───────────┘
               └──────────────┬────────────┘
                              │
                   ┌──────────▼──────────┐
                   │   Profiler Engine    │
                   │  LensEvent stream    │
                   └──────────┬──────────┘
                              │
                   ┌──────────▼──────────┐
                   │    Profile Store     │
                   │  SQLite · Postgres   │
                   └──────────┬──────────┘
                              │
                   ┌──────────▼──────────┐
                   │  Snapshot System     │
                   │  build · export      │
                   │  import · predict    │
                   └──────────┬──────────┘
                              │
                   ┌──────────▼──────────┐
                   │  Optimization Engine │
                   │  pre-select tools    │
                   │  compress schemas    │
                   └─────────────────────┘
```

---

## SDK Reference

### AgentLens facade

```python
from agentlens import AgentLens

lens = AgentLens(
    store="sqlite:///agentlens.db",  # or "postgresql://..."
    model="claude-sonnet-4-6",
)
await lens.init()

# Session context manager
async with lens.session(agent_id="my-agent", task_type="code-review") as sess:
    client = lens.wrap_anthropic(session=sess)   # Anthropic
    client = lens.wrap_openai(session=sess)       # OpenAI (pip install agentlens[openai])
    interceptor = lens.wrap_mcp(session=sess, source="my-mcp-server")

# Predictive task inference (v3)
task_type = await lens.classify_task(
    message="Please review this pull request",
    known_task_types=["code-review", "db-query", "deploy"],
)
```

### Snapshot Registry (share snapshots across teams)

```python
from agentlens.snapshot.registry import SnapshotRegistry

# Export
registry = SnapshotRegistry()
registry.add(snapshot)
registry.export("my_snapshots.json")

# Import
registry = SnapshotRegistry.import_from("my_snapshots.json")
snap = registry.get("code-review")
```

### LangChain Integration

```python
from agentlens.integrations.langchain import LangChainLensCallback

cb = LangChainLensCallback(store=store, session_id="my-session")
chain.invoke({"input": "..."}, config={"callbacks": [cb]})
```

---

## CLI Reference

```bash
# Traces
agentlens trace show <session-id>

# Stats
agentlens stats show --last 7d

# Snapshots
agentlens snapshot build <task-type> --min-sessions 5
agentlens snapshot list
agentlens snapshot export <task-type> snapshots.json
agentlens snapshot import snapshots.json

# MCP Proxy
agentlens proxy start --upstream "uvx mcp-server-filesystem /tmp"
agentlens proxy start --upstream "..." --task-type code-review --port 3100

# Dashboard
agentlens dashboard show --refresh 2
```

---

## Competitive Landscape

| Tool | Observability | Token cost | MCP-aware | Snapshot optimization | Predictive inference |
|---|---|---|---|---|---|
| LangSmith | ✅ | Partial | ❌ | ❌ | ❌ |
| Arize Phoenix | ✅ | Partial | ❌ | ❌ | ❌ |
| Helicone | Partial | ✅ | ❌ | ❌ | ❌ |
| **AgentLens** | **✅** | **✅** | **✅** | **✅** | **✅** |

---

## Roadmap

| Version | Status | What shipped |
|---|---|---|
| v1 (0.1.0) | ✅ | Profiler engine, LensEvent, SQLiteStore, Anthropic + MCP integrations, CLI basics |
| v2 (0.2.0) | ✅ | MCP proxy server, SnapshotStore, PostgresStore, LangChain integration, live dashboard |
| v3 (0.3.0) | ✅ | Predictive task inference, SnapshotRegistry, OpenAI integration, PyPI publish |

---

## License

MIT
