#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
floorplan_state.py - Floorplan-Zustandsverwaltung für PyroMan

Hält Koffer/Kanal-Zuordnungen für die 11 Floorplan-Positionen
(9 Einzelzündungen + 2 Gruppenfeuer). Fired-Status wird aus dem
zentralen Koffer-State (state.py) abgeleitet - kein eigener Fired-State.

(c) Dr. Ralf Korell, 2025/26

Erstellt: 02.03.2026, 18:00
Modified: 02.03.2026, 22:00 - Fired-State entfernt, wird aus state.py abgeleitet
"""

import config
import state

# Logger
logger = config.get_logger(__name__)

# =============================================================================
# Defaults (aus FHEM n_box_reset_on extrahiert)
# =============================================================================

# koffer = koffer_id (1-4), kanal = Kanalnummer (1-10)
# Pos 1-4: Kleine Kanone, Einzelmörser, Zweifach-Mörser (2 Rohre) → K2/Ch1-4
# Pos 5: Große Kanone (Einzelstück) → K3/Ch1 (eigener Koffer)
# Pos 6-9: Vierfach-Mörser (4 Rohre) → K2/Ch5-8 (alle am selben Koffer für Gruppenfeuer!)
# G1: Gruppenfeuer Kanal 1-4, G2: Gruppenfeuer Kanal 5-8 (= alle 4 Vierfach-Rohre)
DEFAULTS = {
    '1':  {'koffer': 2, 'kanal': 1},
    '2':  {'koffer': 2, 'kanal': 2},
    '3':  {'koffer': 2, 'kanal': 3},
    '4':  {'koffer': 2, 'kanal': 4},
    '5':  {'koffer': 3, 'kanal': 1},
    '6':  {'koffer': 2, 'kanal': 5},
    '7':  {'koffer': 2, 'kanal': 6},
    '8':  {'koffer': 2, 'kanal': 7},
    '9':  {'koffer': 2, 'kanal': 8},
    'G1': {'koffer': 2, 'kanal': 9},
    'G2': {'koffer': 2, 'kanal': 10},
}

# Positionen mit festem Kanal (Gruppenfeuer)
FIXED_KANAL = {'G1': 9, 'G2': 10}

# =============================================================================
# State (RAM) - nur Zuordnungen, kein Fired-State
# =============================================================================

_positions = {}   # pos_id -> {koffer: int, kanal: int}

def _init():
    """Initialisiert State mit Defaults."""
    global _positions
    _positions = {pos_id: vals.copy() for pos_id, vals in DEFAULTS.items()}

# Beim Import initialisieren
_init()

# =============================================================================
# Positions (Koffer/Kanal-Zuordnung)
# =============================================================================

def get_position(pos_id):
    """Gibt Koffer/Kanal-Zuordnung einer Position zurück."""
    pos = _positions.get(str(pos_id))
    if pos is None:
        return None
    return pos.copy()

def set_position(pos_id, koffer, kanal):
    """
    Setzt Koffer/Kanal-Zuordnung einer Position.
    Bei G1/G2 wird der Kanal ignoriert (fest 9 bzw. 10).
    """
    pos_id = str(pos_id)
    if pos_id not in _positions:
        logger.warning(f"Unbekannte Floorplan-Position: {pos_id}")
        return False

    # Koffer validieren (1-4)
    if not isinstance(koffer, int) or koffer < 1 or koffer > 4:
        logger.warning(f"Ungültiger Koffer: {koffer}")
        return False

    # Bei Gruppenfeuer: Kanal ist fest
    if pos_id in FIXED_KANAL:
        kanal = FIXED_KANAL[pos_id]
    elif not isinstance(kanal, int) or kanal < 1 or kanal > 8:
        logger.warning(f"Ungültiger Kanal: {kanal}")
        return False

    _positions[pos_id] = {'koffer': koffer, 'kanal': kanal}
    logger.debug(f"Floorplan Position {pos_id}: Koffer {koffer}, Kanal {kanal}")
    return True

def get_all_positions():
    """Gibt alle Positionen als Dict zurück."""
    return {pos_id: vals.copy() for pos_id, vals in _positions.items()}

def reset_defaults():
    """Setzt alle Positionen auf Defaults zurück."""
    global _positions
    _positions = {pos_id: vals.copy() for pos_id, vals in DEFAULTS.items()}
    logger.debug("Floorplan: alle Positionen auf Defaults zurückgesetzt")

# =============================================================================
# Fired-Status (abgeleitet aus state.py)
# =============================================================================

def get_fired_from_state():
    """Leitet Floorplan-Fired-Status aus dem zentralen Koffer-State ab."""
    fired = {}
    for pos_id, pos in _positions.items():
        fired[pos_id] = state.get_koffer_state(pos['koffer'], pos['kanal'])
    return fired

# =============================================================================
# Full State Export
# =============================================================================

def get_full_state():
    """Gibt kompletten Floorplan-State zurück (Positionen + abgeleiteter Fired-Status)."""
    return {
        'positions': get_all_positions(),
        'fired': get_fired_from_state()
    }
