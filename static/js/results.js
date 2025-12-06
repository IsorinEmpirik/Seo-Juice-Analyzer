// results.js - Graphiques et interactions pour la page de résultats

document.addEventListener('DOMContentLoaded', function() {
    // Initialiser la navigation par onglets
    initializeTabNavigation();

    // Initialiser les graphiques
    initializeCategoryChart();
    initializeStatusChart();
    initializeCorrelationChart();
    initializeJuiceDistributionChart();

    // Initialiser DataTables pour le tableau des URLs
    initializeUrlsTable();

    // Initialiser les tableaux Phase 2
    initializePhase2Tables();

    // Bouton export Google Sheets
    const exportBtn = document.getElementById('export-sheets-btn');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportToGoogleSheets);
    }
});

// ==================== NAVIGATION PAR ONGLETS ====================

function initializeTabNavigation() {
    const navLinks = document.querySelectorAll('.sidebar-nav-item[data-tab]');
    const tabPanes = document.querySelectorAll('.tab-pane');

    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();

            const targetTab = this.getAttribute('data-tab');

            // Retirer la classe active de tous les liens avec data-tab
            navLinks.forEach(l => l.classList.remove('active'));

            // Ajouter la classe active au lien cliqué
            this.classList.add('active');

            // Masquer tous les onglets
            tabPanes.forEach(pane => pane.classList.remove('active'));

            // Afficher l'onglet cible
            const targetPane = document.getElementById('tab-' + targetTab);
            if (targetPane) {
                targetPane.classList.add('active');

                // Initialiser les graphiques du second onglet Graphiques si nécessaire
                if (targetTab === 'charts') {
                    initializeChartsTab();
                }
            }
        });
    });
}

// Initialiser les graphiques du deuxième onglet
let chartsTabInitialized = false;
function initializeChartsTab() {
    if (chartsTabInitialized) return;

    const ctx1 = document.getElementById('categoryChart2');
    const ctx2 = document.getElementById('statusChart2');

    if (ctx1) {
        initializeCategoryChartOn(ctx1);
    }
    if (ctx2) {
        initializeStatusChartOn(ctx2);
    }

    chartsTabInitialized = true;
}

// ==================== GRAPHIQUES ====================

// Graphique : Score par catégorie
function initializeCategoryChart() {
    const ctx = document.getElementById('categoryChart');
    if (!ctx) return;
    initializeCategoryChartOn(ctx);
}

function initializeCategoryChartOn(ctx) {
    const categories = resultsData.categories;

    const sortedCategories = Object.entries(categories)
        .sort((a, b) => b[1].avg_score - a[1].avg_score)
        .slice(0, 10);

    const labels = sortedCategories.map(([name, _]) => name);
    const data = sortedCategories.map(([_, stats]) => stats.avg_score);
    const colors = generateColors(labels.length);

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Score Moyen SEO',
                data: data,
                backgroundColor: colors,
                borderColor: colors.map(c => c.replace('0.7', '1')),
                borderWidth: 2
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
                    max: 100,
                    title: { display: true, text: 'Score SEO (/100)' }
                },
                x: {
                    ticks: { maxRotation: 45, minRotation: 45 }
                }
            }
        }
    });
}

// Graphique : Distribution du jus SEO par code status
function initializeStatusChart() {
    const ctx = document.getElementById('statusChart');
    if (!ctx) return;
    initializeStatusChartOn(ctx);
}

function initializeStatusChartOn(ctx) {
    const juiceByStatus = resultsData.juice_by_status;
    const labels = Object.keys(juiceByStatus);
    const data = Object.values(juiceByStatus);

    const colorMap = {
        '200': 'rgba(40, 167, 69, 0.7)',
        '3xx': 'rgba(255, 193, 7, 0.7)',
        '4xx': 'rgba(220, 53, 69, 0.7)',
        '5xx': 'rgba(108, 117, 125, 0.7)',
        'Autre': 'rgba(13, 110, 253, 0.7)'
    };

    const colors = labels.map(label => colorMap[label] || 'rgba(13, 110, 253, 0.7)');

    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderColor: colors.map(c => c.replace('0.7', '1')),
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: true, position: 'bottom' },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${context.label}: ${value.toFixed(2)} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// Graphique : Corrélation Score SEO / Position GSC
let correlationChart = null;
let allCorrelationData = [];

function initializeCorrelationChart() {
    const ctx = document.getElementById('correlationChart');
    if (!ctx) return;

    // Préparer les données : TOUTES les pages, position 100 si pas de GSC
    allCorrelationData = [];

    resultsData.urls.forEach(url => {
        const hasGscKeyword = url.gsc_best_keyword && url.gsc_best_keyword.position;
        allCorrelationData.push({
            x: url.seo_score,
            y: hasGscKeyword ? url.gsc_best_keyword.position : 100,
            url: url.url,
            query: hasGscKeyword ? url.gsc_best_keyword.query : null,
            impressions: hasGscKeyword ? (url.gsc_best_keyword.impressions || 0) : 0,
            hasGsc: hasGscKeyword
        });
    });

    initializeChartFilters();
    updateCorrelationChart();
}

