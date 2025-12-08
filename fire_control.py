#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fire_control.py - Feuer-Orchestrierung für PyroMan

Orchestriert Feuern: Berechtigung prüfen, RF senden, State aktualisieren.
Hält RF-Sender Instanz.

(c) Dr. Ralf Korell, 2025/26

Erstellt: 08.12.2025, 14:30
"""

import config
import state
import direktzuender_wartung
from rf_sender import RFSender, RFSenderError

# Logger
logger = config.get_logger(__name__)

# =============================================================================
# RF-Sender Instanz (lazy init)
# =============================================================================

_rf_sender = None

def _get_rf_sender():
    """Gibt RF-Sender zurück (lazy init)."""
    global _rf_sender
    if _rf_sender is None:
        try:
            _rf_sender = RFSender()
            logger.info("RF-Sender initialisiert")
        except RFSenderError as e:
            logger.error(f"RF-Sender Fehler: {e}")
            return None
    return _rf_sender

# =============================================================================
# Berechtigungsprüfung
# =============================================================================

def _check_authorization():
    """
    Prüft ob Feuern erlaubt ist.
    
    Returns:
        (ok, error_msg) - ok=True wenn erlaubt, sonst error_msg
    """
    if not state.is_authorized():
        return (False, "Nicht autorisiert")
    
    if not state.is_fire_enabled():
        return (False, "Feuer nicht freigegeben")
    
    return (True, None)

# =============================================================================
# Koffer feuern
# =============================================================================

def fire_koffer(koffer_id, kanal_nr):
    """
    Feuert einen Koffer-Kanal.
    
    Args:
        koffer_id: ID des Koffers
        kanal_nr: Kanalnummer (1-10)
    
    Returns:
        (success, error_msg) - success=True bei Erfolg, sonst error_msg
    """
    # Berechtigung prüfen
    ok, error_msg = _check_authorization()
    if not ok:
        return (False, error_msg)
    
    # Code berechnen
    code = config.get_channel_code(koffer_id, kanal_nr)
    if code is None:
        return (False, f"Ungültiger Koffer {koffer_id}")
    
    # RF senden
    sender = _get_rf_sender()
    if sender is None:
        return (False, "RF-Sender nicht verfügbar")
    
    try:
        sender.send(code)
        logger.debug(f"Gefeuert: Koffer {koffer_id}, Kanal {kanal_nr}, Code {code}")
    except RFSenderError as e:
        return (False, f"Sendefehler: {e}")
    
    # State aktualisieren
    state.set_koffer_fired(koffer_id, kanal_nr)
    
    return (True, None)

# =============================================================================
# Direktzünder feuern
# =============================================================================

def fire_direktzuender(nr):
    """
    Feuert einen Direktzünder.
    
    Args:
        nr: Nummer des Direktzünders (1-50)
    
    Returns:
        (success, error_msg) - success=True bei Erfolg, sonst error_msg
    """
    # Berechtigung prüfen
    ok, error_msg = _check_authorization()
    if not ok:
        return (False, error_msg)
    
    # Verfügbarkeit prüfen
    if not direktzuender_wartung.is_direktzuender_available(nr):
        return (False, f"Direktzünder {nr} nicht verfügbar")
    
    # Code berechnen
    code = config.get_direktzuender_code(nr)
    if code is None:
        return (False, f"Ungültiger Direktzünder {nr}")
    
    # RF senden
    sender = _get_rf_sender()
    if sender is None:
        return (False, "RF-Sender nicht verfügbar")
    
    try:
        sender.send(code)
        logger.debug(f"Gefeuert: Direktzünder {nr}, Code {code}")
    except RFSenderError as e:
        return (False, f"Sendefehler: {e}")
    
    # State aktualisieren
    state.set_direktzuender_fired(nr)
    
    return (True, None)

# =============================================================================
# Cleanup
# =============================================================================

def cleanup():
    """Räumt RF-Sender auf."""
    global _rf_sender
    if _rf_sender is not None:
        _rf_sender.cleanup()
        _rf_sender = None
        logger.debug("fire_control cleanup abgeschlossen")
