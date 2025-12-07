#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rf_sender.py - RF-Sender Wrapper für PyroMan

Kapselt _433.tx und liest Parameter aus config.py.
Exponiert Klasse RFSender mit send() und cleanup().

(c) Dr. Ralf Korell, 2025/26

Erstellt: 07.12.2025, 16:45
"""

import pigpio
from lib._433 import tx
import config

# Logger
logger = config.get_logger(__name__)


class RFSenderError(Exception):
    """Fehler im RF-Sender Modul."""
    pass


class RFSender:
    """
    RF-Sender für 433MHz Codes.
    
    Verwendung:
        sender = RFSender()
        sender.send(203)      # Sendet Code 203
        sender.cleanup()      # Am Ende aufrufen
    """
    
    def __init__(self):
        """
        Initialisiert den RF-Sender.
        
        Raises:
            RFSenderError: Wenn Config ungültig oder pigpiod nicht läuft.
        """
        self._pi = None
        self._tx = None
        self._initialized = False
        
        # Config prüfen
        if not config.is_valid():
            errors = config.get_startup_errors()
            raise RFSenderError(f"Config ungültig: {errors}")
        
        # RF-Parameter laden
        rf_config = config.get_rf_sender()
        if rf_config is None:
            raise RFSenderError("RF-Sender Konfiguration fehlt")
        
        self._gpio = rf_config.get("gpio")
        self._gap = rf_config.get("gap")
        self._t0 = rf_config.get("t0")
        self._t1 = rf_config.get("t1")
        self._repeats = rf_config.get("repeats")
        self._bits = rf_config.get("bits")
        
        logger.debug(f"RF-Parameter: GPIO={self._gpio}, gap={self._gap}, "
                     f"t0={self._t0}, t1={self._t1}, repeats={self._repeats}")
        
        # pigpio verbinden
        try:
            self._pi = pigpio.pi()
            if not self._pi.connected:
                raise RFSenderError(
                    "pigpiod nicht erreichbar. "
                    "Bitte starten mit: sudo pigpiod"
                )
        except Exception as e:
            raise RFSenderError(f"pigpio Verbindung fehlgeschlagen: {e}")
        
        # _433.tx initialisieren
        try:
            self._tx = tx(
                self._pi,
                gpio=self._gpio,
                repeats=self._repeats,
                bits=self._bits,
                gap=self._gap,
                t0=self._t0,
                t1=self._t1
            )
        except Exception as e:
            self._pi.stop()
            raise RFSenderError(f"TX Initialisierung fehlgeschlagen: {e}")
        
        self._initialized = True
        logger.debug(f"RFSender initialisiert auf GPIO {self._gpio}")
    
    def send(self, code):
        """
        Sendet einen RF-Code.
        
        Args:
            code: Integer-Code zum Senden (z.B. 203)
        
        Raises:
            RFSenderError: Wenn nicht initialisiert.
        """
        if not self._initialized:
            raise RFSenderError("RFSender nicht initialisiert")
        
        logger.trace(f"send({code}) Start")
        
        try:
            self._tx.send(code)
        except Exception as e:
            logger.error(f"send({code}) Fehler: {e}")
            raise RFSenderError(f"Senden fehlgeschlagen: {e}")
        
        logger.trace(f"send({code}) Ende")
    
    def cleanup(self):
        """
        Beendet den RF-Sender sauber.
        
        Gibt Ressourcen frei (TX und pigpio-Verbindung).
        """
        logger.debug("RFSender cleanup")
        
        if self._tx is not None:
            try:
                self._tx.cancel()
            except Exception as e:
                logger.warning(f"TX cancel Fehler: {e}")
            self._tx = None
        
        if self._pi is not None:
            try:
                self._pi.stop()
            except Exception as e:
                logger.warning(f"pigpio stop Fehler: {e}")
            self._pi = None
        
        self._initialized = False
        logger.debug("RFSender cleanup abgeschlossen")
    
    def is_initialized(self):
        """Gibt True zurück wenn Sender bereit ist."""
        return self._initialized
