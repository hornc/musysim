#!/usr/bin/env python3
"""
https://esolangs.org/wiki/MUSYS simulator
"""

import argparse
import re
import sys

from devices import devices

MAX = 0xfff  # 12 bit maximum values "decimal constant -2048 to +2047"
DEBUG = False
ALPHA = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
RE_DEVICE = re.compile(r'[A-Z][0-9]+')


def mrand():
    """
    a random number R
    such that 1 <= R <= EXP
    or EXP <= R <= 1 if EXP < O
    """
    pass


def max_signed(i):
    """Return i as a singed MAX integer."""
    signbit = i & ((MAX + 1) // 2)
    return -(i - signbit) if signbit else i


class Compiler():
    buses = []
    lines = {}
    macros = {}
    paragraphs = {}
    variables = {}
    pointer = 0

    def __init__(self, source, input_=None):
        self.main_program, macros = re.split(r'\$', source.strip())
        self.store_input(input_)
        self.paragraph = None
        self.EXP = 0  # The expression register
        self.bus = 1  # Current output bus (1-6)
        self.outfile = 'musys.out'
        for i in range(6):
            self.buses.append(Bus(i + 1))
        self.macros = {m.name: m for m in [Macro(m) for m in re.split(r'\s*@\s+|@$', macros) if m]}
        # break program into blocks
        self.main_program = self.split_into_blocks(self.main_program)
        # extract any line numbers
        for i, block in enumerate(self.main_program):
            lineno = re.match(r'^([0-9]+)\s(.*)$', block)
            if lineno:
                self.lines[int(lineno.group(1))] = i
                self.main_program[i] = lineno.group(2)

    def __repr__(self):
        return """==MUSYS program==\n%s\n==Lines==\n%s\n==Macros==\n%s""" % (self.main_program, self.lines, '\n'.join([str(v) for m, v in self.macros.items()]))

    def split_into_blocks(self, routine):
        """Split a string of code into blocks."""
        re_blocks = re.compile(r'(.+\(.*\))|(.+\[.*\])|([A-Z][^"\s]*)\s|(([0-9]*\s)?[^\s]*".*")|(\\)|(#[^;]+;)')
        blocks = [t.strip() for t in re_blocks.split(routine) if t and t.strip()]
        if DEBUG:
            print("  BLOCKS: %s" % blocks)
        return blocks

    def store_input(self, input_):
        if not input_:
            return
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

    def get_val(self, symbol):
        if not symbol:
            return 0
        try:
            return int(symbol)
        except ValueError as e:
            if re.search(r'[+&<>^_*/-]', symbol):
                return self.expr_evaluate(symbol)
            return self.variables.get(symbol, 0)

    def assign(self, var, value):
        v = self.get_val(value)
        if DEBUG:
            print('  ASSIGN "%s" = (%s) TO %s' % (value, v, var))
        self.variables[var] = v

    def goto(self, lineno):
        if DEBUG:
            print("  GOTO %s IN %s" % (lineno, self.lines))
        self.pointer = self.lines[lineno]

    def expr_evaluate(self, expression):
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
            elif p in '↑^':
                self.EXP = mrand(self.EXP)
            elif op is None:
                self.EXP = self.get_val(p)
            else:
                self.EXP = op(self.EXP, self.get_val(p))
        self.EXP = max_signed(self.EXP)
        return self.EXP

    def evaluate(self, routine, increment=True):
        """
        Evaluates routine.
        """
        routine = routine.strip()
        if increment:
            self.pointer += 1
        repeat_match = re.match(r'(.+)\((.)\)', routine)
        output_match = re.match(r'([^"]+)?("(.*)"|\\)', routine)
        send_match = re.match(r'([^\s\.:]+)(\.|:)(.*)$', routine)
        #conditional_match = re.match(r'(.+)\[(.)\]', routine)
        if '[' in routine:  # conditional
            expr, subroutine = re.match(r'([^\[]*)\[(.*)\]', routine).groups()
            if DEBUG:
                print("  COND %s (%s) => %s" % (expr, self.get_val(expr) > 0, subroutine))
                #print("  REPEAT MATCH: %s" % repeat_match)
            if self.get_val(expr) > 0:
                for s in self.split_into_blocks(subroutine):
                    if DEBUG:
                        print(">>>" + s)
                    self.evaluate(s, False)
        elif send_match:
            #print('DEVICE:', send_match.groups())
            v, w, remainder = send_match.groups()
            if not RE_DEVICE.match(v):
                v = self.get_val(v)
            self.output(v, w)
            if remainder:
                self.evaluate(remainder, False)
        elif repeat_match:
            expr, routine = repeat_match.groups()
            for i in range(self.get_val(expr)):
                self.evaluate(routine)
        elif output_match:  # STDOUT for monitor and debug
            val = self.get_val(output_match.group(1))
            output = output_match.group(2).strip('"')
            if output == '\\':
                print(output.replace('\\', str(self.EXP)))
            elif val > 0:
                print(output)
        elif '!' in routine:  # select output bus
            n = re.search(r'([0-9])!', routine).group(1)
            self.bus = int(n)
        elif '=' in routine:  # assignment
            var, val = re.split(r'(\w)+\s*=\s*', routine)[-2:]
            self.assign(var, val)
        elif routine[0] == 'G':  # GOTO
            lineno = int(re.match('G([0-9]+)', routine).group(1))
            self.goto(lineno)
        elif '#' in routine:
            # TODO: Macro calls can apparently be nested
            self.evaluate(self.call_macro(routine), False)
        else:  # simply evaluate the line
            self.expr_evaluate(routine)

    def call_macro(self, routine):
        re_macro = re.compile(r'#([A-Z]+)\s+(.*);')
        name, parameters = re_macro.match(routine).groups()
        values = [self.expr_evaluate(p) for p in parameters.split(',')]
        return self.macros[name].call(values)

    def output(self, value, width):
        """Send an output to current bus."""
        if isinstance(value, str):
            v = devices[value]
        else:
            v = value
        v = oct(int(v))[-2:].replace('o', '0')
        self.buses[self.bus - 1].send(v)

    def write(self):
        """
        Writes all buses / lists to file.
        """
        #TODO: allow a range of data formats
        print('[Writing all data lists to %s...]' % self.outfile)
        with open(self.outfile, 'w') as f:
            for b in self.buses:
                f.write(' '.join(b.data))
                f.write('\n')

    def run(self):
        """ Run the program!"""
        while self.pointer < len(self.main_program):
            self.evaluate(self.main_program[self.pointer])


class Macro():
    def __init__(self, raw):
        data = [t.strip() for t in re.split('(^[A-Z]{2,6})', raw.strip()) if t]
        self.name, self.body = data
        assert len(self.name) < 7

    def call(self, args):
        result = self.body
        for i, a in enumerate(args):
            result = result.replace('%' + chr(65 + i), str(a))
        print('Called %s with %s. RESULT = %s' % (self.name, args, result))
        return result

    def __repr__(self):
        return "Macro <%s>: %s" % (self.name, self.body)


class Bus():
    def __init__(self, n):
        self.n = n
        self.data = []  # a list of octal numbers
        self.buffer = ''

    def send(self, n):
        """n is 2 or 4 digit octal string"""
        #print('DEBUG BUS', n)
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

    if DEBUG:
        print(musys)
    musys.run()
    print(musys.buses[0].data)
    musys.write()

