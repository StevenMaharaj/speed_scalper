import asyncio
import os
from asyncio import Queue

from dotenv import load_dotenv
from pybit.unified_trading import HTTP

from common import Order

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
            order: Order = await self.trade_queue.get()
            print(f"Received trade signal: {order}")

            if order.order_type == "Market":
                self.market_order(order)
            elif order.order_type == "Limit":
                self.limit_order(order)
            elif order.order_type == "Cancel":
                self.cancel_order(order)
            elif order.order_type == "CancelAll":
                self.cancel_all_orders(order)
            else:
                print(f"Unknown order type: {order.order_type}")

    def market_order(self, order: Order):
        if order.order_type != "Market":
            print(f"Invalid order type for market order: {order.order_type}")
            return
        result = self.session.place_order(
            category=CATEGORY,
            symbol=order.symbol,
            side=order.order_side,
            orderType="Market",
            qty=str(order.quantity),
        )
        print(f"Market order result: {result}")
        return result

    def limit_order(self, order: Order):
        if order.order_type != "Limit":
            print(f"Invalid order type for limit order: {order.order_type}")
            return
        result = self.session.place_order(
            category=CATEGORY,
            symbol=order.symbol,
            side=order.order_side,
            orderType="Limit",
            qty=str(order.quantity),
            price=str(order.price),
        )
        print(f"Limit order result: {result}")
        return result

    def cancel_order(self, order: Order):
        result = self.session.cancel_order(
            category=CATEGORY,
            symbol=order.symbol,
            orderId=order.order_id,
        )
        print(f"Cancel order result: {result}")
        return result

    def cancel_all_orders(self, order: Order):
        result = self.session.cancel_all_orders(
            category=CATEGORY,
            symbol=order.symbol,
        )
        print(f"Cancel all orders result: {result}")
        return result


async def produce_trade(market_data_queue: Queue):
    order = Order(
        symbol="BTCUSDT",
        quantity=0.001,
        price=69900.0,
        order_type="Limit",
        order_side="Buy",
        order_status="New",
    )
    await asyncio.sleep(1)  # Simulate some delay before producing the trade signal
    await market_data_queue.put(order)
    await asyncio.sleep(5)  # Simulate some delay
    # Cancel All Orders
    cancel_all_order = Order(
        symbol="BTCUSDT",
        quantity=0.0,
        price=0.0,
        order_type="CancelAll",
        order_side="",
        order_status="New",
    )
    await market_data_queue.put(cancel_all_order)
    # print(f"Produced trade signal: {order}")
    # Here you can implement logic to process the market data, such as generating trade signals


async def main():
    queue = Queue()
    trader = Trader(trade_queue=queue)
    await asyncio.gather(
        trader.run(),
        produce_trade(queue),
    )


if __name__ == "__main__":
    asyncio.run(main())
