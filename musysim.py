#!/usr/bin/env python3
"""
https://esolangs.org/wiki/MUSYS simulator
"""

import argparse
import re
import sys

EXP = 0  # Expression Buffer
MAX = 0xfff  # 12 bit maximum values "decimal constant -2048 to +2047"
DEBUG = False


def mrand():
    """
    a random number R
    such that 1 <= R <= EXP
    or EXP <= R <= 1 if EXP < O
    """
    pass


class Parser():
    main_program = ''
    macros = []
    variables = {}
    lines = {}
    pointer = 0

    def __init__(self, f):
        self.main_program, macros = re.split(r'\$', f.read().strip())
        self.macros = [Macro(m) for m in re.split(r'\s*@\s+|@$', macros) if m]
        # break program into blocks
        self.main_program = self.split_into_blocks(self.main_program)
        # extract any line numbers
        for i, block in enumerate(self.main_program):
            lineno = re.match(r'^([0-9]+)\s(.*)$', block)
            if lineno:
                self.lines[int(lineno.group(1))] = i
                self.main_program[i] = lineno.group(2)

    def __repr__(self):
        return """==MUSYS program==\n%s\n==Lines==\n%s\n==Macros==\n%s""" % (self.main_program, self.lines, '\n'.join([str(m) for m in self.macros]))

    def split_into_blocks(self, routine):
        """Split a string of code into blocks."""
        blocks = [t.strip() for t in re.split(r'(.+\(.*\))|(.+\[.*\])|([A-Z][^"\s]*)\s|(([0-9]*\s)?[^\s]*".*")', routine) if t and t.strip()]
        if DEBUG:
            print("  BLOCKS: %s" % blocks)
        return blocks

    def get_val(self, symbol):
        try:
            return int(symbol)
        except ValueError as e:
            if re.search(r'[+&<>^_*/-]', symbol):
                return self.expr_evaluate(symbol)
            return self.variables.get(symbol, 0)

    def assign(self, var, value):
        if DEBUG:
            print('  ASSIGN "%s" = (%s) TO %s' % (value, self.get_val(value), var))
        self.variables[var] = self.get_val(value)

    def goto(self, lineno):
        if DEBUG:
            print("  GOTO %s IN %s" % (lineno, self.lines))
        self.pointer = self.lines[lineno]

    def expr_evaluate(self, expression):
        global EXP
        operators = {
                '+': lambda x: EXP + x,
                '-': lambda x: EXP - x,
                '*': lambda x: EXP * x,
                '/': lambda x: EXP // x,
                '&': lambda x: EXP & x & MAX,
                '>': lambda x: max(EXP, x),
                '<': lambda x: min(EXP, x),
        }
        parts = [p for p in re.split(r'(\W)', expression) if p]
        op = None
        for p in parts:
            if p in operators.keys():
                op = operators[p]
            elif p in '↑^':
                EXP = mrand(EXP)
            elif op is None:
                EXP = self.get_val(p)
            else:
                EXP = op(self.get_val(p)) & MAX
        return EXP

    def evaluate(self, routine):
        """
        Evaluates routine
        """
        self.pointer += 1
        repeat_match = re.match(r'(.+)\((.)\)', routine)
        output_match = re.match(r'(.+)("(.*)"|\\)', routine)
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
                    self.pointer -= 1
                    self.evaluate(s)
        elif repeat_match:
            expr, routine = repeat_match.groups()
            for i in range(expr):
                self.evaluate(routine)
        elif output_match:
            val = self.get_val(output_match.group(1))
            if val > 0:
                print(output_match.group(2).replace('\\', str(EXP)))
        elif '=' in routine:  # assignment
            var, val = routine.split('=')
            self.assign(var, val)
        elif routine[0] == 'G':  # GOTO
            lineno = int(re.match('G([0-9]+)', routine).group(1))
            self.goto(lineno)
        else:  # simply evaluate the line
            self.expr_evaluate(routine)

    def run(self):
        """ Run the program!"""
        while self.pointer < len(self.main_program):
            self.evaluate(self.main_program[self.pointer])


class Macro():
    name = ''
    body = ''
    def __init__(self, raw):
        data = [t.strip() for t in re.split('(^[A-Z]{2,6})', raw.strip()) if t]
        self.name = data[0]
        self.body = data[1]

    def invoke(self, args):
        pass

    def __repr__(self):
        return "Macro <%s>: %s" % (self.name, self.body)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="MUSYS (1973) simulator.")
    parser.add_argument('-d', '--debug', help='turn on debug output', action='store_true')
    parser.add_argument('file', help='MUSYS source file to process')
    args = parser.parse_args()

    DEBUG = args.debug
    source = args.file

    with open(source, 'r') as f:
        musys = Parser(f)
        if DEBUG:
            print(musys)
        musys.run()

