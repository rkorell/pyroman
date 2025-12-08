/*
 * pyroman.js - PyroMan Frontend JavaScript
 * 
 * WebSocket-Client, UI-Logik, Event-Handler
 * 
 * (c) Dr. Ralf Korell, 2025/26
 * 
 * Erstellt: 07.12.2025, 21:00
 * Modified: 08.12.2025, 12:35 - Bugfix: Gefeuerte Kanäle werden jetzt gesperrt (disabled)
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
    
    updateFireButtons();
    playExplosionSound();
}

function handleChannelReset(data) {
    if (data.target_type === 'koffer') {
        const key = `${data.koffer_id}-${data.kanal_nr}`;
        PyroMan.kofferStates[key] = false;
    } else if (data.target_type === 'direktzuender') {
        PyroMan.direktzuenderStates[data.nr] = false;
    }
    
    updateFireButtons();
}

function handleFireEnabledChanged(data) {
    PyroMan.fireEnabled = data.enabled;
    updateFireMasterSwitch();
    updateFireButtons();
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
    updateFireMasterSwitch();
    updateFireButtons();
}

function updateConnectionStatus(connected) {
    const indicator = document.getElementById('connection-status');
    if (indicator) {
        indicator.classList.toggle('connected', connected);
        indicator.classList.toggle('disconnected', !connected);
    }
}

function updateAuthStatus() {
    const banner = document.getElementById('auth-banner');
    const loginBtn = document.getElementById('login-btn');
    
    if (banner) {
        if (PyroMan.authorized) {
            banner.className = 'status-banner success';
            banner.textContent = '🔓 System autorisiert';
        } else {
            banner.className = 'status-banner danger';
            banner.textContent = '🔒 Nicht autorisiert - Bitte anmelden';
        }
    }
    
    if (loginBtn) {
        loginBtn.classList.toggle('hidden', PyroMan.authorized);
    }
}

function updateFireMasterSwitch() {
    const toggle = document.getElementById('fire-master-toggle');
    const container = document.getElementById('fire-master');
    
    if (toggle) {
        toggle.classList.toggle('active', PyroMan.fireEnabled);
    }
    
    if (container) {
        container.classList.toggle('active', PyroMan.fireEnabled);
        container.classList.toggle('inactive', !PyroMan.fireEnabled);
    }
}

function updateFireButtons() {
    // Koffer Buttons
    document.querySelectorAll('.fire-btn[data-koffer]').forEach(btn => {
        const kofferId = parseInt(btn.dataset.koffer);
        const kanalNr = parseInt(btn.dataset.kanal);
        const key = `${kofferId}-${kanalNr}`;
        const fired = PyroMan.kofferStates[key] || false;
        
        btn.classList.toggle('ready', !fired);
        btn.classList.toggle('fired', fired);
        btn.disabled = !PyroMan.fireEnabled || !PyroMan.authorized || fired;
    });
    
    // Direktzünder Buttons
    document.querySelectorAll('.fire-btn[data-direktzuender]').forEach(btn => {
        const nr = parseInt(btn.dataset.direktzuender);
        const fired = PyroMan.direktzuenderStates[nr] || false;
        const available = btn.dataset.available !== 'false';
        
        btn.classList.remove('ready', 'fired', 'unavailable');
        
        if (!available) {
            btn.classList.add('unavailable');
        } else if (fired) {
            btn.classList.add('fired');
        } else {
            btn.classList.add('ready');
        }
        
        btn.disabled = !PyroMan.fireEnabled || !PyroMan.authorized || !available || fired;
    });
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
    container.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 70px;
        z-index: 1001;
        display: flex;
        flex-direction: column;
        gap: 10px;
    `;
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
    // Fire Buttons (Koffer)
    document.querySelectorAll('.fire-btn[data-koffer]').forEach(btn => {
        btn.addEventListener('click', () => {
            const kofferId = parseInt(btn.dataset.koffer);
            const kanalNr = parseInt(btn.dataset.kanal);
            fireKoffer(kofferId, kanalNr);
        });
    });
    
    // Fire Buttons (Direktzünder)
    document.querySelectorAll('.fire-btn[data-direktzuender]').forEach(btn => {
        btn.addEventListener('click', () => {
            const nr = parseInt(btn.dataset.direktzuender);
            fireDirektzuender(nr);
        });
    });
    
    // Fire Master Toggle
    const fireMasterToggle = document.getElementById('fire-master-toggle');
    if (fireMasterToggle) {
        fireMasterToggle.addEventListener('click', toggleFireEnabled);
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