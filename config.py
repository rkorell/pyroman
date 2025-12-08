#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config.py - Zentrale Konfiguration für PyroMan

Lädt config.json, validiert, richtet Logging ein.
Stellt Getter-Funktionen für alle Module bereit.

(c) Dr. Ralf Korell, 2025/26

Erstellt: 07.12.2025, 15:45
Modified: 08.12.2025, 15:45 - get_ui_config() hinzugefügt
"""

import json
import logging
import os

# =============================================================================
# TRACE-Level (unter DEBUG)
# =============================================================================
TRACE = 5
logging.addLevelName(TRACE, "TRACE")

def _trace(self, message, *args, **kwargs):
    if self.isEnabledFor(TRACE):
        self._log(TRACE, message, args, **kwargs)

logging.Logger.trace = _trace

# =============================================================================
# Modul-Variablen
# =============================================================================
_config = {}
_startup_errors = []
_config_valid = False
_config_path = None

# =============================================================================
# Interne Hilfsfunktionen
# =============================================================================

def _get_config_path():
    """Ermittelt Pfad zu config.json relativ zum Skript."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, "config.json")

def _add_error(message):
    """Fügt Fehler zur Liste hinzu."""
    _startup_errors.append(message)

def _validate_required_section(section_name):
    """Prüft ob Sektion existiert."""
    if section_name not in _config:
        _add_error(f"Sektion '{section_name}' fehlt")
        return False
    return True

def _validate_required_field(section, field_name, field_type, section_name):
    """Prüft ob Feld existiert und korrekten Typ hat."""
    if field_name not in section:
        _add_error(f"{section_name}.{field_name} fehlt")
        return False
    
    value = section[field_name]
    
    if field_type == "numeric":
        if not isinstance(value, (int, float)):
            _add_error(f"{section_name}.{field_name} muss eine Zahl sein (ist: {type(value).__name__})")
            return False
        if isinstance(value, str) and value == "CHANGE_ME":
            _add_error(f"{section_name}.{field_name} ist 'CHANGE_ME' - nicht konfiguriert!")
            return False
    elif field_type == "string":
        if not isinstance(value, str):
            _add_error(f"{section_name}.{field_name} muss ein String sein")
            return False
    elif field_type == "bool":
        if not isinstance(value, bool):
            _add_error(f"{section_name}.{field_name} muss true/false sein")
            return False
    elif field_type == "list":
        if not isinstance(value, list):
            _add_error(f"{section_name}.{field_name} muss eine Liste sein")
            return False
    
    return True

def _validate_rf_sender():
    """Validiert rf_sender Sektion."""
    if not _validate_required_section("rf_sender"):
        return
    
    section = _config["rf_sender"]
    _validate_required_field(section, "gpio", "numeric", "rf_sender")
    _validate_required_field(section, "gap", "numeric", "rf_sender")
    _validate_required_field(section, "t0", "numeric", "rf_sender")
    _validate_required_field(section, "t1", "numeric", "rf_sender")
    _validate_required_field(section, "repeats", "numeric", "rf_sender")
    _validate_required_field(section, "bits", "numeric", "rf_sender")

def _validate_rf_empfaenger():
    """Validiert rf_empfaenger Sektion."""
    if not _validate_required_section("rf_empfaenger"):
        return
    
    section = _config["rf_empfaenger"]
    _validate_required_field(section, "gpio", "numeric", "rf_empfaenger")

def _validate_autorisierung():
    """Validiert autorisierung Sektion."""
    if not _validate_required_section("autorisierung"):
        return
    
    section = _config["autorisierung"]
    _validate_required_field(section, "auth_required", "bool", "autorisierung")
    _validate_required_field(section, "auth_timeout_sekunden", "numeric", "autorisierung")
    
    # auth_code nur prüfen wenn auth_required = true
    if section.get("auth_required", True):
        if "auth_code" not in section:
            _add_error("autorisierung.auth_code fehlt (auth_required ist true)")
        elif section["auth_code"] == "CHANGE_ME":
            _add_error("autorisierung.auth_code ist 'CHANGE_ME' - nicht konfiguriert!")
        elif not isinstance(section["auth_code"], int):
            _add_error("autorisierung.auth_code muss eine Zahl sein")

