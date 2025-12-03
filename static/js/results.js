// results.js - Graphiques et interactions pour la page de résultats

document.addEventListener('DOMContentLoaded', function() {
    // Initialiser les graphiques
    initializeCategoryChart();
    initializeStatusChart();

    // Initialiser DataTables pour le tableau des URLs
    initializeUrlsTable();

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
            url: '//cdn.datatables.net/plug-ins/1.13.7/i18n/fr-FR.json',
            info: "Affichage de _TOTAL_ résultats",
            infoFiltered: " (filtrés parmi _MAX_ résultats au total)",
            infoEmpty: "Aucun résultat",
            zeroRecords: "Aucun résultat trouvé"
        },
        columnDefs: [
            {
                targets: [1, 2, 3, 4, 5], // Colonnes numériques
                className: 'text-center'
            },
            {
                targets: 0, // URL
                width: '30%'
            },
            {
                targets: 6, // Top 3 Ancres
                width: '25%'
            },
            {
                targets: 7, // Catégorie
                width: '8%'
            }
        ]
    });

    // Peupler le filtre catégorie avec les valeurs uniques
    const categories = [];
    dataTable.column(7).data().unique().sort().each(function(d) {
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
        dataTable.column(7).search(this.value).draw();
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
