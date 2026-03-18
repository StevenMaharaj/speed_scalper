from typing import Protocol


class Strategy(Protocol):
    async def run_strategy(self) -> None:
        ...
