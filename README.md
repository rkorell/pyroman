# PyroMan - 433MHz Funkzündsystem für Pyrotechnik

**(c) Dr. Ralf Korell**

## Was ist PyroMan?

PyroMan ist die Steuerungssoftware für ein privates Pyrotechnik-Zündsystem. Es läuft auf
einem Raspberry Pi 5 und steuert per 433MHz-Funk bis zu fünf Arduino-basierte Zündkoffer
(je 8 Kanäle plus 2 Gruppenfeuer) sowie bis zu 50 Direktzünder (einfache Funkempfänger
mit Relais).

Das System ersetzt eine ältere, auf FHEM basierende Lösung. FHEM war ursprünglich als
Hausautomatisierung konzipiert und wurde für die Pyrotechnik-Steuerung zweckentfremdet.
PyroMan ist von Grund auf für diesen einen Zweck gebaut: zuverlässig, übersichtlich und
ohne den Overhead eines Universalsystems.

Die Bedienung erfolgt über ein Web-Interface (Flask + WebSocket), das auf dem Pi selbst
oder von jedem Gerät im lokalen Netz erreichbar ist. Im Feldbetrieb spannt der Pi einen
eigenen WLAN-Hotspot auf, über den Tablets und Smartphones zugreifen können.

### Sicherheitskonzept

Bevor gezündet werden kann, muss das System per 433MHz-Handsender autorisiert werden.
Der Handsender ersetzt einen physischen Schlüsselschalter - ohne den korrekten Funkcode
ist keine Aktion möglich. Zusätzlich gibt es einen globalen Fire-Master-Schalter im
Web-Interface, der über WebSocket auf allen verbundenen Clients synchronisiert wird.
Beide Sicherheitsstufen (Handsender + Fire-Master) müssen aktiv sein, bevor das System
Befehle an die Koffer oder Direktzünder sendet.

## Hardware

| Komponente | Details |
|-----------|---------|
| Steuerung | Raspberry Pi 5, Debian 13 (Trixie) |
| 433MHz Sender (TX) | GPIO 21 (BCM), Pin 40 |
| 433MHz Empfänger (RX) | GPIO 27 (BCM), Pin 13 |
| Stromversorgung | GeeekPi PD Power Expansion Board (EP-0225) |
| Funkkoffer | 5 Stück (Nr. 100-500), Arduino-basiert, je 8 Kanäle + 2 Gruppenfeuer |
| Direktzünder | bis zu 50 Stück, einfache Funkempfänger mit Relais |
| Handsender | 433MHz, zur Autorisierung des Systems |

Die 433MHz-Kommunikation ist unidirektional (Fire-and-Forget). Der Pi sendet Befehle,
erhält aber keine Bestätigung von den Koffern oder Direktzündern.

## Architektur

```
pyroman.py          Flask-Webserver, WebSocket, State-Management, Routing
├── config.py       Konfiguration laden/validieren, Logging
├── rf_sender.py    433MHz Senden (Subprocess: codesend)
├── fire_control.py Zünd-Logik, RFSender-Zugriff
├── state.py        Globaler Zustand (Auth, Fire-Master, Koffer-Status)
├── authorize.py    Autorisierung per 433MHz Handsender (gpiod v2)
├── wetter_api.py   Wunderground-Wetter-API (optional, nur mit Internet)
├── codesend.py     Standalone 433MHz TX-Tool (Symlink /usr/local/bin/codesend)
└── getcode.py      Standalone 433MHz RX-Tool (Symlink /usr/local/bin/getcode)
```

`codesend.py` und `getcode.py` sind eigenständige Kommandozeilen-Tools, die auch ohne
den laufenden Webserver funktionieren - zum Testen, Debuggen und für die Zündkoffer-GUI.
Beide nutzen reines Python mit gpiod v2 für den GPIO-Zugriff.

## Web-Interface

Das Interface ist in Tabs organisiert, erreichbar über Port 5000:

| Tab | Route | Funktion |
|-----|-------|----------|
| Koffer | `/` | Zündung der 5 Koffer (je 8 Kanäle + Gruppenfeuer) |
| Direktzünder | `/direktzuender` | Zündung der Einzelempfänger (1-50) |
| Wartung | `/wartung` | Direktzünder-Verfügbarkeit verwalten |
| Box-Test/Config | `/boxtest` | Koffer testen, Auto-Modus, Gruppenfeuer, Wartezeit, EEprom |
| Wetter | `/wetter` | Wetterdaten von Wunderground (nur mit Internetzugang) |

Alle Tabs teilen denselben globalen Zustand: Autorisierung und Fire-Master gelten
systemweit. Änderungen werden per WebSocket in Echtzeit an alle verbundenen Clients
verteilt.

## Arduino-Archiv (`arduino/`)

Das Verzeichnis `arduino/` enthält die Quelldateien der Arduino-Firmware als Referenz
und Archiv. Diese Dateien werden nicht vom Pi ausgeführt, sondern dokumentieren die
Software, die auf den Funkkoffern und der RX-Bridge läuft.

| Datei | Zweck |
|-------|-------|
| `PyroManAll.ino` | Koffer-Firmware (V1.3.2.14) - Relais-Steuerung, Sonderbefehle, EEprom |
| `PyroManEprom.h` | EEprom-Funktionen der Koffer (Lesen, Schreiben, Löschen) |
| `PyromanSetStatus.ino` | Koffer-Status-Firmware |
| `433EmpfaengerBridgeFuerPi.ino` | RX-Bridge für den Fallback-Pfad (Arduino empfängt 433MHz, leitet per Serial an Pi weiter) |

Die Koffer-Firmware definiert die Code-Bereiche (Normalcodes 1-99999, Sonderbefehle
8000xxx/8100xxx/9999xxx) und die EEprom-Struktur (Box-ID ab Adresse 10, Autonom-Modus
ab Adresse 20, Daten ab Adresse 40).

Die RX-Bridge-Firmware ist Teil des dokumentierten Fallback-Pfads für den Fall, dass
der GPIO-Zugriff in einer zukünftigen Debian-Version erneut verändert wird
(siehe Aufbauanleitung, Schritt 4.5).

## Setup und Rebuild

Die vollständige Aufbauanleitung vom leeren Pi bis zum lauffähigen System:

**[doc/Rebuild-Pyro.md](doc/Rebuild-Pyro.md)**

Die Anleitung umfasst 13 Schritte: Netzwerk (Hotspot + Client-WLAN), GPIO-Verkabelung,
Stromversorgung, 433MHz-Test (inkl. Fallback-Pfad), Git, Abhängigkeiten, Repo klonen,
Konfiguration, Code-Portierung, Funktionstest, systemd-Service, Desktop und Backup.

### Dateien außerhalb des Repos

Zwei Konfigurationsdateien enthalten Zündcodes und API-Keys und sind bewusst
**nicht im Git** (Sicherheit). Sie müssen beim Setup manuell vom Backup oder
vom alten System kopiert werden:

| Datei | Inhalt |
|-------|--------|
| `config.json` | Koffer-Definitionen, Auth-Code, Zündcodes |
| `secrets.json` | Wunderground API-Keys, Station-ID |

Vorlagen mit der erwarteten Struktur liegen als `config.json.example` und
`secrets.json.example` im Repo.

## Backup

PyroMan ist in das zentrale Backup-Konzept eingebunden. Das Backup wird vom
Backup-Server auf dem Webserver (IP .192) initiiert und gesteuert.

## Abhängigkeiten

| Paket | Version | Quelle | Anmerkung |
|-------|---------|--------|-----------|
| Python | 3.13 | System | vorinstalliert unter Trixie |
| Flask | 3.1 | apt | vorinstalliert |
| gpiod | 2.2 | apt | vorinstalliert, ersetzt pigpio |
| requests | 2.32 | apt | vorinstalliert |
| flask-sock | 0.7 | pip | einziges pip-Paket |
