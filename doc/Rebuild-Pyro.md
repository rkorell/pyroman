# Setup: Neues PyroMan-System (Pi 5 / Trixie)

**Autor:** Dr. Ralf Korell
**Ausgangs-OS:** Debian 13 (Trixie)

Fahrplan: Vom leeren, mit Trixie geflashten Pi 5 zum lauffähigen PyroMan.

---

## Schritt 1: Netzwerk einrichten (AP + Client)

PyroMan braucht zwei WLAN-Verbindungen gleichzeitig: einen eigenen Hotspot
(Feldbetrieb) und eine Client-Verbindung ins Heimnetz (Entwicklung/Updates).

**MAC-Bindung nur für den USB-Dongle (KORELL Web):** Der Dongle wandert mit der
SD-Karte und hat immer dieselbe MAC. Der Hotspot bekommt KEINE MAC-Bindung, weil
das Onboard-WLAN bei jedem Pi eine andere MAC hat. Beim SD-Karten-Umzug (Dev → Prod)
nimmt NetworkManager automatisch das freie Onboard-WLAN für den Hotspot - egal welcher Pi.

### Vorbereitung

- USB-WiFi-Dongle (TP-Link 802.11ac) einstecken
- Terminal direkt am Pi öffnen (Touchscreen oder Tastatur)
- **Achtung:** Bei Remote-Zugang wird die SSH-Verbindung während der Umkonfiguration abreißen!

### 1.1 MAC-Adressen ermitteln

```bash
ip link show
```

USB-Dongle identifizieren, MAC notieren (nur Dongle braucht MAC-Bindung).

Dieses System:

| Gerät | MAC |
|-------|-----|
| TP-Link USB-Dongle | 98:03:8E:9E:FC:BE |

> Onboard-WLAN MAC wird NICHT benötigt (keine MAC-Bindung für den Hotspot).

### 1.2 KORELL Web auf USB-Dongle anlegen und aktivieren

Zuerst die Client-Verbindung auf den Dongle legen, damit Netzwerk-Zugang bestehen bleibt.

```bash
nmcli connection add type wifi con-name "KORELL Web" ssid "KORELL Web" wifi.mac-address 98:03:8E:9E:FC:BE wifi-sec.key-mgmt wpa-psk wifi-sec.psk "HIER_WLAN_PASSWORT" ipv4.method auto ipv6.method auto
```

```bash
nmcli connection up "KORELL Web"
```

Prüfen:

```bash
ip -4 addr show wlan1
```

### 1.3 Alte WLAN-Verbindung auf wlan0 entfernen

```bash
nmcli connection show
```

Falls eine bestehende Verbindung zu "KORELL Web" auf wlan0 existiert (z.B. "netplan-wlan0-KORELL Web"):

```bash
nmcli connection delete "netplan-wlan0-KORELL Web"
```

### 1.4 Hotspot auf internem WLAN einrichten und aktivieren

```bash
nmcli connection add type wifi con-name "PyroTablet" ssid "PyroTablet" mode ap wifi-sec.key-mgmt wpa-psk wifi-sec.psk "PT123456789" wifi.band bg wifi.channel 6 ipv4.method shared ipv6.method shared connection.autoconnect-priority 6
```

```bash
nmcli connection up PyroTablet
```

### 1.5 Prüfen

```bash
nmcli device status
```

Erwartetes Ergebnis:

```
DEVICE   TYPE   STATE      CONNECTION
wlan0    wifi   connected  PyroTablet       (AP, 10.42.0.1)
wlan1    wifi   connected  KORELL Web       (Client, DHCP)
```

### 1.6 Netplan-Reste aufräumen (Trixie-spezifisch)

Falls Netplan die WiFi-Konfiguration stört:

```bash
sudo cat /etc/netplan/*.yaml
```

Falls dort WiFi-Einträge stehen, diese entfernen und nur Ethernet/Loopback belassen:

```bash
sudo nano /etc/netplan/01-network-manager-all.yaml
```

```bash
sudo netplan apply
```

### 1.7 Reboot-Test

```bash
sudo reboot
```

```bash
nmcli device status
```

Beide Verbindungen müssen automatisch hochkommen.

