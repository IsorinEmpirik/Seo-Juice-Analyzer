// Application JavaScript

// Fichiers uploadés
let uploadedFiles = {
    screamingfrog: null,
    ahrefs: null,
    gsc: null,
    embeddings: null
};

// Initialisation au chargement de la page
document.addEventListener('DOMContentLoaded', function() {
    initializeUploadZones();
    initializeAnalyzeButton();
    initializePriorityUrlsToggle();
    initializeTooltips();
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
                // Reset les URLs prioritaires si désactivé
                const priorityUrlsTextarea = document.getElementById('priority-urls');
                if (priorityUrlsTextarea) priorityUrlsTextarea.value = '';
            }
        });
    }
}

// Initialiser les zones d'upload
function initializeUploadZones() {
    // Screaming Frog
    setupUploadZone('screamingfrog');

    // Ahrefs
    setupUploadZone('ahrefs');

    // GSC (optionnel)
    setupUploadZone('gsc');

    // Embeddings (optionnel, pour pages prioritaires)
    setupUploadZone('embeddings');
}

// Configurer une zone d'upload
function setupUploadZone(type) {
    const zone = document.getElementById(`${type}-zone`);
    const input = document.getElementById(`${type}-input`);
    const fileName = document.getElementById(`${type}-file-name`);
    const browseBtn = document.getElementById(`${type}-browse-btn`);

    if (!zone || !input) return;

    // Click sur le bouton Parcourir uniquement
    if (browseBtn) {
        browseBtn.addEventListener('click', (e) => {
            e.stopPropagation(); // Empêcher la propagation au parent
            input.click();
        });
    }

    // Click sur la zone (mais pas sur le bouton)
    zone.addEventListener('click', (e) => {
        // Ne pas ouvrir si on clique sur le bouton ou l'input
        if (e.target === browseBtn || e.target === input || browseBtn.contains(e.target)) {
            return;
        }
        input.click();
    });

    // Changement de fichier
    input.addEventListener('change', (e) => {
        handleFileSelect(e.target.files[0], type);
    });

    // Drag & Drop
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

    // Vérifier que c'est un CSV
    if (!file.name.endsWith('.csv')) {
        alert('Veuillez sélectionner un fichier CSV');
        return;
    }

    // Stocker le fichier
    uploadedFiles[type] = file;

    // Mettre à jour l'interface
    const zone = document.getElementById(`${type}-zone`);
    const fileName = document.getElementById(`${type}-file-name`);

    zone.classList.add('uploaded');
    fileName.textContent = `✓ ${file.name}`;

    // Afficher la section des mots-clés marque si GSC est uploadé
    if (type === 'gsc') {
        const brandSection = document.getElementById('brand-keywords-section');
        if (brandSection) {
            brandSection.classList.remove('d-none');
        }
    }

    // Vérifier si on peut activer le bouton d'analyse
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

// Lancer l'analyse (avec prévisualisation)
async function launchAnalysis() {
    const progressSection = document.getElementById('progress-section');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const analyzeBtn = document.getElementById('analyze-btn');

    // Désactiver le bouton
    analyzeBtn.disabled = true;

    // Afficher la barre de progression
    progressSection.classList.remove('d-none');

    // Créer le FormData
    const formData = new FormData();
    formData.append('screamingfrog', uploadedFiles.screamingfrog);
    formData.append('ahrefs', uploadedFiles.ahrefs);

    // Ajouter GSC si présent (optionnel)
    if (uploadedFiles.gsc) {
        formData.append('gsc', uploadedFiles.gsc);

        // Récupérer les mots-clés marque
        const brandKeywordsTextarea = document.getElementById('brand-keywords');
        if (brandKeywordsTextarea && brandKeywordsTextarea.value.trim()) {
            formData.append('brand_keywords', brandKeywordsTextarea.value.trim());
        }
    }

    // Toujours ajouter le fichier d'embeddings (obligatoire)
    formData.append('embeddings', uploadedFiles.embeddings);

    // Ajouter les URLs prioritaires si activées (optionnel)
    const enablePriorityCheckbox = document.getElementById('enable-priority-urls');
    if (enablePriorityCheckbox && enablePriorityCheckbox.checked) {
        const priorityUrlsTextarea = document.getElementById('priority-urls');
        if (priorityUrlsTextarea && priorityUrlsTextarea.value.trim()) {
            formData.append('priority_urls', priorityUrlsTextarea.value.trim());
        }
    }

    try {
        updateProgress(30, 'Upload des fichiers...');

        // Upload pour prévisualisation
        const response = await fetch('/upload-preview', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.status === 'error') {
            throw new Error(data.message);
        }

        updateProgress(70, 'Préparation de la prévisualisation...');

        // Rediriger vers la page de prévisualisation
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

// Mettre à jour la barre de progression
function updateProgress(percent, text) {
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');

    progressBar.style.width = percent + '%';
    progressBar.textContent = percent + '%';
    progressText.textContent = text;
}
