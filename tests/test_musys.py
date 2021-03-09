import pytest
from musysim import Compiler, max_signed


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


def test_strict_left_right_eval():
    code = "10-5*4 $"
    # This is _supposed_ to be 20.
    # i.e. (10-5)*4
    m = Compiler(code)
    m.run()
    assert m.EXP == 20  # Not -10!


def test_max_signed():
    # TODO: What is the most sensible overflow behaviour in all cases?
    assert max_signed(5) == 5
    assert max_signed(-5) == -5
    assert max_signed(-2048 + 5) == -2043
    assert max_signed(2047 + 5) == -4
    #assert max_signed(-2048 - 5) == 4
    #assert max_signed(0xfff + 5) == 4

