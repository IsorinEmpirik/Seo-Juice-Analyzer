// results.js - Graphiques et interactions pour la page de résultats

// Références globales aux DataTables pour pouvoir les ajuster
let dataTables = {};

// Domaine analysé (extrait des résultats)
let analyzedDomain = '';

// Extraire le domaine des URLs
function extractDomain() {
    if (resultsData && resultsData.urls && resultsData.urls.length > 0) {
        try {
            const url = new URL(resultsData.urls[0].url);
            analyzedDomain = url.hostname.replace('www.', '');
        } catch (e) {
            analyzedDomain = 'export';
        }
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Extraire le domaine pour les exports CSV
    extractDomain();

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

    // Initialiser les boutons d'export CSV
    initializeCsvExportButtons();

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

                // Ajuster les colonnes DataTables quand l'onglet devient visible
                adjustDataTablesInTab(targetTab);
            }
        });
    });
}

// Ajuster les colonnes des DataTables dans l'onglet actif
function adjustDataTablesInTab(tabName) {
    // Petit délai pour laisser le DOM se mettre à jour
    setTimeout(() => {
        if (tabName === 'all-pages' && dataTables.urlsTable) {
            dataTables.urlsTable.columns.adjust();
        }
        if (tabName === 'opportunities') {
            if (dataTables.quickWinsTable) {
                dataTables.quickWinsTable.columns.adjust();
            }
            if (dataTables.wastefulTable) {
                dataTables.wastefulTable.columns.adjust();
            }
        }
    }, 10);
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
        autoWidth: false,
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

    // Stocker la référence pour ajustement ultérieur
    dataTables.urlsTable = dataTable;

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

// ==================== EXPORT CSV ====================

/**
 * Génère le nom du fichier CSV avec le format: domaine_tableau_date.csv
 */
function generateCsvFilename(tableName) {
    const today = new Date();
    const dateStr = today.toISOString().slice(0, 10); // YYYY-MM-DD
    const domain = analyzedDomain || 'export';
    // Nettoyer le nom pour éviter les caractères problématiques
    const cleanTableName = tableName.replace(/[^a-zA-Z0-9-_]/g, '-').toLowerCase();
    return `${domain}_${cleanTableName}_${dateStr}.csv`;
}

/**
 * Convertit un tableau HTML en CSV
 */
function tableToCSV(tableId, includeHiddenColumns = false) {
    const table = document.getElementById(tableId);
    if (!table) return '';

    const rows = [];
    const headers = [];

    // Récupérer les en-têtes
    const headerCells = table.querySelectorAll('thead th');
    headerCells.forEach(th => {
        headers.push('"' + th.textContent.trim().replace(/"/g, '""') + '"');
    });
    rows.push(headers.join(';'));

    // Récupérer les lignes de données
    const bodyRows = table.querySelectorAll('tbody tr');
    bodyRows.forEach(tr => {
        const rowData = [];
        const cells = tr.querySelectorAll('td');
        cells.forEach(td => {
            // Extraire le texte (sans HTML)
            let text = td.textContent.trim();
            // Échapper les guillemets et encadrer
            rowData.push('"' + text.replace(/"/g, '""') + '"');
        });
        if (rowData.length > 0) {
            rows.push(rowData.join(';'));
        }
    });

    return rows.join('\n');
}

/**
 * Convertit les données JSON en CSV (pour les tableaux générés dynamiquement)
 */
function dataToCSV(data, columns) {
    const rows = [];

    // En-têtes
    rows.push(columns.map(col => '"' + col.title.replace(/"/g, '""') + '"').join(';'));

    // Données
    data.forEach(item => {
        const rowData = columns.map(col => {
            let value = col.getValue ? col.getValue(item) : item[col.key];
            if (value === undefined || value === null) value = '';
            return '"' + String(value).replace(/"/g, '""') + '"';
        });
        rows.push(rowData.join(';'));
    });

    return rows.join('\n');
}

/**
 * Télécharge un fichier CSV
 */
function downloadCSV(csvContent, filename) {
    // Ajouter BOM pour Excel
    const BOM = '\uFEFF';
    const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8;' });

    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

/**
 * Export du tableau principal "Toutes les pages"
 */
function exportAllPagesCSV() {
    const columns = [
        { title: 'URL', key: 'url' },
        { title: 'Score SEO', getValue: (item) => item.seo_score.toFixed(1) },
        { title: 'Backlinks', key: 'backlinks_count' },
        { title: 'Liens Contenu', key: 'internal_links_received_content' },
        { title: 'Liens Navigation', key: 'internal_links_received_navigation' },
        { title: 'Liens Envoyés', key: 'internal_links_sent' },
        { title: 'Top 3 Ancres', getValue: (item) => item.top_3_anchors ? item.top_3_anchors.map(a => `${a.anchor} (${a.count})`).join(', ') : '' },
        { title: 'Catégorie', key: 'category' },
        { title: 'Code HTTP', key: 'status_code' }
    ];

    // Ajouter colonnes GSC si disponibles
    if (resultsData.has_gsc_data) {
        columns.push(
            { title: 'Clics GSC', getValue: (item) => item.gsc_clicks || 0 },
            { title: 'Impressions GSC', getValue: (item) => item.gsc_impressions || 0 },
            { title: 'Meilleur Mot-clé', getValue: (item) => item.gsc_best_keyword ? item.gsc_best_keyword.query : '' },
            { title: 'Position', getValue: (item) => item.gsc_best_keyword ? item.gsc_best_keyword.position.toFixed(1) : '' }
        );
    }

    const csvContent = dataToCSV(resultsData.urls, columns);
    downloadCSV(csvContent, generateCsvFilename('toutes-les-pages'));
}

/**
 * Export du tableau Quick Wins
 */
function exportQuickWinsCSV() {
    const quickWins = [];

    resultsData.urls.forEach(url => {
        if (url.gsc_keywords) {
            url.gsc_keywords.forEach(kw => {
                if (kw.position >= 5 && kw.position <= 12 && kw.impressions >= 50) {
                    quickWins.push({
                        query: kw.query,
                        position: kw.position,
                        impressions: kw.impressions,
                        clicks: kw.clicks,
                        url: url.url,
                        seo_score: url.seo_score
                    });
                }
            });
        }
    });

    // Trier par impressions décroissantes
    quickWins.sort((a, b) => b.impressions - a.impressions);

    const columns = [
        { title: 'Mot-clé', key: 'query' },
        { title: 'Position', key: 'position' },
        { title: 'Impressions', key: 'impressions' },
        { title: 'Clics', key: 'clicks' },
        { title: 'URL', key: 'url' },
        { title: 'Score SEO', getValue: (item) => item.seo_score.toFixed(1) }
    ];

    const csvContent = dataToCSV(quickWins, columns);
    downloadCSV(csvContent, generateCsvFilename('quick-wins'));
}

/**
 * Export du tableau "Pages qui gaspillent"
 */
function exportWastefulPagesCSV() {
    const wastefulPages = resultsData.urls.filter(url =>
        url.seo_score > resultsData.median_seo_score &&
        (!url.gsc_best_keyword || url.gsc_best_keyword.position > 12)
    );

    const columns = [
        { title: 'URL', key: 'url' },
        { title: 'Score SEO', getValue: (item) => item.seo_score.toFixed(1) },
        { title: 'Liens Reçus', key: 'internal_links_received' },
        { title: 'Meilleur Mot-clé', getValue: (item) => item.gsc_best_keyword ? item.gsc_best_keyword.query : 'Aucun' },
        { title: 'Position', getValue: (item) => item.gsc_best_keyword ? item.gsc_best_keyword.position.toFixed(1) : '-' },
        { title: 'Diagnostic', getValue: (item) => {
            if (!item.gsc_best_keyword) return 'Pas de mot-clé';
            if (item.gsc_best_keyword.position > 50) return 'Hors radar';
            return 'Position 13-50';
        }}
    ];

    const csvContent = dataToCSV(wastefulPages, columns);
    downloadCSV(csvContent, generateCsvFilename('pages-gaspillent-jus'));
}

/**
 * Export du tableau des erreurs
 */
function exportErrorPagesCSV() {
    if (!resultsData.error_pages_with_links) return;

    const columns = [
        { title: 'URL', key: 'url' },
        { title: 'Code Statut', key: 'status_code' },
        { title: 'Liens Reçus', key: 'internal_links_received' },
        { title: 'Score SEO', getValue: (item) => item.seo_score.toFixed(2) }
    ];

    const csvContent = dataToCSV(resultsData.error_pages_with_links, columns);
    downloadCSV(csvContent, generateCsvFilename('pages-erreur'));
}

/**
 * Export du tableau des suggestions de liens
 */
function exportLinkSuggestionsCSV() {
    if (!resultsData.link_recommendations) return;

    // Récupérer l'état des filtres
    const similarityEnabled = document.getElementById('enable-similarity-filter')?.checked ?? true;
    const maxLinksEnabled = document.getElementById('enable-max-links-filter')?.checked ?? false;
    const threshold = parseFloat(document.getElementById('similarity-threshold')?.value) || 0.85;
    const maxLinks = parseInt(document.getElementById('max-links-per-priority')?.value) || 15;
    const targetFilter = document.getElementById('target-url-filter')?.value || '';

    // Trier par similarité décroissante
    const sortedRecs = [...resultsData.link_recommendations].sort((a, b) => b.similarity - a.similarity);

    // Compter les liens par page cible pour le filtre max
    const linksCountByTarget = {};

    // Filtrer selon les critères actuels
    const filteredRecs = sortedRecs.filter(rec => {
        // Filtre par page cible
        if (targetFilter && rec.target_url !== targetFilter) return false;

        // Filtre seuil sémantique (si activé)
        if (similarityEnabled && rec.similarity < threshold) return false;

        // Filtre nombre max de liens (si activé)
        if (maxLinksEnabled) {
            linksCountByTarget[rec.target_url] = (linksCountByTarget[rec.target_url] || 0);
            if (linksCountByTarget[rec.target_url] >= maxLinks) return false;
            linksCountByTarget[rec.target_url]++;
        }

        return true;
    });

    const columns = [
        { title: 'Page Source', key: 'source_url' },
        { title: 'Page Cible', key: 'target_url' },
        { title: 'Similarité', key: 'similarity' },
        { title: 'Ancre Suggérée', key: 'suggested_anchor' }
    ];

    const csvContent = dataToCSV(filteredRecs, columns);
    downloadCSV(csvContent, generateCsvFilename('liens-a-ajouter'));
}

/**
 * Initialise tous les boutons d'export CSV
 */
function initializeCsvExportButtons() {
    // Export toutes les pages
    document.querySelectorAll('.export-csv-all-pages').forEach(btn => {
        btn.addEventListener('click', exportAllPagesCSV);
    });

    // Export Quick Wins
    document.querySelectorAll('.export-csv-quick-wins').forEach(btn => {
        btn.addEventListener('click', exportQuickWinsCSV);
    });

    // Export pages qui gaspillent
    document.querySelectorAll('.export-csv-wasteful').forEach(btn => {
        btn.addEventListener('click', exportWastefulPagesCSV);
    });

    // Export pages erreur
    document.querySelectorAll('.export-csv-errors').forEach(btn => {
        btn.addEventListener('click', exportErrorPagesCSV);
    });

    // Export suggestions de liens
    document.querySelectorAll('.export-csv-link-suggestions').forEach(btn => {
        btn.addEventListener('click', exportLinkSuggestionsCSV);
    });

    // Initialiser le filtre de similarité dynamique
    initializeSimilarityFilter();
}

/**
 * Initialise les filtres dynamiques pour les suggestions de liens
 * - Seuil de similarité sémantique (avec toggle on/off)
 * - Nombre maximum de liens par page prioritaire (avec toggle on/off)
 * - Filtre par page cible
 * - Garde-fou : au moins un filtre doit être actif
 */
function initializeSimilarityFilter() {
    const thresholdSlider = document.getElementById('similarity-threshold');
    const thresholdValue = document.getElementById('similarity-threshold-value');
    const enableSimilarityFilter = document.getElementById('enable-similarity-filter');
    const maxLinksInput = document.getElementById('max-links-per-priority');
    const enableMaxLinksFilter = document.getElementById('enable-max-links-filter');
    const targetFilter = document.getElementById('target-url-filter');
    const filterWarning = document.getElementById('filter-warning');

    if (!thresholdSlider) return;

    // Fonction pour appliquer les filtres
    const updateFilter = () => {
        const similarityEnabled = enableSimilarityFilter?.checked ?? true;
        const maxLinksEnabled = enableMaxLinksFilter?.checked ?? false;
        const threshold = parseFloat(thresholdSlider.value);
        const maxLinks = parseInt(maxLinksInput?.value) || 15;
        const targetUrl = targetFilter?.value || '';

        // Mettre à jour l'affichage de la valeur du seuil
        if (thresholdValue) {
            thresholdValue.textContent = threshold.toFixed(2);
        }

        // Activer/désactiver les inputs selon les toggles
        thresholdSlider.disabled = !similarityEnabled;
        thresholdSlider.style.opacity = similarityEnabled ? '1' : '0.5';
        if (maxLinksInput) {
            maxLinksInput.disabled = !maxLinksEnabled;
        }

        // Compter les liens par page prioritaire (pour le filtre max liens)
        const linksCountByTarget = {};

        // Récupérer toutes les lignes et les préparer pour le filtrage
        const rows = document.querySelectorAll('.link-suggestion-row');
        let visibleCount = 0;

        // D'abord, cacher toutes les lignes et réinitialiser les compteurs
        rows.forEach(row => {
            row.style.display = 'none';
        });

        // Convertir en array et trier par similarité décroissante
        const rowsArray = Array.from(rows).sort((a, b) => {
            return parseFloat(b.dataset.similarity) - parseFloat(a.dataset.similarity);
        });

        // Appliquer les filtres
        rowsArray.forEach(row => {
            const similarity = parseFloat(row.dataset.similarity);
            const target = row.dataset.target;

            // Vérifier le filtre de page cible
            if (targetUrl && target !== targetUrl) {
                return; // Ligne cachée
            }

            // Vérifier le seuil de similarité (si activé)
            if (similarityEnabled && similarity < threshold) {
                return; // Ligne cachée
            }

            // Vérifier le nombre max de liens par page (si activé)
            if (maxLinksEnabled) {
                linksCountByTarget[target] = (linksCountByTarget[target] || 0);
                if (linksCountByTarget[target] >= maxLinks) {
                    return; // Limite atteinte pour cette page cible
                }
                linksCountByTarget[target]++;
            }

            // Afficher la ligne
            row.style.display = '';
            visibleCount++;
        });

        // Mettre à jour le compteur
        const countElement = document.getElementById('filtered-suggestions-count');
        if (countElement) {
            countElement.textContent = visibleCount;
        }
    };

    // Fonction de garde-fou pour s'assurer qu'au moins un filtre est actif
    const enforceGuardrails = () => {
        const similarityEnabled = enableSimilarityFilter?.checked ?? true;
        const maxLinksEnabled = enableMaxLinksFilter?.checked ?? false;

        // Si les deux sont désactivés, réactiver le seuil de similarité
        if (!similarityEnabled && !maxLinksEnabled) {
            if (filterWarning) {
                filterWarning.classList.remove('d-none');
            }
            // Réactiver automatiquement le filtre de similarité
            if (enableSimilarityFilter) {
                enableSimilarityFilter.checked = true;
                thresholdSlider.disabled = false;
                thresholdSlider.style.opacity = '1';
            }
        } else {
            if (filterWarning) {
                filterWarning.classList.add('d-none');
            }
        }

        updateFilter();
    };

    // Écouter les changements
    thresholdSlider.addEventListener('input', updateFilter);

    if (enableSimilarityFilter) {
        enableSimilarityFilter.addEventListener('change', enforceGuardrails);
    }

    if (maxLinksInput) {
        maxLinksInput.addEventListener('input', updateFilter);
    }

    if (enableMaxLinksFilter) {
        enableMaxLinksFilter.addEventListener('change', () => {
            enforceGuardrails();
        });
    }

    if (targetFilter) {
        targetFilter.addEventListener('change', updateFilter);
    }

    // Appliquer le filtre initial
    updateFilter();
}

// ==================== EXPORT GOOGLE SHEETS ====================

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

    dataTables.quickWinsTable = $('#quick-wins-table').DataTable({
        pageLength: 25,
        lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "Tout"]],
        order: [[1, 'asc']],
        scrollY: '400px',
        scrollCollapse: true,
        autoWidth: false,
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

    dataTables.wastefulTable = $('#wasteful-pages-table').DataTable({
        pageLength: 25,
        lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "Tout"]],
        order: [[1, 'desc']],
        scrollY: '400px',
        scrollCollapse: true,
        autoWidth: false,
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
