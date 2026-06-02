// Sélecteurs DOM globaux
const chatWindow = document.getElementById('chat-window');
const form = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const btnReset = document.getElementById('btn-reset');
const btnLogout = document.getElementById('btn-logout');
const userBadge = document.getElementById('user-badge');
const btnShowHistory = document.getElementById('btn-show-history');
const btnCloseHistory = document.getElementById('btn-close-history');
const historyPanel = document.getElementById('history-panel');
const historyList = document.getElementById('history-list');
const btnHeroCodes = document.getElementById('btn-hero-codes');
const btnCloseCodes = document.getElementById('btn-close-codes');
const codesPage = document.getElementById('codes-page');
const codesGrid = document.getElementById('codes-grid');

// Sélecteur pour le bouton de véhicule
const btnSelectVehicle = document.getElementById('btn-select-vehicle');

// URL de base du serveur API
const API_BASE_URL = window.location.origin;

// Session de chat & informations du véhicule en cours
let chatSessionId = localStorage.getItem('mechanic_assistant_session_id') || null;
let currentVehicle = JSON.parse(localStorage.getItem('mechanic_assistant_current_vehicle')) || null;
const storedUserProfile = JSON.parse(localStorage.getItem('mechanic_assistant_user_profile')) || {};
let userProfile = {
    id: storedUserProfile.id || null,
    name: storedUserProfile.name || 'Invité',
    email: storedUserProfile.email || '',
    role: storedUserProfile.role || ''
};
let lastUserMessage = '';

// Messages de bienvenue initiaux
const WELCOME_MESSAGES = [
    `🚗 **Bienvenue sur Mechanic Assistant** ⚡`,
    `Je suis votre assistant diagnostic automobile intelligent. Je peux vous aider à :
    
- 🔍 **Analyser les codes erreurs OBD-II** (ex: P0300, P0171, P0420)
- 📳 **Identifier les pannes** à partir de vos symptômes décrits
- 🛠️ **Vous guider étape par étape** dans la réparation
- 🚘 **Adapter le diagnostic** spécifiquement à votre véhicule

Parlez-moi naturellement : par exemple « J'ai de la fumée noire » ou « mon témoin moteur s'allume ».`
];

// Initialisation de Marked.js
if (typeof marked !== 'undefined') {
    marked.setOptions({
        gfm: true,
        breaks: true,
        headerIds: false,
        mangle: false,
        sanitize: false
    });
}

// Initialisation au chargement de la page
window.addEventListener('DOMContentLoaded', () => {
    initPremiumAuth();
    updateVehicleHeaderButton();
    updateUserBadge();
    
    const btnHeroStart = document.getElementById('btn-hero-start');
    if (btnHeroStart) {
        btnHeroStart.addEventListener('click', () => {
            if (!chatSessionId) {
                demarrerNouvelleSession();
            }
            setPage('chat');
            chatInput.focus();
        });
    }

    if (btnLogout) {
        btnLogout.addEventListener('click', () => {
            if (confirm('Voulez-vous vraiment vous déconnecter ?')) {
                localStorage.removeItem('mechanic_assistant_user_profile');
                localStorage.removeItem('mechanic_assistant_current_vehicle');
                localStorage.removeItem('mechanic_assistant_session_id');
                location.reload();
            }
        });
    }

    if (btnShowHistory) {
        btnShowHistory.addEventListener('click', showHistoryPage);
    }

    if (btnHeroCodes) {
        btnHeroCodes.addEventListener('click', showCodesPage);
    }

    if (btnCloseHistory) {
        btnCloseHistory.addEventListener('click', () => setPage('chat'));
    }

    if (btnCloseCodes) {
        btnCloseCodes.addEventListener('click', () => setPage('chat'));
    }



    if (codesGrid) {
        codesGrid.addEventListener('click', (e) => {
            const card = e.target.closest('.code-card');
            if (!card) return;
            const code = card.getAttribute('data-code');
            if (code) {
                setPage('chat');
                envoyerMessageUtilisateur(code);
            }
        });
    }

    if (!chatSessionId) {
        demarrerNouvelleSession();
    } else {
        afficherMessageAccueil();
    }
});

