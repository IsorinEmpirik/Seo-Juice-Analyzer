// Application JavaScript

// ============================================================
// MANUAL UPLOAD
// ============================================================

// Fichiers uploadés
let uploadedFiles = {
    screamingfrog: null,
    ahrefs: null,
    gsc: null,
    embeddings: null
};

// GSC OAuth state
let gscOAuthProperty = null;

// Initialisation au chargement de la page
document.addEventListener('DOMContentLoaded', function() {
    initializeUploadZones();
    initializeAnalyzeButton();
    initializePriorityUrlsToggle();
    initializeTooltips();
    initializeGscOAuth();
});

// Initialiser les tooltips Bootstrap
function initializeTooltips() {
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipTriggerList.forEach(function(tooltipTriggerEl) {
        new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Initialiser le toggle pour les URLs prioritaires
function initializePriorityUrlsToggle() {
    const enableCheckbox = document.getElementById('enable-priority-urls');
    const prioritySection = document.getElementById('priority-urls-section');

    if (enableCheckbox && prioritySection) {
        enableCheckbox.addEventListener('change', function() {
            if (this.checked) {
                prioritySection.classList.remove('d-none');
            } else {
                prioritySection.classList.add('d-none');
                const priorityUrlsTextarea = document.getElementById('priority-urls');
                if (priorityUrlsTextarea) priorityUrlsTextarea.value = '';
            }
        });
    }
}

// Initialiser GSC OAuth : charger les propriétés si connecté
function initializeGscOAuth() {
    const propertySelect = document.getElementById('gsc-property-select');
    if (!propertySelect) return;

    // Charger les propriétés disponibles
    fetch('/api/gsc/properties')
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success' && data.properties.length > 0) {
                propertySelect.innerHTML = '<option value="">-- Choisir une propriete --</option>';
                data.properties.forEach(prop => {
                    const opt = document.createElement('option');
                    opt.value = prop.site_url;
                    opt.textContent = prop.site_url;
                    propertySelect.appendChild(opt);
                });

                const statusEl = document.getElementById('gsc-property-status');
                if (statusEl) statusEl.textContent = `${data.properties.length} propriete(s) disponible(s)`;
            } else {
                propertySelect.innerHTML = '<option value="">Aucune propriete trouvee</option>';
                const statusEl = document.getElementById('gsc-property-status');
                if (statusEl) {
                    statusEl.textContent = data.message || 'Reconnectez votre compte GSC';
                    statusEl.classList.add('text-danger');
                }
            }
        })
        .catch(err => {
            console.error('Erreur chargement propriétés GSC:', err);
            propertySelect.innerHTML = '<option value="">Erreur de chargement</option>';
        });

    // Quand une propriété est sélectionnée
    propertySelect.addEventListener('change', function() {
        gscOAuthProperty = this.value || null;
        const brandSection = document.getElementById('brand-keywords-section');
        if (brandSection) {
            if (gscOAuthProperty) {
                brandSection.classList.remove('d-none');
                const gscZone = document.getElementById('gsc-zone');
                if (gscZone) gscZone.classList.add('uploaded');
                const statusEl = document.getElementById('gsc-property-status');
                if (statusEl) {
                    statusEl.textContent = 'Les donnees seront recuperees via l\'API';
                    statusEl.classList.remove('text-danger');
                    statusEl.classList.add('text-success');
                }
            } else {
                brandSection.classList.add('d-none');
                const gscZone = document.getElementById('gsc-zone');
                if (gscZone) gscZone.classList.remove('uploaded');
                const statusEl = document.getElementById('gsc-property-status');
                if (statusEl) {
                    statusEl.textContent = '';
                    statusEl.classList.remove('text-success');
                }
            }
        }
    });
}

// Initialiser les zones d'upload
function initializeUploadZones() {
    setupUploadZone('screamingfrog');
    setupUploadZone('ahrefs');
    setupUploadZone('gsc');
    setupUploadZone('embeddings');
}

