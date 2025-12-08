#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wetter_api.py - Wetter-API Modul

API-Aufrufe zu Wunderground für PWS (aktuelles Wetter) und Forecast (Voraussage).

(c) Dr. Ralf Korell, 2025/26

Erstellt: 08.12.2025, 18:00
Modified: 08.12.2025, 19:15 - PWS Wind m/s → km/h konvertiert
"""

import json
import logging
import requests
from pathlib import Path

# =============================================================================
# Logger
# =============================================================================

logger = logging.getLogger(__name__)

# =============================================================================
# Secrets laden
# =============================================================================

_secrets = None

def _load_secrets():
    """Lädt secrets.json."""
    global _secrets
    if _secrets is not None:
        return _secrets
    
    secrets_path = Path(__file__).parent / "secrets.json"
    
    if not secrets_path.exists():
        logger.error(f"secrets.json nicht gefunden: {secrets_path}")
        return None
    
    try:
        with open(secrets_path, 'r', encoding='utf-8') as f:
            _secrets = json.load(f)
        return _secrets
    except json.JSONDecodeError as e:
        logger.error(f"JSON-Fehler in secrets.json: {e}")
        return None
    except Exception as e:
        logger.error(f"Fehler beim Laden von secrets.json: {e}")
        return None

def get_wetter_config():
    """Gibt Wetter-Konfiguration zurück."""
    secrets = _load_secrets()
    if secrets and 'wetter' in secrets:
        return secrets['wetter']
    return None

# =============================================================================
# Windrichtung konvertieren
# =============================================================================

def get_wind_direction(degree):
    """Konvertiert Windrichtung von Grad in Himmelsrichtung (deutsch)."""
    directions = [
        "N", "NNO", "NO", "ONO", "O", "OSO", "SO", "SSO",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
    ]
    if degree is None:
        return "?"
    normalized = degree % 360
    index = round(normalized / (360 / len(directions))) % len(directions)
    return directions[index]

# =============================================================================
# PWS - Aktuelles Wetter
# =============================================================================

def fetch_pws_data():
    """
    Holt aktuelle Wetterdaten von der PWS.
    
    Returns:
        dict: Wetterdaten oder None bei Fehler
    """
    config = get_wetter_config()
    if not config or 'pws' not in config:
        logger.error("PWS-Konfiguration fehlt in secrets.json")
        return None
    
    pws_config = config['pws']
    api_key = pws_config.get('api_key')
    station_id = pws_config.get('station_id')
    
    if not api_key or not station_id:
        logger.error("PWS api_key oder station_id fehlt")
        return None
    
    url = (
        f"https://api.weather.com/v2/pws/observations/current"
        f"?format=json&units=m&numericPrecision=decimal"
        f"&stationId={station_id}&apiKey={api_key}"
    )
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if 'observations' not in data or len(data['observations']) == 0:
            logger.error("Keine PWS-Beobachtungen in Antwort")
            return None
        
        obs = data['observations'][0]
        metric = obs.get('metric', {})
        
        # PWS liefert Wind in m/s, konvertieren zu km/h (* 3.6)
        wind_speed_ms = metric.get('windSpeed')
        wind_gust_ms = metric.get('windGust')
        
        result = {
            'temp': metric.get('temp'),
            'wind_speed': wind_speed_ms * 3.6 if wind_speed_ms is not None else None,
            'wind_gust': wind_gust_ms * 3.6 if wind_gust_ms is not None else None,
            'wind_dir': get_wind_direction(obs.get('winddir')),
            'wind_degree': obs.get('winddir'),
            'humidity': obs.get('humidity'),
            'precip_total': metric.get('precipTotal'),
            'precip_rate': metric.get('precipRate'),
            'pressure': metric.get('pressure'),
            'uv': obs.get('uv'),
            'solar_radiation': obs.get('solarRadiation'),
            'station_id': obs.get('stationID'),
            'obs_time': obs.get('obsTimeLocal')
        }
        
        logger.debug(f"PWS-Daten geladen: {result['temp']}°C, Wind {result['wind_speed']} km/h")
        return result
        
    except requests.exceptions.Timeout:
        logger.error("PWS-API Timeout")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"PWS-API Fehler: {e}")
        return None
    except Exception as e:
        logger.error(f"PWS-Daten Verarbeitungsfehler: {e}")
        return None

# =============================================================================
# Forecast - Voraussage
# =============================================================================

def fetch_forecast_data(hours=12):
    """
    Holt stündliche Wettervorhersage.
    
    Args:
        hours: Anzahl der Stunden (max 24)
    
    Returns:
        list: Liste von Stunden-Daten oder None bei Fehler
    """
    config = get_wetter_config()
    if not config or 'forecast' not in config:
        logger.error("Forecast-Konfiguration fehlt in secrets.json")
        return None
    
    forecast_config = config['forecast']
    api_key = forecast_config.get('api_key')
    geocode = forecast_config.get('geocode')
    
    if not api_key or not geocode:
        logger.error("Forecast api_key oder geocode fehlt")
        return None
    
    url = (
        f"https://api.weather.com/v3/wx/forecast/hourly/1day"
        f"?apiKey={api_key}&geocode={geocode}&units=m&language=de-DE&format=json"
    )
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Daten extrahieren (Arrays mit je 24 Einträgen)
        result = []
        
        for i in range(min(hours, 24)):
            hour_data = {
                'time': data.get('validTimeLocal', [None] * 24)[i],
                'temp': data.get('temperature', [None] * 24)[i],
                'condition': data.get('wxPhraseLong', [None] * 24)[i],
                'condition_short': data.get('wxPhraseShort', [None] * 24)[i],
                'icon_code': data.get('iconCode', [None] * 24)[i],
                'precip_chance': data.get('precipChance', [None] * 24)[i],
                'precip_type': data.get('precipType', [None] * 24)[i],
                'qpf': data.get('qpf', [None] * 24)[i],  # Niederschlagsmenge
                'cloud_cover': data.get('cloudCover', [None] * 24)[i],
                'humidity': data.get('relativeHumidity', [None] * 24)[i],
                'wind_speed': data.get('windSpeed', [None] * 24)[i],
                'wind_dir': data.get('windDirectionCardinal', [None] * 24)[i],
                'wind_gust': data.get('windGust', [None] * 24)[i],
                'uv_index': data.get('uvIndex', [None] * 24)[i]
            }
            
            # Zeit formatieren (nur Stunde)
            if hour_data['time']:
                try:
                    # Format: "2025-12-08T18:00:00+0100"
                    time_part = hour_data['time'].split('T')[1][:5]  # "18:00"
                    hour_data['time_short'] = time_part
                except Exception:
                    hour_data['time_short'] = hour_data['time']
            else:
                hour_data['time_short'] = '?'
            
            result.append(hour_data)
        
        logger.debug(f"Forecast-Daten geladen: {len(result)} Stunden")
        return result
        
    except requests.exceptions.Timeout:
        logger.error("Forecast-API Timeout")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Forecast-API Fehler: {e}")
        return None
    except Exception as e:
        logger.error(f"Forecast-Daten Verarbeitungsfehler: {e}")
        return None

# =============================================================================
# Kombinierte Funktion
# =============================================================================

def fetch_all_weather_data():
    """
    Holt alle Wetterdaten (PWS + Forecast).
    
    Returns:
        dict: {'pws': {...}, 'forecast': [...], 'error': str oder None}
    """
    result = {
        'pws': None,
        'forecast': None,
        'error': None
    }
    
    errors = []
    
    # PWS laden
    pws_data = fetch_pws_data()
    if pws_data:
        result['pws'] = pws_data
    else:
        errors.append("PWS-Daten nicht verfügbar")
    
    # Forecast laden
    forecast_data = fetch_forecast_data(12)
    if forecast_data:
        result['forecast'] = forecast_data
    else:
        errors.append("Forecast-Daten nicht verfügbar")
    
    if errors:
        result['error'] = "; ".join(errors)
    
    return result
