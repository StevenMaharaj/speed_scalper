import asyncio
import copy
import os
from asyncio import Queue

from dotenv import load_dotenv
from pybit.unified_trading import WebSocket

from common import Order, OrderManager, Positions
from fed_logger import get_logger

log = get_logger(__name__)


class AccountDataStreamer:
    def __init__(self, symbols: list[str], account_data_queue: Queue):
        self.account_data_queue = account_data_queue
        self.account_data = {
            "positions": Positions(symbols),
            "orders": OrderManager(symbols),
        }

        self.account_data_queue = account_data_queue
        self.api_key, self.api_secret = self.load_api_credentials()

    def load_api_credentials(self):
        load_dotenv()
        api_key = os.getenv("BYBIT_1_KEY")
        api_secret = os.getenv("BYBIT_1_SECRET")
        return api_key, api_secret

    def on_message(self, message):
        # print(f"Received message: {message}")
        if message.get("topic") != "order":
            return
        self.handle_order_topic(message)
        self.loop.call_soon_threadsafe(
            self.account_data_queue.put_nowait, copy.deepcopy(self.account_data)
        )

    async def stream(self):
        print("Starting account data stream...")
        self.loop = asyncio.get_event_loop()
        self._stop = asyncio.Event()
        self.ws = WebSocket(
            channel_type="private",
            testnet=False,
            api_key=self.api_key,
            api_secret=self.api_secret,
        )
        self.ws.order_stream(self.on_message)
        await self._stop.wait()

    def handle_order_topic(self, message):
        for data in message.get("data", []):
            order = Order(
                symbol=data["symbol"],
                quantity=float(data["qty"]),
                price=float(data["price"]),
                order_type=data["orderType"],
                order_side=data["side"],
                order_status=data["orderStatus"],
                order_id=data["orderId"],
                client_order_id=data.get("orderLinkId", ""),
            )
            log.info(f"Processing order update: {order}")
            if order.order_status == "Filled":
                qty = float(data["cumExecQty"])
                avg_price = float(data["avgPrice"])
                if data["side"] == "Sell":
                    qty = -qty
                self.account_data["positions"].add_position(
                    data["symbol"], qty, avg_price
                )
                self.account_data["orders"].delete_order(order)
            elif order.order_status in ("Cancelled", "Rejected"):
                self.account_data["orders"].delete_order(order)
            else:
                self.account_data["orders"].add_order(order)

        self._log_account_data()

        # log.info(f"Updated account data: {self.account_data}")
    def _log_account_data(self):
        log.info(f"Account data: {self.account_data['positions']} | {self.account_data['orders']}")



async def receive_order_data(market_data_queue: Queue):
    while True:
        market_data = await market_data_queue.get()
        print(f"Received market data: {market_data}")
        # Here you can implement logic to process the market data, such as generating trade signals


async def main():
    queue = Queue()
    streamer = AccountDataStreamer(
        symbols=["BTCUSDT", "ETHUSDT", "XRPUSDT"],
        account_data_queue=queue,
    )
    await asyncio.gather(
        streamer.stream(),
        receive_order_data(queue),
    )


if __name__ == "__main__":
    asyncio.run(main())
