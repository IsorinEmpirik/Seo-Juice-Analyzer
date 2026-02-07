// history.js - Gestion de l'historique et comparaison des analyses

// Variables globales pour l'historique
let currentComparison = null;
let evolutionChart = null;
let errorEvolutionChart = null;
let currentDomain = '';

document.addEventListener('DOMContentLoaded', function() {
    // Initialiser l'onglet historique quand on clique dessus
    const historyTab = document.querySelector('[data-tab="history"]');
    if (historyTab) {
        historyTab.addEventListener('click', initializeHistoryTab);
    }

    // Initialiser les événements
    initializeHistoryEvents();
});

// ==================== INITIALISATION ====================

let historyInitialized = false;

function initializeHistoryTab() {
    if (historyInitialized) return;

    loadDomains();
    historyInitialized = true;
}

function initializeHistoryEvents() {
    // Changement de domaine
    const domainSelect = document.getElementById('history-domain-filter');
    if (domainSelect) {
        domainSelect.addEventListener('change', function() {
            loadAnalysesForDomain(this.value);
        });
    }

    // Changement d'analyse
    const analysisSelect = document.getElementById('history-analysis-select');
    if (analysisSelect) {
        analysisSelect.addEventListener('change', function() {
            const compareBtn = document.getElementById('compare-btn');
            if (compareBtn) {
                compareBtn.disabled = !this.value;
            }
        });
    }

    // Bouton comparer
    const compareBtn = document.getElementById('compare-btn');
    if (compareBtn) {
        compareBtn.addEventListener('click', performComparison);
    }

    // Export CSV des changements
    const exportBtn = document.getElementById('export-changes-csv');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportChangesToCSV);
    }
}

// ==================== CHARGEMENT DES DONNÉES ====================

async function loadDomains() {
    const domainSelect = document.getElementById('history-domain-filter');
    if (!domainSelect) return;

    try {
        const response = await fetch('/api/history/domains');
        const data = await response.json();

        if (data.status === 'success') {
            domainSelect.innerHTML = '<option value="">Tous les domaines</option>';

            data.domains.forEach(d => {
                const option = document.createElement('option');
                option.value = d.domain;
                option.textContent = `${d.domain} (${d.count} analyse${d.count > 1 ? 's' : ''})`;
                domainSelect.appendChild(option);
            });

            // Extraire le domaine actuel depuis les résultats
            if (resultsData && resultsData.urls && resultsData.urls.length > 0) {
                try {
                    const url = new URL(resultsData.urls[0].url);
                    currentDomain = url.hostname.replace('www.', '');

                    // Sélectionner automatiquement ce domaine
                    domainSelect.value = currentDomain;
                    loadAnalysesForDomain(currentDomain);
                } catch (e) {
                    // Charger toutes les analyses
                    loadAnalysesForDomain('');
                }
            } else {
                loadAnalysesForDomain('');
            }
        }
    } catch (error) {
        console.error('Erreur chargement domaines:', error);
        domainSelect.innerHTML = '<option value="">Erreur de chargement</option>';
    }
}

async function loadAnalysesForDomain(domain) {
    const analysisSelect = document.getElementById('history-analysis-select');
    const compareBtn = document.getElementById('compare-btn');
    const noHistoryMsg = document.getElementById('no-history-message');
    const comparisonResults = document.getElementById('comparison-results');

    if (!analysisSelect) return;

    analysisSelect.disabled = true;
    analysisSelect.innerHTML = '<option value="">Chargement...</option>';

    try {
        const url = domain
            ? `/api/history/analyses?domain=${encodeURIComponent(domain)}&limit=50`
            : '/api/history/analyses?limit=50';

        const response = await fetch(url);
        const data = await response.json();

        if (data.status === 'success') {
            const analyses = data.analyses.filter(a => a.analysis_id !== analysisId);

            if (analyses.length === 0) {
                analysisSelect.innerHTML = '<option value="">Aucune analyse précédente</option>';
                analysisSelect.disabled = true;
                if (compareBtn) compareBtn.disabled = true;
                if (noHistoryMsg) noHistoryMsg.classList.remove('d-none');
                if (comparisonResults) comparisonResults.classList.add('d-none');
                return;
            }

            if (noHistoryMsg) noHistoryMsg.classList.add('d-none');

            analysisSelect.innerHTML = '<option value="">Choisir une analyse...</option>';

            analyses.forEach(a => {
                const option = document.createElement('option');
                option.value = a.analysis_id;

                const date = new Date(a.created_at);
                const dateStr = date.toLocaleDateString('fr-FR', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });

                option.textContent = `${dateStr} - ${a.domain} (${a.total_urls} URLs, score: ${a.median_seo_score?.toFixed(1) || 'N/A'})`;
                analysisSelect.appendChild(option);
            });

            analysisSelect.disabled = false;
        }
    } catch (error) {
        console.error('Erreur chargement analyses:', error);
        analysisSelect.innerHTML = '<option value="">Erreur de chargement</option>';
    }
}