---

## Schritt 2: GPIO-Hardware anschließen (433MHz)

### 2.1 Sender (TX)

| 433MHz Sender Pin | Pi 5 GPIO | Physical Pin |
|-------------------|-----------|--------------|
| VCC               | 5V        | Pin 2        |
| GND               | GND       | Pin 6        |
| DATA              | GPIO 21   | Pin 40       |

**Antenne:** 17,3 cm Draht (λ/4 für 433MHz) an den Antennen-Pin löten. Zwingend für Reichweite!

### 2.2 Empfänger (RX)

| 433MHz Empfänger Pin | Pi 5 GPIO | Physical Pin |
|----------------------|-----------|--------------|
| VCC                  | 5V        | Pin 4        |
| GND                  | GND       | Pin 9        |
| DATA                 | GPIO 27   | Pin 13       |

**Antenne:** Spiralantenne am Empfänger verbessert Empfang deutlich.

---

## Schritt 3: Stromversorgung und Sicherheitsschalter

Der Pi 5 braucht stabile 5V/5A. Das offizielle Netzteil liefert das, ist aber
stationär. Für den mobilen Feldbetrieb (Powerbank) gibt es zwei Varianten.

### Hintergrund: USB-C und Schalter

Ein Schlüsselschalter im USB-C-Kabel funktioniert NICHT: USB-C braucht einen
CC-Handshake über die Signalleitungen. Unterbricht man nur Plus/Minus, erkennt
der Pi keine Stromquelle und bootet nicht.

### Variante A: Powerbank am USB-C (ohne Hardware-Schlüsselschalter)

Getestet: GeeekPi PD Power Expansion Board (EP-0225) zwischen Powerbank und Pi.

```
Powerbank (USB-C) → GeeekPi Board (USB-C in) → (USB-C out) → Pi 5
```

- Das Board verhandelt PD mit der Powerbank und liefert stabile 5.15V/5A
- Funktioniert auch mit Powerbanks ohne echtes PD (z.B. INIU 22.5W 10000mAh)
- Always-ON-Switch am Board auf "Enabled" setzen → Pi startet automatisch

**Sicherung:** Ohne Hardware-Schlüsselschalter übernimmt der **433MHz-Handsender**
die Autorisierung (authorize.py). Der Handsender ersetzt den physischen Schlüssel -
ohne Handsender-Code kann nicht gezündet werden. Voraussetzung: 433MHz-Empfang
muss funktionieren (→ Schritt 4).

### Variante B: 12V-Quelle am DC-Eingang (mit Hardware-Schlüsselschalter)

Das GeeekPi Board hat einen DC-Eingang (Klinke 3.5x1.35mm, innen +, außen -, 9-24V).
In diese Leitung kann ein Schlüsselschalter eingebaut werden - kein USB-C,
kein Handshake, einfach Plus und Minus unterbrechen.

```
12V-Quelle → Schlüsselschalter (2-polig) → DC-Klinke 3.5x1.35mm → GeeekPi Board → USB-C → Pi 5
```

- Always-ON-Switch am Board auf "Enabled" → Pi bootet wenn Schlüssel eingesteckt wird
- Schlüssel abziehen → Pi stromlos
- 12V-Quelle: z.B. KFZ-Ladegerät mit Akku, 3S-LiPo, oder ähnliches
- **Achtung:** DC-Eingang und USB-C-Eingang sind **nicht gleichzeitig** nutzbar!

### GeeekPi Board im Gehäuse

Das Board (52Pi EP-0225) hat Pi-5-Formfaktor, muss aber NICHT auf dem Pi sitzen.
Es wird lose ins Gehäuse gelegt oder verschraubt und per USB-C-Kabel mit dem
Pi verbunden. Bei selbst entworfenem Gehäuse (3D-Druck) ggf. Halterung anpassen.

> **Doku:** https://wiki.52pi.com/index.php?title=EP-0225

---

## Schritt 4: 433MHz testen (codesend.py, getcode.py)

433MHz Senden und Empfangen läuft unter Trixie nativ über gpiod v2 -
ohne pigpio, ohne wiringPi, ohne Arduino-Bridge. gpiod v2 ist unter
Trixie vorinstalliert, keine zusätzliche Installation nötig.

