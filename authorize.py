#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
authorize.py - Autorisierung per 433MHz für PyroMan

Wartet auf 433MHz-Signal vom Handsender und validiert gegen auth_code.
Flask/Aufrufer weiß nichts von 433MHz - nur True/False.

(c) Dr. Ralf Korell, 2025/26

Erstellt: 07.12.2025, 17:00
"""

import threading
import time
import pigpio
from lib._433 import rx
import config

# Logger
logger = config.get_logger(__name__)


class AuthorizeError(Exception):
    """Fehler im Authorize Modul."""
    pass


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
        logger.debug("auth_required=False, überspringe Autorisierung")
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
    
    rf_config = config.get_rf_empfaenger()
    if rf_config is None:
        raise AuthorizeError("RF-Empfänger Konfiguration fehlt")
    
    gpio = rf_config.get("gpio")
    
    logger.debug(f"Autorisierung gestartet, warte {timeout}s auf GPIO {gpio}")
    
    # Zustand für Callback
    result = {"authenticated": False, "done": False}
    
    def on_code_received(code, bits, gap, t0, t1):
        """Callback wenn Code empfangen."""
        logger.trace(f"Code empfangen: {code} (bits={bits})")
        
        if code == auth_code:
            logger.debug("Autorisierung erfolgreich")
            result["authenticated"] = True
            result["done"] = True
    
    # pigpio verbinden
    pi = None
    receiver = None
    
    try:
        pi = pigpio.pi()
        if not pi.connected:
            raise AuthorizeError(
                "pigpiod nicht erreichbar. "
                "Bitte starten mit: sudo pigpiod"
            )
        
        # Empfänger starten
        receiver = rx(pi, gpio=gpio, callback=on_code_received)
        
        # Warten bis Auth oder Timeout
        start_time = time.time()
        while not result["done"]:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                logger.debug("Autorisierung Timeout")
                break
            time.sleep(0.05)  # 50ms Polling
        
        return result["authenticated"]
    
    except AuthorizeError:
        raise
    except Exception as e:
        raise AuthorizeError(f"Autorisierung fehlgeschlagen: {e}")
    
    finally:
        # Aufräumen
        if receiver is not None:
            try:
                receiver.cancel()
            except Exception as e:
                logger.warning(f"RX cancel Fehler: {e}")
        
        if pi is not None:
            try:
                pi.stop()
            except Exception as e:
                logger.warning(f"pigpio stop Fehler: {e}")
