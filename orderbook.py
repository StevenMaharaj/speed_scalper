import asyncio
from asyncio import Queue

from pybit.unified_trading import WebSocket


class MarketDataStreamer:
    def __init__(self, symbols: list[str], market_data_queue: Queue):
        self.symbols = symbols
        self.prices = {symbol: 0.0 for symbol in symbols}
        self.market_data_queue = market_data_queue

    async def stream(self):
        t1 = asyncio.create_task(self._conn())
        t2 = asyncio.create_task(self.push_market_data())
        await asyncio.gather(t1, t2)

    def on_message(self, message):
        # print(f"Received message: {message}")
        self.handle_order_book_update(message)
        # print(f"{self.prices}")

    async def push_market_data(self):
        while True:
            await asyncio.sleep(1)  # Adjust the sleep duration as needed
            await self.market_data_queue.put(
                self.prices.copy()
            )  # Push a copy of the current prices to the queue

    def handle_order_book_update(self, message):
        data = message.get("data")
        symbol = data.get("s")
        if symbol in self.prices:
            self.prices[symbol] = 0.5 * (
                float(data.get("b")[0][0]) + float(data.get("a")[0][0])
            )  # Update the price with the best bid

    async def _conn(self):
        ws = WebSocket(channel_type="linear", testnet=False)  # Use testnet for testing
        ws.orderbook_stream(1, self.symbols, self.on_message)


async def receive_market_data(market_data_queue: Queue):
    while True:
        market_data = await market_data_queue.get()
        print(f"Received market data: {market_data}")
        # Here you can implement logic to process the market data, such as generating trade signals


async def main():
    queue = Queue()
    streamer = MarketDataStreamer(
        symbols=["BTCUSDT", "ETHUSDT", "XRPUSDT"], market_data_queue=queue
    )
    await asyncio.gather(streamer.stream(), receive_market_data(queue))


if __name__ == "__main__":
    asyncio.run(main())
