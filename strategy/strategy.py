from typing import Protocol


class Strategy(Protocol):
    def run_strategy(self) -> None:
        ...
