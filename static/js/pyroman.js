/*
 * pyroman.js - PyroMan Frontend JavaScript
 * 
 * WebSocket-Client, UI-Logik, Event-Handler
 * 
 * (c) Dr. Ralf Korell, 2025/26
 * 
 * Erstellt: 07.12.2025, 21:00
 * Modified: 08.12.2025, 12:35 - Bugfix: Gefeuerte Kanäle werden jetzt gesperrt (disabled)
 * Modified: 08.12.2025, 15:45 - Fire-Master Button, Icon-Wechsel bei Abfeuern, vertikale Listen
 * Modified: 08.12.2025, 17:00 - Auth-Flow UI-Updates (Elemente ein-/ausblenden)
 */

// =============================================================================
// State
// =============================================================================

const PyroMan = {
    socket: null,
    authorized: false,
    fireEnabled: false,
    currentKoffer: 1,
    kofferStates: {},
    direktzuenderStates: {},
    audioEnabled: true,
    explosionSound: null
};

// =============================================================================
// WebSocket
// =============================================================================

function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    console.log('[WS] Connecting to', wsUrl);
    
    PyroMan.socket = new WebSocket(wsUrl);
    
    PyroMan.socket.onopen = function() {
        console.log('[WS] Connected');
        updateConnectionStatus(true);
    };
    
    PyroMan.socket.onclose = function() {
        console.log('[WS] Disconnected');
        updateConnectionStatus(false);
        // Reconnect nach 3 Sekunden
        setTimeout(initWebSocket, 3000);
    };
    
    PyroMan.socket.onerror = function(error) {
        console.error('[WS] Error:', error);
    };
    
    PyroMan.socket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        handleServerMessage(data);
    };
}

function sendMessage(type, payload) {
    if (PyroMan.socket && PyroMan.socket.readyState === WebSocket.OPEN) {
        PyroMan.socket.send(JSON.stringify({ type, ...payload }));
    } else {
        console.warn('[WS] Not connected');
    }
}

// =============================================================================
// Server Message Handler
// =============================================================================

function handleServerMessage(data) {
    console.log('[WS] Received:', data.type, data);
    
    switch (data.type) {
        case 'state_update':
            handleStateUpdate(data);
            break;
        case 'channel_fired':
            handleChannelFired(data);
            break;
        case 'channel_reset':
            handleChannelReset(data);
            break;
        case 'fire_enabled_changed':
            handleFireEnabledChanged(data);
            break;
        case 'auth_waiting':
            showAuthModal();
            break;
        case 'auth_success':
            handleAuthSuccess();
            break;
        case 'auth_timeout':
            handleAuthTimeout();
            break;
        case 'error':
            showError(data.message);
            break;
    }
}

function handleStateUpdate(data) {
    PyroMan.authorized = data.authorized;
    PyroMan.fireEnabled = data.fire_enabled;
    PyroMan.kofferStates = data.koffer_states || {};
    PyroMan.direktzuenderStates = data.direktzuender_states || {};
    
    updateUI();
}

function handleChannelFired(data) {
    if (data.target_type === 'koffer') {
        const key = `${data.koffer_id}-${data.kanal_nr}`;
        PyroMan.kofferStates[key] = true;
    } else if (data.target_type === 'direktzuender') {
        PyroMan.direktzuenderStates[data.nr] = true;
    }
    
    updateFireItems();
    playExplosionSound();
}

function handleChannelReset(data) {
    if (data.target_type === 'koffer') {
        const key = `${data.koffer_id}-${data.kanal_nr}`;
        PyroMan.kofferStates[key] = false;
    } else if (data.target_type === 'direktzuender') {
        PyroMan.direktzuenderStates[data.nr] = false;
    }
    
    updateFireItems();
}

function handleFireEnabledChanged(data) {
    PyroMan.fireEnabled = data.enabled;
    updateFireMasterButton();
    updateFireItems();
}

function handleAuthSuccess() {
    PyroMan.authorized = true;
    hideAuthModal();
    updateAuthStatus();
    showToast('Autorisierung erfolgreich', 'success');
}