> **Hinweis:** `rpi-rf-gpiod` (pip) ist inkompatibel mit gpiod v2 - NICHT verwenden.

### 3.1 codesend.py installieren (433MHz Senden)

`codesend.py` liegt im Repo (nach Schritt 7). Für den Frühtest vor dem
Repo-Clone die Datei manuell anlegen oder vom alten System kopieren.

```bash
chmod +x /home/pi/pyroman/codesend.py
```

```bash
sudo ln -s /home/pi/pyroman/codesend.py /usr/local/bin/codesend
```

Benutzung:

```bash
codesend <code> [protocol] [pulselength]
```

> Defaults: protocol=1, pulselength=350

### 3.2 getcode.py installieren (433MHz Empfangen)

```bash
chmod +x /home/pi/pyroman/getcode.py
```

```bash
sudo ln -s /home/pi/pyroman/getcode.py /usr/local/bin/getcode
```

Benutzung:

```bash
getcode [sekunden]
```

> Default: 10 Sekunden. Ctrl+C zum vorzeitigen Abbrechen.

### 3.3 TX testen

Einen Funkkoffer einschalten, dann:

```bash
codesend 301
```

> Erwartung: Koffer 3, Kanal 1 empfängt.

### 3.4 RX testen

```bash
getcode 30
```

Handsender drücken.

> Erwartung: Code 7654321, Protocol 1, 24 Bit, ~352µs Delay.

Wenn beides funktioniert: Die Arduino-Bridge wird nicht mehr benötigt.

### 4.5 Fallback: wiringPi + 433Utils + Arduino (falls gpiod nicht verfügbar)

Falls gpiod v2 in einer zukünftigen Debian-Version nicht mehr funktioniert
(wie pigpio unter Trixie wegfiel), gibt es einen erprobten Fallback-Pfad.
TX und RX haben unterschiedliche Fallbacks:

- **TX (Senden):** C-Binary aus wiringPi + 433Utils ersetzt codesend.py
- **RX (Empfangen):** Arduino Serial Bridge ersetzt getcode.py + authorize.py

**Pin-Mapping (für beide Fallbacks relevant):**

| BCM | WiringPi | Physical | Funktion |
|-----|----------|----------|----------|
| 21  | 29       | 40       | TX (Sender) |
| 27  | 2        | 13       | RX (Empfänger) |

#### TX-Fallback: wiringPi + 433Utils (C-Binary ersetzt codesend.py)

wiringPi ist aktiv gepflegt (v3.18+, unterstützt Pi 5), auch wenn es aus den
Debian-Repos entfernt wurde. 433Utils enthält rc-switch als Git-Submodul -
rc-switch muss NICHT separat installiert werden.

```bash
# 1. wiringPi aus Source bauen
git clone https://github.com/WiringPi/WiringPi.git
cd WiringPi
./build

# 2. 433Utils klonen (rc-switch kommt als Submodul mit)
cd ~
git clone --recursive https://github.com/ninjablocks/433Utils.git
cd 433Utils/RPi_utils
```

In `codesend.cpp` den PIN anpassen (Default ist 0, wir brauchen 29):

```cpp
// codesend.cpp, Zeile mit PIN-Definition:
int PIN = 29;  // WiringPi 29 = BCM 21 = Physical 40 (unser TX-Pin)
```

```bash
# 3. Kompilieren und installieren
make
sudo cp codesend /usr/local/bin/codesend
```

**Drop-in-Ersatz:** `rf_sender.py` ruft `/usr/local/bin/codesend` als Subprocess auf.
Ob dahinter das Python-Script oder ein C-Binary steht, ist egal - selbe CLI-Schnittstelle
(`codesend <code> [protocol] [pulselength]`).

#### RX-Fallback: Arduino Serial Bridge (ersetzt getcode.py + authorize.py)

RX über GPIO hat auf dem Pi 5 unter Bookworm NIE funktioniert (pigpio inkompatibel
mit dem RP1-Chip). Der Fallback für RX ist die Arduino Serial Bridge - ein Arduino
mit eigenem 433MHz-Empfänger, der dekodierte Codes per Serial an den Pi weitergibt.