function setPage(page) {
    const isChat = page === 'chat';
    chatWindow.classList.toggle('hidden', !isChat);
    document.querySelector('.quick-tags-container').classList.toggle('hidden', !isChat);
    form.classList.toggle('hidden', !isChat);
    codesPage.classList.toggle('hidden', page !== 'codes');
    historyPanel.classList.toggle('hidden', page !== 'history');
}

async function showCodesPage() {
    setPage('codes');
    if (codesGrid && codesGrid.children.length === 0) {
        await loadObdCodes();
    }
}

function showHistoryPage() {
    setPage('history');
    loadHistory();
}





async function saveUserProfile() {
    const profile = {
        name: inputUserName?.value.trim() || 'Invité',
        email: inputUserEmail?.value.trim() || '',
        role: inputUserRole?.value.trim() || ''
    };
    if (!profile.email) {
        alert('Merci de renseigner un email professionnel.');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/user/profile`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(profile)
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || 'Impossible d’enregistrer le profil utilisateur.');
        }

        const saved = await response.json();
        userProfile = {
            id: saved.user_id,
            name: saved.name,
            email: saved.email,
            role: saved.role || ''
        };
        localStorage.setItem('mechanic_assistant_user_profile', JSON.stringify(userProfile));
        updateUserBadge();
        closeUserModal();
    } catch (err) {
        console.error(err);
        alert('Erreur lors de l’enregistrement du profil utilisateur.');
    }
}

function updateUserBadge() {
    if (!userBadge) return;
    const name = userProfile?.name || 'Invité';
    const role = userProfile?.role ? ` • ${userProfile.role}` : '';
    userBadge.textContent = `👤 ${name}${role}`;
}

async function loadHistory() {
    if (userProfile?.id) {
        try {
            const response = await fetch(`${API_BASE_URL}/api/user/history?user_id=${encodeURIComponent(userProfile.id)}`);
            if (response.ok) {
                const serverHistory = await response.json();
                if (serverHistory.length) {
                    renderHistory(serverHistory);
                    return;
                }
            }
        } catch (err) {
            console.error('Erreur de récupération de l’historique serveur :', err);
        }
    }

    const historyKey = userProfile?.id ? `mechanic_assistant_history_${userProfile.id}` : 'mechanic_assistant_history_guest';
    const rawHistory = localStorage.getItem(historyKey);
    const entries = rawHistory ? JSON.parse(rawHistory) : [];
    renderHistory(entries);
}

function renderHistory(entries) {
    if (!historyList) return;

    if (!entries.length) {
        historyList.innerHTML = '<div class="loading-message">Aucun historique disponible pour le moment.</div>';
        return;
    }

    historyList.innerHTML = entries.map(entry => {
        const timestamp = entry.created_at || entry.timestamp || new Date().toISOString();
        const date = new Date(timestamp);
        const userMessage = entry.user_message || entry.user || '';
        const botReply = entry.bot_reply || entry.bot || '';
        const title = userMessage.length > 48 ? `${userMessage.slice(0, 45)}...` : userMessage;
        const badgeRole = entry.user_role ? `<span class="history-badge">${entry.user_role}</span>` : '';
        const badgeEmail = entry.user_email ? `<span class="history-badge history-badge-light">${entry.user_email}</span>` : '';
        const sessionLabel = entry.session_label || (entry.session_id ? `#${entry.session_id.slice(-6)}` : 'N/A');
        const profileName = entry.user_name || userProfile?.name || 'Invité';
        const vehicleInfo = entry.vehicle || 'Non précisé';

        return `
            <div class="history-card" data-history-id="${entry.id}">
                <div class="history-card-header">
                    <div>
                        <strong>${profileName}</strong>
                        <div class="history-card-meta">${badgeRole}${badgeEmail}</div>
                    </div>
                    <div class="history-card-tag">
                        <span>${sessionLabel}</span>
                        <span>${date.toLocaleString('fr-FR')}</span>
                    </div>
                </div>
                <div class="history-card-subtitle">Véhicule : ${vehicleInfo}</div>
                <div class="history-card-body">
                    <p><strong>Requête :</strong> ${title}</p>
                    <p><strong>Réponse :</strong> ${botReply}</p>
                </div>
                <div class="history-card-actions">
                    <button class="history-restore-btn" data-history-id="${entry.id}">Relancer</button>
                    <button class="history-delete-btn" data-history-id="${entry.id}">🗑️ Supprimer</button>
                </div>
            </div>
        `;
    }).join('');

    historyList.querySelectorAll('.history-restore-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const entry = entries.find(item => String(item.id) === String(btn.getAttribute('data-history-id')));
            if (entry) {
                setPage('chat');
                envoyerMessageUtilisateur(entry.user_message || entry.user);
            }
        });
    });

    historyList.querySelectorAll('.history-delete-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const entryId = btn.getAttribute('data-history-id');
            if (confirm('Voulez-vous vraiment supprimer ce diagnostic de votre historique ?')) {
                if (userProfile?.id) {
                    try {
                        const response = await fetch(`${API_BASE_URL}/api/user/history/${entryId}?user_id=${userProfile.id}`, {
                            method: 'DELETE'
                        });
                        if (!response.ok) {
                            throw new Error("Impossible de supprimer de l'historique serveur.");
                        }
                    } catch (err) {
                        console.error(err);
                    }
                }
                
                const historyKey = userProfile?.id ? `mechanic_assistant_history_${userProfile.id}` : 'mechanic_assistant_history_guest';
                const rawHistory = localStorage.getItem(historyKey);
                if (rawHistory) {
                    let localEntries = JSON.parse(rawHistory);
                    localEntries = localEntries.filter(item => String(item.id) !== String(entryId));
                    localStorage.setItem(historyKey, JSON.stringify(localEntries));
                }

                loadHistory();
            }
        });
    });
}

