import pytest
from musysim import Parser


def test_register_addition():
    code = "10+5 $"
    p = Parser(code)
    assert p.EXP == 0
    p.run()
    assert p.EXP == 15


def test_extra_23bit_precision():
    """
    The spec states that 23 bit precision is available 
    if a multiplication is immediately followed by a division
    Example given:  100*200/10 should equal 2000
    """
    code = "100*200/10$"
    p = Parser(code)
    p.run()
    assert p.EXP == 2000


def test_max_value():
    code = "2047+5 $"
    p = Parser(code)
    p.run()
    assert p.EXP < 2048
    assert p.EXP == -4