**Hardware:**

- Arduino Nano oder Uno
- 433MHz Empfänger an Arduino Pin D2 (Interrupt-fähig)
- Verbindung zum Pi per UART oder USB:

| Variante | Arduino | Pi | Port |
|----------|---------|-----|------|
| UART | TX → Pi GPIO 15 (RXD), GND → GND | `/dev/ttyAMA0` |
| USB | USB-Kabel | `/dev/ttyUSB0` |

**Firmware flashen:**

Die Arduino-Firmware liegt im Repo: `pyroman/arduino/433EmpfaengerBridgeFuerPi.ino`

1. Arduino IDE öffnen
2. RCSwitch-Library installieren (Library Manager → "rc-switch" suchen)
3. `433EmpfaengerBridgeFuerPi.ino` öffnen und auf Arduino flashen

Protokoll (9600 Baud):
```
Pi → Arduino:   "SCAN\n"       → Arduino beginnt zu scannen
Arduino → Pi:   "<code>\n"     → Empfangener 433MHz-Code als Dezimalzahl
Pi → Arduino:   "STOP\n"       → Arduino stoppt Scan
```

**Software zurückbauen:**

Die alte `authorize.py` mit Arduino-Support ist in der Git-Historie:

```bash
# Alte Version anzeigen (Commit 4433c56):
git show 4433c56:authorize.py
```

Relevante Funktion: `_authenticate_arduino()` - Serial 9600 Baud, 2s Reset-Wait,
SCAN-Befehl senden, empfangene Codes per Polling lesen.

Weitere Änderungen für den RX-Fallback:
- `config.json`: `"arduino_port": "/dev/ttyAMA0"` (oder `/dev/ttyUSB0`) wieder eintragen
- `config.py`: `get_arduino_port()` wiederherstellen (ebenfalls aus Git-Historie, Commit `4433c56`)
- `getcode.py`: Analog umbauen - statt gpiod Edge-Detection den Arduino per Serial ansprechen

#### GitHub-Links

| Projekt | URL | Zweck |
|---------|-----|-------|
| wiringPi | https://github.com/WiringPi/WiringPi | GPIO-Zugriff (C-Library) |
| 433Utils | https://github.com/ninjablocks/433Utils | codesend + RFSniffer (C-Binaries) |
| rc-switch | https://github.com/sui77/rc-switch | 433MHz-Protokoll (Submodul in 433Utils) |

---

## Schritt 5: Git + SSH einrichten

### 4.1 SSH-Key für GitHub

Falls noch kein SSH-Key vorhanden, entweder neu erzeugen oder vom
alten PyroTablet kopieren (Key ist dort bereits bei GitHub hinterlegt):

```bash
scp pi@172.23.56.154:~/.ssh/id_ed25519 ~/.ssh/id_ed25519_github
```

```bash
scp pi@172.23.56.154:~/.ssh/id_ed25519.pub ~/.ssh/id_ed25519_github.pub
```

```bash
chmod 600 ~/.ssh/id_ed25519_github
```

```bash
chmod 644 ~/.ssh/id_ed25519_github.pub
```

### 4.2 SSH-Config für GitHub

```bash
cat >> ~/.ssh/config << 'EOF'
Host github.com
    IdentityFile ~/.ssh/id_ed25519_github
    IdentitiesOnly yes
EOF
```

```bash
chmod 600 ~/.ssh/config
```

### 4.3 Git-User konfigurieren

```bash
git config --global user.name "Ralf Korell"
```

```bash
git config --global user.email "ralf@korell.org"
```

### 4.4 Verbindung testen

```bash
ssh -T git@github.com
```

> Erwartung: "Hi rkorell! You've successfully authenticated..."

---

## Schritt 6: Abhängigkeiten installieren

### 6.1 Referenz: Paketstatus unter Trixie (Stand Feb 2026)

