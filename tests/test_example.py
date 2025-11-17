"""
Basic example tests for demonstration purposes.
These tests are simple and always pass to demonstrate the test workflow.
"""


def test_addition():
    """Test basic addition."""
    assert 1 + 1 == 2


def test_subtraction():
    """Test basic subtraction."""
    assert 5 - 3 == 2


def test_multiplication():
    """Test basic multiplication."""
    assert 2 * 3 == 6


def test_division():
    """Test basic division."""
    assert 10 / 2 == 5


def test_string_concatenation():
    """Test string operations."""
    assert "Hello" + " " + "World" == "Hello World"


def test_list_operations():
    """Test list operations."""
    my_list = [1, 2, 3]
    assert len(my_list) == 3
    assert my_list[0] == 1
    assert my_list[-1] == 3