function saveHistoryEntry(userMessage, botReply) {
    if (!userMessage || !botReply) return;
    const historyKey = userProfile?.id ? `mechanic_assistant_history_${userProfile.id}` : 'mechanic_assistant_history_guest';
    const rawHistory = localStorage.getItem(historyKey);
    const entries = rawHistory ? JSON.parse(rawHistory) : [];
    const vehicleInfo = currentVehicle ? `${currentVehicle.brand} ${currentVehicle.model} (${currentVehicle.year})` : 'Non précisé';
    const sessionLabel = chatSessionId ? `#${chatSessionId.slice(-6)}` : 'N/A';

    entries.unshift({
        id: `${Date.now()}-${Math.random().toString(36).slice(2,8)}`,
        timestamp: new Date().toISOString(),
        session_id: chatSessionId || '',
        session_label: sessionLabel,
        user_name: userProfile?.name || 'Invité',
        user_email: userProfile?.email || '',
        user_role: userProfile?.role || '',
        vehicle: vehicleInfo,
        user: userMessage,
        bot: botReply
    });

    if (entries.length > 40) {
        entries.length = 40;
    }

    localStorage.setItem(historyKey, JSON.stringify(entries));
}

async function loadObdCodes() {
    if (!codesGrid) return;
    codesGrid.innerHTML = '<div class="loading-message">Chargement des codes OBD…</div>';

    try {
        const response = await fetch(`${API_BASE_URL}/api/obd-codes`);
        if (!response.ok) {
            throw new Error('Erreur de chargement des codes');
        }
        const data = await response.json();
        renderObdCodes(data);
    } catch (error) {
        codesGrid.innerHTML = '<div class="loading-message error">Impossible de charger les codes OBD. Réessayez plus tard.</div>';
        console.error(error);
    }
}

function renderObdCodes(data) {
    if (!codesGrid) return;
    const entries = Object.entries(data).sort(([a], [b]) => a.localeCompare(b));
    if (!entries.length) {
        codesGrid.innerHTML = '<div class="loading-message">Aucun code trouvé.</div>';
        return;
    }

    codesGrid.innerHTML = entries.map(([code, info]) => {
        const systeme = info.systeme || info.type || 'Système inconnu';
        const description = info.description || 'Description non disponible.';
        const label = getSeverityLabel(info);
        const severityClass = getSeverityClass(info);
        return `
            <div class="code-card" data-code="${code}">
                <div class="code-card-top">
                    <span class="code-label">${code}</span>
                    <span class="code-system">${systeme}</span>
                </div>
                <div class="code-title">${description.split('. ')[0] || description}</div>
                <div class="code-description">${description}</div>
                <div class="code-severity ${severityClass}">${label}</div>
            </div>
        `;
    }).join('');
}