| Paket | Quelle | Vorinstalliert | Benötigt für |
|-------|--------|---------------|-------------|
| Flask 3.1 | apt | ja | pyroman.py (Webserver) |
| Jinja2 3.1 | apt | ja | Templates (Flask-Abhängigkeit) |
| Werkzeug 3.1 | apt | ja | Flask-Abhängigkeit |
| gpiod 2.2 | apt | ja | 433MHz TX/RX (authorize.py, codesend.py, getcode.py) |
| requests 2.32 | apt | ja | wetter_api.py (Wunderground API) |
| flask-sock 0.7 | **pip** | nein | pyroman.py (WebSocket) |
| pigpio | — | **nicht verfügbar** | Ersetzt durch gpiod v2, NICHT nötig |

> **Achtung:** `flask-sock` ist NICHT als apt-Paket verfügbar. Nicht verwechseln
> mit `python3-flask-sockets` (anderes Paket) oder `python3-flask-socketio` (andere Library).

### 6.2 Abhängigkeiten prüfen

```bash
python3 -c "import flask; print('Flask OK')"
python3 -c "from flask_sock import Sock; print('flask-sock OK')"
python3 -c "import gpiod; print('gpiod OK')"
python3 -c "import requests; print('requests OK')"
```

### 6.3 Fehlende Pakete installieren

Zuerst prüfen, ob das Paket als System-Paket verfügbar ist:

```bash
apt-cache search <paketname>
```

Falls ja (bevorzugt):

```bash
sudo apt install python3-<paketname>
```

Falls nicht als System-Paket verfügbar, per pip:

```bash
pip install <paketname> --break-system-packages
```

> `--break-system-packages` ist seit Debian 12 nötig, weil pip die Installation
> in die System-Python-Umgebung sonst verweigert. System-Pakete (apt) sind
> immer vorzuziehen, da sie keine Konflikte verursachen.

### 6.4 flask-sock installieren (pip)

```bash
pip install flask-sock --break-system-packages
```

---

## Schritt 7: Repository klonen

### 7.1 Variante A: Leeres Verzeichnis

```bash
git clone git@github.com:rkorell/pyroman.git /home/pi/pyroman
```

### 7.2 Variante B: Verzeichnis existiert bereits (z.B. durch Vorab-Dateien)

Falls `/home/pi/pyroman` bereits existiert (codesend.py, getcode.py, CLAUDE.md
aus früheren Schritten), kann `git clone` dort nicht hin. Stattdessen:

```bash
cd /home/pi/pyroman
git init
git remote add origin git@github.com:rkorell/pyroman.git
git fetch origin
git checkout main
```

Lokale Dateien, die nicht im Repo sind (codesend.py, getcode.py, CLAUDE.md),
bleiben als untracked stehen und kollidieren nicht.

### 7.3 .gitignore prüfen

CLAUDE.md, .claude/ und config.json müssen in `.gitignore` stehen:

```bash
grep -E 'CLAUDE.md|\.claude|config.json' .gitignore
```

Falls nicht vorhanden, ergänzen:

```bash
cat >> .gitignore << 'EOF'
config.json
CLAUDE.md
.claude/
EOF
```

---

## Schritt 8: config.json und secrets.json vom alten System kopieren

Zwei Konfigurationsdateien sind NICHT im Git (Sicherheit!) und müssen
manuell vom bestehenden System kopiert werden:

| Datei | Inhalt | Benötigt für |
|-------|--------|-------------|
| config.json | Zündcodes, Auth-Code, Koffer-Definitionen | Gesamtes System |
| secrets.json | Wunderground API-Keys, Station-ID | Wetter-Seite (/wetter) |

```bash
scp pi@172.23.56.154:/home/pi/pyroman/config.json /home/pi/pyroman/
scp pi@172.23.56.154:/home/pi/pyroman/secrets.json /home/pi/pyroman/
```

Beide Dateien sind in .gitignore eingetragen.

Falls config.json historisch im Repo committed war, aus dem Tracking entfernen:

```bash
git rm --cached config.json
git commit -m "config.json aus Git-Tracking entfernen (Sicherheit)"
```

> Damit bleibt die Datei lokal erhalten, wird aber nicht mehr von git getrackt.
> .gitignore greift nur für untracked Dateien - einmal committed, muss man
> explizit `git rm --cached` ausführen.

---

## Schritt 9: Code portieren (rf_sender.py, authorize.py)

