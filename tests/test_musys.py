import pytest
from musysim import Compiler


def test_register_addition():
    code = "10+5 $"
    m = Compiler(code)
    assert m.EXP == 0
    m.run()
    assert m.EXP == 15


def test_extra_23bit_precision():
    """
    The spec states that 23 bit precision is available 
    if a multiplication is immediately followed by a division
    Example given:  100*200/10 should equal 2000
    """
    code = "100*200/10$"
    m = Compiler(code)
    m.run()
    assert m.EXP == 2000


def test_max_value():
    code = "2047+5 $"
    m = Compiler(code)
    m.run()
    assert m.EXP < 2048
    assert m.EXP == -4