function getSeverityClass(info) {
    const text = `${info.systeme || ''} ${info.description || ''}`.toLowerCase();
    if (text.includes('allumage') || text.includes('bobine') || text.includes('bougie') || text.includes('raté') || text.includes('catalyseur')) {
        return 'high';
    }
    if (text.includes('carburant') || text.includes('lambda') || text.includes('pollution') || text.includes('sonde') || text.includes('admission')) {
        return 'medium';
    }
    return 'low';
}

function getSeverityLabel(info) {
    const level = getSeverityClass(info);
    if (level === 'high') return 'Élevée';
    if (level === 'medium') return 'Modérée';
    return 'Faible';
}

// Réinitialiser la conversation
btnReset.addEventListener('click', () => {
    if (confirm('Voulez-vous vraiment commencer un nouveau diagnostic ? L\'historique actuel sera effacé.')) {
        demarrerNouvelleSession();
    }
});

function demarrerNouvelleSession() {
    chatSessionId = null;
    localStorage.removeItem('mechanic_assistant_session_id');
    chatWindow.innerHTML = '';
    afficherMessageAccueil();
    chatInput.focus();
}

function afficherMessageAccueil() {
    WELCOME_MESSAGES.forEach((msg, idx) => {
        setTimeout(() => {
            ajouterMessage(msg, 'bot');
        }, idx * 150);
    });
}

/**
 * Analyse et extrait les balises personnalisées de Mechanic Assistant
 * pour restituer de superbes fiches interactives dans le chat.
 */
