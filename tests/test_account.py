import asyncio
from unittest.mock import MagicMock

from account import AccountDataStreamer
from common import Position


def test_add_position():
    position = Position(
        symbol="AAPL",
        quantity=0.10,
        avg_price=150.0,
        current_price=155.0,
    )
    position.add_position(quantity=0.05, price=160.0)

    assert position.quantity == 0.15
    assert position.avg_price == round((150.0 * 0.10 + 160.0 * 0.05) / 0.15, 8)


def test_reduce_position():
    position = Position(
        symbol="AAPL",
        quantity=10,
        avg_price=150.0,
        current_price=155.0,
    )
    position.add_position(quantity=-5, price=160.0)

    assert position.quantity == 5
    assert position.avg_price == (150.0 * 10 + 160.0 * (-5)) / 5


def test_filled_order_updates_position(order_new_message, order_filled_message):
    queue = asyncio.Queue()
    streamer = AccountDataStreamer(
        symbols=["ETHUSDT"],
        account_data_queue=queue,
    )
    streamer.loop = MagicMock()

    streamer.on_message(order_new_message)
    streamer.on_message(order_filled_message)

    position = streamer.account_data["positions"].positions["ETHUSDT"]
    assert position.quantity == 0.01
    assert position.avg_price == 2359.5


def test_cancelled_order_removed_from_orders(order_new_message, order_cancelled_message):
    queue = asyncio.Queue()
    streamer = AccountDataStreamer(
        symbols=["ETHUSDT"],
        account_data_queue=queue,
    )
    streamer.loop = MagicMock()

    streamer.on_message(order_new_message)
    streamer.on_message(order_cancelled_message)

    orders = streamer.account_data["orders"].orders["ETHUSDT"]
    assert orders.bids == []
    position = streamer.account_data["positions"].positions["ETHUSDT"]
    assert position.quantity == 0.0