function initializeChartFilters() {
    const scoreMinSlider = document.getElementById('score-min-chart');
    const scoreMaxSlider = document.getElementById('score-max-chart');
    const scoreMinValue = document.getElementById('score-min-chart-value');
    const scoreMaxValue = document.getElementById('score-max-chart-value');
    const resetBtn = document.getElementById('reset-chart-filters');

    if (!scoreMinSlider || !scoreMaxSlider) return;

    scoreMinSlider.addEventListener('input', function() {
        scoreMinValue.textContent = this.value;
        if (parseInt(this.value) > parseInt(scoreMaxSlider.value)) {
            scoreMaxSlider.value = this.value;
            scoreMaxValue.textContent = this.value;
        }
        updateCorrelationChart();
    });

    scoreMaxSlider.addEventListener('input', function() {
        scoreMaxValue.textContent = this.value;
        if (parseInt(this.value) < parseInt(scoreMinSlider.value)) {
            scoreMinSlider.value = this.value;
            scoreMinValue.textContent = this.value;
        }
        updateCorrelationChart();
    });

    if (resetBtn) {
        resetBtn.addEventListener('click', function() {
            scoreMinSlider.value = 0;
            scoreMaxSlider.value = 100;
            scoreMinValue.textContent = '0';
            scoreMaxValue.textContent = '100';
            updateCorrelationChart();
        });
    }
}

function updateCorrelationChart() {
    const ctx = document.getElementById('correlationChart');
    if (!ctx) return;

    const scoreMin = parseFloat(document.getElementById('score-min-chart')?.value) || 0;
    const scoreMax = parseFloat(document.getElementById('score-max-chart')?.value) || 100;

    const filteredData = allCorrelationData.filter(d =>
        d.x >= scoreMin && d.x <= scoreMax
    );

    const countBadge = document.getElementById('correlation-count');
    if (countBadge) {
        const withGsc = filteredData.filter(d => d.hasGsc).length;
        const withoutGsc = filteredData.filter(d => !d.hasGsc).length;
        countBadge.textContent = `${filteredData.length} pages (${withGsc} avec GSC, ${withoutGsc} sans)`;
    }

    const getColorByPosition = (position, hasGsc) => {
        if (!hasGsc) return 'rgba(108, 117, 125, 0.7)';
        if (position <= 10) return 'rgba(40, 167, 69, 0.7)';
        if (position <= 20) return 'rgba(255, 193, 7, 0.7)';
        return 'rgba(220, 53, 69, 0.7)';
    };

    const pointColors = filteredData.map(d => getColorByPosition(d.y, d.hasGsc));
    const borderColors = pointColors.map(c => c.replace('0.7', '1'));

    if (correlationChart) {
        correlationChart.destroy();
    }

    const maxScore = Math.max(...filteredData.map(d => d.x), 10);
    const dynamicMaxX = Math.ceil(maxScore / 10) * 10;

    correlationChart = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Pages',
                data: filteredData,
                backgroundColor: pointColors,
                borderColor: borderColors,
                borderWidth: 2,
                pointRadius: 6,
                pointHoverRadius: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
                padding: {
                    left: 15,
                    right: 15,
                    top: 15,
                    bottom: 15
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            const item = context[0].raw;
                            return item.url.length > 60 ? item.url.substring(0, 60) + '...' : item.url;
                        },
                        label: function(context) {
                            const item = context.raw;
                            if (item.hasGsc) {
                                return [
                                    `Score SEO: ${item.x.toFixed(1)}`,
                                    `Position: ${item.y.toFixed(1)}`,
                                    `Mot-clé: ${item.query ? (item.query.length > 40 ? item.query.substring(0, 40) + '...' : item.query) : 'N/A'}`,
                                    `Impressions: ${item.impressions.toLocaleString()}`
                                ];
                            } else {
                                return [
                                    `Score SEO: ${item.x.toFixed(1)}`,
                                    `Position: 100 (pas de mot-clé GSC)`
                                ];
                            }
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: { display: true, text: 'Score SEO', font: { weight: 'bold' } },
                    min: Math.max(0, scoreMin - 5),
                    max: Math.min(100, dynamicMaxX + 5),
                    grid: { color: 'rgba(0, 0, 0, 0.05)' },
                    ticks: {
                        padding: 10
                    }
                },
                y: {
                    title: { display: true, text: 'Position GSC', font: { weight: 'bold' } },
                    reverse: true,
                    min: 0,
                    max: 105,
                    grid: { color: 'rgba(0, 0, 0, 0.05)' },
                    ticks: {
                        padding: 10
                    }
                }
            }
        }
    });
}

