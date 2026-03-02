/*
 * floorplan.js - PyroMan Floorplan JavaScript
 *
 * Zündbuttons auf Böller-Hintergrundbild, Konfig-Modus,
 * Kompaktes Config-Popup am Klick-Ort.
 * Steuer-Icons als Click-Areas direkt auf dem Bild.
 *
 * (c) Dr. Ralf Korell, 2025/26
 *
 * Erstellt: 02.03.2026, 18:00
 * Modified: 02.03.2026, 20:00 - Click-Areas, Label-Format
 * Modified: 02.03.2026, 21:00 - Kompaktes Config-Popup am Klick-Ort
 * Modified: 02.03.2026, 21:20 - Auth-Check für Config-Mode und Steuer-Icons
 * Modified: 02.03.2026, 22:00 - Fired-State aus Koffer-State, channel_fired/reset Handler
 */

// =============================================================================
// State
// =============================================================================

const Floorplan = {
    configMode: false,
    positions: {},
    fired: {},
    editingPos: null,
    popup: null,
    kanonenschussSound: null
};

const FIXED_KANAL = { 'G1': 9, 'G2': 10 };

// =============================================================================
// Init
// =============================================================================

document.addEventListener('DOMContentLoaded', function() {
    initFloorplanSound();
    createConfigPopup();
    initFloorplanEvents();
    initFloorplanWsHandlers();
});

function initFloorplanSound() {
    const soundSrc = document.body.dataset.kanonenschussSound;
    Floorplan.kanonenschussSound = new Audio(soundSrc || '/static/sounds/kanonenschuss.wav');
}

function playKanonenschuss() {
    if (PyroMan.audioEnabled && Floorplan.kanonenschussSound) {
        Floorplan.kanonenschussSound.currentTime = 0;
        Floorplan.kanonenschussSound.play().catch(() => {});
    }
}

// =============================================================================
// Config Popup (dynamisch erzeugt, lebt im floorplan-container)
// =============================================================================

function createConfigPopup() {
    const container = document.getElementById('floorplan-container');
    const popup = document.createElement('div');
    popup.className = 'fp-config-popup';
    popup.id = 'fp-config-popup';
    popup.innerHTML = `
        <div class="fp-config-popup-title" id="fp-popup-title">Pos 1</div>
        <div class="fp-picker-row">
            <span class="fp-picker-label">K</span>
            <button class="fp-seg-btn" data-type="koffer" data-val="1">1</button>
            <button class="fp-seg-btn" data-type="koffer" data-val="2">2</button>
            <button class="fp-seg-btn" data-type="koffer" data-val="3">3</button>
            <button class="fp-seg-btn" data-type="koffer" data-val="4">4</button>
        </div>
        <div class="fp-picker-row" id="fp-popup-kanal-row">
            <span class="fp-picker-label">Ch</span>
            <button class="fp-seg-btn" data-type="kanal" data-val="1">1</button>
            <button class="fp-seg-btn" data-type="kanal" data-val="2">2</button>
            <button class="fp-seg-btn" data-type="kanal" data-val="3">3</button>
            <button class="fp-seg-btn" data-type="kanal" data-val="4">4</button>
            <button class="fp-seg-btn" data-type="kanal" data-val="5">5</button>
            <button class="fp-seg-btn" data-type="kanal" data-val="6">6</button>
            <button class="fp-seg-btn" data-type="kanal" data-val="7">7</button>
            <button class="fp-seg-btn" data-type="kanal" data-val="8">8</button>
        </div>
        <div class="fp-config-fixed" id="fp-popup-fixed" style="display:none">Kanal fest: <strong id="fp-popup-fixed-val"></strong></div>
    `;
    container.appendChild(popup);
    Floorplan.popup = popup;

    // Klick auf Picker-Buttons
    popup.querySelectorAll('.fp-seg-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            if (!Floorplan.editingPos) return;
            const type = this.dataset.type;
            const val = parseInt(this.dataset.val);
            const pos = Floorplan.positions[Floorplan.editingPos] || {};

            if (type === 'koffer') {
                sendMessage('floorplan_set_position', {
                    pos_id: Floorplan.editingPos,
                    koffer: val,
                    kanal: pos.kanal || 1
                });
            } else {
                sendMessage('floorplan_set_position', {
                    pos_id: Floorplan.editingPos,
                    koffer: pos.koffer || 2,
                    kanal: val
                });
            }
        });
    });

    // Klick außerhalb schließt
    document.addEventListener('click', function(e) {
        if (Floorplan.popup && Floorplan.popup.classList.contains('visible')) {
            if (!Floorplan.popup.contains(e.target)) {
                closeConfigPopup();
            }
        }
    });
}

