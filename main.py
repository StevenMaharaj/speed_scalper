import importlib
import pkgutil
import inspect
import typer
import strategy as strategy_pkg
from strategy.strategy import Strategy

app = typer.Typer()


def load_strategies() -> dict[str, type]:
    strategies = {}
    for _, module_name, _ in pkgutil.iter_modules(strategy_pkg.__path__):
        if module_name == "strategy":
            continue
        module = importlib.import_module(f"strategy.{module_name}")
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if name != "Strategy" and hasattr(obj, "run_strategy"):
                strategies[name] = obj
    return strategies


@app.command()
def run(strategy_name: str = typer.Argument(..., help="Name of the strategy class to run")):
    strategies = load_strategies()
    if strategy_name not in strategies:
        available = ", ".join(strategies.keys()) or "none found"
        typer.echo(f"Unknown strategy '{strategy_name}'. Available: {available}", err=True)
        raise typer.Exit(1)
    instance: Strategy = strategies[strategy_name]()
    instance.run_strategy()


if __name__ == "__main__":
    app()
