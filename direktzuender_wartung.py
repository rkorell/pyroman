#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
direktzuender_wartung.py - Direktzünder Verfügbarkeitsverwaltung für PyroMan

Verwaltet persistenten Status (available) der Direktzünder.
Speichert in direktzuender_status.json.

Config ist Master für Anzahl. JSON speichert available-Status.
Historische Einträge bleiben erhalten (JSON wird nie gekürzt).

(c) Dr. Ralf Korell, 2025/26

Erstellt: 08.12.2025, 14:30
Modified: 08.12.2025, 15:15 - Bugfix: Config-Anzahl wird berücksichtigt, historische Daten bleiben erhalten
"""

import json
import os

import config

# Logger
logger = config.get_logger(__name__)

# =============================================================================
# Konstanten
# =============================================================================

DIREKTZUENDER_STATUS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'direktzuender_status.json'
)

# =============================================================================
# Interne Funktionen
# =============================================================================

def _load_full_status():
    """
    Lädt komplette Status-Liste aus Datei.
    Erweitert bei Bedarf (wenn config.anzahl > Datei-Einträge).
    Kürzt nie (historische Daten bleiben erhalten).
    
    Returns:
        Liste von Dicts: [{"nr": 1, "available": True}, ...]
    """
    dz_config = config.get_direktzuender_config()
    config_anzahl = dz_config.get('anzahl', 50) if dz_config else 50
    
    status_list = []
    
    # Existierende Datei laden
    if os.path.exists(DIREKTZUENDER_STATUS_FILE):
        try:
            with open(DIREKTZUENDER_STATUS_FILE, 'r') as f:
                status_list = json.load(f)
        except Exception as e:
            logger.warning(f"Fehler beim Laden von direktzuender_status.json: {e}")
            status_list = []
    
    # Bei Bedarf erweitern (nie kürzen)
    current_count = len(status_list)
    if current_count < config_anzahl:
        for i in range(current_count + 1, config_anzahl + 1):
            status_list.append({'nr': i, 'available': True})
        _save_full_status(status_list)
        logger.debug(f"Direktzünder-Status erweitert: {current_count} -> {config_anzahl}")
    
    # Falls Datei leer war, initialisieren
    if not status_list:
        status_list = [{'nr': i, 'available': True} for i in range(1, config_anzahl + 1)]
        _save_full_status(status_list)
        logger.debug(f"Direktzünder-Status initialisiert: {config_anzahl} Einträge")
    
    return status_list

def _save_full_status(status_list):
    """
    Speichert komplette Status-Liste in Datei.
    
    Args:
        status_list: Liste von Dicts: [{"nr": 1, "available": True}, ...]
    """
    try:
        with open(DIREKTZUENDER_STATUS_FILE, 'w') as f:
            json.dump(status_list, f, indent=2)
        logger.debug("Direktzünder-Status gespeichert")
    except Exception as e:
        logger.error(f"Fehler beim Speichern von direktzuender_status.json: {e}")

# =============================================================================
# Öffentliche API
# =============================================================================

def get_direktzuender_list():
    """
    Gibt Liste der Direktzünder für UI zurück.
    Anzahl wird durch config.json bestimmt.
    
    Returns:
        Liste von Dicts: [{"nr": 1, "available": True}, ...]
    """
    dz_config = config.get_direktzuender_config()
    config_anzahl = dz_config.get('anzahl', 50) if dz_config else 50
    
    full_list = _load_full_status()
    
    # Nur die ersten 'anzahl' Einträge zurückgeben
    return full_list[:config_anzahl]

def is_direktzuender_available(nr):
    """
    Prüft ob Direktzünder verfügbar ist.
    
    Args:
        nr: Nummer des Direktzünders
    
    Returns:
        True wenn verfügbar, sonst False
    """
    full_list = _load_full_status()
    for dz in full_list:
        if dz['nr'] == nr:
            return dz.get('available', True)
    return False

def set_direktzuender_available(nr, available):
    """
    Setzt Verfügbarkeit eines Direktzünders.
    
    Args:
        nr: Nummer des Direktzünders
        available: True/False
    """
    full_list = _load_full_status()
    for dz in full_list:
        if dz['nr'] == nr:
            dz['available'] = available
            break
    _save_full_status(full_list)
    logger.debug(f"Direktzünder {nr} available = {available}")
