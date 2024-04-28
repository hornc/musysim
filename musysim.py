#!/usr/bin/env python3
"""
https://esolangs.org/wiki/MUSYS simulator
"""

import argparse
import re
from copy import copy
from random import randint

from devices import devices


MAX = 0xfff  # 12 bit maximum values "decimal constant -2048 to +2047"
DEBUG = False
ALPHA = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

CONST = '[0-9]+'
VAR = '[A-Z]'
ITEM = f'({CONST}|{VAR}|←)'
OP = r'[-+&<>/*]'
EXPR = f'{ITEM}([↑^]|{OP}{ITEM})*'
RE_EXPR = re.compile(EXPR)
RE_ASSIGN = re.compile(f'([A-Z])=({EXPR})')  # Should this accept whitespace around = ?
RE_DEVICE = re.compile(r'[A-Z][0-9]+')
RE_GOTO = re.compile(r'G([0-9]+)')
RE_MACRO = re.compile(r'#([A-Z]+)\s+(.*);')
RE_PARAGRAPH_SELECT = re.compile(f'←[{ALPHA}]')


def dprint(*s):
    if DEBUG:
        print(*s)


def max_signed(i):
    """Return i as a signed MAX integer."""
    if -MAX // 2 <= i <= MAX // 2:
        return i
    signbit = i & ((MAX + 1) // 2)
    return -(i - signbit) if signbit else i


class Pointer():
    def __init__(self, obj):
        self.l = 0  # line
        self.c = 0  # character
        self.counter = 1
        self.obj = obj
        self.stack = []

    def advance(self, n=1):
        """Advance the pointer."""
        self.c += n
        if isinstance(self.obj, Compiler):
            if self.l >= len(self.obj.main_program):
                return False
            chars = len(self.obj.main_program[self.l])
            lines = len(self.obj.main_program)
        else:
            chars = len(self.obj.routine)
            lines = 1

        if self.c >= chars:
            self.c = 0
            self.l += 1
            if isinstance(self.obj, Macro):
                return self.pop()
        if self.l < lines:
            return True

    def decr_repeat(self):
        """
        Reached the end of a repeat block,
        either repeat the block, or resume.
        """
        self.counter -= 1
        if not self.counter:
            current = (self.l, self.c)
            self.pop()  # repeat finished, resume
            self.l, self.c = current
            return True  # TODO: standardise these return values to something meaningful
        dprint('DECR', self.counter)
        self.l = self.stack[-1][0]
        self.c = self.stack[-1][1]

    def goto(self, lineno):
        self.c = 0
        dprint('LINES', self.obj.lines)
        self.l = self.obj.lines[lineno]
        return self.l

    def pop(self):
        self.obj.values = []
        self.obj.routine = ''
        loc = self.stack.pop()
        self.l, self.c, self.obj, self.counter = loc
        dprint('POINTER LOC:', loc)
        return self.obj

    def push(self, obj, counter=0):
        self.stack.append((self.l, self.c, self.obj, self.counter))
        self.obj = obj
        if not counter:  # If this is a repeat loop, don't zero the position
            self.l = 0
            self.c = 0
        self.counter = counter

    def __repr__(self):
        return f'<Pointer> ({self.l}, {self.c}) Counter: {self.counter} ({str(self.obj)[:5]}) Stack size: {len(self.stack)}'


class Compiler():
    buses = []
    lines = {}
    macros = {}
    paragraphs = {}
    variables = {}

    def __init__(self, source, input_=None):
        self.main_program, macros = re.split(r'\$', source.strip())
        self.main_program = [line for line in self.main_program.split('\n') if line]
        self.pointer = Pointer(self)
        self.store_input(input_)
        self.paragraph = None
        self.EXP = 0  # The expression register
        self.bus = 1  # Current output bus (1-6)
        self.buffer = None  # buffer for storing device codes
        self.outfile = 'musys.out'
        self.state = None
        self.nest = 0  # used for tracking conditional nesting

        for i in range(6):
            self.buses.append(Bus(i + 1))
        self.macros = {m.name: m for m in [Macro(m) for m in re.split(r'\s*@\s+|@$', macros) if m]}
        # extract any line numbers
        for i, block in enumerate(self.main_program):
            lineno = re.match(r'^([0-9]+)\s(.*)$', block)
            if lineno:
                self.lines[int(lineno.group(1))] = i
                self.main_program[i] = lineno.group(2)

    def __repr__(self):
        return """==MUSYS program==\n%s\n==Lines==\n%s\n==Macros==\n%s""" % (self.main_program, self.lines, '\n'.join([str(v) for m, v in self.macros.items()]))

    def store_input(self, input_:str):
        if not input_:
            return
        dprint(f'READING DATAFILE!')
        re_parens = re.compile(r'[\(\)\[\]]')
        re_delims = re.compile(r'[,;\s]+')
        i = 0
        for line in input_.split('\n'):
            if not self.paragraphs:
                self.paragraphs[ALPHA[i]] = []
            line = re_parens.sub('', line.strip())
            if line == '':
                i += 1
                self.paragraphs[ALPHA[i]] = []
                continue
            self.paragraphs[ALPHA[i]] += [int(v.strip()) for v in re_delims.split(line)]
        dprint(f'PARAGRAPHS: {self.paragraphs}')

    def read_data(self):
        """Read the next number from the current datafile paragraph."""
        # TODO: What happens when we have read all values in a paragraph?
        # TODO: Unsure whether these should be read destructively, does ←A reset the position in the
        # paragraph back to 0? Destructive .pop(0) seems the easiest for now.
        n = self.paragraphs[self.paragraph].pop(0)
        # TODO: figure out whether this is supposed to be 6bit or 12bit & guard against overflows (assume 12bit for now)
        return n

    def assign(self, var, expr):
        v = self.expr_evaluate(expr)
        dprint('  ASSIGN "%s" = (%s) TO %s' % (expr, v, var))
        self.variables[var] = v

    def mrand(self, e):
        """
        A random number R
        such that 1 <= R <= EXP
        or EXP <= R <= 1 if EXP < O
        """
        if e == 0:
            return 0
        sign = e // abs(e)
        return randint(1, abs(e)) * sign

    def get_val(self, symbol):
        # TODO: this should not be called by anything other than expr_evaluate()
        if not symbol:
            return 0
        try:
            return int(symbol)
        except ValueError as e:
            if re.search(r'[+&<>^_*/-]', symbol):
                return self.expr_evaluate(symbol)
            return self.variables.get(symbol, 0)

    def expr_evaluate(self, expression):
        """
            Evaluates an expression.
            An expression is composed of items and operators.
            1) Decimal constant (-2048 to +2047)
            2) Variable [A-Z]
            3) Device code (unclear how this can be part of an expression)
            4) ← (read input from current paragraph)
            Effect: updates EXP
        """
        operators = {
                '+': lambda e, x: e + x,
                '-': lambda e, x: e - x,
                '*': lambda e, x: e * x,
                '/': lambda e, x: e // x,
                '&': lambda e, x: e & x & MAX,
                '>': lambda e, x: max(e, x),
                '<': lambda e, x: min(e, x),
        }
        parts = [p for p in re.split(r'(\W)', expression) if p]
        op = None
        for p in parts:
            if p in operators.keys():
                op = operators[p]
            elif p == '%':
                value = self.expr_evaluate(expression[2:-1]) - 1
                dprint('MACRO formal parameter found:', p, expression, value, 'Macro:', self.pointer.obj.name, self.pointer.obj.values, self.pointer.obj.values[value])
                self.EXP = self.pointer.obj.values[value]
                break
            elif p in '↑^':
                self.EXP = self.mrand(self.EXP)
            elif p == '←':
                dprint(f"READ VALUE!")
                self.EXP = self.read_data()
            elif op is None:
                self.EXP = self.get_val(p)
            else:
                self.EXP = op(self.EXP, self.get_val(p))
        self.EXP = max_signed(self.EXP)
        dprint('EXPR:', expression, '=>', self.EXP)
        return self.EXP

    def str_out(self, s):
        """Output a string / character if EXP is non-zero."""
        if self.EXP:
            print(s, end='')

    def evaluate(self):
        """
        Evaluates routine.
        "'routine' is used to denote a section of program that may use any MUSYS facilities provided
        that bracketing characters, (), [], "", '' are nested." (Grogono, 1973. p.373)
        """
        l, c, o = self.pointer.l, self.pointer.c, self.pointer.obj
        if o == self:
            if l >= len(self.main_program):
                return False
            routine = self.main_program[l]
        else:
            routine = o.routine
        routine = routine[c:]
        symbol = routine[0]
        mov = 1  # number of symbols to advance after this read

        if self.state == 'FCOND':  # in False condition
            if symbol == '[':
                self.nest += 1
            elif symbol == ']':
                self.nest -= 1
            if self.nest == 0:
                self.state = None
            return self.pointer.advance()

        if not self.state == 'STRING':  # Strings comment / STDOUT
            m = RE_EXPR.match(routine)
            dprint(f'ROUTINE: {routine} SYMBOL: <{symbol}>')
            dprint(self.pointer)

        if self.state == 'STRING':
            if symbol == '"':
                self.state = None
                self.str_out('\n')
            else:
                self.str_out(symbol)
        elif symbol == '"':
            self.state = 'STRING'
        elif symbol == '\\':  # print EXP to STDOUT
            print(self.EXP)
        elif symbol == '[':  # Conditional block
            m = re.match(r'([^\[]*)\[(.*)\]', routine)
            expr, subroutine = m.group(1, 2)
            cond = self.expr_evaluate(expr) > 0
            dprint(f"  COND {expr} ({cond}) => {subroutine}")

            if not cond:
                self.state = 'FCOND'
                self.nest += 1
        elif symbol == '(':  # Repeat block
            dprint('REPEAT FOUND!', routine, self.pointer)
            self.pointer.push(self.pointer.obj, self.EXP)
        elif symbol == ')':  # End of repeat block
            dprint('END REPEAT FOUND!', routine, self.pointer)
            self.pointer.decr_repeat()
        elif symbol == '#':  # Macro
            macro = self.call_macro(routine)
            dprint(f'MACRO FOUND! {routine} => {macro.routine}')
            self.pointer.push(macro)
            return macro
        #elif symbol in '] ':
        #    pass
        elif symbol == '@':  # Early return from macro
            self.pointer.pop()
        elif RE_GOTO.match(routine):  # GOTO
            m = RE_GOTO.match(routine)
            dprint('GOTO', m.group(1))
            return self.pointer.goto(int(m.group(1)))
        elif RE_DEVICE.match(routine):  # device found
            device = RE_DEVICE.match(routine).group(0)
            self.buffer = device
            dprint('DEVICE', device)
            return self.pointer.advance(len(device))
        elif symbol in '.:!':  # Send output to a list
            widths = {'.': 6, ':': 12}
            output = self.buffer if self.buffer is not None else self.EXP
            if symbol == '!':
                self.bus = output
            else:
                self.output(output, widths[symbol])
                self.buffer = None
        elif RE_ASSIGN.match(routine):  # Assignment
            m = RE_ASSIGN.match(routine)
            var, expr = m.group(1, 2)
            self.assign(var, expr)
            mov = len(m.group(0))
            dprint('MOV', mov)
        elif RE_PARAGRAPH_SELECT.match(routine):  # Select data paragraph
            self.paragraph = routine[1]
            dprint(f'SELECTING PARA {self.paragraph}!')
            mov = 2
        elif m:
            expr = m.group()
            dprint(f'EXPR FOUND: {expr}')
            self.expr_evaluate(expr)
            mov = len(expr)

        return self.pointer.advance(mov)


    def call_macro(self, routine):
        m = RE_MACRO.match(routine)
        name, parameters = m.group(1, 2)
        values = [self.expr_evaluate(p) for p in parameters.split(',')]
        self.pointer.advance(len(m.group(0)))
        macro = copy(self.macros[name])
        return macro.call(values)

    def output(self, value, width):
        """Send an output to current bus."""
        if isinstance(value, str):
            v = devices[value]
        else:
            v = value
        v = oct(int(v))[-width//3:].replace('o', '0')
        self.buses[self.bus - 1].send(v)

    def write(self):
        """
        Writes all buses / lists to file.
        """
        #TODO: allow a range of data formats
        print(f'[Writing all data lists to {self.outfile}...]')
        with open(self.outfile, 'w') as f:
            for b in self.buses:
                f.write(' '.join(b.data))
                f.write('\n')

    def run(self):
        """ Run the program!"""
        while self.evaluate():
            pass


class Macro():
    def __init__(self, raw):
        data = [t.strip() for t in re.split('(^[A-Z]{2,6})', raw.strip()) if t]
        self.name, self.body = data
        self.values = []
        assert len(self.name) < 7

    def call(self, args):
        result = self.body
        for i, a in enumerate(args):
            result = result.replace('%' + ALPHA[i], str(a))
        dprint(f'Called {self.name} with {args}. RESULT = {result}')
        self.values = args
        self.routine = result
        return self

    def __repr__(self):
        return f'Macro <{self.name}>: {self.body}'


class Bus():
    def __init__(self, n):
        self.n = n
        self.data = []  # a list of octal numbers
        self.buffer = ''

    def send(self, n):
        """n is 2 or 4 digit octal string"""
        if self.buffer:
            self.data.append(self.buffer + n)
            self.buffer = ''
        elif len(n) == 2:
            self.buffer = n
        else:
            self.data.append(n)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="MUSYS (1973) simulator.")
    parser.add_argument('file', help='MUSYS source file to process')
    parser.add_argument('-d', '--debug', help='turn on debug output', action='store_true')
    parser.add_argument('-i', '--input', help='input file; paragraphs (A-Z) of numerical data')
    args = parser.parse_args()

    DEBUG = args.debug
    source = args.file
    input_ = args.input

    if input_:
        with open(input_) as data:
            input_ = data.read()

    with open(source, 'r') as f:
        musys = Compiler(f.read(), input_)

    dprint(musys)
    musys.run()
    for i, bus in enumerate(musys.buses):
        if bus.data:
            print(f'BUS{i+1}: {bus.data}')
    musys.write()

