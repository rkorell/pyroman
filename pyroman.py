#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pyroman.py - PyroMan Flask-Server

Hauptanwendung mit Routes, WebSocket, Templates.

(c) Dr. Ralf Korell, 2025/26

Erstellt: 07.12.2025, 21:00
Modified: 08.12.2025, 14:30 - Modularisierung: state, fire_control, direktzuender_wartung ausgelagert
Modified: 08.12.2025, 15:45 - scroll_safe_zone an Templates übergeben
Modified: 08.12.2025, 17:00 - Neue Route /wetter
Modified: 08.12.2025, 18:00 - Route /wetter holt echte Wetterdaten via wetter_api
Modified: 12.12.2025, 17:00 - Auth-Logik entfernt (Pi 5 Kompatibilität)
Modified: 14.12.2025, 14:30 - AP7: Auth-Logik wiederhergestellt mit Plattform-Erkennung
"""

import json
import os
import threading
from flask import Flask, render_template, redirect, url_for, request, jsonify
from flask_sock import Sock

import config
import state
import fire_control
import direktzuender_wartung
import wetter_api
import authorize

# =============================================================================
# Flask App Setup
# =============================================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
sock = Sock(app)

# Logger
logger = config.get_logger(__name__)

# =============================================================================
# Template Context
# =============================================================================

@app.context_processor
def inject_ui_config():
    """Injiziert UI-Konfiguration in alle Templates."""
    ui_config = config.get_ui_config()
    return {
        'scroll_safe_zone': ui_config.get('scroll_safe_zone', 50)
    }

# =============================================================================
# WebSocket Clients
# =============================================================================

ws_clients = set()

# =============================================================================
# WebSocket Broadcast
# =============================================================================

def broadcast(message):
    """Sendet Nachricht an alle verbundenen Clients."""
    dead_clients = set()
    for client in ws_clients:
        try:
            client.send(json.dumps(message))
        except Exception:
            dead_clients.add(client)
    
    # Entferne tote Clients
    ws_clients.difference_update(dead_clients)

def get_full_state_message():
    """Gibt vollständigen State für Client zurück (mit type)."""
    full_state = state.get_full_state()
    full_state['type'] = 'state_update'
    return full_state

# =============================================================================
# WebSocket Handler
# =============================================================================

@sock.route('/ws')
def websocket(ws):
    """WebSocket Endpoint."""
    ws_clients.add(ws)
    logger.debug(f"WebSocket Client verbunden ({len(ws_clients)} aktiv)")
    
    # Sende initialen State
    try:
        ws.send(json.dumps(get_full_state_message()))
    except Exception:
        pass
    
    try:
        while True:
            data = ws.receive()
            if data is None:
                break
            
            try:
                message = json.loads(data)
                handle_ws_message(ws, message)
            except json.JSONDecodeError:
                logger.warning("Ungültige JSON-Nachricht empfangen")
            except Exception as e:
                logger.error(f"WebSocket Handler Fehler: {e}")
    finally:
        ws_clients.discard(ws)
        logger.debug(f"WebSocket Client getrennt ({len(ws_clients)} aktiv)")

def handle_ws_message(ws, message):
    """Verarbeitet WebSocket-Nachricht."""
    msg_type = message.get('type')
    logger.debug(f"WS Message: {msg_type}")
    
    if msg_type == 'fire':
        handle_fire(message)
    elif msg_type == 'reset':
        handle_reset(message)
    elif msg_type == 'reset_all':
        handle_reset_all()
    elif msg_type == 'set_fire_enabled':
        handle_set_fire_enabled(message)
    elif msg_type == 'auth_start':
        handle_auth_start(ws)
    else:
        logger.warning(f"Unbekannter Message-Typ: {msg_type}")

def handle_fire(message):
    """Verarbeitet Feuer-Befehl."""
    target_type = message.get('target_type')
    
    if target_type == 'koffer':
        koffer_id = message.get('koffer_id')
        kanal_nr = message.get('kanal_nr')
        
        success, error_msg = fire_control.fire_koffer(koffer_id, kanal_nr)
        
        if success:
            broadcast({
                'type': 'channel_fired',
                'target_type': 'koffer',
                'koffer_id': koffer_id,
                'kanal_nr': kanal_nr
            })
        else:
            broadcast({'type': 'error', 'message': error_msg})
    
    elif target_type == 'direktzuender':
        nr = message.get('nr')
        
        success, error_msg = fire_control.fire_direktzuender(nr)
        
        if success:
            broadcast({
                'type': 'channel_fired',
                'target_type': 'direktzuender',
                'nr': nr
            })
        else:
            broadcast({'type': 'error', 'message': error_msg})

def handle_reset(message):
    """Verarbeitet Reset-Befehl."""
    target_type = message.get('target_type')
    
    if target_type == 'koffer':
        koffer_id = message.get('koffer_id')
        kanal_nr = message.get('kanal_nr')
        state.reset_koffer(koffer_id, kanal_nr)
        
        broadcast({
            'type': 'channel_reset',
            'target_type': 'koffer',
            'koffer_id': koffer_id,
            'kanal_nr': kanal_nr
        })
    
    elif target_type == 'direktzuender':
        nr = message.get('nr')
        state.reset_direktzuender(nr)
        
        broadcast({
            'type': 'channel_reset',
            'target_type': 'direktzuender',
            'nr': nr
        })

def handle_reset_all():
    """Setzt alle Kanäle zurück."""
    state.reset_all()
    broadcast(get_full_state_message())
    logger.debug("Alle Kanäle zurückgesetzt")

def handle_set_fire_enabled(message):
    """Setzt globalen Feuer-Schalter."""
    enabled = message.get('enabled', False)
    state.set_fire_enabled(enabled)
    
    broadcast({
        'type': 'fire_enabled_changed',
        'enabled': enabled
    })
    logger.debug(f"Feuer {'aktiviert' if enabled else 'deaktiviert'}")

def handle_auth_start(ws):
    """
    Startet Autorisierungsprozess.
    
    Sendet auth_waiting, wartet auf 433MHz-Signal, 
    sendet auth_success oder auth_timeout.
    """
    logger.debug("Auth-Start angefordert")
    
    # Client informieren dass Auth läuft
    try:
        ws.send(json.dumps({'type': 'auth_waiting'}))
    except Exception:
        pass
    
    def do_auth():
        """Auth in separatem Thread."""
        try:
            success = authorize.authenticate()
            
            if success:
                state.set_authorized(True)
                broadcast({'type': 'auth_success'})
                broadcast(get_full_state_message())
            else:
                broadcast({'type': 'auth_timeout'})
        
        except authorize.AuthorizeError as e:
            logger.error(f"Auth-Fehler: {e}")
            broadcast({'type': 'error', 'message': str(e)})
    
    # Auth in separatem Thread starten (blockiert nicht WebSocket)
    thread = threading.Thread(target=do_auth)
    thread.daemon = True
    thread.start()

# =============================================================================
# HTTP Routes
# =============================================================================

@app.route('/')
def index():
    """Redirect zu Koffer-Seite."""
    return redirect(url_for('koffer_page'))

@app.route('/koffer')
def koffer_page():
    """Funkkoffer Interface."""
    if not config.is_valid():
        return render_template('error.html', errors=config.get_startup_errors())
    
    koffer_list = config.get_koffer_list()
    
    # Aktuellen Koffer aus Query-Parameter oder ersten
    koffer_id = request.args.get('id', type=int)
    if koffer_id:
        current_koffer = next((k for k in koffer_list if k['id'] == koffer_id), koffer_list[0] if koffer_list else None)
    else:
        current_koffer = koffer_list[0] if koffer_list else None
    
    return render_template('koffer.html',
                           active_page='koffer',
                           koffer_list=koffer_list,
                           current_koffer=current_koffer)

@app.route('/direktzuender')
def direktzuender_page():
    """Direktzünder Interface."""
    if not config.is_valid():
        return render_template('error.html', errors=config.get_startup_errors())
    
    return render_template('direktzuender.html',
                           active_page='direktzuender',
                           direktzuender_list=direktzuender_wartung.get_direktzuender_list())

@app.route('/wartung')
def wartung_page():
    """Wartungs-Seite für Direktzünder-Verfügbarkeit."""
    if not config.is_valid():
        return render_template('error.html', errors=config.get_startup_errors())
    
    return render_template('wartung.html',
                           active_page='wartung',
                           direktzuender_list=direktzuender_wartung.get_direktzuender_list())

@app.route('/wetter')
def wetter_page():
    """Wetter-Seite - holt Daten bei jedem Aufruf."""
    if not config.is_valid():
        return render_template('error.html', errors=config.get_startup_errors())
    
    # Wetterdaten bei Seitenaufruf laden
    weather_data = wetter_api.fetch_all_weather_data()
    
    return render_template('wetter.html',
                           active_page='wetter',
                           pws=weather_data.get('pws'),
                           forecast=weather_data.get('forecast'),
                           weather_error=weather_data.get('error'))

# =============================================================================
# API Routes
# =============================================================================

@app.route('/api/state')
def api_state():
    """Gibt aktuellen State zurück."""
    return jsonify(get_full_state_message())

@app.route('/api/direktzuender/<int:nr>/available', methods=['POST'])
def api_set_direktzuender_available(nr):
    """Setzt Verfügbarkeit eines Direktzünders."""
    data = request.get_json()
    available = data.get('available', True)
    
    direktzuender_wartung.set_direktzuender_available(nr, available)
    
    # Broadcast an alle Clients
    broadcast({
        'type': 'direktzuender_available_changed',
        'nr': nr,
        'available': available
    })
    
    return jsonify({'success': True, 'nr': nr, 'available': available})

# =============================================================================
# Main
# =============================================================================

def main():
    """Startet den Server."""
    logger.info("PyroMan startet...")
    
    if not config.is_valid():
        logger.error("Config ungültig! Server startet trotzdem (zeigt Fehlerseite).")
        for error in config.get_startup_errors():
            logger.error(f"  - {error}")
    else:
        logger.info("Config OK")
    
    # Auth-Check beim Start
    if not config.get_auth_check():
        logger.info("auth_check=false, System automatisch autorisiert")
        state.set_authorized(True)
    else:
        logger.info("auth_check=true, Autorisierung erforderlich")
    
    # Server starten
    port = 5000
    logger.info(f"Server läuft auf Port {port}")
    
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    main()