function openConfigPopup(posId, clickX, clickY) {
    Floorplan.editingPos = posId;
    const popup = Floorplan.popup;

    // Titel
    const popupTitle = { 'G1': 'Gruppe 1', 'G2': 'Gruppe 2' };
    document.getElementById('fp-popup-title').textContent = popupTitle[posId] || ('Pos ' + posId);

    // Gruppenfeuer: Kanal-Row verstecken
    const kanalRow = document.getElementById('fp-popup-kanal-row');
    const fixedInfo = document.getElementById('fp-popup-fixed');
    if (FIXED_KANAL[posId] !== undefined) {
        kanalRow.style.display = 'none';
        fixedInfo.style.display = 'block';
        document.getElementById('fp-popup-fixed-val').textContent = FIXED_KANAL[posId];
    } else {
        kanalRow.style.display = 'flex';
        fixedInfo.style.display = 'none';
    }

    updatePopupSelection();

    // Position: oberhalb des Klick-Orts (verhindert Scroll-Probleme bei unteren Positionen)
    popup.style.left = (clickX + 10) + 'px';
    popup.style.top = '0px';
    popup.classList.add('visible');
    const popupHeight = popup.offsetHeight;
    popup.style.top = (clickY - popupHeight - 10) + 'px';
}

function closeConfigPopup() {
    Floorplan.editingPos = null;
    if (Floorplan.popup) {
        Floorplan.popup.classList.remove('visible');
    }
}

function updatePopupSelection() {
    if (!Floorplan.editingPos || !Floorplan.popup) return;
    const pos = Floorplan.positions[Floorplan.editingPos];
    if (!pos) return;

    Floorplan.popup.querySelectorAll('.fp-seg-btn[data-type="koffer"]').forEach(btn => {
        btn.classList.toggle('active', parseInt(btn.dataset.val) === pos.koffer);
    });
    Floorplan.popup.querySelectorAll('.fp-seg-btn[data-type="kanal"]').forEach(btn => {
        btn.classList.toggle('active', parseInt(btn.dataset.val) === pos.kanal);
    });
}

// =============================================================================
// Event-Handler
// =============================================================================

function initFloorplanEvents() {
    // Zündbuttons
    document.querySelectorAll('.fire-position').forEach(pos => {
        pos.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const posId = this.dataset.pos;

            if (Floorplan.configMode) {
                if (!PyroMan.authorized || !PyroMan.fireEnabled) return;
                // Klick-Koordinaten relativ zum Container
                const container = document.getElementById('floorplan-container');
                const rect = container.getBoundingClientRect();
                const scrollEl = container.parentElement;
                const clickX = e.clientX - rect.left + scrollEl.scrollLeft;
                const clickY = e.clientY - rect.top + scrollEl.scrollTop;
                openConfigPopup(posId, clickX, clickY);
            } else {
                fireFloorplanPosition(posId, this);
            }
        });
    });

    // Steuer-Icons (Click-Areas)
    document.querySelectorAll('.fp-control-area').forEach(area => {
        area.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const action = this.dataset.action;

            // Alle Steuer-Aktionen nur mit Berechtigung
            if (!PyroMan.authorized || !PyroMan.fireEnabled) return;

            switch (action) {
                case 'reset_fired':
                    sendMessage('floorplan_reset_fired', {});
                    break;
                case 'reset_defaults':
                    sendMessage('floorplan_reset_defaults', {});
                    break;
                case 'config_mode':
                    Floorplan.configMode = !Floorplan.configMode;
                    this.classList.toggle('active', Floorplan.configMode);
                    updateFloorplanMode();
                    if (!Floorplan.configMode) closeConfigPopup();
                    break;
            }
        });
    });
}

// =============================================================================
// WS Message Handler
// =============================================================================

