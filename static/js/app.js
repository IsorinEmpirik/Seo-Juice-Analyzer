// Application JavaScript

// Fichiers uploadés
let uploadedFiles = {
    screamingfrog: null,
    ahrefs: null
};

// Initialisation au chargement de la page
document.addEventListener('DOMContentLoaded', function() {
    initializeUploadZones();
    initializeAnalyzeButton();
});

// Initialiser les zones d'upload
function initializeUploadZones() {
    // Screaming Frog
    setupUploadZone('screamingfrog');

    // Ahrefs
    setupUploadZone('ahrefs');
}

// Configurer une zone d'upload
function setupUploadZone(type) {
    const zone = document.getElementById(`${type}-zone`);
    const input = document.getElementById(`${type}-input`);
    const fileName = document.getElementById(`${type}-file-name`);

    if (!zone || !input) return;

    // Click sur la zone
    zone.addEventListener('click', (e) => {
        if (e.target !== input) {
            input.click();
        }
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

    // Vérifier si on peut activer le bouton d'analyse
    checkAnalyzeButton();
}

// Vérifier si on peut activer le bouton d'analyse
function checkAnalyzeButton() {
    const btn = document.getElementById('analyze-btn');

    if (uploadedFiles.screamingfrog && uploadedFiles.ahrefs) {
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

// Lancer l'analyse
async function launchAnalysis() {
    const progressSection = document.getElementById('progress-section');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');

    // Afficher la barre de progression
    progressSection.classList.remove('d-none');

    // Créer le FormData
    const formData = new FormData();
    formData.append('screamingfrog', uploadedFiles.screamingfrog);
    formData.append('ahrefs', uploadedFiles.ahrefs);

    // Récupérer les paramètres
    formData.append('backlink_score', document.getElementById('backlink-score').value);
    formData.append('iterations', document.getElementById('iterations').value);
    formData.append('transmission_rate', document.getElementById('transmission-rate').value);
    formData.append('content_rate', document.getElementById('content-rate').value);

    try {
        // Simuler le progrès (à remplacer par une vraie API plus tard)
        updateProgress(20, 'Upload des fichiers...');

        // TODO: Remplacer par un vrai appel API
        await new Promise(resolve => setTimeout(resolve, 1000));
        updateProgress(40, 'Parsing des CSV...');

        await new Promise(resolve => setTimeout(resolve, 1000));
        updateProgress(60, 'Calcul du jus SEO...');

        await new Promise(resolve => setTimeout(resolve, 1000));
        updateProgress(80, 'Génération des statistiques...');

        await new Promise(resolve => setTimeout(resolve, 1000));
        updateProgress(100, 'Analyse terminée !');

        // Rediriger vers les résultats
        setTimeout(() => {
            window.location.href = '/results';
        }, 500);

    } catch (error) {
        console.error('Erreur:', error);
        alert('Une erreur est survenue lors de l\'analyse');
        progressSection.classList.add('d-none');
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