function parserContenuBot(texte) {
    let html = texte;

    // 1. Rendu de la fiche Diagnostic <diagnostic ... />
    const diagRegex = /<diagnostic\s+code="([^"]+)"\s+title="([^"]+)"\s+severity="([^"]+)"\s+price="([^"]+)"\s+time="([^"]+)"\s+steps="([^"]+)"\s+causes="([^"]+)"\s*\/?>/gi;
    html = html.replace(diagRegex, (match, code, title, severity, price, time, steps, causesStr) => {
        const causes = causesStr.split('|').map(c => `<li>${c.trim()}</li>`).join('');
        const severityClass = severity.toLowerCase() === 'critical' ? 'critical' : 'moderate';
        const severityLabel = severity.toLowerCase() === 'critical' ? 'Critique' : 'Modérée';
        
        return `
            <div class="diag-card">
                <div class="diag-card-header">
                    <div class="diag-code-info">
                        <h3>${code}</h3>
                        <p>${title}</p>
                    </div>
                    <span class="badge-severity ${severityClass}">${severityLabel}</span>
                </div>
                <div class="diag-causes-section">
                    <h4>Causes possibles</h4>
                    <ul class="diag-causes-list">
                        ${causes}
                    </ul>
                </div>
                <div class="diag-meta-capsules">
                    <div class="meta-capsule">💶 ${price}</div>
                    <div class="meta-capsule">⏱️ ${time}</div>
                    <div class="meta-capsule">🔧 ${steps}</div>
                </div>
                <div class="diag-actions">
                    <button class="btn-diag-primary btn-action-trigger" data-action="start_guidage" data-code="${code}">Guidage étape par étape</button>
                    <button class="btn-diag-secondary btn-action-trigger" data-action="plus_infos" data-code="${code}">Plus d'infos</button>
                </div>
            </div>
        `;
    });

    // 2. Rendu de la fiche Étape <step ...>...</step>
    const stepRegex = /<step\s+number="([^"]+)"\s+title="([^"]+)"\s+difficulty="([^"]+)"\s+time="([^"]+)"\s+tools="([^"]+)"\s*>([\s\S]*?)<\/step>/gi;
    html = html.replace(stepRegex, (match, number, title, difficulty, time, toolsStr, desc) => {
        const tools = toolsStr.split('|').map(t => `<span class="tool-tag">${t.trim()}</span>`).join('');
        const diffClass = difficulty.toLowerCase() === 'easy' ? 'easy' : (difficulty.toLowerCase() === 'medium' ? 'medium' : 'hard');
        const diffLabel = difficulty.toLowerCase() === 'easy' ? 'Facile' : (difficulty.toLowerCase() === 'medium' ? 'Moyen' : 'Difficile');

        return `
            <div class="step-card">
                <div class="step-card-header">
                    <div class="step-title-area">
                        <div class="step-circle-num">${number}</div>
                        <span class="step-title-text">${title}</span>
                    </div>
                    <span class="badge-difficulty ${diffClass}">${diffLabel}</span>
                </div>
                <p class="step-desc-text">${desc.trim()}</p>
                <div class="step-tools-bar">
                    ${tools}
                </div>
                <div class="step-time-tag">⏱️ Durée estimée : ${time}</div>
                <div class="step-actions">
                    <button class="btn-step-resolve btn-action-trigger" data-action="resolve_problem" data-step="${number}" data-title="${title}">Problème résolu</button>
                    <button class="btn-step-next btn-action-trigger" data-action="next_step" data-step="${number}">Étape terminée</button>
                </div>
            </div>
        `;
    });

    // 3. Rendu de la fiche Succès <success ...>...</success>
    const successRegex = /<success\s+maintenance="([^"]+)"\s*>([\s\S]*?)<\/success>/gi;
    html = html.replace(successRegex, (match, maintenance, text) => {
        return `
            <div class="success-card">
                <div class="success-icon-container">
                    <div class="success-icon-circle">✓</div>
                </div>
                <h3>Problème résolu</h3>
                <p>${text.trim()}</p>
                <div class="maintenance-tip-box">
                    <h5>Conseil d'entretien</h5>
                    <p>${maintenance.trim()}</p>
                </div>
                <button class="btn-success-action btn-action-trigger" data-action="new_diagnostic">Nouveau diagnostic</button>
            </div>
        `;
    });

    // 4. Rendu de la fiche Détails Supplémentaires <detailsinfo ...>...</detailsinfo>
    const detailsRegex = /<detailsinfo\s+code="([^"]+)"\s+symptoms="([^"]+)"\s+tip="([^"]+)"\s*\/>/gi;
    html = html.replace(detailsRegex, (match, code, symptomsStr, tip) => {
        const symptoms = symptomsStr.split('|').map(s => `<li>${s.trim()}</li>`).join('');
        return `
            <div class="details-card">
                <div class="details-card-title">Détails supplémentaires — ${code}</div>
                <div class="details-section">
                    <h4>Symptômes associés :</h4>
                    <ul class="details-symptom-list">
                        ${symptoms}
                    </ul>
                </div>
                <div class="details-tip-box">
                    <h5>Conseil d'entretien :</h5>
                    <p>${tip.trim()}</p>
                </div>
            </div>
        `;
    });

    return html;
}

/**
 * Ajoute un message dans la fenêtre de chat.
 * Supporte le rendu Markdown et nos cartes riches.
 */
function ajouterMessage(contenu, auteur) {
    const div = document.createElement('div');
    div.className = `message ${auteur}`;

    if (auteur === 'bot') {
        // 1. Parser les balises personnalisées
        let htmlContenu = parserContenuBot(contenu);
        
        // 2. Si marked.js est disponible et que le message ne contient pas déjà du HTML complexe
        if (typeof marked !== 'undefined' && !htmlContenu.includes('class="diag-card"') && !htmlContenu.includes('class="step-card"') && !htmlContenu.includes('class="success-card"') && !htmlContenu.includes('class="details-card"')) {
            div.innerHTML = `<div class="markdown-content">${marked.parse(htmlContenu)}</div>`;
        } else {
            div.innerHTML = `<div class="markdown-content">${htmlContenu}</div>`;
        }
    } else {
        const p = document.createElement('p');
        p.textContent = contenu;
        div.appendChild(p);
    }

    chatWindow.appendChild(div);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    return div;
}

