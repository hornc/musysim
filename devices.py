"""
Device list lookup and other information for MUSYSim.
"""


full_devices = {
    'O1': {
        'number': 1,
        'group': 'Oscillators',
        'description': 'Oscillator 1',
        'information_source': 'inferred from O2',
        'arguments': {
            'pitch': {
                'bits': 6
            }
        }
    },
    'O2': {
        'number': 2,
        'group': 'Oscillators',
        'description': 'Oscillator 2',
        'information_source': 'Grogono, 1973, p.377',
        'arguments': {
            'pitch': {
                'bits': 6
            }
        }
    },
    'O3': {
        'number': 2,
        'group': 'Oscillators',
        'description': 'Oscillator 3',
        'information_source': 'inferred from O2',
        'arguments': {
            'pitch': {
                'bits': 6
            }
        }
    },
    'K1': {
        'number': 8,
        'group': 'Oscillators',
        'description': 'Frequency Oscillator 1',
        'information_source': 'Grogono, 1973, p.378',
        'arguments': {
            'frequency': {
                'units': 'Hz',
                'bits': 12
            }
        }
    },
    'L1': {
        'number': 12,
        'group': 'Amplifiers',
        'description': 'Loudness amplifier 1',
        'information_source': 'inferred from L2',
    },
    'L2': {
        'number': 13,
        'group': 'Amplifiers',
        'description': 'Loudness amplifier 2',
        'information_source': 'Grogono, 1973, p.377',
    },
    'L3': {
        'number': 14,
        'group': 'Amplifiers',
        'description': 'Loudness amplifier 3',
        'information_source': 'inferred from L2',
    },
    'A1': {
        'number': 12,
        'group': 'Amplifiers',
        'description': 'Gain amplifier 1',
        'information_source': '',
    },
    'A2': {
        'number': 13,
        'group': 'Amplifiers',
        'description': 'Gain amplifier 2',
        'information_source': '',
    },
    'E1': {
        'number': 24,
        'group': 'Envelope shapers',
        'description': 'Envelope shaper 1',
        'information_source': '',
    },
    'E2': {
        'number': 25,
        'group': 'Envelope shapers',
        'description': 'Envelope shaper 2',
        'information_source': '',
    },
    'E3': {
        'number': 26,
        'group': 'Envelope shapers',
        'description': 'Envelope shaper 3',
        'information_source': '',
    },
    'T1': {
        'number': 60,
        'group': 'Timers',
        'description': 'Timer 1: Wait timer',
        'information_source': 'Grogono, 1973, p.377',
        'arguments': {
            'wait': { 
                'units': 'interrupts',
                'bits': 6
            }
        }
    },
    'T2': {
        'number': 61,
        'group': 'Timers',
        'description': 'Timer 2',
        'information_source': 'inferred from T1 and T3',
    },
    'T3': {
        'number': 62,
        'group': 'Timers',
        'description': 'Timer 3: HW clock interrupt, 0.25Hz – 16KHz',
        'information_source': 'Grogono, 1973, p.377',
        'arguments': {
            'rate': {
                'units': 'interrupts / second',
                'bits': 6
            }
        }
    },
}


devices = {k: v['number'] for k, v in full_devices.items()}


def get_device(n):
    # TODO: something efficient...
    for k, v in full_devices.items():
        if v['number'] == n:
            return v
