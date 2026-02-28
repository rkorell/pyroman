#!/usr/bin/env python3
"""
codesend.py - 433MHz Code senden via gpiod v2
Ersetzt das C-Binary codesend (wiringPi/433Utils) fuer Pi 5 / Trixie.

Usage: codesend.py <code> [protocol] [pulselength]

Defaults: protocol=1, pulselength=350

(c) Dr. Ralf Korell, 2026
# Created: 23.02.2026, 19:30 - Initiale Version
# Modified: 28.02.2026, 17:00 - QS: try-finally fuer GPIO Resource Cleanup
"""

import sys
import time
import gpiod
from gpiod.line import Direction, Value

GPIO_PIN = 21
CHIP = '/dev/gpiochip0'
REPEAT = 10
LENGTH = 24

PROTOCOLS = {
    1: {'pulselength': 350, 'sync': (1, 31), 'zero': (1, 3), 'one': (3, 1)},
    2: {'pulselength': 650, 'sync': (1, 10), 'zero': (1, 2), 'one': (2, 1)},
    3: {'pulselength': 100, 'sync': (30, 71), 'zero': (4, 11), 'one': (9, 6)},
    4: {'pulselength': 380, 'sync': (1, 6), 'zero': (1, 3), 'one': (3, 1)},
    5: {'pulselength': 500, 'sync': (6, 14), 'zero': (1, 2), 'one': (2, 1)},
}

def send(code, protocol=1, pulselength=None):
    if protocol not in PROTOCOLS:
        print(f"Fehler: Unbekanntes Protokoll {protocol}", file=sys.stderr)
        sys.exit(1)

    proto = PROTOCOLS[protocol]
    pl = pulselength or proto['pulselength']

    chip = gpiod.Chip(CHIP)
    line = chip.request_lines(
        consumer="codesend",
        config={GPIO_PIN: gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.INACTIVE)}
    )

    try:
        rawcode = format(code, f'#0{LENGTH + 2}b')[2:]

        for _ in range(REPEAT):
            for bit in rawcode:
                if bit == '0':
                    h, l = proto['zero']
                else:
                    h, l = proto['one']
                line.set_value(GPIO_PIN, Value.ACTIVE)
                time.sleep(h * pl / 1000000)
                line.set_value(GPIO_PIN, Value.INACTIVE)
                time.sleep(l * pl / 1000000)
            # Sync
            sh, sl = proto['sync']
            line.set_value(GPIO_PIN, Value.ACTIVE)
            time.sleep(sh * pl / 1000000)
            line.set_value(GPIO_PIN, Value.INACTIVE)
            time.sleep(sl * pl / 1000000)

        line.set_value(GPIO_PIN, Value.INACTIVE)
    finally:
        line.release()
        chip.close()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: codesend.py <code> [protocol] [pulselength]")
        print("  code         Dezimalcode (z.B. 301)")
        print("  protocol     1-5 (default: 1)")
        print("  pulselength  in Mikrosekunden (default: 350)")
        sys.exit(1)

    code = int(sys.argv[1])
    protocol = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    pulselength = int(sys.argv[3]) if len(sys.argv) > 3 else None

    send(code, protocol, pulselength)
    print(f"Gesendet: {code}")
