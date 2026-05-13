from src.calculator import add


def test_add_negative_numbers():
    assert add(-1, -2) == -3