function afficherIndicateurChargement() {
    const div = document.createElement('div');
    div.className = 'message bot typing-container';
    div.innerHTML = `
        <div class="typing-indicator">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
        </div>
    `;
    chatWindow.appendChild(div);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    return div;
}

/**
 * Écouteur global sur la fenêtre de chat pour gérer les clics tactiles 
 * sur les boutons d'actions des cartes (Guidage, Étape suivante, Résolu).
 */
chatWindow.addEventListener('click', (e) => {
    const trigger = e.target.closest('.btn-action-trigger');
    if (!trigger) return;

    const action = trigger.getAttribute('data-action');
    
    // Désactiver les boutons de cette carte pour éviter les doubles clics
    const parentCard = trigger.closest('.diag-card, .step-card, .success-card');
    if (parentCard) {
        parentCard.querySelectorAll('button').forEach(btn => btn.disabled = true);
    }

    if (action === 'start_guidage') {
        const code = trigger.getAttribute('data-code');
        envoyerMessageUtilisateur(`Démarrons le guidage de réparation pour le code ${code}.`);
    } else if (action === 'plus_infos') {
        const code = trigger.getAttribute('data-code');
        envoyerMessageUtilisateur(`Donne-moi plus d'informations techniques sur le code d'erreur ${code}.`);
    } else if (action === 'resolve_problem') {
        const stepNum = trigger.getAttribute('data-step');
        envoyerMessageUtilisateur(`Le problème est résolu à l'étape ${stepNum} !`);
    } else if (action === 'next_step') {
        const stepNum = trigger.getAttribute('data-step');
        envoyerMessageUtilisateur(`J'ai effectué l'étape ${stepNum}. Passons à l'étape suivante.`);
    } else if (action === 'new_diagnostic') {
        demarrerNouvelleSession();
    }
});

// Écouteur sur les Quick-Tags interactifs
document.querySelector('.quick-tags-container').addEventListener('click', (e) => {
    const tag = e.target.closest('.quick-tag');
    if (!tag) return;
    const msg = tag.getAttribute('data-msg');
    envoyerMessageUtilisateur(msg);
});

// Envoi d'un message
form.addEventListener('submit', (e) => {
    e.preventDefault();
    const msg = chatInput.value.trim();
    if (!msg) return;
    envoyerMessageUtilisateur(msg);
    chatInput.value = '';
});

/**
 * Envoie un message au backend
 */