function initFloorplanWsHandlers() {
    const originalHandler = handleServerMessage;
    handleServerMessage = function(data) {
        switch (data.type) {
            case 'floorplan_fired':
                handleFloorplanFired(data);
                return;
            case 'floorplan_position_changed':
                handleFloorplanPositionChanged(data);
                return;
            case 'floorplan_state':
                handleFloorplanState(data);
                return;
            case 'channel_fired':
                if (data.target_type === 'koffer') {
                    updateFloorplanFromKofferEvent(data.koffer_id, data.kanal_nr, true);
                }
                break;
            case 'channel_reset':
                if (data.target_type === 'koffer') {
                    updateFloorplanFromKofferEvent(data.koffer_id, data.kanal_nr, false);
                }
                break;
            case 'state_update':
                if (data.floorplan) {
                    Floorplan.positions = data.floorplan.positions || {};
                    Floorplan.fired = data.floorplan.fired || {};
                    updateFloorplanUI();
                }
                break;
        }
        originalHandler(data);
    };
}

function handleFloorplanFired(data) {
    Floorplan.fired[data.pos_id] = true;
    updateFirePosition(data.pos_id);
    playKanonenschuss();
}

function handleFloorplanPositionChanged(data) {
    Floorplan.positions[data.pos_id] = {
        koffer: data.koffer,
        kanal: data.kanal
    };
    updateFirePosition(data.pos_id);
    if (Floorplan.editingPos === data.pos_id) {
        updatePopupSelection();
    }
}

function handleFloorplanState(data) {
    if (data.floorplan) {
        Floorplan.positions = data.floorplan.positions || {};
        Floorplan.fired = data.floorplan.fired || {};
        updateFloorplanUI();
    }
}

function updateFloorplanFromKofferEvent(kofferId, kanalNr, fired) {
    // Findet Floorplan-Positionen die diesem Koffer/Kanal zugeordnet sind
    for (const [posId, pos] of Object.entries(Floorplan.positions)) {
        if (pos.koffer === kofferId && pos.kanal === kanalNr) {
            Floorplan.fired[posId] = fired;
            updateFirePosition(posId);
        }
    }
}

// =============================================================================
// Fire
// =============================================================================

function fireFloorplanPosition(posId, element) {
    // Berechtigung prüfen BEVOR UI geändert wird
    if (!PyroMan.authorized || !PyroMan.fireEnabled) return;
    if (element.classList.contains('fired') || element.classList.contains('disabled')) return;

    // Erst jetzt UI aktualisieren (Double-Fire-Schutz)
    element.classList.add('fired', 'disabled');
    const img = element.querySelector('.fire-btn');
    if (img) img.src = '/static/images/pyrologo.png';

    sendMessage('floorplan_fire', { pos_id: posId });
}

// =============================================================================
// UI Updates
// =============================================================================

function updateFloorplanUI() {
    document.querySelectorAll('.fire-position').forEach(el => {
        updateFirePosition(el.dataset.pos);
    });
    updateFloorplanMode();
}

function updateFirePosition(posId) {
    const el = document.querySelector(`.fire-position[data-pos="${posId}"]`);
    if (!el) return;

    const pos = Floorplan.positions[posId];
    const fired = Floorplan.fired[posId] || false;

    const img = el.querySelector('.fire-btn');
    if (img) {
        img.src = fired ? '/static/images/pyrologo.png' : '/static/images/zuenderklein.png';
    }

    el.classList.toggle('fired', fired);
    el.classList.toggle('disabled', fired);

    const label = el.querySelector('.pos-label');
    if (label && pos) {
        const isGroup = FIXED_KANAL[posId] !== undefined;
        const groupName = { 'G1': 'Gruppe 1', 'G2': 'Gruppe 2' };
        label.textContent = isGroup
            ? groupName[posId]
            : `K${pos.koffer} / Ch${pos.kanal}`;
    }
}

function updateFloorplanMode() {
    const container = document.getElementById('floorplan-container');
    if (!container) return;

    if (Floorplan.configMode) {
        container.classList.add('config-mode');
        container.classList.remove('fire-mode');
    } else {
        container.classList.remove('config-mode');
        container.classList.add('fire-mode');
    }
}
