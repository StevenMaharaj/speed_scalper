import os
from asyncio import Queue

from dotenv import load_dotenv
from pybit.unified_trading import HTTP

CATEGORY = "linear"


class Trader:
    def __init__(self, trade_queue: Queue):
        self.trade_queue = trade_queue
        api_key, api_secret = self._load_api_credentials()
        self.session = HTTP(
            testnet=False,
            api_key=api_key,
            api_secret=api_secret,
        )

    def _load_api_credentials(self):
        load_dotenv()
        return os.getenv("BYBIT_1_KEY"), os.getenv("BYBIT_1_SECRET")

    async def run(self):
        while True:
            signal = await self.trade_queue.get()
            action = signal.get("action")
            print(f"Received trade signal: {signal}")

            if action == "market":
                self.market_order(signal["symbol"], signal["side"], signal["qty"])
            elif action == "limit":
                self.limit_order(signal["symbol"], signal["side"], signal["qty"], signal["price"])
            elif action == "cancel":
                self.cancel_order(signal["symbol"], signal["order_id"])
            elif action == "cancel_all":
                self.cancel_all_orders(signal["symbol"])
            else:
                print(f"Unknown action: {action}")

    def market_order(self, symbol: str, side: str, qty: str):
        result = self.session.place_order(
            category=CATEGORY,
            symbol=symbol,
            side=side,
            orderType="Market",
            qty=qty,
        )
        print(f"Market order result: {result}")
        return result

    def limit_order(self, symbol: str, side: str, qty: str, price: str):
        result = self.session.place_order(
            category=CATEGORY,
            symbol=symbol,
            side=side,
            orderType="Limit",
            qty=qty,
            price=price,
        )
        print(f"Limit order result: {result}")
        return result

    def cancel_order(self, symbol: str, order_id: str):
        result = self.session.cancel_order(
            category=CATEGORY,
            symbol=symbol,
            orderId=order_id,
        )
        print(f"Cancel order result: {result}")
        return result

    def cancel_all_orders(self, symbol: str):
        result = self.session.cancel_all_orders(
            category=CATEGORY,
            symbol=symbol,
        )
        print(f"Cancel all orders result: {result}")
        return result