// ==================== COMPARAISON ====================

async function performComparison() {
    const previousId = document.getElementById('history-analysis-select').value;
    if (!previousId) return;

    const loadingDiv = document.getElementById('comparison-loading');
    const resultsDiv = document.getElementById('comparison-results');
    const compareBtn = document.getElementById('compare-btn');

    // Afficher le chargement
    if (loadingDiv) loadingDiv.classList.remove('d-none');
    if (resultsDiv) resultsDiv.classList.add('d-none');
    if (compareBtn) {
        compareBtn.disabled = true;
        compareBtn.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Chargement...';
    }

    try {
        const response = await fetch('/api/history/compare', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                current_id: analysisId,
                previous_id: previousId
            })
        });

        const data = await response.json();

        if (data.status === 'success') {
            currentComparison = data.comparison;
            displayComparison(data.comparison);

            // Charger l'évolution
            if (currentDomain) {
                loadEvolutionData(currentDomain);
            }
        } else {
            alert('Erreur: ' + data.message);
        }
    } catch (error) {
        console.error('Erreur comparaison:', error);
        alert('Erreur lors de la comparaison: ' + error.message);
    } finally {
        if (loadingDiv) loadingDiv.classList.add('d-none');
        if (resultsDiv) resultsDiv.classList.remove('d-none');
        if (compareBtn) {
            compareBtn.disabled = false;
            compareBtn.innerHTML = '<i class="bi bi-arrow-left-right me-2"></i>Comparer';
        }
    }
}

// ==================== AFFICHAGE DES RÉSULTATS ====================

function displayComparison(comparison) {
    // Afficher les dates
    const datesSpan = document.getElementById('comparison-dates');
    if (datesSpan) {
        const prevDate = new Date(comparison.previous.created_at).toLocaleDateString('fr-FR');
        const currDate = new Date(comparison.current.created_at).toLocaleDateString('fr-FR');
        datesSpan.textContent = `${prevDate} → ${currDate}`;
    }

    // Afficher les cartes de métriques delta
    displayDeltaCards(comparison.global_delta);

    // Afficher les Quick Wins
    displayQuickWinsComparison(comparison.quick_wins);

    // Afficher les erreurs
    displayErrorsComparison(comparison.errors);

    // Afficher le tableau des changements
    displayUrlChanges(comparison.url_changes);
}