// Graphique : Distribution du Jus SEO (Rank vs No-Rank)
function initializeJuiceDistributionChart() {
    const ctx = document.getElementById('juiceDistributionChart');
    if (!ctx) return;

    let rankingPages = [];
    let noRankingPages = [];

    resultsData.urls.forEach(url => {
        const hasRanking = url.gsc_best_keyword && url.gsc_best_keyword.position <= 12;
        if (hasRanking) {
            rankingPages.push(url);
        } else {
            noRankingPages.push(url);
        }
    });

    const rankingJuice = rankingPages.reduce((sum, u) => sum + u.seo_score, 0);
    const noRankingJuice = noRankingPages.reduce((sum, u) => sum + u.seo_score, 0);
    const totalJuice = rankingJuice + noRankingJuice;

    const rankingPercent = totalJuice > 0 ? ((rankingJuice / totalJuice) * 100).toFixed(1) : 0;
    const noRankingPercent = totalJuice > 0 ? ((noRankingJuice / totalJuice) * 100).toFixed(1) : 0;

    // Mettre à jour les statistiques dans tous les emplacements
    ['stat-ranking-pages', 'stat-ranking-pages-2'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = rankingPages.length;
    });

    ['stat-noranking-pages', 'stat-noranking-pages-2'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = noRankingPages.length;
    });

    const statWasted = document.getElementById('stat-wasted-juice');
    if (statWasted) statWasted.textContent = noRankingPercent + '%';

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Pages qui rankent (pos. ≤12)', 'Pages sans ranking'],
            datasets: [{
                data: [rankingJuice, noRankingJuice],
                backgroundColor: ['rgba(40, 167, 69, 0.8)', 'rgba(220, 53, 69, 0.8)'],
                borderColor: ['rgba(40, 167, 69, 1)', 'rgba(220, 53, 69, 1)'],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: true, position: 'bottom' },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.parsed;
                            const percent = totalJuice > 0 ? ((value / totalJuice) * 100).toFixed(1) : 0;
                            const count = context.dataIndex === 0 ? rankingPages.length : noRankingPages.length;
                            return [
                                `Score SEO total: ${value.toFixed(1)}`,
                                `${percent}% du jus total`,
                                `${count} pages`
                            ];
                        }
                    }
                }
            }
        }
    });

    const statsContainer = document.getElementById('juice-distribution-stats');
    if (statsContainer) {
        statsContainer.innerHTML = `
            <div class="row text-center small">
                <div class="col-6">
                    <span class="text-success fw-bold">${rankingPercent}%</span> génère du trafic
                </div>
                <div class="col-6">
                    <span class="text-danger fw-bold">${noRankingPercent}%</span> gaspillé
                </div>
            </div>
        `;
    }
}

// ==================== DATATABLES ====================

function initializeUrlsTable() {
    const table = document.getElementById('urls-table');
    if (!table) return;

    const dataTable = $('#urls-table').DataTable({
        pageLength: -1,
        lengthMenu: [[25, 50, 100, -1], [25, 50, 100, "Tout"]],
        order: [[1, 'desc']],
        scrollY: '500px',
        scrollCollapse: false,
        scrollX: false,
        paging: false,
        dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"i>>' +
             '<"row"<"col-sm-12"tr>>',
        language: {
            url: 'https://cdn.datatables.net/plug-ins/1.13.7/i18n/fr-FR.json',
            info: "Affichage de _TOTAL_ résultats",
            infoFiltered: " (filtrés parmi _MAX_)",
            infoEmpty: "Aucun résultat",
            zeroRecords: "Aucun résultat trouvé"
        },
        columnDefs: [
            { targets: [1, 2, 3, 4], className: 'text-center' },
            { targets: 0, width: '30%' },
            { targets: 5, width: '25%' },
            { targets: 6, width: '10%' }
        ]
    });

    // Peupler le filtre catégorie
    const categories = [];
    dataTable.column(6).data().unique().sort().each(function(d) {
        const match = d.match(/>([^<]+)</);
        const categoryText = match ? match[1] : d;
        if (categoryText && !categories.includes(categoryText)) {
            categories.push(categoryText);
            $('#category-filter').append('<option value="' + categoryText + '">' + categoryText + '</option>');
        }
    });

    // Filtres
    $('#url-filter').on('keyup', function() {
        dataTable.column(0).search(this.value).draw();
    });

    $('#category-filter').on('change', function() {
        dataTable.column(6).search(this.value).draw();
    });

    $.fn.dataTable.ext.search.push(function(settings, data, dataIndex) {
        const scoreMin = parseFloat($('#score-min-filter').val()) || 0;
        const backlinksMin = parseFloat($('#backlinks-filter').val()) || 0;

        const scoreMatch = data[1].match(/([\d.]+)/);
        const score = scoreMatch ? parseFloat(scoreMatch[1]) : 0;

        const backlinksMatch = data[2].match(/(\d+)/);
        const backlinks = backlinksMatch ? parseInt(backlinksMatch[1]) : 0;

        if (score < scoreMin) return false;
        if (backlinks < backlinksMin) return false;

        return true;
    });

    $('#score-min-filter, #backlinks-filter').on('keyup change', function() {
        dataTable.draw();
    });

    $('#reset-filters').on('click', function() {
        $('#url-filter').val('');
        $('#category-filter').val('');
        $('#score-min-filter').val('');
        $('#backlinks-filter').val('');
        dataTable.search('').columns().search('').draw();
    });
}