Erledigt (26.02.2026). Zusammenfassung:

- **authorize.py**: Komplett-Umbau auf gpiod v2 Edge-Detection.
  pigpio, Arduino Serial Bridge und Plattform-Erkennung entfernt.
  Neue `_authenticate_gpiod()` nutzt gleiche RX-Logik wie getcode.py.
- **rf_sender.py**: Ruft weiterhin `codesend` als Subprocess auf (war bereits kompatibel).
  Nur Fehlermeldung aktualisiert.
- **config.py**: RF-Sender/Empfänger Validierung und Getter entfernt,
  `get_arduino_port()` entfernt. RF-Parameter sind jetzt in codesend.py/getcode.py
  gekapselt (autarke Standalone-Tools).
- **config.json**: `rf_sender`-Block, `rf_empfaenger`-Block und `arduino_port` entfernt.
- **lib/_433.py**: Gelöscht (komplett durch gpiod v2 ersetzt). `lib/`-Verzeichnis entfernt.

---

## Checkliste: Externe Abhängigkeiten vor dem ersten Start

Alles was PyroMan zum Laufen braucht und NICHT automatisch da ist.

### Konfigurationsdateien (nicht im Git!)

| Datei | Benötigt von | Inhalt | Manuell kopieren |
|-------|-------------|--------|-----------------|
| `config.json` | config.py → gesamtes System | Koffer-Definitionen, Auth-Code, Zündcodes | ja (Schritt 8) |
| `secrets.json` | wetter_api.py → /wetter | Wunderground API-Keys, Station-ID | ja (Schritt 8) |
| `direktzuender_status.json` | direktzuender_wartung.py | Persistenter Verfügbarkeitsstatus | nein (wird automatisch erzeugt) |

### Python-Pakete

| Paket | Quelle | Vorinstalliert unter Trixie | Installieren mit |
|-------|--------|---------------------------|-----------------|
| Flask 3.1 | apt | ja | — |
| gpiod 2.2 | apt | ja | — |
| requests 2.32 | apt | ja | — |
| flask-sock 0.7 | **pip** | **nein** | `pip install flask-sock --break-system-packages` |

### Symlinks

| Symlink | Ziel | Benötigt von | Anlegen mit |
|---------|------|-------------|------------|
| `/usr/local/bin/codesend` | `/home/pi/pyroman/codesend.py` | rf_sender.py (subprocess) | `sudo ln -s /home/pi/pyroman/codesend.py /usr/local/bin/codesend` |
| `/usr/local/bin/getcode` | `/home/pi/pyroman/getcode.py` | Standalone-Tool | `sudo ln -s /home/pi/pyroman/getcode.py /usr/local/bin/getcode` |

### Hardware (GPIO)

| Komponente | GPIO (BCM) | Geräte-Pfad |
|-----------|-----------|------------|
| 433MHz TX-Sender | 21 | `/dev/gpiochip0` |
| 433MHz RX-Empfänger | 27 | `/dev/gpiochip0` |
| GeeekPi PD Power Board | — | USB-C in/out |

### Externe APIs (nur mit Internetzugang, nur für /wetter)

| URL | Benötigt von | Zweck |
|-----|-------------|-------|
| `https://api.weather.com/v2/pws/observations/current` | wetter_api.py | PWS aktuelles Wetter |
| `https://api.weather.com/v3/wx/forecast/hourly/1day` | wetter_api.py | Stündlicher Forecast |

> Ohne Internet (Feldbetrieb) funktioniert alles außer /wetter.

### Static Assets (im Git, müssen vorhanden sein)

| Datei | Referenziert von |
|-------|-----------------|
| `static/images/rkicon.png` | base.html (Favicon + Header-Logo) |
| `static/images/zuenderklein.png` | koffer.html (Zünd-Button) |
| `static/images/pyrologo.png` | koffer.html, direktzuender.html (gefeuert-Icon) |
| `static/images/fw_off.png` | direktzuender.html, wartung.html |
| `static/images/fw_n_a.png` | direktzuender.html, wartung.html |
| `static/sounds/explosion.mp3` | base.html → pyroman.js (Zünd-Sound) |
| `static/css/style.css` | base.html, error.html |
| `static/js/pyroman.js` | base.html |