function handleAuthTimeout() {
    hideAuthModal();
    showToast('Autorisierung fehlgeschlagen', 'danger');
}

// =============================================================================
// UI Updates
// =============================================================================

function updateUI() {
    updateAuthStatus();
    updateFireMasterButton();
    updateFireItems();
}

function updateConnectionStatus(connected) {
    const indicator = document.getElementById('connection-status');
    if (indicator) {
        indicator.classList.toggle('connected', connected);
        indicator.classList.toggle('disconnected', !connected);
    }
}

function updateAuthStatus() {
    const authSection = document.getElementById('auth-section');
    const mainNav = document.getElementById('main-nav');
    const controlsSection = document.getElementById('controls-section');
    
    if (PyroMan.authorized) {
        // Autorisiert: Auth-Sektion ausblenden, Nav + Controls einblenden
        if (authSection) authSection.classList.add('hidden');
        if (mainNav) mainNav.classList.remove('hidden');
        if (controlsSection) controlsSection.classList.remove('hidden');
    } else {
        // Nicht autorisiert: Auth-Sektion einblenden, Nav + Controls ausblenden
        if (authSection) authSection.classList.remove('hidden');
        if (mainNav) mainNav.classList.add('hidden');
        if (controlsSection) controlsSection.classList.add('hidden');
    }
}

function updateFireMasterButton() {
    const btn = document.getElementById('fire-master-btn');
    if (!btn) return;
    
    const icon = btn.querySelector('.fire-master-icon');
    const text = btn.querySelector('.fire-master-text');
    
    if (PyroMan.fireEnabled) {
        btn.classList.remove('inactive');
        btn.classList.add('active');
        if (icon) icon.textContent = '🔥';
        if (text) text.textContent = 'Feuer freigegeben';
    } else {
        btn.classList.remove('active');
        btn.classList.add('inactive');
        if (icon) icon.textContent = '🔒';
        if (text) text.textContent = 'Feuer gesperrt';
    }
}

function updateFireItems() {
    // Koffer Items
    document.querySelectorAll('.fire-item[data-koffer]').forEach(item => {
        const kofferId = parseInt(item.dataset.koffer);
        const kanalNr = parseInt(item.dataset.kanal);
        const key = `${kofferId}-${kanalNr}`;
        const fired = PyroMan.kofferStates[key] || false;
        
        updateFireItemState(item, fired, true);
    });
    
    // Direktzünder Items
    document.querySelectorAll('.fire-item[data-direktzuender]').forEach(item => {
        const nr = parseInt(item.dataset.direktzuender);
        const fired = PyroMan.direktzuenderStates[nr] || false;
        const available = item.dataset.available !== 'false';
        
        if (!available) {
            item.classList.remove('ready', 'fired');
            item.classList.add('unavailable');
            updateItemDisabled(item, true);
        } else {
            item.classList.remove('unavailable');
            updateFireItemState(item, fired, available);
        }
    });
}

function updateFireItemState(item, fired, available) {
    const iconReady = item.querySelector('.icon-ready');
    const iconFired = item.querySelector('.icon-fired');
    const status = item.querySelector('.fire-item-status');
    
    if (fired) {
        item.classList.remove('ready');
        item.classList.add('fired');
        if (iconReady) iconReady.classList.add('hidden');
        if (iconFired) iconFired.classList.remove('hidden');
        if (status) status.textContent = 'Abgefeuert';
    } else {
        item.classList.remove('fired');
        item.classList.add('ready');
        if (iconReady) iconReady.classList.remove('hidden');
        if (iconFired) iconFired.classList.add('hidden');
        if (status) status.textContent = 'Bereit';
    }
    
    // Disabled wenn: nicht autorisiert, Feuer gesperrt, oder bereits gefeuert
    const disabled = !PyroMan.fireEnabled || !PyroMan.authorized || fired || !available;
    updateItemDisabled(item, disabled);
}