def _validate_koffer():
    """Validiert koffer Sektion."""
    if not _validate_required_section("koffer"):
        return
    
    koffer_list = _config["koffer"]
    if not isinstance(koffer_list, list):
        _add_error("koffer muss eine Liste sein")
        return
    
    for i, koffer in enumerate(koffer_list):
        prefix = f"koffer[{i}]"
        
        if not isinstance(koffer, dict):
            _add_error(f"{prefix} muss ein Objekt sein")
            continue
        
        _validate_required_field(koffer, "id", "numeric", prefix)
        _validate_required_field(koffer, "name", "string", prefix)
        _validate_required_field(koffer, "koffer_nummer", "numeric", prefix)
        _validate_required_field(koffer, "enabled", "bool", prefix)
        
        # Prüfen ob koffer_nummer "CHANGE_ME" ist
        if koffer.get("koffer_nummer") == "CHANGE_ME":
            _add_error(f"{prefix}.koffer_nummer ist 'CHANGE_ME' - nicht konfiguriert!")

def _validate_direktzuender():
    """Validiert direktzuender Sektion."""
    if not _validate_required_section("direktzuender"):
        return
    
    section = _config["direktzuender"]
    _validate_required_field(section, "enabled", "bool", "direktzuender")
    _validate_required_field(section, "erste_box_nr", "numeric", "direktzuender")
    _validate_required_field(section, "anzahl", "numeric", "direktzuender")
    
    if section.get("erste_box_nr") == "CHANGE_ME":
        _add_error("direktzuender.erste_box_nr ist 'CHANGE_ME' - nicht konfiguriert!")

