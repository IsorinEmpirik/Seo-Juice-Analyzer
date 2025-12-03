// results.js - Graphiques et interactions pour la page de résultats

document.addEventListener('DOMContentLoaded', function() {
    // Initialiser les graphiques
    initializeCategoryChart();
    initializeStatusChart();

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

// Graphique : Score par catégorie
function initializeCategoryChart() {
    const ctx = document.getElementById('categoryChart');
    if (!ctx) return;

    const categories = resultsData.categories;

    // Trier par score décroissant et prendre le top 10
    const sortedCategories = Object.entries(categories)
        .sort((a, b) => b[1].avg_score - a[1].avg_score)
        .slice(0, 10);

    const labels = sortedCategories.map(([name, _]) => name);
    const data = sortedCategories.map(([_, stats]) => stats.avg_score);

    // Générer des couleurs
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
                legend: {
                    display: false
                },
                title: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Score SEO (/100)'
                    }
                },
                x: {
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45
                    }
                }
            }
        }
    });
}

// Graphique : Distribution du jus SEO par code status
function initializeStatusChart() {
    const ctx = document.getElementById('statusChart');
    if (!ctx) return;

    const juiceByStatus = resultsData.juice_by_status;

    const labels = Object.keys(juiceByStatus);
    const data = Object.values(juiceByStatus);

    // Couleurs par code status
    const colorMap = {
        '200': 'rgba(40, 167, 69, 0.7)',    // Vert
        '3xx': 'rgba(255, 193, 7, 0.7)',     // Jaune
        '4xx': 'rgba(220, 53, 69, 0.7)',     // Rouge
        '5xx': 'rgba(108, 117, 125, 0.7)',   // Gris
        'Autre': 'rgba(13, 110, 253, 0.7)'   // Bleu
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
                legend: {
                    display: true,
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value.toFixed(2)} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// Initialiser DataTables pour le tableau des URLs
function initializeUrlsTable() {
    const table = document.getElementById('urls-table');
    if (!table) return;

    // Initialiser DataTables avec options avancées
    const dataTable = $('#urls-table').DataTable({
        pageLength: -1, // Afficher toutes les lignes par défaut
        lengthMenu: [[25, 50, 100, -1], [25, 50, 100, "Tout"]],
        order: [[1, 'desc']], // Trier par score SEO décroissant
        scrollY: '600px', // Hauteur fixe avec scroll interne
        scrollCollapse: false,
        scrollX: false,
        paging: false, // Désactiver la pagination pour avoir tout visible avec scroll
        dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"i>>' +
             '<"row"<"col-sm-12"tr>>',
        language: {
            url: 'https://cdn.datatables.net/plug-ins/1.13.7/i18n/fr-FR.json',
            info: "Affichage de _TOTAL_ résultats",
            infoFiltered: " (filtrés parmi _MAX_ résultats au total)",
            infoEmpty: "Aucun résultat",
            zeroRecords: "Aucun résultat trouvé"
        },
        columnDefs: [
            {
                targets: [1, 2, 3], // Colonnes numériques (Score, Backlinks, Liens Reçus)
                className: 'text-center'
            },
            {
                targets: 0, // URL
                width: '35%'
            },
            {
                targets: 4, // Top 3 Ancres
                width: '30%'
            },
            {
                targets: 5, // Catégorie
                width: '10%'
            }
        ]
    });

    // Peupler le filtre catégorie avec les valeurs uniques
    const categories = [];
    dataTable.column(5).data().unique().sort().each(function(d) {
        // Extraire le texte du badge HTML
        const match = d.match(/>([^<]+)</);
        const categoryText = match ? match[1] : d;
        if (categoryText && !categories.includes(categoryText)) {
            categories.push(categoryText);
            $('#category-filter').append('<option value="' + categoryText + '">' + categoryText + '</option>');
        }
    });

    // === FILTRES PERSONNALISÉS ===

    // Filtre par URL (recherche partielle)
    $('#url-filter').on('keyup', function() {
        dataTable.column(0).search(this.value).draw();
    });

    // Filtre par catégorie
    $('#category-filter').on('change', function() {
        dataTable.column(5).search(this.value).draw();
    });

    // Filtre personnalisé pour le score minimum
    $.fn.dataTable.ext.search.push(function(settings, data, dataIndex) {
        const scoreMin = parseFloat($('#score-min-filter').val()) || 0;
        const backlinksMin = parseFloat($('#backlinks-filter').val()) || 0;

        // Extraire le score SEO du badge (colonne 1)
        const scoreMatch = data[1].match(/([\d.]+)/);
        const score = scoreMatch ? parseFloat(scoreMatch[1]) : 0;

        // Extraire le nombre de backlinks (colonne 2)
        const backlinksMatch = data[2].match(/(\d+)/);
        const backlinks = backlinksMatch ? parseInt(backlinksMatch[1]) : 0;

        // Vérifier les conditions
        if (score < scoreMin) return false;
        if (backlinks < backlinksMin) return false;

        return true;
    });

    // Événements pour les filtres numériques
    $('#score-min-filter, #backlinks-filter').on('keyup change', function() {
        dataTable.draw();
    });

    // Bouton reset des filtres
    $('#reset-filters').on('click', function() {
        $('#url-filter').val('');
        $('#category-filter').val('');
        $('#score-min-filter').val('');
        $('#backlinks-filter').val('');

        // Réinitialiser tous les filtres
        dataTable.search('').columns().search('').draw();
    });

    // Ajouter un indicateur visuel quand des filtres sont actifs
    $('#url-filter, #category-filter, #score-min-filter, #backlinks-filter').on('keyup change', function() {
        const hasFilters = $('#url-filter').val() || $('#category-filter').val() ||
                          $('#score-min-filter').val() || $('#backlinks-filter').val();

        if (hasFilters) {
            $('#reset-filters').removeClass('btn-outline-secondary').addClass('btn-warning');
        } else {
            $('#reset-filters').removeClass('btn-warning').addClass('btn-outline-secondary');
        }
    });
}

// Exporter vers Google Sheets
async function exportToGoogleSheets() {
    const btn = document.getElementById('export-sheets-btn');
    const originalText = btn.innerHTML;

    try {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Export en cours...';

        const response = await fetch(`/export-sheets/${analysisId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (data.status === 'success') {
            alert('Export vers Google Sheets réussi ! (Fonctionnalité à venir)');
        } else {
            throw new Error(data.message);
        }

    } catch (error) {
        alert('Erreur lors de l\'export : ' + error.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

// Générer des couleurs pour les graphiques
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
    // Compter et initialiser Quick Wins
    initializeQuickWinsTable();

    // Compter et initialiser Pages qui gaspillent
    initializeWastefulPagesTable();

    // Compter et initialiser Pages orphelines
    initializeOrphanPagesTable();
}

// Tableau Quick Wins (positions 5-12)
function initializeQuickWinsTable() {
    const table = document.getElementById('quick-wins-table');
    if (!table) return;

    const rows = table.querySelectorAll('tbody tr.quick-win-row');
    const count = rows.length;

    // Mettre à jour le compteur
    const countBadge = document.getElementById('quick-wins-count');
    if (countBadge) {
        countBadge.textContent = count + ' page' + (count > 1 ? 's' : '');
    }

    // Masquer la section si vide
    if (count === 0) {
        const card = table.closest('.card');
        if (card) {
            const cardBody = card.querySelector('.card-body');
            if (cardBody) {
                cardBody.innerHTML = '<p class="text-muted text-center py-4"><i class="bi bi-check-circle text-success me-2"></i>Aucune page en position 5-12 avec des impressions. Excellent !</p>';
            }
        }
        return;
    }

    // Initialiser DataTables
    $('#quick-wins-table').DataTable({
        pageLength: 25,
        lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "Tout"]],
        order: [[1, 'asc']], // Trier par position croissante (meilleures positions d'abord)
        scrollY: '400px',
        scrollCollapse: true,
        paging: count > 25,
        dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"i>>' +
             '<"row"<"col-sm-12"tr>>',
        language: {
            url: 'https://cdn.datatables.net/plug-ins/1.13.7/i18n/fr-FR.json',
            info: "_TOTAL_ Quick Win" + (count > 1 ? 's' : ''),
            infoEmpty: "Aucun Quick Win",
            zeroRecords: "Aucun résultat trouvé"
        }
    });
}

// Tableau Pages qui gaspillent le jus SEO
function initializeWastefulPagesTable() {
    const table = document.getElementById('wasteful-pages-table');
    if (!table) return;

    const rows = table.querySelectorAll('tbody tr.wasteful-row');
    const count = rows.length;

    // Mettre à jour le compteur
    const countBadge = document.getElementById('wasteful-pages-count');
    if (countBadge) {
        countBadge.textContent = count + ' page' + (count > 1 ? 's' : '');
    }

    // Masquer la section si vide
    if (count === 0) {
        const card = table.closest('.card');
        if (card) {
            const cardBody = card.querySelector('.card-body');
            if (cardBody) {
                cardBody.innerHTML = '<p class="text-muted text-center py-4"><i class="bi bi-check-circle text-success me-2"></i>Toutes les pages avec du jus SEO se positionnent bien. Excellent !</p>';
            }
        }
        return;
    }

    // Initialiser DataTables
    $('#wasteful-pages-table').DataTable({
        pageLength: 25,
        lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "Tout"]],
        order: [[1, 'desc']], // Trier par score SEO décroissant (plus gros gaspillages d'abord)
        scrollY: '400px',
        scrollCollapse: true,
        paging: count > 25,
        dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"i>>' +
             '<"row"<"col-sm-12"tr>>',
        language: {
            url: 'https://cdn.datatables.net/plug-ins/1.13.7/i18n/fr-FR.json',
            info: "_TOTAL_ page" + (count > 1 ? 's' : '') + " gaspillant du jus",
            infoEmpty: "Aucune page",
            zeroRecords: "Aucun résultat trouvé"
        }
    });
}

// Tableau Pages orphelines
function initializeOrphanPagesTable() {
    const table = document.getElementById('orphan-pages-table');
    if (!table) return;

    const rows = table.querySelectorAll('tbody tr.orphan-row');
    const count = rows.length;

    // Mettre à jour le compteur
    const countBadge = document.getElementById('orphan-pages-count');
    if (countBadge) {
        countBadge.textContent = count + ' page' + (count > 1 ? 's' : '');
    }

    // Masquer la section si vide
    if (count === 0) {
        const card = table.closest('.card');
        if (card) {
            const cardBody = card.querySelector('.card-body');
            if (cardBody) {
                cardBody.innerHTML = '<p class="text-muted text-center py-4"><i class="bi bi-check-circle text-success me-2"></i>Aucune page orpheline. Votre maillage interne est complet !</p>';
            }
        }
        return;
    }

    // Initialiser DataTables
    $('#orphan-pages-table').DataTable({
        pageLength: 25,
        lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "Tout"]],
        order: [[1, 'desc']], // Trier par score SEO décroissant (pages avec potentiel d'abord)
        scrollY: '400px',
        scrollCollapse: true,
        paging: count > 25,
        dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"i>>' +
             '<"row"<"col-sm-12"tr>>',
        language: {
            url: 'https://cdn.datatables.net/plug-ins/1.13.7/i18n/fr-FR.json',
            info: "_TOTAL_ page" + (count > 1 ? 's' : '') + " orpheline" + (count > 1 ? 's' : ''),
            infoEmpty: "Aucune page orpheline",
            zeroRecords: "Aucun résultat trouvé"
        }
    });
}