function updateItemDisabled(item, disabled) {
    if (disabled) {
        item.classList.add('disabled');
    } else {
        item.classList.remove('disabled');
    }
}

// =============================================================================
// Actions
// =============================================================================

function fireKoffer(kofferId, kanalNr) {
    if (!PyroMan.authorized || !PyroMan.fireEnabled) {
        console.warn('Not authorized or fire disabled');
        return;
    }
    
    console.log(`[Action] Fire Koffer ${kofferId}, Kanal ${kanalNr}`);
    sendMessage('fire', {
        target_type: 'koffer',
        koffer_id: kofferId,
        kanal_nr: kanalNr
    });
}

function fireDirektzuender(nr) {
    if (!PyroMan.authorized || !PyroMan.fireEnabled) {
        console.warn('Not authorized or fire disabled');
        return;
    }
    
    console.log(`[Action] Fire Direktzünder ${nr}`);
    sendMessage('fire', {
        target_type: 'direktzuender',
        nr: nr
    });
}

function resetChannel(targetType, kofferId, kanalNr, nr) {
    if (targetType === 'koffer') {
        sendMessage('reset', { target_type: 'koffer', koffer_id: kofferId, kanal_nr: kanalNr });
    } else {
        sendMessage('reset', { target_type: 'direktzuender', nr: nr });
    }
}

function resetAll() {
    if (confirm('Wirklich ALLE Kanäle zurücksetzen?')) {
        sendMessage('reset_all', {});
    }
}

function toggleFireEnabled() {
    sendMessage('set_fire_enabled', { enabled: !PyroMan.fireEnabled });
}

function startAuth() {
    sendMessage('auth_start', {});
}

function selectKoffer(kofferId) {
    PyroMan.currentKoffer = kofferId;
    // Seite neu laden mit anderem Koffer
    window.location.href = `/koffer?id=${kofferId}`;
}

// =============================================================================
// Auth Modal
// =============================================================================

function showAuthModal() {
    const overlay = document.getElementById('auth-overlay');
    if (overlay) {
        overlay.classList.add('visible');
        // Focus auf Input
        const input = overlay.querySelector('.auth-input');
        if (input) input.focus();
    }
}

function hideAuthModal() {
    const overlay = document.getElementById('auth-overlay');
    if (overlay) {
        overlay.classList.remove('visible');
    }
}

// =============================================================================
// Audio
// =============================================================================

function initAudio() {
    const soundPath = document.body.dataset.explosionSound;
    if (soundPath) {
        PyroMan.explosionSound = new Audio(soundPath);
        PyroMan.explosionSound.volume = 0.5;
    }
    
    // Audio-Toggle aus localStorage laden
    const stored = localStorage.getItem('pyroman-audio');
    PyroMan.audioEnabled = stored !== 'false';
    updateAudioToggle();
}

function playExplosionSound() {
    if (PyroMan.audioEnabled && PyroMan.explosionSound) {
        PyroMan.explosionSound.currentTime = 0;
        PyroMan.explosionSound.play().catch(e => console.warn('Audio play failed:', e));
    }
}

function toggleAudio() {
    PyroMan.audioEnabled = !PyroMan.audioEnabled;
    localStorage.setItem('pyroman-audio', PyroMan.audioEnabled);
    updateAudioToggle();
}

function updateAudioToggle() {
    const btn = document.getElementById('audio-toggle');
    if (btn) {
        btn.textContent = PyroMan.audioEnabled ? '🔊' : '🔇';
    }
}

// =============================================================================
// Theme
// =============================================================================

function initTheme() {
    const stored = localStorage.getItem('pyroman-theme');
    if (stored === 'light') {
        document.documentElement.setAttribute('data-theme', 'light');
    }
    updateThemeToggle();
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const newTheme = current === 'light' ? 'dark' : 'light';
    
    document.documentElement.setAttribute('data-theme', newTheme === 'light' ? 'light' : '');
    localStorage.setItem('pyroman-theme', newTheme);
    updateThemeToggle();
}

