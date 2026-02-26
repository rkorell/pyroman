#!/usr/bin/env python3
"""
getcode.py - 433MHz Codes empfangen via gpiod v2
Lauscht auf GPIO 27 und gibt alle empfangenen Codes aus.

Usage: getcode.py [sekunden]

Default: 10 Sekunden Lauschzeit

Nutzt gpiod v2 Edge-Detection mit Nanosekunden-Timestamps vom Kernel.
Dekodiert rc-switch Protokolle 1-5.

(c) Dr. Ralf Korell, 2026
# Created: 23.02.2026, 20:15 - Initiale Version
"""

import sys
import time
import gpiod
from gpiod.line import Edge

GPIO_PIN = 27
CHIP = '/dev/gpiochip0'
MAX_CHANGES = 67
TOLERANCE = 80  # Prozent

PROTOCOLS = [
    None,
    {'pulselength': 350, 'sync': (1, 31), 'zero': (1, 3), 'one': (3, 1)},
    {'pulselength': 650, 'sync': (1, 10), 'zero': (1, 2), 'one': (2, 1)},
    {'pulselength': 100, 'sync': (30, 71), 'zero': (4, 11), 'one': (9, 6)},
    {'pulselength': 380, 'sync': (1, 6), 'zero': (1, 3), 'one': (3, 1)},
    {'pulselength': 500, 'sync': (6, 14), 'zero': (1, 2), 'one': (2, 1)},
]


def try_decode(timings, pnum, change_count_val):
    """Versucht einen empfangenen Puls-Train als rc-switch Code zu dekodieren."""
    proto = PROTOCOLS[pnum]
    code = 0
    delay = timings[0] // proto['sync'][1]
    delay_tol = delay * TOLERANCE // 100

    for i in range(1, change_count_val, 2):
        zh = proto['zero'][0] * delay
        zl = proto['zero'][1] * delay
        oh = proto['one'][0] * delay
        ol = proto['one'][1] * delay

        if abs(timings[i] - zh) < delay_tol and abs(timings[i+1] - zl) < delay_tol:
            code <<= 1
        elif abs(timings[i] - oh) < delay_tol and abs(timings[i+1] - ol) < delay_tol:
            code <<= 1
            code |= 1
        else:
            return None

    if change_count_val > 6 and code != 0:
        bitlength = change_count_val // 2
        return {'code': code, 'bitlength': bitlength, 'delay': delay, 'protocol': pnum}
    return None


def listen(timeout_seconds):
    """Lauscht auf 433MHz-Signale und gibt empfangene Codes aus."""
    request = gpiod.request_lines(
        CHIP,
        consumer="rf433rx",
        config={GPIO_PIN: gpiod.LineSettings(edge_detection=Edge.BOTH)}
    )

    timings = [0] * (MAX_CHANGES + 1)
    last_timestamp = 0
    change_count = 0
    repeat_count = 0
    last_code = 0
    last_code_time = 0

    print(f"Lausche auf GPIO {GPIO_PIN} ({timeout_seconds}s)...")
    start = time.time()

    try:
        while time.time() - start < timeout_seconds:
            if request.wait_edge_events(timeout=0.5):
                events = request.read_edge_events()
                for event in events:
                    timestamp_us = event.timestamp_ns // 1000
                    duration = timestamp_us - last_timestamp

                    if duration > 5000:
                        if abs(duration - timings[0]) < 200:
                            repeat_count += 1
                            cc = change_count - 1
                            if repeat_count == 2:
                                for pnum in range(1, len(PROTOCOLS)):
                                    result = try_decode(timings, pnum, cc)
                                    if result:
                                        # Duplikate unterdruecken (gleicher Code < 500ms)
                                        now = time.time()
                                        if result['code'] != last_code or (now - last_code_time) > 0.5:
                                            print(f"Code: {result['code']}  "
                                                  f"(Protocol: {result['protocol']}, "
                                                  f"Bits: {result['bitlength']}, "
                                                  f"Delay: {result['delay']}us)")
                                            last_code = result['code']
                                            last_code_time = now
                                        break
                                repeat_count = 0
                        change_count = 0

                    if change_count >= MAX_CHANGES:
                        change_count = 0
                        repeat_count = 0
                    timings[change_count] = duration
                    change_count += 1
                    last_timestamp = timestamp_us

    except KeyboardInterrupt:
        print("\nAbgebrochen.")
    finally:
        request.release()

    print("Fertig.")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] in ('-h', '--help'):
        print("Usage: getcode.py [sekunden]")
        print("  sekunden  Lauschzeit (default: 10)")
        sys.exit(0)

    timeout = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    listen(timeout)
