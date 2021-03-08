#!/usr/bin/env python3
import argparse
from devices import get_device

"""
Sofka simulator for MUSYS.

Takes the output lists generated by the simulated
MUSYS compiler, musysim, and simulates the
effects of sending this data to various
hardware audio devices by generating
Nyquist code.

"""
DEBUG = False

def dprint(*s):
    if DEBUG:
        print(*s)


class Sofka:
    def __init__(self, lists):
        self.lists = [b.split(' ') for b in lists.split('\n')]
        self.clock = 100  # Interrupts per second
                          # default implied by example at http://users.encs.concordia.ca/~grogono/Bio/ems.html
        self.oscillators = [None] * 3
        self.envelopes = [None] * 3

    def perform(self):
        # TODO this needs to be refactored once a sensible system
        # for combining all the audio sources and effects for 
        # all six lists is settled on.
        for b in self.lists:
            if not b[0]:
                continue
            for c in b:
                n = int(c[:2], 8)
                v = int(c[2:], 8)
                device = get_device(int(c[:2], 8))
                dprint(device, c)
                if n == 62:  # Interrupt timer
                    self.clock = v
                if 0 < n < 4:  # Osc
                    dprint('OSC', n)
                    if self.oscillators[n - 1]:
                        self.oscillators[n - 1].change(v)
                    else:
                        self.oscillators[n - 1] = Oscillator(v)
                    self.active = n - 1
                if 23 < n < 27:  # Envelopes
                    n = n - 24
                    dprint('Envelope', n + 1)
                    d = self.secs(v)
                    if self.envelopes[n]:
                        self.envelopes[n].addtime(d)
                    else:
                        self.envelopes[n] = Envelope(d)
                if n == 60:  # Wait timer
                    d = self.secs(v) 
                    dprint('WAIT:', d)
                    self.oscillators[self.active].duration += d
                    if self.envelopes[self.active]:
                        self.envelopes[self.active].addtime(d)
        # write the generated audio
        sources = [o for o in self.oscillators if o]
        sources += [e for e in self.envelopes if e]
        dprint('SOURCES', sources)
        output = ' '.join(['(seq %s)' % ' '.join(s.out()) for s in sources])
        return '(mult %s)' % output

    def secs(self, n):
        """ Number of seconds of time with current clock."""
        return n * 1/self.clock


class Envelope:
    durations = []  # Attack, On, Decay, Off
    def __init__(self, duration):
        self.addtime(duration)

    def addtime(self, d):
        self.durations.append(d)

    def out(self):
        attack = min(self.durations[0], self.durations[1])
        L1 = self.durations[0] / attack
        on = self.durations[1] - attack
        decay = min(self.durations[2], self.durations[3])
        L3 = 1 - (decay / self.durations[2])
        dur = attack + on + decay
        return ["(env {t1} {t2} 0 {L1} {L1} {L3} {dur})".format(t1=attack, t2=on, L1=L1, L3=L3, dur=dur)]


class Oscillator:
    def __init__(self, pitch=32):
        # Hypothesised: {Nyquist (MIDI) tone} = {MUSYS tone} + 28
        # Middle C = Nyquist 60, MUSYS 32
        self.pitch = pitch + 28
        self.duration = 0
        self.history = []

    def change(self, pitch):
        self.history.append(self.out(False))
        self.pitch = pitch + 28
        self.duration = 0

    def out(self, history=True):
        if not history:
            return "(osc %s %s)" % (self.pitch, self.duration)
        self.change(0)
        return self.history


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="MUSYS (1973) Sofka simulator.")
    #parser.add_argument('file', help='compiled MUSYS data lists to perform')
    parser.add_argument('-d', '--debug', help='turn on debug output', action='store_true')
    args = parser.parse_args()

    DEBUG = args.debug
    listfile = 'musys.out'
    with open(listfile, 'r') as f:
        s = Sofka(f.read())

    print('(play %s)' % s.perform())