function updateThemeToggle() {
    const btn = document.getElementById('theme-toggle');
    if (btn) {
        const isLight = document.documentElement.getAttribute('data-theme') === 'light';
        btn.textContent = isLight ? '🌙' : '☀️';
    }
}

// =============================================================================
// Toast Notifications
// =============================================================================

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    // Auto-remove nach 3 Sekunden
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
    return container;
}

function showError(message) {
    showToast(message, 'danger');
}

// =============================================================================
// Wartung
// =============================================================================

function toggleDirektzuenderAvailable(nr) {
    const item = document.querySelector(`.wartung-item[data-nr="${nr}"]`);
    const toggle = item?.querySelector('.toggle');
    
    if (toggle) {
        const newState = !toggle.classList.contains('active');
        
        // API-Call
        fetch(`/api/direktzuender/${nr}/available`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ available: newState })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                toggle.classList.toggle('active', newState);
                item.classList.toggle('disabled', !newState);
                
                // Toggle-Label aktualisieren
                const label = item.querySelector('.toggle-label');
                if (label) {
                    label.textContent = newState ? 'Aktiv' : 'Inaktiv';
                }
                
                showToast(`Direktzünder ${nr}: ${newState ? 'aktiviert' : 'deaktiviert'}`, 'success');
            } else {
                showToast('Fehler beim Speichern', 'danger');
            }
        })
        .catch(err => {
            console.error('Error:', err);
            showToast('Fehler beim Speichern', 'danger');
        });
    }
}

// =============================================================================
// Event Listeners
// =============================================================================

function initEventListeners() {
    // Fire Items (Koffer)
    document.querySelectorAll('.fire-item[data-koffer]').forEach(item => {
        item.addEventListener('click', () => {
            if (item.classList.contains('disabled')) return;
            const kofferId = parseInt(item.dataset.koffer);
            const kanalNr = parseInt(item.dataset.kanal);
            fireKoffer(kofferId, kanalNr);
        });
    });
    
    // Fire Items (Direktzünder)
    document.querySelectorAll('.fire-item[data-direktzuender]').forEach(item => {
        item.addEventListener('click', () => {
            if (item.classList.contains('disabled') || item.classList.contains('unavailable')) return;
            const nr = parseInt(item.dataset.direktzuender);
            fireDirektzuender(nr);
        });
    });
    
    // Fire Master Button
    const fireMasterBtn = document.getElementById('fire-master-btn');
    if (fireMasterBtn) {
        fireMasterBtn.addEventListener('click', toggleFireEnabled);
    }
    
    // Login Button
    const loginBtn = document.getElementById('login-btn');
    if (loginBtn) {
        loginBtn.addEventListener('click', startAuth);
    }
    
    // Reset All Button
    const resetAllBtn = document.getElementById('reset-all-btn');
    if (resetAllBtn) {
        resetAllBtn.addEventListener('click', resetAll);
    }
    
    // Theme Toggle
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }
    
    // Audio Toggle
    const audioToggle = document.getElementById('audio-toggle');
    if (audioToggle) {
        audioToggle.addEventListener('click', toggleAudio);
    }
    
    // Koffer Dropdown
    const kofferDropdown = document.getElementById('koffer-select');
    if (kofferDropdown) {
        kofferDropdown.addEventListener('change', (e) => {
            selectKoffer(parseInt(e.target.value));
        });
    }
    
    // Wartung Toggles
    document.querySelectorAll('.wartung-item .toggle').forEach(toggle => {
        toggle.addEventListener('click', () => {
            const nr = parseInt(toggle.closest('.wartung-item').dataset.nr);
            toggleDirektzuenderAvailable(nr);
        });
    });
    
    // Auth Modal Close (Escape)
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            hideAuthModal();
        }
    });
}

// =============================================================================
// Init
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('[PyroMan] Initializing...');
    
    initTheme();
    initAudio();
    initEventListeners();
    initWebSocket();
    
    console.log('[PyroMan] Ready');
});