def _setup_logging():
    """Richtet Logging basierend auf config ein."""
    level_str = _config.get("logging", {}).get("level", "INFO").upper()
    
    level_map = {
        "TRACE": TRACE,
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO
    }
    
    level = level_map.get(level_str, logging.INFO)
    
    # Root-Logger konfigurieren
    logging.basicConfig(
        level=level,
        format='[%(levelname)-5s] %(asctime)s %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Logger für dieses Modul
    logger = logging.getLogger(__name__)
    logger.debug(f"Logging initialisiert auf Level: {level_str}")

def _load_config():
    """Lädt und validiert config.json."""
    global _config, _config_valid, _config_path
    
    _config_path = _get_config_path()
    
    # Datei existiert?
    if not os.path.exists(_config_path):
        _add_error(f"config.json nicht gefunden: {_config_path}")
        return
    
    # JSON laden
    try:
        with open(_config_path, 'r', encoding='utf-8') as f:
            _config = json.load(f)
    except json.JSONDecodeError as e:
        _add_error(f"JSON-Syntaxfehler in config.json: Zeile {e.lineno}, {e.msg}")
        return
    except Exception as e:
        _add_error(f"Fehler beim Lesen von config.json: {e}")
        return
    
    # Logging zuerst einrichten (auch bei Config-Fehlern nützlich)
    _setup_logging()
    
    # Validierungen
    _validate_rf_sender()
    _validate_rf_empfaenger()
    _validate_autorisierung()
    _validate_koffer()
    _validate_direktzuender()
    
    # Ergebnis
    if not _startup_errors:
        _config_valid = True
        logger = logging.getLogger(__name__)
        logger.info("Konfiguration erfolgreich geladen")

# =============================================================================
# Öffentliche API
# =============================================================================

def get_startup_errors():
    """Gibt Liste der Config-Fehler zurück (leer wenn OK)."""
    return _startup_errors.copy()

def is_valid():
    """True wenn Config fehlerfrei geladen."""
    return _config_valid

def get_config_path():
    """Gibt Pfad zur config.json zurück."""
    return _config_path

# --- RF Sender ---

def get_rf_sender():
    """Gibt rf_sender Konfiguration zurück."""
    if not _config_valid:
        return None
    return _config.get("rf_sender", {}).copy()

# --- RF Empfänger ---

def get_rf_empfaenger():
    """Gibt rf_empfaenger Konfiguration zurück."""
    if not _config_valid:
        return None
    return _config.get("rf_empfaenger", {}).copy()

# --- Autorisierung ---

def get_auth_code():
    """Gibt auth_code zurück (int oder None)."""
    if not _config_valid:
        return None
    return _config.get("autorisierung", {}).get("auth_code")

def get_auth_timeout():
    """Gibt auth_timeout_sekunden zurück (default 5)."""
    if not _config_valid:
        return 5
    return _config.get("autorisierung", {}).get("auth_timeout_sekunden", 5)

def is_auth_required():
    """Gibt zurück ob Autorisierung erforderlich ist."""
    if not _config_valid:
        return True  # Im Zweifel: ja
    return _config.get("autorisierung", {}).get("auth_required", True)

# --- Koffer ---

def get_koffer_list():
    """Gibt Liste aller Koffer zurück (nur enabled)."""
    if not _config_valid:
        return []
    return [k.copy() for k in _config.get("koffer", []) if k.get("enabled", False)]

def get_channel_code(koffer_id, kanal_nr):
    """
    Berechnet den Zündcode für einen Koffer-Kanal.
    
    Args:
        koffer_id: ID des Koffers (1-8)
        kanal_nr: Kanalnummer (1-8) oder Batterie (9, 10)
    
    Returns:
        int: Der Zündcode (z.B. 203 für Koffer 2, Kanal 3)
        None: Wenn Koffer nicht gefunden
    """
    if not _config_valid:
        return None
    
    for koffer in _config.get("koffer", []):
        if koffer.get("id") == koffer_id:
            koffer_nummer = koffer.get("koffer_nummer")
            if koffer_nummer is not None:
                return koffer_nummer + kanal_nr
    
    return None

# --- Direktzünder ---

def get_direktzuender_config():
    """Gibt direktzuender Konfiguration zurück."""
    if not _config_valid:
        return None
    return _config.get("direktzuender", {}).copy()

def get_direktzuender_code(nr):
    """
    Berechnet den Zündcode für einen Direktzünder.
    
    Args:
        nr: Nummer des Direktzünders (1-50)
    
    Returns:
        int: Der Zündcode (z.B. 1015 für Box 15)
    """
    if not _config_valid:
        return None
    
    config_dz = _config.get("direktzuender", {})
    erste_box_nr = config_dz.get("erste_box_nr", 1001)
    return erste_box_nr + nr - 1

def is_direktzuender_enabled():
    """Gibt zurück ob Direktzünder-Modul aktiv ist."""
    if not _config_valid:
        return False
    return _config.get("direktzuender", {}).get("enabled", False)

# --- Audio ---

def get_audio_config():
    """Gibt audio Konfiguration zurück."""
    if not _config_valid:
        return {"explosion_sound": "", "enabled_default": False}
    return _config.get("audio", {}).copy()

# --- UI ---

def get_ui_config():
    """Gibt UI Konfiguration zurück."""
    if not _config_valid:
        return {"scroll_safe_zone": 50}
    return _config.get("ui", {"scroll_safe_zone": 50}).copy()

# --- Logging ---

def get_log_level():
    """Gibt konfiguriertes Log-Level zurück."""
    return _config.get("logging", {}).get("level", "INFO").upper()

def get_logger(name):
    """Erzeugt Logger mit TRACE-Unterstützung."""
    return logging.getLogger(name)

# =============================================================================
# Initialisierung beim Import
# =============================================================================
_load_config()
