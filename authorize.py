#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
authorize.py - Autorisierung per 433MHz für PyroMan

Wartet auf 433MHz-Signal vom Handsender und validiert gegen auth_code.
Flask/Aufrufer weiß nichts von 433MHz - nur True/False.

Nutzt gpiod v2 Edge-Detection auf GPIO 27 (gleiche Logik wie getcode.py).

(c) Dr. Ralf Korell, 2025/26

Erstellt: 07.12.2025, 17:00
Modified: 14.12.2025, 14:30 - AP7: Plattform-Erkennung Pi4/Pi5, Arduino Serial Bridge
Modified: 14.12.2025, 14:45 - AP7: Arduino Reset-Zeit 2s, Buffer leeren, #-Zeilen ignorieren
Modified: 14.12.2025, 15:30 - AP7: get_auth_check() durch is_auth_required() ersetzt
Modified: 26.02.2026, 17:30 - AP1: Komplett-Umbau auf gpiod v2 (pigpio/Arduino/Plattform-Erkennung entfernt)
Modified: 28.02.2026, 17:00 - QS: Array-Bounds in Decode-Loop, Resource Cleanup Guard
Modified: 28.02.2026, 23:00 - QS2: request=None Init vor try-Block (NameError-Absicherung)
"""

import time
import gpiod
from gpiod.line import Edge
import config

# Logger
logger = config.get_logger(__name__)

# GPIO-Pin für 433MHz-Empfänger
RX_GPIO = 27
GPIO_CHIP = '/dev/gpiochip0'

# rc-switch Dekodier-Parameter
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


class AuthorizeError(Exception):
    """Fehler im Authorize Modul."""
    pass


def _try_decode(timings, pnum, change_count_val):
    """Versucht einen empfangenen Puls-Train als rc-switch Code zu dekodieren."""
    proto = PROTOCOLS[pnum]
    code = 0
    delay = timings[0] // proto['sync'][1]
    delay_tol = delay * TOLERANCE // 100

    for i in range(1, change_count_val - 1, 2):
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


def authenticate(timeout=None):
    """
    Wartet auf 433MHz-Signal und prüft gegen auth_code.

    Blockiert bis korrekter Code empfangen oder Timeout erreicht.

    Args:
        timeout: Sekunden zu warten (default aus config)

    Returns:
        True wenn korrekter Code empfangen, sonst False

    Raises:
        AuthorizeError: Bei Config- oder Hardware-Fehlern
    """

    # Prüfen ob Auth überhaupt erforderlich
    if not config.is_auth_required():
        logger.debug("auth_required=false, überspringe Autorisierung")
        return True

    # Config prüfen
    if not config.is_valid():
        errors = config.get_startup_errors()
        raise AuthorizeError(f"Config ungültig: {errors}")

    # Parameter laden
    auth_code = config.get_auth_code()
    if auth_code is None:
        raise AuthorizeError("auth_code nicht konfiguriert")

    if timeout is None:
        timeout = config.get_auth_timeout()

    return _authenticate_gpiod(auth_code, timeout)


def _authenticate_gpiod(auth_code, timeout):
    """
    Authentifizierung via gpiod v2 Edge-Detection.

    Gleiche RX-Logik wie getcode.py: Lauscht auf GPIO 27, dekodiert
    rc-switch Protokolle, vergleicht mit auth_code.

    Args:
        auth_code: Erwarteter Code (int)
        timeout: Timeout in Sekunden

    Returns:
        True wenn korrekter Code empfangen, sonst False
    """
    logger.debug(f"Auth: Warte {timeout}s auf Code {auth_code} (GPIO {RX_GPIO})")

    request = None
    try:
        request = gpiod.request_lines(
            GPIO_CHIP,
            consumer="pyroman_auth",
            config={RX_GPIO: gpiod.LineSettings(edge_detection=Edge.BOTH)}
        )
    except Exception as e:
        raise AuthorizeError(f"GPIO {RX_GPIO} nicht verfügbar: {e}")

    timings = [0] * (MAX_CHANGES + 1)
    last_timestamp = 0
    change_count = 0
    repeat_count = 0

    start = time.time()

    try:
        while time.time() - start < timeout:
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
                                    result = _try_decode(timings, pnum, cc)
                                    if result:
                                        logger.debug(f"Code empfangen: {result['code']} "
                                                     f"(Protocol: {result['protocol']}, "
                                                     f"Bits: {result['bitlength']})")
                                        if result['code'] == auth_code:
                                            logger.debug("Autorisierung erfolgreich")
                                            return True
                                        break
                                repeat_count = 0
                        change_count = 0

                    if change_count >= MAX_CHANGES:
                        change_count = 0
                        repeat_count = 0
                    timings[change_count] = duration
                    change_count += 1
                    last_timestamp = timestamp_us

        logger.debug("Autorisierung Timeout")
        return False

    except AuthorizeError:
        raise
    except Exception as e:
        raise AuthorizeError(f"Autorisierung fehlgeschlagen: {e}")

    finally:
        try:
            if request is not None:
                request.release()
        except Exception as e:
            logger.warning(f"GPIO release Fehler: {e}")
