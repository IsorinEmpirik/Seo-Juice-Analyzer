// results.js - Graphiques et interactions pour la page de résultats

document.addEventListener('DOMContentLoaded', function() {
    // Initialiser les graphiques
    initializeCategoryChart();
    initializeSourcesChart();

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

// Graphique : Top sources de jus
function initializeSourcesChart() {
    const ctx = document.getElementById('sourcesChart');
    if (!ctx) return;

    const topSources = resultsData.top_juice_sources.slice(0, 10);

    const labels = topSources.map(url => {
        // Extraire le chemin de l'URL pour le label
        try {
            const urlObj = new URL(url.url);
            let path = urlObj.pathname;
            if (path.length > 30) {
                path = path.substring(0, 27) + '...';
            }
            return path || '/';
        } catch {
            return url.url.substring(0, 30) + '...';
        }
    });

    const backlinks = topSources.map(url => url.backlinks_count);
    const scores = topSources.map(url => url.seo_score);

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Nombre de Backlinks',
                    data: backlinks,
                    backgroundColor: 'rgba(75, 192, 192, 0.7)',
                    borderColor: 'rgba(75, 192, 192, 1)',
                    borderWidth: 2,
                    yAxisID: 'y'
                },
                {
                    label: 'Score SEO',
                    data: scores,
                    backgroundColor: 'rgba(255, 99, 132, 0.7)',
                    borderColor: 'rgba(255, 99, 132, 1)',
                    borderWidth: 2,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Nombre de Backlinks'
                    },
                    beginAtZero: true
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Score SEO (/100)'
                    },
                    max: 100,
                    beginAtZero: true,
                    grid: {
                        drawOnChartArea: false,
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
