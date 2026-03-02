#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
state.py - RAM-Zustandsverwaltung für PyroMan

Hält globalen Zustand: authorized, fire_enabled, fired-states.
Bietet Getter/Setter API für alle Module.

(c) Dr. Ralf Korell, 2025/26

Erstellt: 08.12.2025, 14:30
Modified: 12.12.2025, 17:00 - authorized = True (Auth entfernt)
Modified: 14.12.2025, 14:30 - AP7: authorized = False (Auth wiederhergestellt)
Modified: 02.03.2026, 22:00 - Gruppenfeuer-Logik: Kanal 9/10 setzt Einzelkanäle mit
"""

import config

# Logger
logger = config.get_logger(__name__)

# =============================================================================
# Globaler State (RAM)
# =============================================================================

_state = {
    'authorized': False,
    'fire_enabled': False,
    'koffer_states': {},       # "koffer_id-kanal_nr": True/False
    'direktzuender_states': {} # nr: True/False
}

# =============================================================================
# Authorized
# =============================================================================

def is_authorized():
    """Gibt zurück ob System autorisiert ist."""
    return _state['authorized']

def set_authorized(value):
    """Setzt Autorisierungsstatus."""
    _state['authorized'] = bool(value)
    logger.debug(f"authorized = {_state['authorized']}")

# =============================================================================
# Fire Enabled
# =============================================================================

def is_fire_enabled():
    """Gibt zurück ob globaler Feuer-Schalter aktiv ist."""
    return _state['fire_enabled']

def set_fire_enabled(value):
    """Setzt globalen Feuer-Schalter."""
    _state['fire_enabled'] = bool(value)
    logger.debug(f"fire_enabled = {_state['fire_enabled']}")

# =============================================================================
# Koffer States
# =============================================================================

# Gruppenfeuer: Kanal 9 zündet Einzelkanäle 1-4, Kanal 10 zündet 5-8
GRUPPENFEUER = {9: [1, 2, 3, 4], 10: [5, 6, 7, 8]}

def get_koffer_state(koffer_id, kanal_nr):
    """
    Gibt zurück ob Koffer-Kanal gefeuert wurde.

    Args:
        koffer_id: ID des Koffers
        kanal_nr: Kanalnummer (1-10)

    Returns:
        True wenn gefeuert, sonst False
    """
    key = f"{koffer_id}-{kanal_nr}"
    return _state['koffer_states'].get(key, False)

def set_koffer_fired(koffer_id, kanal_nr):
    """
    Markiert Koffer-Kanal als gefeuert.
    Bei Gruppenfeuer (Kanal 9/10) werden auch die Einzelkanäle gesetzt.

    Args:
        koffer_id: ID des Koffers
        kanal_nr: Kanalnummer (1-10)

    Returns:
        Liste der gefeuerten (koffer_id, kanal_nr)-Paare
    """
    key = f"{koffer_id}-{kanal_nr}"
    _state['koffer_states'][key] = True
    fired = [(koffer_id, kanal_nr)]
    logger.debug(f"Koffer {koffer_id} Kanal {kanal_nr} gefeuert")

    if kanal_nr in GRUPPENFEUER:
        for sub_kanal in GRUPPENFEUER[kanal_nr]:
            sub_key = f"{koffer_id}-{sub_kanal}"
            _state['koffer_states'][sub_key] = True
            fired.append((koffer_id, sub_kanal))
        logger.debug(f"Gruppenfeuer: Kanäle {GRUPPENFEUER[kanal_nr]} mit-gefeuert")

    return fired

def reset_koffer(koffer_id, kanal_nr):
    """
    Setzt Koffer-Kanal zurück.
    Bei Gruppenfeuer (Kanal 9/10) werden auch die Einzelkanäle zurückgesetzt.

    Args:
        koffer_id: ID des Koffers
        kanal_nr: Kanalnummer (1-10)

    Returns:
        Liste der zurückgesetzten (koffer_id, kanal_nr)-Paare
    """
    key = f"{koffer_id}-{kanal_nr}"
    _state['koffer_states'][key] = False
    reset = [(koffer_id, kanal_nr)]
    logger.debug(f"Koffer {koffer_id} Kanal {kanal_nr} zurückgesetzt")

    if kanal_nr in GRUPPENFEUER:
        for sub_kanal in GRUPPENFEUER[kanal_nr]:
            sub_key = f"{koffer_id}-{sub_kanal}"
            _state['koffer_states'][sub_key] = False
            reset.append((koffer_id, sub_kanal))
        logger.debug(f"Gruppenfeuer: Kanäle {GRUPPENFEUER[kanal_nr]} mit-zurückgesetzt")

    return reset

# =============================================================================
# Direktzünder States
# =============================================================================

def get_direktzuender_state(nr):
    """
    Gibt zurück ob Direktzünder gefeuert wurde.
    
    Args:
        nr: Nummer des Direktzünders (1-50)
    
    Returns:
        True wenn gefeuert, sonst False
    """
    return _state['direktzuender_states'].get(nr, False)

def set_direktzuender_fired(nr):
    """
    Markiert Direktzünder als gefeuert.
    
    Args:
        nr: Nummer des Direktzünders (1-50)
    """
    _state['direktzuender_states'][nr] = True
    logger.debug(f"Direktzünder {nr} gefeuert")

def reset_direktzuender(nr):
    """
    Setzt Direktzünder zurück.
    
    Args:
        nr: Nummer des Direktzünders (1-50)
    """
    _state['direktzuender_states'][nr] = False
    logger.debug(f"Direktzünder {nr} zurückgesetzt")

# =============================================================================
# Reset All
# =============================================================================

def reset_all():
    """Setzt alle Koffer- und Direktzünder-States zurück."""
    _state['koffer_states'] = {}
    _state['direktzuender_states'] = {}
    logger.debug("Alle Kanäle zurückgesetzt")

# =============================================================================
# Full State Export
# =============================================================================

def get_full_state():
    """
    Gibt kompletten State als Dict zurück.
    
    Returns:
        Dict mit authorized, fire_enabled, koffer_states, direktzuender_states
    """
    return {
        'authorized': _state['authorized'],
        'fire_enabled': _state['fire_enabled'],
        'koffer_states': _state['koffer_states'].copy(),
        'direktzuender_states': _state['direktzuender_states'].copy()
    }