### Netzwerk

| Port | Protokoll | Benötigt von | Zweck |
|------|-----------|-------------|-------|
| 5000 | TCP | pyroman.py | Flask-Webserver + WebSocket |

---

## Schritt 10: Testen

### 10.1 PyroMan starten

```bash
cd /home/pi/pyroman
```

```bash
python3 pyroman.py
```

### 10.2 Funktionstests

- Webinterface erreichbar über http://10.42.0.1:5000 (Hotspot)
- Webinterface erreichbar über http://DHCP-IP:5000 (KORELL Web)
- Autorisierung per Handsender
- Feuern eines Koffers
- Feuern eines Direktzünders
- WebSocket-Sync zwischen mehreren Clients
- Fire-Master Schalter

---

## Schritt 11: systemd-Service einrichten

```bash
sudo tee /etc/systemd/system/pyroman.service > /dev/null << 'EOF'
[Unit]
Description=PyroMan Pyrotechnik-Steuerung
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/pyroman
ExecStart=/usr/bin/python3 /home/pi/pyroman/pyroman.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

```bash
sudo systemctl daemon-reload
```

```bash
sudo systemctl enable pyroman
```

```bash
sudo systemctl start pyroman
```

```bash
sudo systemctl status pyroman
```

Reboot-Test:

```bash
sudo reboot
```

```bash
sudo systemctl status pyroman
```

---

## Schritt 12: Desktop einrichten (Hintergrund, Icons, Tools)

Das Prod-System hat Desktop-Verknüpfungen für Runterfahren und Zündkoffer-GUI.
Die Quelldateien liegen als Archiv in `/home/pi/pyroman_doc/desktop/`.
Box-Test ist als Tab in PyroMan integriert und braucht kein Desktop-Icon mehr.

### 12.1 Dateien an Prod-Positionen kopieren

```bash
# Desktop-Icons (Bilder)
cp ~/pyroman_doc/desktop/bomb.png ~/pyroman_doc/desktop/ShutDown.png ~/pyroman_doc/desktop/pyroman.ico ~/

# Hintergrundbild
cp ~/pyroman_doc/desktop/PyroTABLET.jpg ~/Pictures/

