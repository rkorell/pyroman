#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_rf_sender.py - Test-Skript für rf_sender.py

Verwendung:
    python3 test_rf_sender.py           # Nur initialisieren
    python3 test_rf_sender.py 203       # Code 203 senden

(c) Dr. Ralf Korell, 2025/26

Erstellt: 07.12.2025, 16:45
"""

import sys
from rf_sender import RFSender, RFSenderError

print("=== PyroMan rf_sender.py Test ===\n")

try:
    # Initialisieren
    print("Initialisiere RFSender...")
    sender = RFSender()
    print(f"✓ RFSender initialisiert: {sender.is_initialized()}\n")
    
    # Code senden wenn Argument angegeben
    if len(sys.argv) > 1:
        code = int(sys.argv[1])
        print(f"Sende Code {code}...")
        sender.send(code)
        print(f"✓ Code {code} gesendet\n")
    else:
        print("Kein Code angegeben (Aufruf mit: python3 test_rf_sender.py 203)\n")
    
    # Cleanup
    print("Cleanup...")
    sender.cleanup()
    print("✓ Cleanup abgeschlossen")
    
except RFSenderError as e:
    print(f"\n❌ RFSender Fehler: {e}")
    sys.exit(1)
except ValueError as e:
    print(f"\n❌ Ungültiger Code: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Unerwarteter Fehler: {e}")
    sys.exit(1)

print("\n=== Test Ende ===")
