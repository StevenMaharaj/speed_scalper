from common import Order, OrderManager


def test_order_manager():
    symbols = ["AAPL", "GOOG"]
    order_manager = OrderManager(symbols)

    order1 = Order(
        symbol="AAPL",
        quantity=10,
        price=150.0,
        order_side="Buy",
        order_status="New",
        order_type="Limit",
    )
    order2 = Order(
        symbol="AAPL",
        quantity=5,
        price=151.0,
        order_side="Sell",
        order_status="New",
        order_type="Limit",
    )
    order3 = Order(
        symbol="GOOG",
        quantity=20,
        price=2500.0,
        order_side="Buy",
        order_status="New",
        order_type="Limit",
    )

    order_manager.add_order(order1)
    order_manager.add_order(order2)
    order_manager.add_order(order3)

    assert order_manager.orders["AAPL"].bids is not None
    assert order_manager.orders["AAPL"].asks is not None
    assert order_manager.orders["GOOG"].bids is not None
    assert order_manager.orders["GOOG"].asks is not None
    assert len(order_manager.orders["AAPL"].bids) == 1
    assert len(order_manager.orders["AAPL"].asks) == 1
    assert len(order_manager.orders["GOOG"].bids) == 1
    assert len(order_manager.orders["GOOG"].asks) == 0

    order_manager.delete_order(order1)
    assert len(order_manager.orders["AAPL"].bids) == 0
