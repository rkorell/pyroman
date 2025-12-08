#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_config.py - Test-Skript für config.py

(c) Dr. Ralf Korell, 2025/26

Erstellt: 07.12.2025, 16:00
"""

import config

print("=== PyroMan config.py Test ===\n")

# 1. Validierung
print(f"Config valid: {config.is_valid()}")
print(f"Config path:  {config.get_config_path()}")

errors = config.get_startup_errors()
if errors:
    print(f"\n❌ {len(errors)} Fehler gefunden:")
    for e in errors:
        print(f"   - {e}")
else:
    print("\n✓ Keine Fehler")

# 2. Getter testen (nur wenn valid)
if config.is_valid():
    print("\n--- RF Sender ---")
    rf = config.get_rf_sender()
    print(f"  GPIO: {rf['gpio']}, gap: {rf['gap']}, t0: {rf['t0']}, t1: {rf['t1']}")
    
    print("\n--- Koffer ---")
    for k in config.get_koffer_list():
        print(f"  {k['name']}: koffer_nummer={k['koffer_nummer']}, enabled={k['enabled']}")
    
    print("\n--- Code-Berechnung Koffer ---")
    print(f"  Koffer 1, Kanal 1:      {config.get_channel_code(1, 1)}")
    print(f"  Koffer 1, Kanal 8:      {config.get_channel_code(1, 8)}")
    print(f"  Koffer 1, Batterie 1-4: {config.get_channel_code(1, 9)}")
    print(f"  Koffer 1, Batterie 5-8: {config.get_channel_code(1, 10)}")
    print(f"  Koffer 2, Kanal 3:      {config.get_channel_code(2, 3)}")
    print(f"  Koffer 5, Kanal 8:      {config.get_channel_code(5, 8)}")
    
    print("\n--- Code-Berechnung Direktzünder ---")
    print(f"  Direktzünder 1:  {config.get_direktzuender_code(1)}")
    print(f"  Direktzünder 15: {config.get_direktzuender_code(15)}")
    print(f"  Direktzünder 50: {config.get_direktzuender_code(50)}")
    
    print("\n--- Autorisierung ---")
    print(f"  auth_required: {config.is_auth_required()}")
    print(f"  auth_timeout:  {config.get_auth_timeout()}s")
    print(f"  auth_code:     {'[gesetzt]' if config.get_auth_code() else 'FEHLT'}")
    
    print("\n--- Logging ---")
    print(f"  Level: {config.get_log_level()}")

print("\n=== Test Ende ===")