// ==================== EXPORT ====================

async function exportToGoogleSheets() {
    const btn = document.getElementById('export-sheets-btn');
    const originalText = btn.innerHTML;

    try {
        btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Export...';

        const response = await fetch(`/export-sheets/${analysisId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (data.status === 'success') {
            alert('Export vers Google Sheets réussi ! (Fonctionnalité à venir)');
        } else {
            throw new Error(data.message);
        }

    } catch (error) {
        alert('Erreur : ' + error.message);
    } finally {
        btn.innerHTML = originalText;
    }
}

// ==================== UTILITAIRES ====================

function generateColors(count) {
    const colors = [];
    const hueStep = 360 / count;

    for (let i = 0; i < count; i++) {
        const hue = i * hueStep;
        colors.push(`hsla(${hue}, 70%, 60%, 0.7)`);
    }

    return colors;
}

// ==================== PHASE 2: Tableaux spécifiques ====================

function initializePhase2Tables() {
    initializeQuickWinsTable();
    initializeWastefulPagesTable();
}

function initializeQuickWinsTable() {
    const table = document.getElementById('quick-wins-table');
    if (!table) return;

    const rows = table.querySelectorAll('tbody tr.quick-win-row');
    const count = rows.length;

    const countBadge = document.getElementById('quick-wins-count');
    if (countBadge) {
        countBadge.textContent = count + ' opportunité' + (count > 1 ? 's' : '');
    }

    if (count === 0) {
        const card = table.closest('.card');
        if (card) {
            const cardBody = card.querySelector('.card-body');
            if (cardBody) {
                cardBody.innerHTML = '<p class="text-muted text-center py-4"><i class="bi bi-check-circle text-success me-2"></i>Aucune page en position 5-12. Excellent !</p>';
            }
        }
        return;
    }

    $('#quick-wins-table').DataTable({
        pageLength: 25,
        lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "Tout"]],
        order: [[1, 'asc']],
        scrollY: '400px',
        scrollCollapse: true,
        paging: count > 25,
        dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"i>>' +
             '<"row"<"col-sm-12"tr>>',
        language: {
            url: 'https://cdn.datatables.net/plug-ins/1.13.7/i18n/fr-FR.json',
            info: "_TOTAL_ Quick Win" + (count > 1 ? 's' : ''),
            infoEmpty: "Aucun Quick Win"
        }
    });
}

function initializeWastefulPagesTable() {
    const table = document.getElementById('wasteful-pages-table');
    if (!table) return;

    const rows = table.querySelectorAll('tbody tr.wasteful-row');
    const count = rows.length;

    const countBadge = document.getElementById('wasteful-pages-count');
    if (countBadge) {
        countBadge.textContent = count + ' page' + (count > 1 ? 's' : '');
    }

    if (count === 0) {
        const card = table.closest('.card');
        if (card) {
            const cardBody = card.querySelector('.card-body');
            if (cardBody) {
                cardBody.innerHTML = '<p class="text-muted text-center py-4"><i class="bi bi-check-circle text-success me-2"></i>Toutes les pages se positionnent bien. Excellent !</p>';
            }
        }
        return;
    }

    $('#wasteful-pages-table').DataTable({
        pageLength: 25,
        lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "Tout"]],
        order: [[1, 'desc']],
        scrollY: '400px',
        scrollCollapse: true,
        paging: count > 25,
        dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"i>>' +
             '<"row"<"col-sm-12"tr>>',
        language: {
            url: 'https://cdn.datatables.net/plug-ins/1.13.7/i18n/fr-FR.json',
            info: "_TOTAL_ page" + (count > 1 ? 's' : '') + " gaspillant du jus",
            infoEmpty: "Aucune page"
        }
    });
}
