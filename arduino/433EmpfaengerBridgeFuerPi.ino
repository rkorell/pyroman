/*
 * 433EmpfaengerBridgeFuerPi.ino - 433MHz Empfänger Bridge für Raspberry Pi 5
 * 
 * Empfängt 433MHz Signale und sendet dekodierte Codes via Serial an den Pi.
 * 
 * Protokoll:
 * - Pi sendet "SCAN\n" → Arduino beginnt zu scannen
 * - Arduino sendet "<code>\n" wenn gültiger Code empfangen
 * 
 * Hardware:
 * - Arduino Nano/Uno
 * - 433MHz Empfänger an Pin 2 (Interrupt-fähig)
 * 
 * (c) Dr. Ralf Korell, 2025/26
 * 
 * Erstellt: 14.12.2025, 14:30 - AP7: Arduino RX Bridge für Pi 5
 */

#include <RCSwitch.h>

RCSwitch mySwitch = RCSwitch();

const int RX_PIN = 2;  // Interrupt-fähiger Pin
bool scanning = false;

void setup() {
    Serial.begin(9600);
    mySwitch.enableReceive(digitalPinToInterrupt(RX_PIN));
    
    // Startup-Nachricht
    Serial.println("433Bridge ready");
}

void loop() {
    // Serielle Befehle verarbeiten
    if (Serial.available()) {
        String cmd = Serial.readStringUntil('\n');
        cmd.trim();
        
        if (cmd == "SCAN") {
            scanning = true;
            Serial.println("SCANNING");
        } else if (cmd == "STOP") {
            scanning = false;
            Serial.println("STOPPED");
        }
    }
    
    // 433MHz Empfang
    if (scanning && mySwitch.available()) {
        unsigned long code = mySwitch.getReceivedValue();
        
        if (code != 0) {
            Serial.println(code);
        }
        
        mySwitch.resetAvailable();
    }
}
