#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_433.py - Low-Level 433MHz RF-Bibliothek (pigpio-basiert)

Nur für Pi 4 - Pi 5 nutzt Arduino via Serial.

Original von Joan @ pigpio, angepasst für PyroMan.

(c) Dr. Ralf Korell, 2025/26

Erstellt: 07.12.2025, 21:00
Modified: 14.12.2025, 14:30 - AP7: Wiederhergestellt für Pi 4 Auth
"""

import pigpio


class rx():
    """
    433MHz Empfänger-Klasse.
    
    Dekodiert empfangene Codes und ruft Callback auf.
    """
    
    def __init__(self, pi, gpio, callback=None,
                 min_bits=8, max_bits=32, glitch=150):
        """
        Initialisiert den Empfänger.
        
        Args:
            pi: pigpio.pi() Instanz
            gpio: GPIO-Pin (BCM)
            callback: Funktion(code, bits, gap, t0, t1)
            min_bits: Minimale Bits für gültigen Code
            max_bits: Maximale Bits für gültigen Code
            glitch: Glitch-Filter in Mikrosekunden
        """
        self.pi = pi
        self.gpio = gpio
        self.callback = callback
        self.min_bits = min_bits
        self.max_bits = max_bits
        
        self._in_code = False
        self._edge = 0
        self._code = 0
        self._gap = 0
        self._t0 = 0
        self._t1 = 0
        self._bits = 0
        self._last_edge_tick = 0
        
        pi.set_mode(gpio, pigpio.INPUT)
        pi.set_glitch_filter(gpio, glitch)
        
        self._cb = pi.callback(gpio, pigpio.EITHER_EDGE, self._cbf)
    
    def _cbf(self, gpio, level, tick):
        """Callback bei Flanke."""
        if level == 2:  # Watchdog timeout
            if self._in_code:
                if self.min_bits <= self._bits <= self.max_bits:
                    if self.callback:
                        self.callback(self._code, self._bits,
                                     self._gap, self._t0, self._t1)
                self._in_code = False
            return
        
        if self._last_edge_tick:
            edge_len = pigpio.tickDiff(self._last_edge_tick, tick)
        else:
            edge_len = 0
        
        self._last_edge_tick = tick
        
        if not self._in_code:
            # Warte auf lange Gap (> 4000µs = Start)
            if edge_len > 4000:
                self._in_code = True
                self._edge = 0
                self._code = 0
                self._gap = edge_len
                self._bits = 0
        else:
            # In Code - sammle Bits
            if self._edge == 0:
                self._t0 = edge_len
            elif self._edge == 1:
                self._t1 = edge_len
            
            if self._edge % 2 == 1:
                # Bit komplett
                if self._t0 < self._t1:
                    self._code = (self._code << 1) | 1
                else:
                    self._code = self._code << 1
                self._bits += 1
            
            self._edge += 1
            
            # Code beendet?
            if edge_len > 4000:
                if self.min_bits <= self._bits <= self.max_bits:
                    if self.callback:
                        self.callback(self._code, self._bits,
                                     self._gap, self._t0, self._t1)
                self._in_code = False
    
    def cancel(self):
        """Stoppt den Empfänger."""
        if self._cb:
            self._cb.cancel()
            self._cb = None
