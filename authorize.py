#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
authorize.py - Autorisierung per 433MHz für PyroMan

Wartet auf 433MHz-Signal vom Handsender und validiert gegen auth_code.
Flask/Aufrufer weiß nichts von 433MHz - nur True/False.

Plattform-Erkennung:
- Pi 4: pigpio + lib/_433.py (direkter GPIO-Empfang)
- Pi 5: Arduino Serial Bridge (433EmpfaengerBridgeFuerPi.ino)

(c) Dr. Ralf Korell, 2025/26

Erstellt: 07.12.2025, 17:00
Modified: 14.12.2025, 14:30 - AP7: Plattform-Erkennung Pi4/Pi5, Arduino Serial Bridge
Modified: 14.12.2025, 14:45 - AP7: Arduino Reset-Zeit 2s, Buffer leeren, #-Zeilen ignorieren
"""

import time
import config

# Logger
logger = config.get_logger(__name__)


class AuthorizeError(Exception):
    """Fehler im Authorize Modul."""
    pass


def detect_platform():
    """
    Erkennt Pi 4 vs Pi 5 via device-tree.
    
    Returns:
        'pi4', 'pi5', oder 'unknown'
    """
    try:
        with open('/proc/device-tree/model', 'r') as f:
            model = f.read().strip('\x00')
        if 'Pi 5' in model:
            return 'pi5'
        elif 'Pi 4' in model:
            return 'pi4'
        else:
            return 'unknown'
    except Exception:
        return 'unknown'


def authenticate(timeout=None):
    """
    Wartet auf 433MHz-Signal und prüft gegen auth_code.
    
    Blockiert bis korrekter Code empfangen oder Timeout erreicht.
    Wählt automatisch die richtige Methode (Pi 4: pigpio, Pi 5: Arduino).
    
    Args:
        timeout: Sekunden zu warten (default aus config)
    
    Returns:
        True wenn korrekter Code empfangen, sonst False
    
    Raises:
        AuthorizeError: Bei Config- oder Hardware-Fehlern
    """
    
    # Prüfen ob Auth überhaupt erforderlich
    if not config.get_auth_check():
        logger.debug("auth_check=False, überspringe Autorisierung")
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
    
    # Plattform erkennen
    platform = detect_platform()
    logger.debug(f"Plattform erkannt: {platform}")
    
    if platform == 'pi5':
        return _authenticate_arduino(auth_code, timeout)
    elif platform == 'pi4':
        return _authenticate_pigpio(auth_code, timeout)
    else:
        logger.warning(f"Unbekannte Plattform: {platform}, versuche Arduino")
        return _authenticate_arduino(auth_code, timeout)


def _authenticate_pigpio(auth_code, timeout):
    """
    Authentifizierung via pigpio (Pi 4).
    
    Args:
        auth_code: Erwarteter Code
        timeout: Timeout in Sekunden
    
    Returns:
        True wenn korrekter Code empfangen
    """
    import pigpio
    from lib._433 import rx
    
    rf_config = config.get_rf_empfaenger()
    if rf_config is None:
        raise AuthorizeError("RF-Empfänger Konfiguration fehlt")
    
    gpio = rf_config.get("gpio")
    
    logger.debug(f"Pi 4 Auth: Warte {timeout}s auf GPIO {gpio}")
    
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


def _authenticate_arduino(auth_code, timeout):
    """
    Authentifizierung via Arduino Serial Bridge (Pi 5).
    
    Protokoll:
    - Warte 2s für Arduino Reset
    - Buffer leeren (# Zeilen ignorieren)
    - Sende "SCAN\n" an Arduino
    - Arduino antwortet mit "<code>\n" wenn Signal empfangen
    - Zeilen mit "#" sind Status-Meldungen und werden ignoriert
    
    Args:
        auth_code: Erwarteter Code
        timeout: Timeout in Sekunden
    
    Returns:
        True wenn korrekter Code empfangen
    """
    import serial
    
    arduino_port = config.get_arduino_port()
    
    logger.debug(f"Pi 5 Auth: Warte {timeout}s auf Arduino ({arduino_port})")
    
    ser = None
    
    try:
        ser = serial.Serial(arduino_port, 9600, timeout=0.5)
        
        # Arduino Reset abwarten (2 Sekunden)
        logger.debug("Warte auf Arduino Reset (2s)...")
        time.sleep(2)
        
        # Buffer leeren - alle Startup-Meldungen lesen und ignorieren
        while ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='replace').strip()
            logger.trace(f"Arduino Startup: {line}")
        
        # Scan-Modus starten
        ser.write(b'SCAN\n')
        ser.flush()
        logger.debug("SCAN Befehl gesendet")
        
        # Warten auf Code
        start_time = time.time()
        while True:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                logger.debug("Autorisierung Timeout")
                return False
            
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='replace').strip()
                
                # Zeilen mit # sind Status-Meldungen - ignorieren
                if line.startswith('#'):
                    logger.trace(f"Arduino Status: {line}")
                    continue
                
                if line:
                    try:
                        received_code = int(line)
                        logger.debug(f"Code empfangen: {received_code}")
                        
                        if received_code == auth_code:
                            logger.debug("Autorisierung erfolgreich")
                            return True
                    except ValueError:
                        logger.trace(f"Ignoriere ungültige Zeile: {line}")
            
            time.sleep(0.05)  # 50ms Polling
    
    except serial.SerialException as e:
        raise AuthorizeError(f"Arduino Serial Fehler: {e}")
    except Exception as e:
        raise AuthorizeError(f"Autorisierung fehlgeschlagen: {e}")
    
    finally:
        if ser is not None:
            try:
                ser.close()
            except Exception:
                pass