// Configurer une zone d'upload
function setupUploadZone(type) {
    const zone = document.getElementById(`${type}-zone`);
    const input = document.getElementById(`${type}-input`);
    const fileName = document.getElementById(`${type}-file-name`);
    const browseBtn = document.getElementById(`${type}-browse-btn`);

    if (!zone || !input) return;

    if (browseBtn) {
        browseBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            input.click();
        });
    }

    zone.addEventListener('click', (e) => {
        if (e.target === browseBtn || e.target === input || (browseBtn && browseBtn.contains(e.target))) {
            return;
        }
        // Don't trigger file input if clicking on modal links, other buttons, or selects
        if (e.target.closest('a[data-bs-toggle="modal"]') || e.target.closest('a[href]') || e.target.closest('select')) {
            return;
        }
        input.click();
    });

    input.addEventListener('change', (e) => {
        handleFileSelect(e.target.files[0], type);
    });

    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.classList.add('dragover');
    });

    zone.addEventListener('dragleave', () => {
        zone.classList.remove('dragover');
    });

    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('dragover');
        const file = e.dataTransfer.files[0];
        handleFileSelect(file, type);
    });
}

// Gérer la sélection d'un fichier
function handleFileSelect(file, type) {
    if (!file) return;

    if (!file.name.endsWith('.csv')) {
        alert('Veuillez sélectionner un fichier CSV');
        return;
    }

    uploadedFiles[type] = file;

    const zone = document.getElementById(`${type}-zone`);
    const fileName = document.getElementById(`${type}-file-name`);

    zone.classList.add('uploaded');
    fileName.textContent = `✓ ${file.name}`;

    if (type === 'gsc') {
        const brandSection = document.getElementById('brand-keywords-section');
        if (brandSection) {
            brandSection.classList.remove('d-none');
        }
    }

    checkAnalyzeButton();
}

// Vérifier si on peut activer le bouton d'analyse
function checkAnalyzeButton() {
    const btn = document.getElementById('analyze-btn');

    if (uploadedFiles.screamingfrog && uploadedFiles.ahrefs && uploadedFiles.embeddings) {
        btn.disabled = false;
        btn.classList.add('pulse');
    } else {
        btn.disabled = true;
        btn.classList.remove('pulse');
    }
}

// Initialiser le bouton d'analyse
function initializeAnalyzeButton() {
    const btn = document.getElementById('analyze-btn');

    if (btn) {
        btn.addEventListener('click', launchAnalysis);
    }
}

// Lancer l'analyse manuelle (avec prévisualisation)
async function launchAnalysis() {
    const progressSection = document.getElementById('progress-section');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const analyzeBtn = document.getElementById('analyze-btn');

    analyzeBtn.disabled = true;
    progressSection.classList.remove('d-none');

    const formData = new FormData();
    formData.append('screamingfrog', uploadedFiles.screamingfrog);
    formData.append('ahrefs', uploadedFiles.ahrefs);

    // GSC : soit un fichier CSV, soit une propriété OAuth
    if (uploadedFiles.gsc) {
        formData.append('gsc', uploadedFiles.gsc);
        const brandKeywordsTextarea = document.getElementById('brand-keywords');
        if (brandKeywordsTextarea && brandKeywordsTextarea.value.trim()) {
            formData.append('brand_keywords', brandKeywordsTextarea.value.trim());
        }
    } else if (gscOAuthProperty) {
        formData.append('gsc_oauth_property', gscOAuthProperty);
        const brandKeywordsTextarea = document.getElementById('brand-keywords');
        if (brandKeywordsTextarea && brandKeywordsTextarea.value.trim()) {
            formData.append('brand_keywords', brandKeywordsTextarea.value.trim());
        }
    }

    formData.append('embeddings', uploadedFiles.embeddings);

    const enablePriorityCheckbox = document.getElementById('enable-priority-urls');
    if (enablePriorityCheckbox && enablePriorityCheckbox.checked) {
        const priorityUrlsTextarea = document.getElementById('priority-urls');
        if (priorityUrlsTextarea && priorityUrlsTextarea.value.trim()) {
            formData.append('priority_urls', priorityUrlsTextarea.value.trim());
        }
    }

    try {
        updateProgress(30, 'Upload des fichiers...');

        const response = await fetch('/upload-preview', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.status === 'error') {
            throw new Error(data.message);
        }

        updateProgress(70, 'Préparation de la prévisualisation...');

        setTimeout(() => {
            window.location.href = `/preview/${data.upload_id}`;
        }, 500);

    } catch (error) {
        console.error('Erreur:', error);
        alert('Une erreur est survenue : ' + error.message);
        progressSection.classList.add('d-none');
        analyzeBtn.disabled = false;
    }
}

// Mettre à jour la barre de progression manuelle
function updateProgress(percent, text) {
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');

    progressBar.style.width = percent + '%';
    progressBar.textContent = percent + '%';
    progressText.textContent = text;
}
