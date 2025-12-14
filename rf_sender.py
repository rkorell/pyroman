#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rf_sender.py - RF-Sender Wrapper für PyroMan

Nutzt codesend (433Utils) für 433MHz-Übertragung.
Exponiert Klasse RFSender mit send() und cleanup().

(c) Dr. Ralf Korell, 2025/26

Erstellt: 07.12.2025, 16:45
Modified: 12.12.2025, 17:00 - Umstellung auf codesend (Pi 4 + Pi 5 kompatibel)
"""

import subprocess
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
            RFSenderError: Wenn Config ungültig.
        """
        self._initialized = False
        
        # Config prüfen
        if not config.is_valid():
            errors = config.get_startup_errors()
            raise RFSenderError(f"Config ungültig: {errors}")
        
        self._initialized = True
        logger.debug("RFSender initialisiert (codesend)")
    
    def send(self, code):
        """
        Sendet einen RF-Code via codesend.
        
        Args:
            code: Integer-Code zum Senden (z.B. 203)
        
        Raises:
            RFSenderError: Wenn Senden fehlschlägt.
        """
        if not self._initialized:
            raise RFSenderError("RFSender nicht initialisiert")
        
        logger.trace(f"send({code}) Start")
        
        try:
            result = subprocess.run(
                ['codesend', str(code)],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0:
                raise RFSenderError(f"codesend Fehler: {result.stderr.decode()}")
        except subprocess.TimeoutExpired:
            raise RFSenderError("codesend Timeout")
        except FileNotFoundError:
            raise RFSenderError("codesend nicht gefunden - 433Utils installiert?")
        except Exception as e:
            logger.error(f"send({code}) Fehler: {e}")
            raise RFSenderError(f"Senden fehlgeschlagen: {e}")
        
        logger.trace(f"send({code}) Ende")
    
    def cleanup(self):
        """
        Beendet den RF-Sender sauber.
        
        Bei codesend nichts zu tun.
        """
        logger.debug("RFSender cleanup")
        self._initialized = False
        logger.debug("RFSender cleanup abgeschlossen")
    
    def is_initialized(self):
        """Gibt True zurück wenn Sender bereit ist."""
        return self._initialized
