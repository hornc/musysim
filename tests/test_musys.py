import pytest
from musysim import Parser

def test_register_addition():
    code = "10+5$"
    p = Parser(code)
    assert p.EXP == 0
    p.run()
    assert p.EXP == 15


