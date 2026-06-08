import typer
from agentlens.cli.trace import app as trace_app
from agentlens.cli.stats import app as stats_app
from agentlens.cli.snapshot import app as snapshot_app
from agentlens.cli.dashboard import app as dashboard_app
from agentlens.cli.proxy import app as proxy_app

app = typer.Typer(name="agentlens", help="AgentLens — AI agent profiler and optimizer")
app.add_typer(trace_app, name="trace")
app.add_typer(stats_app, name="stats")
app.add_typer(snapshot_app, name="snapshot")
app.add_typer(dashboard_app, name="dashboard")
app.add_typer(proxy_app, name="proxy")

if __name__ == "__main__":
    app()
