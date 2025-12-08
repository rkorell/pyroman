#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_authorize.py - Test-Skript für authorize.py

Startet Autorisierung und wartet auf Handsender.

Verwendung:
    python3 test_authorize.py           # Standard-Timeout aus config
    python3 test_authorize.py 10        # 10 Sekunden Timeout

(c) Dr. Ralf Korell, 2025/26

Erstellt: 07.12.2025, 17:00
"""

import sys
from authorize import authenticate, AuthorizeError

print("=== PyroMan authorize.py Test ===\n")

# Timeout aus Argument oder None (= config default)
timeout = None
if len(sys.argv) > 1:
    try:
        timeout = int(sys.argv[1])
        print(f"Timeout: {timeout} Sekunden\n")
    except ValueError:
        print(f"Ungültiger Timeout: {sys.argv[1]}\n")
        sys.exit(1)

try:
    print("Warte auf Handsender...")
    print("(Drücke jetzt den Handsender-Knopf)\n")
    
    result = authenticate(timeout=timeout)
    
    if result:
        print("✓ Autorisierung ERFOLGREICH")
    else:
        print("✗ Autorisierung FEHLGESCHLAGEN (Timeout)")
    
except AuthorizeError as e:
    print(f"\n❌ Authorize Fehler: {e}")
    sys.exit(1)
except KeyboardInterrupt:
    print("\n\nAbgebrochen (Ctrl+C)")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Unerwarteter Fehler: {e}")
    sys.exit(1)

print("\n=== Test Ende ===")
