#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pyroman.py - PyroMan Flask-Server

Hauptanwendung mit Routes, WebSocket, Templates.

(c) Dr. Ralf Korell, 2025/26

Erstellt: 07.12.2025, 21:00
"""

import json
import os
from flask import Flask, render_template, redirect, url_for, request, jsonify
from flask_sock import Sock

import config
from rf_sender import RFSender, RFSenderError
from authorize import authenticate, AuthorizeError

# =============================================================================
# Flask App Setup
# =============================================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
sock = Sock(app)

# Logger
logger = config.get_logger(__name__)

# =============================================================================
# Globaler State (RAM)
# =============================================================================

state = {
    'authorized': False,
    'fire_enabled': False,
    'koffer_states': {},       # "koffer_id-kanal_nr": True/False
    'direktzuender_states': {} # nr: True/False
}

# WebSocket Clients
ws_clients = set()

# RF-Sender (lazy init)
rf_sender = None

# =============================================================================
# Direktzünder Status (persistent)
# =============================================================================

DIREKTZUENDER_STATUS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'direktzuender_status.json'
)

def load_direktzuender_status():
    """Lädt Direktzünder-Status aus Datei oder generiert Default."""
    if os.path.exists(DIREKTZUENDER_STATUS_FILE):
        try:
            with open(DIREKTZUENDER_STATUS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Fehler beim Laden von direktzuender_status.json: {e}")
    
    # Generiere Default aus config
    dz_config = config.get_direktzuender_config()
    if dz_config:
        anzahl = dz_config.get('anzahl', 50)
        status_list = [{'nr': i, 'available': True} for i in range(1, anzahl + 1)]
        save_direktzuender_status(status_list)
        return status_list
    
    return []

def save_direktzuender_status(status_list):
    """Speichert Direktzünder-Status in Datei."""
    try:
        with open(DIREKTZUENDER_STATUS_FILE, 'w') as f:
            json.dump(status_list, f, indent=2)
        logger.debug("Direktzünder-Status gespeichert")
    except Exception as e:
        logger.error(f"Fehler beim Speichern von direktzuender_status.json: {e}")

def get_direktzuender_list():
    """Gibt Liste aller Direktzünder mit Status zurück."""
    return load_direktzuender_status()

def set_direktzuender_available(nr, available):
    """Setzt Verfügbarkeit eines Direktzünders."""
    status_list = load_direktzuender_status()
    for dz in status_list:
        if dz['nr'] == nr:
            dz['available'] = available
            break
    save_direktzuender_status(status_list)

# =============================================================================
# RF-Sender Helper
# =============================================================================

def get_rf_sender():
    """Gibt RF-Sender zurück (lazy init)."""
    global rf_sender
    if rf_sender is None:
        try:
            rf_sender = RFSender()
            logger.info("RF-Sender initialisiert")
        except RFSenderError as e:
            logger.error(f"RF-Sender Fehler: {e}")
            return None
    return rf_sender

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

def get_full_state():
    """Gibt vollständigen State für Client zurück."""
    return {
        'type': 'state_update',
        'authorized': state['authorized'],
        'fire_enabled': state['fire_enabled'],
        'koffer_states': state['koffer_states'],
        'direktzuender_states': state['direktzuender_states']
    }

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
        ws.send(json.dumps(get_full_state()))
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
    if not state['authorized']:
        broadcast({'type': 'error', 'message': 'Nicht autorisiert'})
        return
    
    if not state['fire_enabled']:
        broadcast({'type': 'error', 'message': 'Feuer nicht freigegeben'})
        return
    
    target_type = message.get('target_type')
    
    if target_type == 'koffer':
        koffer_id = message.get('koffer_id')
        kanal_nr = message.get('kanal_nr')
        
        code = config.get_channel_code(koffer_id, kanal_nr)
        if code:
            sender = get_rf_sender()
            if sender:
                sender.send(code)
                logger.debug(f"Gefeuert: Koffer {koffer_id}, Kanal {kanal_nr}, Code {code}")
                
                # State aktualisieren
                key = f"{koffer_id}-{kanal_nr}"
                state['koffer_states'][key] = True
                
                # Broadcast
                broadcast({
                    'type': 'channel_fired',
                    'target_type': 'koffer',
                    'koffer_id': koffer_id,
                    'kanal_nr': kanal_nr
                })
    
    elif target_type == 'direktzuender':
        nr = message.get('nr')
        
        # Prüfen ob verfügbar
        dz_list = get_direktzuender_list()
        dz = next((d for d in dz_list if d['nr'] == nr), None)
        if not dz or not dz.get('available', True):
            broadcast({'type': 'error', 'message': f'Direktzünder {nr} nicht verfügbar'})
            return
        
        code = config.get_direktzuender_code(nr)
        if code:
            sender = get_rf_sender()
            if sender:
                sender.send(code)
                logger.debug(f"Gefeuert: Direktzünder {nr}, Code {code}")
                
                # State aktualisieren
                state['direktzuender_states'][nr] = True
                
                # Broadcast
                broadcast({
                    'type': 'channel_fired',
                    'target_type': 'direktzuender',
                    'nr': nr
                })

def handle_reset(message):
    """Verarbeitet Reset-Befehl."""
    target_type = message.get('target_type')
    
    if target_type == 'koffer':
        koffer_id = message.get('koffer_id')
        kanal_nr = message.get('kanal_nr')
        key = f"{koffer_id}-{kanal_nr}"
        state['koffer_states'][key] = False
        
        broadcast({
            'type': 'channel_reset',
            'target_type': 'koffer',
            'koffer_id': koffer_id,
            'kanal_nr': kanal_nr
        })
    
    elif target_type == 'direktzuender':
        nr = message.get('nr')
        state['direktzuender_states'][nr] = False
        
        broadcast({
            'type': 'channel_reset',
            'target_type': 'direktzuender',
            'nr': nr
        })

def handle_reset_all():
    """Setzt alle Kanäle zurück."""
    state['koffer_states'] = {}
    state['direktzuender_states'] = {}
    broadcast(get_full_state())
    logger.debug("Alle Kanäle zurückgesetzt")

def handle_set_fire_enabled(message):
    """Setzt globalen Feuer-Schalter."""
    enabled = message.get('enabled', False)
    state['fire_enabled'] = enabled
    
    broadcast({
        'type': 'fire_enabled_changed',
        'enabled': enabled
    })
    logger.debug(f"Feuer {'aktiviert' if enabled else 'deaktiviert'}")

def handle_auth_start(ws):
    """Startet Autorisierung."""
    # Broadcast: Warte auf Auth
    try:
        ws.send(json.dumps({'type': 'auth_waiting'}))
    except Exception:
        pass
    
    try:
        result = authenticate()
        
        if result:
            state['authorized'] = True
            broadcast({'type': 'auth_success'})
            broadcast(get_full_state())
            logger.info("Autorisierung erfolgreich")
        else:
            try:
                ws.send(json.dumps({'type': 'auth_timeout'}))
            except Exception:
                pass
            logger.debug("Autorisierung Timeout")
    
    except AuthorizeError as e:
        logger.error(f"Autorisierung Fehler: {e}")
        try:
            ws.send(json.dumps({'type': 'error', 'message': str(e)}))
        except Exception:
            pass

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
                           direktzuender_list=get_direktzuender_list())

@app.route('/wartung')
def wartung_page():
    """Wartungs-Seite für Direktzünder-Verfügbarkeit."""
    if not config.is_valid():
        return render_template('error.html', errors=config.get_startup_errors())
    
    return render_template('wartung.html',
                           active_page='wartung',
                           direktzuender_list=get_direktzuender_list())

# =============================================================================
# API Routes
# =============================================================================

@app.route('/api/state')
def api_state():
    """Gibt aktuellen State zurück."""
    return jsonify(get_full_state())

@app.route('/api/direktzuender/<int:nr>/available', methods=['POST'])
def api_set_direktzuender_available(nr):
    """Setzt Verfügbarkeit eines Direktzünders."""
    data = request.get_json()
    available = data.get('available', True)
    
    set_direktzuender_available(nr, available)
    
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
        
        # Auth-Status prüfen
        if not config.is_auth_required():
            state['authorized'] = True
            logger.info("auth_required=False, System ist autorisiert")
    
    # Server starten
    port = 5000
    logger.info(f"Server läuft auf Port {port}")
    
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    main()
