#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_arduino_serial.py - Arduino Serial Bridge Test

Testet die Kommunikation mit dem Arduino 433MHz Empfänger.
Loggt ALLES was über Serial kommt.

Verwendung:
    python3 test_arduino_serial.py
    python3 test_arduino_serial.py /dev/ttyUSB1   # anderer Port

(c) Dr. Ralf Korell, 2025/26
Erstellt: 14.12.2025, 14:30
"""

import sys
import time
import serial

# Port aus Argument oder Default
PORT = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyUSB0'
BAUD = 9600

print("=" * 60)
print("Arduino Serial Bridge Test")
print("=" * 60)
print(f"Port: {PORT}")
print(f"Baud: {BAUD}")
print()

try:
    print(f"[1] Öffne Serial Port...")
    ser = serial.Serial(PORT, BAUD, timeout=0.5)
    print(f"    ✓ Port geöffnet")
    
    print(f"[2] Warte auf Arduino Reset (3 Sekunden)...")
    for i in range(3, 0, -1):
        print(f"    {i}...")
        time.sleep(1)
    print(f"    ✓ Reset-Zeit abgelaufen")
    
    print(f"[3] Lese alles was im Buffer ist...")
    while ser.in_waiting > 0:
        line = ser.readline().decode('utf-8', errors='replace').strip()
        print(f"    << RX: '{line}'")
    print(f"    ✓ Buffer geleert")
    
    print(f"[4] Sende 'SCAN' Befehl...")
    ser.write(b'SCAN\n')
    ser.flush()
    print(f"    >> TX: 'SCAN'")
    
    print(f"[5] Warte auf Antwort (1 Sekunde)...")
    time.sleep(1)
    while ser.in_waiting > 0:
        line = ser.readline().decode('utf-8', errors='replace').strip()
        print(f"    << RX: '{line}'")
    
    print()
    print("=" * 60)
    print("JETZT: Drücke den Handsender!")
    print("       (Ctrl+C zum Beenden)")
    print("=" * 60)
    print()
    
    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='replace').strip()
            timestamp = time.strftime('%H:%M:%S')
            print(f"[{timestamp}] << RX: '{line}'")
            
            # Versuche als Zahl zu parsen
            try:
                code = int(line)
                print(f"           ✓ Code erkannt: {code}")
            except ValueError:
                pass
        
        time.sleep(0.05)

except serial.SerialException as e:
    print(f"\n❌ Serial Fehler: {e}")
    sys.exit(1)
except KeyboardInterrupt:
    print(f"\n\nAbgebrochen (Ctrl+C)")
except Exception as e:
    print(f"\n❌ Fehler: {e}")
    sys.exit(1)
finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()
        print("Serial Port geschlossen")

print("\n=== Test Ende ===")
