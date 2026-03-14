from ..account import Position


def test_add_position():
    position = Position(
        symbol="AAPL",
        quantity=0.10,
        avg_price=150.0,
        current_price=155.0,
    )
    position.add_position(quantity=0.05, price=160.0)

    assert position.quantity == 0.05
    assert position.avg_price == (150.0 * 0.10 + 160.0 * 0.05) / 15


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