function displayDeltaCards(globalDelta) {
    const container = document.getElementById('delta-cards');
    if (!container) return;

    const metrics = [
        { key: 'total_urls', label: 'URLs Totales', icon: 'bi-file-earmark', color: 'primary' },
        { key: 'total_internal_links', label: 'Liens Internes', icon: 'bi-link-45deg', color: 'success' },
        { key: 'total_backlinks', label: 'Backlinks', icon: 'bi-box-arrow-in-down', color: 'info' },
        { key: 'median_seo_score', label: 'Score PR Médian', icon: 'bi-speedometer2', color: 'warning', decimals: 1 },
        { key: 'error_juice_rate', label: 'Jus sur Erreurs (%)', icon: 'bi-exclamation-triangle', color: 'danger', decimals: 2, inverse: true }
    ];

    container.innerHTML = metrics.map(m => {
        const data = globalDelta[m.key];
        if (!data) return '';

        const delta = data.delta;
        const percent = data.percent;
        const isPositive = m.inverse ? delta < 0 : delta > 0;
        const isNegative = m.inverse ? delta > 0 : delta < 0;

        const deltaClass = isPositive ? 'text-success' : (isNegative ? 'text-danger' : 'text-muted');
        const deltaIcon = isPositive ? 'bi-arrow-up' : (isNegative ? 'bi-arrow-down' : 'bi-dash');
        const deltaSign = delta > 0 ? '+' : '';

        const currentVal = m.decimals ? data.current.toFixed(m.decimals) : data.current;
        const deltaVal = m.decimals ? delta.toFixed(m.decimals) : delta;

        return `
            <div class="col-md-4 col-lg">
                <div class="card h-100 border-0 shadow-sm">
                    <div class="card-body text-center">
                        <i class="bi ${m.icon} text-${m.color}" style="font-size: 1.5rem;"></i>
                        <div class="h4 mb-0 mt-2">${currentVal}</div>
                        <small class="text-muted d-block">${m.label}</small>
                        <div class="mt-2 ${deltaClass} fw-bold">
                            <i class="bi ${deltaIcon}"></i>
                            ${deltaSign}${deltaVal}
                            <small>(${deltaSign}${percent}%)</small>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function displayQuickWinsComparison(quickWins) {
    // Quick Wins résolus
    const resolvedList = document.getElementById('resolved-quick-wins-list');
    const resolvedCount = document.getElementById('resolved-qw-count');

    if (resolvedList && quickWins.resolved) {
        resolvedCount.textContent = quickWins.resolved.length;

        if (quickWins.resolved.length === 0) {
            resolvedList.innerHTML = '<p class="text-muted text-center small">Aucun Quick Win résolu</p>';
        } else {
            resolvedList.innerHTML = quickWins.resolved.map(qw => `
                <div class="d-flex justify-content-between align-items-center border-bottom py-2">
                    <div>
                        <strong class="small">${truncateText(qw.keyword, 40)}</strong>
                        <br>
                        <small class="text-muted">${truncateText(qw.url, 50)}</small>
                    </div>
                    <span class="badge bg-success">Pos. ${qw.position?.toFixed(1) || 'N/A'}</span>
                </div>
            `).join('');
        }
    }

    // Nouveaux Quick Wins
    const newList = document.getElementById('new-quick-wins-list');
    const newCount = document.getElementById('new-qw-count');

    if (newList && quickWins.new) {
        newCount.textContent = quickWins.new.length;

        if (quickWins.new.length === 0) {
            newList.innerHTML = '<p class="text-muted text-center small">Aucun nouveau Quick Win</p>';
        } else {
            newList.innerHTML = quickWins.new.map(qw => `
                <div class="d-flex justify-content-between align-items-center border-bottom py-2">
                    <div>
                        <strong class="small">${truncateText(qw.keyword, 40)}</strong>
                        <br>
                        <small class="text-muted">${truncateText(qw.url, 50)}</small>
                    </div>
                    <span class="badge bg-warning text-dark">Pos. ${qw.position?.toFixed(1) || 'N/A'}</span>
                </div>
            `).join('');
        }
    }
}

function displayErrorsComparison(errors) {
    // Erreurs corrigées
    const fixedList = document.getElementById('fixed-errors-list');
    const fixedCount = document.getElementById('fixed-errors-count');

    if (fixedList && errors.fixed) {
        fixedCount.textContent = errors.fixed.length;

        if (errors.fixed.length === 0) {
            fixedList.innerHTML = '<p class="text-muted text-center small">Aucune erreur corrigée</p>';
        } else {
            fixedList.innerHTML = errors.fixed.map(e => `
                <div class="d-flex justify-content-between align-items-center border-bottom py-2">
                    <small class="text-truncate" style="max-width: 70%;">${e.url}</small>
                    <span class="badge bg-secondary">${e.status_code}</span>
                </div>
            `).join('');
        }
    }

    // Nouvelles erreurs
    const newList = document.getElementById('new-errors-list');
    const newCount = document.getElementById('new-errors-count');

    if (newList && errors.new) {
        newCount.textContent = errors.new.length;

        if (errors.new.length === 0) {
            newList.innerHTML = '<p class="text-muted text-center small">Aucune nouvelle erreur</p>';
        } else {
            newList.innerHTML = errors.new.map(e => `
                <div class="d-flex justify-content-between align-items-center border-bottom py-2">
                    <small class="text-truncate" style="max-width: 70%;">${e.url}</small>
                    <span class="badge bg-danger">${e.status_code}</span>
                </div>
            `).join('');
        }
    }
}

function displayUrlChanges(urlChanges) {
    const tbody = document.getElementById('url-changes-tbody');
    const countBadge = document.getElementById('url-changes-count');

    if (!tbody) return;

    if (countBadge) {
        countBadge.textContent = `${urlChanges.length} page${urlChanges.length > 1 ? 's' : ''}`;
    }

    if (urlChanges.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-muted py-4">
                    Aucun changement significatif détecté
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = urlChanges.map(change => {
        const scoreDelta = change.seo_score.delta;
        const linksDelta = change.internal_links_received.delta;

        const scoreClass = scoreDelta > 0 ? 'text-success' : (scoreDelta < 0 ? 'text-danger' : '');
        const linksClass = linksDelta > 0 ? 'text-success' : (linksDelta < 0 ? 'text-danger' : '');

        const scoreSign = scoreDelta > 0 ? '+' : '';
        const linksSign = linksDelta > 0 ? '+' : '';

        return `
            <tr>
                <td>
                    <a href="${change.url}" target="_blank" class="small text-decoration-none">
                        ${truncateText(change.url, 50)}
                    </a>
                </td>
                <td class="text-center">${change.seo_score.previous?.toFixed(1) || 'N/A'}</td>
                <td class="text-center">${change.seo_score.current?.toFixed(1) || 'N/A'}</td>
                <td class="text-center ${scoreClass} fw-bold">${scoreSign}${scoreDelta.toFixed(1)}</td>
                <td class="text-center">${change.internal_links_received.previous || 0}</td>
                <td class="text-center">${change.internal_links_received.current || 0}</td>
                <td class="text-center ${linksClass} fw-bold">${linksSign}${linksDelta}</td>
            </tr>
        `;
    }).join('');
}

// ==================== GRAPHIQUES D'ÉVOLUTION ====================

async function loadEvolutionData(domain) {
    try {
        const response = await fetch(`/api/history/evolution/${encodeURIComponent(domain)}?limit=10`);
        const data = await response.json();

        if (data.status === 'success' && data.evolution.length >= 2) {
            createEvolutionCharts(data.evolution);
        }
    } catch (error) {
        console.error('Erreur chargement évolution:', error);
    }
}

function createEvolutionCharts(evolution) {
    const labels = evolution.map(e => {
        const date = new Date(e.created_at);
        return date.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' });
    });

    // Graphique Score PR
    const scoreCtx = document.getElementById('evolutionChart');
    if (scoreCtx) {
        if (evolutionChart) evolutionChart.destroy();

        evolutionChart = new Chart(scoreCtx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Score PR Médian',
                    data: evolution.map(e => e.median_seo_score),
                    borderColor: 'rgb(13, 110, 253)',
                    backgroundColor: 'rgba(13, 110, 253, 0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 5,
                    pointHoverRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        title: { display: true, text: 'Score' }
                    }
                }
            }
        });
    }

    // Graphique Taux d'erreur
    const errorCtx = document.getElementById('errorEvolutionChart');
    if (errorCtx) {
        if (errorEvolutionChart) errorEvolutionChart.destroy();

        errorEvolutionChart = new Chart(errorCtx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Jus sur Erreurs (%)',
                    data: evolution.map(e => e.error_juice_rate),
                    borderColor: 'rgb(220, 53, 69)',
                    backgroundColor: 'rgba(220, 53, 69, 0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 5,
                    pointHoverRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: '%' }
                    }
                }
            }
        });
    }
}

// ==================== EXPORT CSV ====================

function exportChangesToCSV() {
    if (!currentComparison || !currentComparison.url_changes) {
        alert('Aucune donnée à exporter');
        return;
    }

    const changes = currentComparison.url_changes;
    const headers = ['URL', 'Score Avant', 'Score Après', 'Delta Score', 'Liens Avant', 'Liens Après', 'Delta Liens', 'Catégorie'];

    const rows = changes.map(c => [
        c.url,
        c.seo_score.previous?.toFixed(1) || '',
        c.seo_score.current?.toFixed(1) || '',
        c.seo_score.delta.toFixed(1),
        c.internal_links_received.previous || 0,
        c.internal_links_received.current || 0,
        c.internal_links_received.delta,
        c.category || ''
    ]);

    const csvContent = [
        headers.join(';'),
        ...rows.map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(';'))
    ].join('\n');

    // Télécharger
    const BOM = '\uFEFF';
    const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);

    const today = new Date().toISOString().slice(0, 10);
    link.setAttribute('href', url);
    link.setAttribute('download', `${currentDomain || 'export'}_comparison_${today}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

// ==================== UTILITAIRES ====================

function truncateText(text, maxLength) {
    if (!text) return '';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}