async function envoyerMessageUtilisateur(texte) {
    // Ajouter le message à l'écran
    ajouterMessage(texte, 'user');
    lastUserMessage = texte;
    
    const loader = afficherIndicateurChargement();

    // Enrichir le message avec les informations du véhicule si sélectionné
    let messageAEnvoyer = texte;
    if (currentVehicle && !texte.includes("[VEHICULE:")) {
        messageAEnvoyer = `[VEHICULE: ${currentVehicle.brand} ${currentVehicle.model} ${currentVehicle.year} (${currentVehicle.fuel})] ${texte}`;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/chat`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                message: messageAEnvoyer,
                session_id: chatSessionId,
                user_id: userProfile?.id,
                user_email: userProfile?.email || undefined,
                user_name: userProfile?.name || undefined,
                user_role: userProfile?.role || undefined,
                vehicle: currentVehicle ? `${currentVehicle.brand} ${currentVehicle.model} ${currentVehicle.year} ${currentVehicle.fuel}` : undefined
            })
        });

        loader.remove();

        if (!response.ok) {
            const errData = await response.json();
            ajouterMessage(`⚠️ **Erreur** : ${errData.detail || 'Erreur serveur.'}`, 'bot');
            return;
        }

        const data = await response.json();

        // Enregistrer la session
        if (data.session_id) {
            chatSessionId = data.session_id;
            localStorage.setItem('mechanic_assistant_session_id', chatSessionId);
        }

        // Afficher la réponse du bot
        ajouterMessage(data.reply, 'bot');
        saveHistoryEntry(lastUserMessage, data.reply);

    } catch (err) {
        loader.remove();
        ajouterMessage(`❌ **Erreur de connexion** : Impossible de contacter le serveur Mechanic Assistant.`, 'bot');
        console.error(err);
    }
}


/* ========================================================
   LOGIQUE DU SÉLECTEUR DE VÉHICULE (MODAL INTERACTIF)
   ======================================================== */

function updateVehicleHeaderButton() {
    if (!btnSelectVehicle) return;
    if (currentVehicle) {
        btnSelectVehicle.style.display = 'inline-flex';
        btnSelectVehicle.textContent = `🚗 ${currentVehicle.brand} ${currentVehicle.model} (${currentVehicle.year})`;
        btnSelectVehicle.classList.add('selected');
    } else {
        btnSelectVehicle.style.display = 'none';
        btnSelectVehicle.classList.remove('selected');
    }
}

function initPremiumAuth() {
    const authContainer = document.getElementById('auth-container');
    const loginSection = document.getElementById('login-section');
    const plateSection = document.getElementById('plate-section');
    const container = document.querySelector('.container');

    // Onglets & Panneaux
    const tabLogin = document.getElementById('tab-login');
    const tabRegister = document.getElementById('tab-register');
    const panelLogin = document.getElementById('panel-login');
    const panelRegister = document.getElementById('panel-register');

    // Connexion
    const loginForm = document.getElementById('login-form');
    const loginEmailInput = document.getElementById('login-email');
    const loginPasswordInput = document.getElementById('login-password');
    const loginError = document.getElementById('login-error');

    // Inscription
    const registerForm = document.getElementById('register-form');
    const registerNameInput = document.getElementById('register-name');
    const registerEmailInput = document.getElementById('register-email');
    const registerPasswordInput = document.getElementById('register-password');
    const registerConfirmInput = document.getElementById('register-confirm');
    const registerError = document.getElementById('register-error');

    // Immatriculation
    const plateForm = document.getElementById('plate-form');
    const plateInput = document.getElementById('plate-input');
    const plateError = document.getElementById('plate-error');
    const plateResult = document.getElementById('plate-result');

    const resBrand = document.getElementById('res-brand');
    const resModel = document.getElementById('res-model');
    const resYear = document.getElementById('res-year');
    const resFuel = document.getElementById('res-fuel');

    const btnStartChat = document.getElementById('btn-start-chat');

    // Stockage temporaire du véhicule identifié par la plaque
    let tempVehicle = null;

    // Basculement des onglets
    if (tabLogin && tabRegister) {
        tabLogin.addEventListener('click', () => {
            tabLogin.classList.add('active');
            tabRegister.classList.remove('active');
            panelLogin.classList.remove('hidden');
            panelRegister.classList.add('hidden');
        });

        tabRegister.addEventListener('click', () => {
            tabRegister.classList.add('active');
            tabLogin.classList.remove('active');
            panelRegister.classList.remove('hidden');
            panelLogin.classList.add('hidden');
        });
    }

    // Étape 1 : Vérifier si l'utilisateur est déjà connecté dans localStorage
    const savedProfile = JSON.parse(localStorage.getItem('mechanic_assistant_user_profile'));
    if (savedProfile && savedProfile.id) {
        userProfile = savedProfile;
        updateUserBadge();
    }
    // Afficher toujours la première page à l'ouverture et au rafraîchissement.
    loginSection.classList.remove('hidden');
    plateSection.classList.add('hidden');
    authContainer.classList.remove('hidden');
    container.classList.add('hidden');

    // Gérer la soumission du formulaire de connexion
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = loginEmailInput.value.trim();
            const password = loginPasswordInput.value.trim();

            if (!email || !password) {
                showLoginError("Veuillez remplir tous les champs.");
                return;
            }

            try {
                loginError.classList.add('hidden');
                const btn = document.getElementById('btn-login');
                btn.disabled = true;
                btn.textContent = "Connexion en cours...";

                const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });

                btn.disabled = false;
                btn.textContent = "Se connecter →";

                if (!response.ok) {
                    const errData = await response.json();
                    throw new Error(errData.detail || "Identifiants incorrects.");
                }

                const data = await response.json();
                userProfile = {
                    id: data.user_id,
                    name: data.name,
                    email: data.email,
                    role: data.role || 'Utilisateur'
                };

                // Enregistrer dans localStorage
                localStorage.setItem('mechanic_assistant_user_profile', JSON.stringify(userProfile));
                updateUserBadge();

                // Transition fluide vers l'écran d'immatriculation
                loginSection.classList.add('hidden');
                plateSection.classList.remove('hidden');

            } catch (err) {
                showLoginError(err.message);
            }
        });
    }

    // Gérer la soumission du formulaire d'inscription
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const name = registerNameInput.value.trim();
            const email = registerEmailInput.value.trim();
            const password = registerPasswordInput.value.trim();
            const confirmPass = registerConfirmInput.value.trim();

            if (!name || !email || !password || !confirmPass) {
                showRegisterError("Veuillez remplir tous les champs.");
                return;
            }

            if (password !== confirmPass) {
                showRegisterError("Les mots de passe ne correspondent pas.");
                return;
            }

            if (password.length < 4) {
                showRegisterError("Le mot de passe doit faire au moins 4 caractères.");
                return;
            }

            try {
                registerError.classList.add('hidden');
                const btn = document.getElementById('btn-register');
                btn.disabled = true;
                btn.textContent = "Inscription en cours...";

                const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, email, password })
                });

                btn.disabled = false;
                btn.textContent = "Créer mon compte ✓";

                if (!response.ok) {
                    const errData = await response.json();
                    throw new Error(errData.detail || "Erreur lors de l'inscription.");
                }

                const data = await response.json();
                userProfile = {
                    id: data.user_id,
                    name: data.name,
                    email: data.email,
                    role: 'Utilisateur'
                };

                // Enregistrer dans localStorage
                localStorage.setItem('mechanic_assistant_user_profile', JSON.stringify(userProfile));
                updateUserBadge();

                // Transition fluide vers l'écran d'immatriculation
                loginSection.classList.add('hidden');
                plateSection.classList.remove('hidden');

            } catch (err) {
                showRegisterError(err.message);
            }
        });
    }

    // Gérer la soumission du formulaire de recherche de plaque
    if (plateForm) {
        plateForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const plate = plateInput.value.trim();

            if (!plate) {
                showPlateError("Veuillez saisir un numéro d'immatriculation.");
                return;
            }

            try {
                plateError.classList.add('hidden');
                plateResult.classList.add('hidden');
                const btn = document.getElementById('btn-search-plate');
                btn.disabled = true;
                btn.textContent = "Recherche en cours...";

                const response = await fetch(`${API_BASE_URL}/api/vehicle/plate?matriculation=${encodeURIComponent(plate)}`);

                btn.disabled = false;
                btn.textContent = "Rechercher le Véhicule";

                if (!response.ok) {
                    const errData = await response.json();
                    throw new Error(errData.detail || "Véhicule introuvable.");
                }

                const data = await response.json();
                tempVehicle = {
                    brand: data.marque,
                    model: data.modele,
                    year: data.annee,
                    fuel: data.carburant,
                    matriculation: data.matriculation
                };

                // Afficher les résultats
                resBrand.textContent = tempVehicle.brand;
                resModel.textContent = tempVehicle.model;
                resYear.textContent = tempVehicle.year;
                resFuel.textContent = tempVehicle.fuel;

                plateResult.classList.remove('hidden');

            } catch (err) {
                showPlateError(err.message);
            }
        });
    }

    // Démarrer le diagnostic avec le véhicule trouvé
    if (btnStartChat) {
        btnStartChat.addEventListener('click', () => {
            if (!tempVehicle) return;

            currentVehicle = tempVehicle;
            localStorage.setItem('mechanic_assistant_current_vehicle', JSON.stringify(currentVehicle));

            updateVehicleHeaderButton();

            // Masquer l'écran d'authentification et afficher l'application
            authContainer.classList.add('hidden');
            container.classList.remove('hidden');

            // Démarrer une session propre
            demarrerNouvelleSession();
        });
    }

    function showLoginError(msg) {
        loginError.textContent = "❌ " + msg;
        loginError.classList.remove('hidden');
    }

    function showRegisterError(msg) {
        registerError.textContent = "❌ " + msg;
        registerError.classList.remove('hidden');
    }

    function showPlateError(msg) {
        plateError.textContent = "❌ " + msg;
        plateError.classList.remove('hidden');
    }
}

