#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
state.py - RAM-Zustandsverwaltung für PyroMan

Hält globalen Zustand: authorized, fire_enabled, fired-states.
Bietet Getter/Setter API für alle Module.

(c) Dr. Ralf Korell, 2025/26

Erstellt: 08.12.2025, 14:30
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
    
    Args:
        koffer_id: ID des Koffers
        kanal_nr: Kanalnummer (1-10)
    """
    key = f"{koffer_id}-{kanal_nr}"
    _state['koffer_states'][key] = True
    logger.debug(f"Koffer {koffer_id} Kanal {kanal_nr} gefeuert")

def reset_koffer(koffer_id, kanal_nr):
    """
    Setzt Koffer-Kanal zurück.
    
    Args:
        koffer_id: ID des Koffers
        kanal_nr: Kanalnummer (1-10)
    """
    key = f"{koffer_id}-{kanal_nr}"
    _state['koffer_states'][key] = False
    logger.debug(f"Koffer {koffer_id} Kanal {kanal_nr} zurückgesetzt")

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