# Zündkoffer-GUI + Assets
mkdir -p ~/python
cp ~/pyroman_doc/desktop/Zuendkoffer.py ~/pyroman_doc/desktop/suitcase.png ~/pyroman_doc/desktop/button.png ~/pyroman_doc/desktop/buttonred.png ~/python/
```

### 12.2 Desktop-Verknüpfungen anlegen

```bash
cp ~/pyroman_doc/desktop/shutdown.desktop ~/pyroman_doc/desktop/Zuendkoffer.desktop ~/Desktop/
chmod +x ~/Desktop/*.desktop
```

### 12.3 Hintergrundbild setzen

Unter Trixie mit labwc/Wayland nutzt pcmanfm das Profil `default` mit Monitor-Name als Suffix.
Am einfachsten über die Desktop-Einstellungen setzen (Rechtsklick → Desktop-Einstellungen),
oder manuell:

```bash
mkdir -p ~/.config/pcmanfm/default
cat > ~/.config/pcmanfm/default/desktop-items-HDMI-A-1.conf << 'EOF'
[*]
desktop_bg=#D6D3DE
desktop_shadow=#D6D3DE
desktop_fg=#E8E8E8
desktop_font=Nunito Sans Light 12
wallpaper=/home/pi/Pictures/PyroTABLET.jpg
wallpaper_mode=crop
show_documents=0
show_trash=1
show_mounts=1
folder=/home/pi/Desktop
EOF
```

> **Hinweis:** Der Monitor-Name `HDMI-A-1` kann je nach Anschluss variieren.
> Die manuelle Methode über Desktop-Einstellungen ist zuverlässiger.

### 12.4 Desktop-Icons: Einzelklick und ohne Rückfrage

Damit Desktop-Icons per Einzelklick starten und keine "Executable Script"-Rückfrage kommt:

**Per Datei-Manager:** Bearbeiten → Einstellungen → Allgemein:
- [x] Open files with a single left-click
- [x] Don't ask options on launch executable files

**Alternativ per Config-Datei:**

```bash
mkdir -p ~/.config/libfm
cat > ~/.config/libfm/libfm.conf << 'EOF'
[config]
single_click=1
quick_exec=1
EOF
```

> Die Config-Datei wird beim nächsten Öffnen der Einstellungen um alle
> weiteren Defaults ergänzt (autogenerated by libfm).

### Dateien-Übersicht

| Datei | Ziel-Pfad | Zweck |
|-------|----------|-------|
| `PyroTABLET.jpg` | `~/Pictures/` | Desktop-Hintergrundbild |
| `shutdown.desktop` + `ShutDown.png` | `~/Desktop/` + `~/` | Runterfahren-Icon |
| `Zuendkoffer.desktop` + `bomb.png` | `~/Desktop/` + `~/` | Zündkoffer-GUI Verknüpfung |
| `Zuendkoffer.py` + `suitcase.png` + `button.png` + `buttonred.png` | `~/python/` | Zündkoffer tkinter-GUI |
| `pyroman.ico` | `~/` | PyroMan-Icon |

> Zuendkoffer.py ruft `sudo codesend` auf. Der Symlink `/usr/local/bin/codesend`
> muss vorhanden sein (Schritt 4).

> **Box-Test:** Die Funktionalität von BoxTest.py ist als Tab "Box-Test/Config" in PyroMan
> integriert (Route `/boxtest`). Ein Desktop-Icon ist nicht mehr nötig.
> Analyse: `pyroman_doc/BoxTest_Analyse.md`, Arduino-Quelldateien: `pyroman_doc/arduino/`

### 12.5 Browser-Startseite einrichten

Im Standard-Browser (Chromium) als Startseite setzen:
- Einstellungen → Beim Start → Bestimmte Seite öffnen → `http://localhost:5000`

---

## Schritt 13: Backup einrichten

PyroMan in das zentrale Backup-Konzept einbinden. Das Backup wird vom
Backup-Server auf dem Webserver (IP .192) initiiert und gesteuert.

---

## Optional: Floorplan (visuelle Zündansicht)

Das alte FHEM-System hatte einen "Floorplan": ein Hintergrundbild mit Fotos der
physischen Böller, auf dem Koffer/Kanal-Zuordnungen und Zündbuttons als klickbare
Elemente positioniert waren. Diese Ansicht kann als zusätzliche Route `/floorplan`
in PyroMan nachgebaut werden.

### Konzept

- Hintergrundbild (`fp_boeller.png`) mit absolut positionierten HTML-Elementen darauf
- Pro Zündposition: Koffer-Wähler (1-4), Kanal-Wähler (1-8), Zündbutton
- Gruppenzündung (G1: Kanäle 1-4, G2: Kanäle 5-8)
- Steuer-Schalter: Änderungen erlauben, Feuern erlauben, Reset
- Zustand über WebSocket synchronisiert (wie der Rest von PyroMan)

### Vorhandenes Material

Grafiken und FHEM-Referenz-Config liegen als Archiv in `/home/pi/pyroman_doc/floorplan/`.
Bei Implementierung müssen die Grafiken nach `pyroman/static/images/floorplan/` kopiert werden.

| Datei | Verwendung |
|-------|------------|
| `fp_boeller.png` | Hintergrundbild (804 KB, Fotos der Böller) |
| `zuenderklein.png` | Zünder bereit (off) |
| `pyrologo.png` | Zünder gezündet (on) |
| `fw_off.png` | Direktzünder aus |
| `fw_on.png` | Direktzünder gezündet |
| `fw_n_a.png` | Direktzünder deaktiviert |
| `black_btn2_0..9.png` | Zahlen-Buttons für Koffer/Kanal-Wähler |
| `kanonenschuss.wav` | Sound-Effekt bei Zündung |
| `fhem_floorplan_config.txt` | FHEM-Originalkonfiguration als Referenz |

### Positionen der Elemente (aus FHEM)

Die Pixel-Positionen auf dem Hintergrundbild sind in `fhem_floorplan_config.txt`
dokumentiert (Format: `x,y` in Pixeln vom linken oberen Rand).
