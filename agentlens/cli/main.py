import typer
from agentlens.cli.trace import app as trace_app
from agentlens.cli.stats import app as stats_app

app = typer.Typer(name="agentlens", help="AgentLens — AI agent profiler and optimizer")
app.add_typer(trace_app, name="trace")
app.add_typer(stats_app, name="stats")

if __name__ == "__main__":
    app()
