// graph.js - Visualisation interactive du maillage interne avec Cytoscape.js

let cy = null;
let graphData = null;
let graphInitialized = false;

// État des modifications
const modifications = {
    added: [],    // [{source, target, link_type}]
    removed: []   // [{source, target, edgeId}]
};

// État du mode création de lien
let linkCreationMode = false;
let linkCreationSource = null;

// Debounce timer pour le recalcul PageRank
let recalcDebounceTimer = null;

// URL de la homepage détectée
let homepageUrl = null;

// Pages désactivées du menu navigation (simulation)
const disabledNavPages = new Set();

// Cache des liens navigation (pour toggle rapide)
let allNavLinks = []; // [{source, target, edgeId}]

// Vérifier et enregistrer le plugin fcose
let fcoseAvailable = false;
try {
    if (typeof cytoscape !== 'undefined' && typeof cytoscapeFcose !== 'undefined') {
        cytoscape.use(cytoscapeFcose);
        fcoseAvailable = true;
    }
} catch (e) {
    console.warn('fcose plugin non disponible, fallback sur cose:', e);
}

// ==================== INITIALISATION ====================

function initializeGraphTab() {
    if (graphInitialized) return;
    graphInitialized = true;

    loadGraphData();
}

async function loadGraphData() {
    const loadingEl = document.getElementById('graph-loading');

    try {
        const response = await fetch(`/api/graph-data/${analysisId}`);
        const data = await response.json();

        if (data.status !== 'success') {
            throw new Error(data.message || 'Erreur de chargement');
        }

        graphData = data;

        // Détecter la homepage
        homepageUrl = findHomepage(data.nodes);

        // Extraire tous les liens navigation pour le panneau toggle
        extractNavLinks(data.edges);

        populateDirectoryFilter(data.directories);

        // Mettre le filtre par défaut sur "Contenu" avant d'initialiser
        const linkTypeSelect = document.getElementById('graph-filter-link-type');
        if (linkTypeSelect) linkTypeSelect.value = 'Contenu';

        initializeCytoscape(data);
        initializeNavLinksPanel();

        if (loadingEl) loadingEl.classList.add('d-none');

    } catch (error) {
        console.error('Erreur chargement graphe:', error);
        if (loadingEl) {
            loadingEl.innerHTML = `
                <div class="text-center">
                    <i class="bi bi-exclamation-triangle text-danger" style="font-size: 2rem;"></i>
                    <p class="text-muted mt-2">Erreur: ${error.message}</p>
                    <button class="btn btn-outline-primary btn-sm" onclick="loadGraphData()">Réessayer</button>
                </div>`;
        }
    }
}

function findHomepage(nodes) {
    // Chercher l'URL racine (path = "/")
    const rootNode = nodes.find(n => {
        try {
            return new URL(n.id).pathname === '/';
        } catch(e) {
            return false;
        }
    });
    if (rootNode) return rootNode.id;

    // Fallback: page avec le plus de backlinks
    if (nodes.length > 0) {
        const best = nodes.reduce((b, n) =>
            n.backlinks_count > b.backlinks_count ? n : b, nodes[0]);
        return best.id;
    }
    return null;
}

function extractNavLinks(edges) {
    // Collecter tous les liens de type navigation pour le panneau toggle
    allNavLinks = [];
    const navTargets = {};

    edges.forEach(edge => {
        const pos = (edge.link_type || '').toLowerCase();
        if (pos !== 'contenu' && pos !== 'content') {
            allNavLinks.push({
                source: edge.source,
                target: edge.target,
                edgeId: edge.id,
                link_type: edge.link_type
            });
            // Compter les liens reçus par page cible
            if (!navTargets[edge.target]) {
                navTargets[edge.target] = { url: edge.target, count: 0 };
            }
            navTargets[edge.target].count++;
        }
    });

    // Stocker pour le panneau
    allNavLinks._targetsSummary = Object.values(navTargets)
        .sort((a, b) => b.count - a.count);
}

function populateDirectoryFilter(directories) {
    const select = document.getElementById('graph-filter-directory');
    if (!select) return;

    directories.forEach(dir => {
        const option = document.createElement('option');
        option.value = dir;
        option.textContent = '/' + dir;
        select.appendChild(option);
    });
}

// ==================== CYTOSCAPE ====================

function initializeCytoscape(data) {
    // Appliquer le filtre initial (Contenu uniquement, top 100 pages)
    const { filteredNodes, filteredEdges } = applyFilters(data);

    // Construire les éléments Cytoscape
    const elements = buildCytoscapeElements(filteredNodes, filteredEdges);

    cy = cytoscape({
        container: document.getElementById('cytoscape-container'),
        elements: elements,
        style: getCytoscapeStyle(),
        layout: getLayout(filteredNodes.length),
        minZoom: 0.1,
        maxZoom: 5,
        wheelSensitivity: 0.3,
        boxSelectionEnabled: false,
        autoungrabify: false // Noeuds déplaçables
    });

    // Événements
    setupCytoscapeEvents();
    setupFilterListeners();
    setupButtonListeners();
    updateStats();

    // Centrer sur la homepage après le layout
    if (homepageUrl) {
        setTimeout(() => {
            const hp = cy.getElementById(homepageUrl);
            if (hp.length) {
                cy.center(hp);
                cy.zoom({ level: cy.zoom(), position: hp.position() });
            }
        }, 100);
    }
}

function buildCytoscapeElements(nodes, edges) {
    const elements = [];

    // Noeuds
    nodes.forEach(node => {
        const isHomepage = node.id === homepageUrl;
        elements.push({
            group: 'nodes',
            data: {
                id: node.id,
                label: node.label,
                seo_score: node.seo_score,
                category: node.category,
                directory: node.directory,
                backlinks_count: node.backlinks_count,
                internal_links_received: node.internal_links_received,
                internal_links_sent: node.internal_links_sent,
                status_code: node.status_code,
                isHomepage: isHomepage,
                nodeSize: isHomepage
                    ? Math.max(40, Math.min(80, 25 + node.seo_score * 0.55))
                    : Math.max(20, Math.min(60, 15 + node.seo_score * 0.45)),
                nodeColor: getScoreColor(node.seo_score)
            }
        });
    });

    // Arêtes
    const nodeIds = new Set(nodes.map(n => n.id));
    edges.forEach(edge => {
        if (nodeIds.has(edge.source) && nodeIds.has(edge.target)) {
            elements.push({
                group: 'edges',
                data: {
                    id: edge.id,
                    source: edge.source,
                    target: edge.target,
                    link_type: edge.link_type,
                    anchor: edge.anchor,
                    similarity: edge.similarity,
                    edgeColor: edge.link_type === 'Navigation' ? '#6c757d' : '#0d6efd',
                    edgeStyle: edge.link_type === 'Navigation' ? 'dashed' : 'solid',
                    isNew: false,
                    simLabel: edge.similarity !== null ? edge.similarity.toFixed(2) : ''
                }
            });
        }
    });

    return elements;
}

function getScoreColor(score) {
    if (score >= 80) return '#28a745';
    if (score >= 60) return '#20c997';
    if (score >= 40) return '#ffc107';
    if (score >= 20) return '#fd7e14';
    return '#dc3545';
}

function getCytoscapeStyle() {
    return [
        {
            selector: 'node',
            style: {
                'label': 'data(label)',
                'width': 'data(nodeSize)',
                'height': 'data(nodeSize)',
                'background-color': 'data(nodeColor)',
                'border-width': 2,
                'border-color': '#fff',
                'color': '#333',
                'font-size': '8px',
                'text-valign': 'bottom',
                'text-halign': 'center',
                'text-margin-y': 5,
                'text-max-width': '80px',
                'text-wrap': 'ellipsis',
                'text-outline-color': '#fff',
                'text-outline-width': 2,
                'min-zoomed-font-size': 6,
                'z-index': 10
            }
        },
        // Homepage: bordure dorée
        {
            selector: 'node[?isHomepage]',
            style: {
                'border-width': 4,
                'border-color': '#ffc107',
                'font-size': '10px',
                'font-weight': 'bold',
                'z-index': 20
            }
        },
        {
            selector: 'node:selected',
            style: {
                'border-width': 4,
                'border-color': '#0d6efd',
                'overlay-color': '#0d6efd',
                'overlay-padding': 4,
                'overlay-opacity': 0.2
            }
        },
        {
            selector: 'node.highlighted',
            style: {
                'border-width': 4,
                'border-color': '#e83e8c',
                'overlay-color': '#e83e8c',
                'overlay-padding': 4,
                'overlay-opacity': 0.15
            }
        },
        {
            selector: 'node.link-source',
            style: {
                'border-width': 5,
                'border-color': '#28a745',
                'overlay-color': '#28a745',
                'overlay-padding': 6,
                'overlay-opacity': 0.25
            }
        },
        {
            selector: 'node.dimmed',
            style: {
                'opacity': 0.15
            }
        },
        // Noeuds déplacés par l'utilisateur
        {
            selector: 'node:grabbed',
            style: {
                'border-width': 3,
                'border-color': '#0d6efd',
                'overlay-color': '#0d6efd',
                'overlay-padding': 4,
                'overlay-opacity': 0.1
            }
        },
        {
            selector: 'edge',
            style: {
                'width': 1.5,
                'line-color': 'data(edgeColor)',
                'target-arrow-color': 'data(edgeColor)',
                'target-arrow-shape': 'triangle',
                'curve-style': 'bezier',
                'arrow-scale': 0.8,
                'opacity': 0.4,
                'line-style': 'data(edgeStyle)',
                'label': 'data(simLabel)',
                'font-size': '6px',
                'text-rotation': 'autorotate',
                'text-outline-color': '#fff',
                'text-outline-width': 1.5,
                'color': '#666',
                'min-zoomed-font-size': 8
            }
        },
        {
            selector: 'edge:selected',
            style: {
                'width': 3,
                'opacity': 1,
                'line-color': '#e83e8c',
                'target-arrow-color': '#e83e8c'
            }
        },
        {
            selector: 'edge.new-link',
            style: {
                'width': 3,
                'line-color': '#28a745',
                'target-arrow-color': '#28a745',
                'line-style': 'dashed',
                'opacity': 0.9
            }
        },
        {
            selector: 'edge.to-remove',
            style: {
                'width': 3,
                'line-color': '#dc3545',
                'target-arrow-color': '#dc3545',
                'line-style': 'dotted',
                'opacity': 0.9
            }
        },
        {
            selector: 'edge.dimmed',
            style: {
                'opacity': 0.05
            }
        }
    ];
}

function getLayout(nodeCount) {
    // Contrainte: homepage au centre si disponible
    const fixedConstraints = [];
    if (homepageUrl && fcoseAvailable) {
        fixedConstraints.push({ nodeId: homepageUrl, position: { x: 0, y: 0 } });
    }

    if (!fcoseAvailable) {
        // Fallback: layout cose intégré à Cytoscape
        return {
            name: 'cose',
            animate: false,
            randomize: true,
            nodeRepulsion: function() { return 15000; },
            idealEdgeLength: function() { return nodeCount <= 100 ? 200 : 120; },
            edgeElasticity: function() { return 100; },
            gravity: 0.25,
            numIter: 1000,
            nodeDimensionsIncludeLabels: true
        };
    }

    if (nodeCount <= 100) {
        return {
            name: 'fcose',
            animate: false,
            quality: 'default',
            randomize: true,
            fixedNodeConstraint: fixedConstraints.length > 0 ? fixedConstraints : undefined,
            nodeSep: 150,
            idealEdgeLength: 200,
            nodeRepulsion: 15000,
            edgeElasticity: 0.1,
            gravity: 0.2,
            gravityRange: 2.5,
            numIter: 2500,
            tile: true,
            tilingPaddingVertical: 30,
            tilingPaddingHorizontal: 30
        };
    }
    // Pour les gros graphes, utiliser un layout plus rapide
    return {
        name: 'fcose',
        animate: false,
        quality: 'default',
        randomize: true,
        fixedNodeConstraint: fixedConstraints.length > 0 ? fixedConstraints : undefined,
        nodeSep: 80,
        idealEdgeLength: 120,
        nodeRepulsion: 8000,
        edgeElasticity: 0.05,
        gravity: 0.35,
        numIter: 1500,
        tile: true
    };
}

// ==================== ÉVÉNEMENTS CYTOSCAPE ====================

function setupCytoscapeEvents() {
    // Clic sur un noeud : afficher les infos
    cy.on('tap', 'node', function(evt) {
        const node = evt.target;

        if (linkCreationMode) {
            // Mode création de lien : le clic sur un noeud = définir la cible
            completeLinkCreation(node.id());
            return;
        }

        hideEdgeInfo();
        showNodeInfo(node);
        highlightConnected(node);
    });

    // Double-clic sur un noeud : démarrer la création d'un lien
    cy.on('dbltap', 'node', function(evt) {
        startLinkCreation(evt.target.id());
    });

    // Clic sur une arête : afficher les infos du lien avec option de suppression
    cy.on('tap', 'edge', function(evt) {
        const edge = evt.target;
        hideNodeInfo();
        showEdgeInfo(edge);
    });

    // Clic droit sur une arête : suppression rapide (power user)
    cy.on('cxttap', 'edge', function(evt) {
        const edge = evt.target;
        if (edge.hasClass('new-link')) {
            undoAddLink(edge.data('source'), edge.data('target'));
        } else if (!edge.hasClass('to-remove')) {
            markEdgeForRemoval(edge);
        } else {
            undoRemoveLink(edge.data('source'), edge.data('target'));
        }
    });

    // Clic sur le fond : déselectionner tout
    cy.on('tap', function(evt) {
        if (evt.target === cy) {
            clearHighlights();
            hideNodeInfo();
            hideEdgeInfo();

            if (linkCreationMode) {
                cancelLinkCreation();
            }
        }
    });

    // Escape pour annuler le mode création
    document.addEventListener('keydown', function(evt) {
        if (evt.key === 'Escape' && linkCreationMode) {
            cancelLinkCreation();
        }
    });
}

function highlightConnected(node) {
    clearHighlights();

    // Dimmer tous les éléments
    cy.elements().addClass('dimmed');

    // Mettre en avant le noeud et ses voisins
    const neighborhood = node.neighborhood().add(node);
    neighborhood.removeClass('dimmed');
    node.addClass('highlighted');
}

function clearHighlights() {
    cy.elements().removeClass('dimmed').removeClass('highlighted');
}

function showNodeInfo(node) {
    const infoDiv = document.getElementById('graph-node-info');
    const bodyDiv = document.getElementById('graph-node-info-body');
    if (!infoDiv || !bodyDiv) return;

    const d = node.data();
    const url = d.id;
    const shortUrl = url.length > 50 ? url.substring(0, 50) + '...' : url;
    const isHP = d.isHomepage ? '<span class="badge bg-warning text-dark ms-1">Homepage</span>' : '';

    bodyDiv.innerHTML = `
        <div class="small">
            <a href="${url}" target="_blank" class="text-decoration-none d-block mb-2" style="word-break: break-all;">
                ${shortUrl}
            </a>${isHP}
            <div class="row g-1 text-center mt-1">
                <div class="col-4">
                    <div class="p-1 bg-light rounded">
                        <div class="fw-bold text-primary">${d.seo_score.toFixed(1)}</div>
                        <div class="text-muted" style="font-size: 0.65rem;">Score PR</div>
                    </div>
                </div>
                <div class="col-4">
                    <div class="p-1 bg-light rounded">
                        <div class="fw-bold text-success">${d.backlinks_count}</div>
                        <div class="text-muted" style="font-size: 0.65rem;">Backlinks</div>
                    </div>
                </div>
                <div class="col-4">
                    <div class="p-1 bg-light rounded">
                        <div class="fw-bold text-info">${d.internal_links_received}</div>
                        <div class="text-muted" style="font-size: 0.65rem;">Liens reçus</div>
                    </div>
                </div>
            </div>
            <div class="mt-2">
                <span class="badge bg-secondary">${d.category}</span>
                <span class="badge ${d.status_code === 200 ? 'bg-success' : 'bg-danger'}">${d.status_code}</span>
            </div>
        </div>
    `;

    infoDiv.style.display = 'block';
}

function hideNodeInfo() {
    const infoDiv = document.getElementById('graph-node-info');
    if (infoDiv) infoDiv.style.display = 'none';
}

// ==================== INFO ARÊTE (CLIC) ====================

function showEdgeInfo(edge) {
    const infoDiv = document.getElementById('graph-edge-info');
    const bodyDiv = document.getElementById('graph-edge-info-body');
    if (!infoDiv || !bodyDiv) return;

    const d = edge.data();
    const srcPath = shortPath(d.source);
    const tgtPath = shortPath(d.target);
    const isNew = edge.hasClass('new-link');
    const isRemoved = edge.hasClass('to-remove');
    const simText = d.similarity !== null && d.similarity !== undefined ? d.similarity.toFixed(2) : '-';

    let actionBtn = '';
    if (isNew) {
        actionBtn = `<button class="btn btn-outline-danger btn-sm w-100 mt-2"
            onclick="undoAddLink('${escapeJs(d.source)}', '${escapeJs(d.target)}'); hideEdgeInfo();">
            <i class="bi bi-x-circle me-1"></i>Annuler l'ajout
        </button>`;
    } else if (isRemoved) {
        actionBtn = `<button class="btn btn-outline-success btn-sm w-100 mt-2"
            onclick="undoRemoveLink('${escapeJs(d.source)}', '${escapeJs(d.target)}'); hideEdgeInfo();">
            <i class="bi bi-arrow-counterclockwise me-1"></i>Restaurer le lien
        </button>`;
    } else {
        actionBtn = `<button class="btn btn-outline-danger btn-sm w-100 mt-2"
            onclick="markEdgeForRemovalById('${escapeJs(d.id)}'); hideEdgeInfo();">
            <i class="bi bi-trash me-1"></i>Supprimer ce lien
        </button>`;
    }

    bodyDiv.innerHTML = `
        <div class="small">
            <div class="mb-2">
                <div class="text-muted" style="font-size: 0.65rem;">SOURCE</div>
                <a href="${d.source}" target="_blank" class="text-decoration-none" style="word-break: break-all;" title="${d.source}">
                    ${srcPath}
                </a>
            </div>
            <div class="text-center my-1"><i class="bi bi-arrow-down text-primary"></i></div>
            <div class="mb-2">
                <div class="text-muted" style="font-size: 0.65rem;">CIBLE</div>
                <a href="${d.target}" target="_blank" class="text-decoration-none" style="word-break: break-all;" title="${d.target}">
                    ${tgtPath}
                </a>
            </div>
            <div class="d-flex gap-2 mt-2">
                <span class="badge ${d.link_type === 'Contenu' || d.link_type === 'Content' ? 'bg-primary' : 'bg-secondary'}">${d.link_type}</span>
                <span class="badge bg-info">Sim: ${simText}</span>
                ${d.anchor ? `<span class="badge bg-light text-dark">${d.anchor}</span>` : ''}
            </div>
            ${actionBtn}
        </div>
    `;

    infoDiv.style.display = 'block';
}

function hideEdgeInfo() {
    const infoDiv = document.getElementById('graph-edge-info');
    if (infoDiv) infoDiv.style.display = 'none';
}

function markEdgeForRemovalById(edgeId) {
    if (!cy) return;
    const edge = cy.getElementById(edgeId);
    if (edge.length) {
        markEdgeForRemoval(edge);
    }
}

// ==================== CRÉATION DE LIENS ====================

function startLinkCreation(sourceId) {
    linkCreationMode = true;
    linkCreationSource = sourceId;

    // UI feedback
    const banner = document.getElementById('graph-link-mode-banner');
    if (banner) banner.classList.remove('d-none');

    // Mettre en avant le noeud source
    const sourceNode = cy.getElementById(sourceId);
    clearHighlights();
    cy.elements().addClass('dimmed');
    sourceNode.removeClass('dimmed').addClass('link-source');

    // Montrer les cibles possibles (retirer dimmed des noeuds qui n'ont pas déjà un lien depuis la source)
    const connectedTargets = new Set();
    sourceNode.outgoers('edge').forEach(edge => {
        connectedTargets.add(edge.target().id());
    });

    cy.nodes().forEach(n => {
        if (n.id() !== sourceId && !connectedTargets.has(n.id())) {
            n.removeClass('dimmed');
        }
    });
}

function completeLinkCreation(targetId) {
    if (!linkCreationMode || !linkCreationSource || targetId === linkCreationSource) {
        cancelLinkCreation();
        return;
    }

    // Vérifier si le lien existe déjà
    const existingEdge = cy.edges().filter(e =>
        e.data('source') === linkCreationSource && e.data('target') === targetId
    );

    if (existingEdge.length > 0) {
        cancelLinkCreation();
        return;
    }

    // Demander le type de lien
    showLinkTypeModal(linkCreationSource, targetId);
}

function showLinkTypeModal(source, target) {
    // Créer un mini-modal inline
    const sourcePath = new URL(source).pathname;
    const targetPath = new URL(target).pathname;

    const existingModal = document.getElementById('link-type-modal-overlay');
    if (existingModal) existingModal.remove();

    const overlay = document.createElement('div');
    overlay.id = 'link-type-modal-overlay';
    overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:9999;display:flex;align-items:center;justify-content:center;';
    overlay.innerHTML = `
        <div class="card shadow" style="width: 400px; max-width: 90%;">
            <div class="card-header bg-success text-white">
                <h6 class="mb-0"><i class="bi bi-plus-circle me-2"></i>Nouveau lien</h6>
            </div>
            <div class="card-body">
                <p class="small mb-2"><strong>De :</strong> ${sourcePath}</p>
                <p class="small mb-3"><strong>Vers :</strong> ${targetPath}</p>
                <label class="form-label fw-bold small">Type de lien :</label>
                <div class="d-flex gap-2">
                    <button class="btn btn-primary flex-fill" id="link-type-contenu">
                        <i class="bi bi-file-text me-1"></i> Contenu
                    </button>
                    <button class="btn btn-secondary flex-fill" id="link-type-navigation">
                        <i class="bi bi-list me-1"></i> Navigation
                    </button>
                </div>
                <button class="btn btn-outline-dark btn-sm w-100 mt-2" id="link-type-cancel">Annuler</button>
            </div>
        </div>
    `;

    document.body.appendChild(overlay);

    document.getElementById('link-type-contenu').addEventListener('click', () => {
        overlay.remove();
        addNewLink(source, target, 'Contenu');
        cancelLinkCreation();
    });

    document.getElementById('link-type-navigation').addEventListener('click', () => {
        overlay.remove();
        addNewLink(source, target, 'Navigation');
        cancelLinkCreation();
    });

    document.getElementById('link-type-cancel').addEventListener('click', () => {
        overlay.remove();
        cancelLinkCreation();
    });

    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            overlay.remove();
            cancelLinkCreation();
        }
    });
}

function addNewLink(source, target, linkType) {
    // Ajouter aux modifications
    modifications.added.push({ source, target, link_type: linkType });

    // Ajouter l'arête dans Cytoscape
    const edgeId = `new_${modifications.added.length}`;
    cy.add({
        group: 'edges',
        data: {
            id: edgeId,
            source: source,
            target: target,
            link_type: linkType,
            edgeColor: '#28a745',
            edgeStyle: 'dashed',
            isNew: true,
            simLabel: 'NEW'
        },
        classes: 'new-link'
    });

    updateModificationsUI();
    triggerPageRankRecalculation();
}

function cancelLinkCreation() {
    linkCreationMode = false;
    linkCreationSource = null;

    const banner = document.getElementById('graph-link-mode-banner');
    if (banner) banner.classList.add('d-none');

    clearHighlights();
    cy.nodes().removeClass('link-source');
}

// ==================== SUPPRESSION DE LIENS ====================

function markEdgeForRemoval(edge) {
    const source = edge.data('source');
    const target = edge.data('target');
    const edgeId = edge.data('id');

    // Éviter les doublons
    if (modifications.removed.some(l => l.source === source && l.target === target)) return;

    modifications.removed.push({ source, target, edgeId });
    edge.addClass('to-remove');

    updateModificationsUI();
    triggerPageRankRecalculation();
}

function undoAddLink(source, target) {
    const idx = modifications.added.findIndex(l => l.source === source && l.target === target);
    if (idx === -1) return;

    modifications.added.splice(idx, 1);

    // Supprimer l'arête du graphe
    cy.edges().filter(e =>
        e.data('source') === source && e.data('target') === target && e.hasClass('new-link')
    ).remove();

    updateModificationsUI();
    triggerPageRankRecalculation();
}

function undoRemoveLink(source, target) {
    const idx = modifications.removed.findIndex(l => l.source === source && l.target === target);
    if (idx === -1) return;

    modifications.removed.splice(idx, 1);

    // Retirer la classe de l'arête
    cy.edges().filter(e =>
        e.data('source') === source && e.data('target') === target
    ).removeClass('to-remove');

    updateModificationsUI();
    triggerPageRankRecalculation();
}

// ==================== UI MODIFICATIONS ====================

function updateModificationsUI() {
    // Liens ajoutés
    const addedTbody = document.getElementById('added-links-tbody');
    const addedCount = document.getElementById('added-links-count');
    const noAddedMsg = document.getElementById('no-added-links-msg');

    if (addedTbody) {
        // Vider sauf le message "aucun"
        addedTbody.querySelectorAll('tr:not(#no-added-links-msg)').forEach(r => r.remove());

        if (modifications.added.length > 0) {
            if (noAddedMsg) noAddedMsg.style.display = 'none';
            modifications.added.forEach((link, idx) => {
                const srcPath = shortPath(link.source);
                const tgtPath = shortPath(link.target);
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="small" title="${link.source}">${srcPath}</td>
                    <td class="small" title="${link.target}">${tgtPath}</td>
                    <td class="small"><span class="badge ${link.link_type === 'Contenu' ? 'bg-primary' : 'bg-secondary'}">${link.link_type === 'Contenu' ? 'C' : 'N'}</span></td>
                    <td><button class="btn btn-outline-danger btn-sm py-0 px-1" onclick="undoAddLink('${escapeJs(link.source)}', '${escapeJs(link.target)}')"><i class="bi bi-x"></i></button></td>
                `;
                addedTbody.appendChild(tr);
            });
        } else {
            if (noAddedMsg) noAddedMsg.style.display = '';
        }
    }
    if (addedCount) addedCount.textContent = modifications.added.length;

    // Liens supprimés
    const removedTbody = document.getElementById('removed-links-tbody');
    const removedCount = document.getElementById('removed-links-count');
    const noRemovedMsg = document.getElementById('no-removed-links-msg');

    if (removedTbody) {
        removedTbody.querySelectorAll('tr:not(#no-removed-links-msg)').forEach(r => r.remove());

        if (modifications.removed.length > 0) {
            if (noRemovedMsg) noRemovedMsg.style.display = 'none';
            modifications.removed.forEach((link, idx) => {
                const srcPath = shortPath(link.source);
                const tgtPath = shortPath(link.target);
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="small" title="${link.source}">${srcPath}</td>
                    <td class="small" title="${link.target}">${tgtPath}</td>
                    <td><button class="btn btn-outline-success btn-sm py-0 px-1" onclick="undoRemoveLink('${escapeJs(link.source)}', '${escapeJs(link.target)}')"><i class="bi bi-arrow-counterclockwise"></i></button></td>
                `;
                removedTbody.appendChild(tr);
            });
        } else {
            if (noRemovedMsg) noRemovedMsg.style.display = '';
        }
    }
    if (removedCount) removedCount.textContent = modifications.removed.length;

    // Stats
    const modsCount = document.getElementById('graph-stats-mods');
    if (modsCount) {
        const total = modifications.added.length + modifications.removed.length;
        modsCount.textContent = total + ' modif' + (total > 1 ? 's' : '');
    }
}

function shortPath(url) {
    try {
        const path = new URL(url).pathname;
        if (path.length <= 25) return path;
        const segments = path.split('/').filter(s => s);
        if (segments.length >= 2) return '/.../' + segments[segments.length - 1];
        return path.substring(0, 22) + '...';
    } catch (e) {
        return url.substring(0, 25) + '...';
    }
}

function escapeJs(str) {
    return str.replace(/'/g, "\\'").replace(/"/g, '\\"');
}

// ==================== PANNEAU LIENS NAVIGATION ====================

function initializeNavLinksPanel() {
    const tbody = document.getElementById('nav-links-tbody');
    const countEl = document.getElementById('nav-links-count');
    if (!tbody) return;

    const targets = allNavLinks._targetsSummary || [];
    if (countEl) countEl.textContent = targets.length;

    if (targets.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="text-center text-muted small py-2">Aucun lien navigation</td></tr>';
        return;
    }

    tbody.innerHTML = '';
    targets.forEach((t, idx) => {
        const path = shortPath(t.url);
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td class="small" title="${t.url}">${path}</td>
            <td class="text-center small">${t.count}</td>
            <td class="text-center">
                <div class="form-check form-switch d-flex justify-content-center mb-0">
                    <input class="form-check-input" type="checkbox" checked
                           id="nav-toggle-${idx}" data-url="${escapeJs(t.url)}"
                           onchange="toggleNavPage('${escapeJs(t.url)}', this.checked)">
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function toggleNavPage(targetUrl, enabled) {
    if (enabled) {
        // Réactiver: retirer de la liste désactivée
        disabledNavPages.delete(targetUrl);
    } else {
        // Désactiver: ajouter à la liste
        disabledNavPages.add(targetUrl);
    }

    // Recalculer le PageRank avec les liens nav désactivés
    triggerPageRankRecalculation();
}

function getDisabledNavRemovedLinks() {
    // Pour chaque page désactivée, retourner tous les liens navigation pointant vers elle
    const removed = [];
    allNavLinks.forEach(link => {
        if (disabledNavPages.has(link.target)) {
            removed.push({ source: link.source, target: link.target });
        }
    });
    return removed;
}

// ==================== RECALCUL PAGERANK ====================

function triggerPageRankRecalculation() {
    // Debounce : attendre 600ms après la dernière modification
    clearTimeout(recalcDebounceTimer);
    recalcDebounceTimer = setTimeout(doRecalculatePageRank, 600);
}

async function doRecalculatePageRank() {
    // Combiner les modifications manuelles + les liens nav désactivés
    const navRemoved = getDisabledNavRemovedLinks();
    const allRemovedLinks = [...modifications.removed, ...navRemoved];

    if (modifications.added.length === 0 && allRemovedLinks.length === 0) {
        // Pas de modifications : afficher le message par défaut
        const tbody = document.getElementById('pagerank-impact-tbody');
        const noMsg = document.getElementById('no-impact-msg');
        if (tbody) {
            tbody.querySelectorAll('tr:not(#no-impact-msg)').forEach(r => r.remove());
        }
        if (noMsg) noMsg.style.display = '';
        return;
    }

    const loadingEl = document.getElementById('pagerank-impact-loading');
    if (loadingEl) loadingEl.classList.remove('d-none');

    try {
        const response = await fetch(`/api/recalculate-pagerank/${analysisId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                added_links: modifications.added,
                removed_links: allRemovedLinks
            })
        });

        const data = await response.json();
        if (data.status !== 'success') throw new Error(data.message);

        displayPageRankImpact(data.deltas, data.scores);

        // Mettre à jour les tailles/couleurs des noeuds dans Cytoscape
        updateNodeScores(data.scores);

    } catch (error) {
        console.error('Erreur recalcul PageRank:', error);
    } finally {
        if (loadingEl) loadingEl.classList.add('d-none');
    }
}

function displayPageRankImpact(deltas, scores) {
    const tbody = document.getElementById('pagerank-impact-tbody');
    const noMsg = document.getElementById('no-impact-msg');
    if (!tbody) return;

    tbody.querySelectorAll('tr:not(#no-impact-msg)').forEach(r => r.remove());

    // Trier les deltas par valeur absolue décroissante
    const sortedDeltas = Object.entries(deltas)
        .sort((a, b) => Math.abs(b[1].delta) - Math.abs(a[1].delta))
        .slice(0, 20);

    if (sortedDeltas.length === 0) {
        if (noMsg) {
            noMsg.style.display = '';
            noMsg.querySelector('td').textContent = 'Aucun impact significatif détecté';
        }
        return;
    }

    if (noMsg) noMsg.style.display = 'none';

    sortedDeltas.forEach(([url, info]) => {
        const path = shortPath(url);
        const deltaClass = info.delta > 0 ? 'text-success' : 'text-danger';
        const deltaSign = info.delta > 0 ? '+' : '';

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td class="small" title="${url}">${path}</td>
            <td class="text-center small">${info.old_score.toFixed(1)}</td>
            <td class="text-center small fw-bold">${info.new_score.toFixed(1)}</td>
            <td class="text-center small fw-bold ${deltaClass}">${deltaSign}${info.delta.toFixed(1)}</td>
        `;
        tbody.appendChild(tr);
    });
}

function updateNodeScores(newScores) {
    if (!cy) return;

    cy.nodes().forEach(node => {
        const url = node.id();
        const newScore = newScores[url];
        if (newScore !== undefined) {
            node.data('seo_score', newScore);
            node.data('nodeSize', Math.max(20, Math.min(60, 15 + newScore * 0.45)));
            node.data('nodeColor', getScoreColor(newScore));
        }
    });
}

// ==================== FILTRES ====================

function applyFilters(data) {
    const linkType = document.getElementById('graph-filter-link-type')?.value || 'Contenu';
    const directory = document.getElementById('graph-filter-directory')?.value || 'all';
    const similarity = parseFloat(document.getElementById('graph-filter-similarity')?.value) || 0;
    const simDirection = document.getElementById('graph-filter-sim-direction')?.value || 'above';
    const topPagesVal = document.getElementById('graph-filter-top-pages')?.value || '100';

    let filteredNodes = [...data.nodes];

    // Filtre répertoire
    if (directory !== 'all') {
        filteredNodes = filteredNodes.filter(n => n.directory === directory);
    }

    // Filtre top pages (trier par score, prendre les N premiers)
    if (topPagesVal !== 'all') {
        const topN = parseInt(topPagesVal);
        filteredNodes.sort((a, b) => b.seo_score - a.seo_score);
        filteredNodes = filteredNodes.slice(0, topN);
    }

    const nodeIds = new Set(filteredNodes.map(n => n.id));

    // Filtre arêtes
    let filteredEdges = data.edges.filter(e =>
        nodeIds.has(e.source) && nodeIds.has(e.target)
    );

    // Filtre type de lien
    if (linkType !== 'all') {
        filteredEdges = filteredEdges.filter(e => {
            const pos = (e.link_type || '').toLowerCase();
            if (linkType === 'Contenu') {
                return pos === 'contenu' || pos === 'content';
            }
            return pos !== 'contenu' && pos !== 'content';
        });
    }

    // Filtre similarité
    if (similarity > 0) {
        if (simDirection === 'below') {
            filteredEdges = filteredEdges.filter(e =>
                e.similarity !== null && e.similarity <= similarity
            );
        } else {
            filteredEdges = filteredEdges.filter(e =>
                e.similarity !== null && e.similarity >= similarity
            );
        }
    }

    return { filteredNodes, filteredEdges };
}

function rebuildGraph() {
    if (!cy || !graphData) return;

    const { filteredNodes, filteredEdges } = applyFilters(graphData);
    const elements = buildCytoscapeElements(filteredNodes, filteredEdges);

    cy.elements().remove();
    cy.add(elements);

    // Ré-ajouter les liens modifiés qui sont encore pertinents
    const nodeIds = new Set(filteredNodes.map(n => n.id));

    modifications.added.forEach((link, idx) => {
        if (nodeIds.has(link.source) && nodeIds.has(link.target)) {
            cy.add({
                group: 'edges',
                data: {
                    id: `new_re_${idx}`,
                    source: link.source,
                    target: link.target,
                    link_type: link.link_type,
                    edgeColor: '#28a745',
                    edgeStyle: 'dashed',
                    isNew: true,
                    simLabel: 'NEW'
                },
                classes: 'new-link'
            });
        }
    });

    modifications.removed.forEach(link => {
        cy.edges().filter(e =>
            e.data('source') === link.source && e.data('target') === link.target && !e.hasClass('new-link')
        ).addClass('to-remove');
    });

    cy.layout(getLayout(filteredNodes.length)).run();
    updateStats();

    // Recentrer sur la homepage
    if (homepageUrl) {
        setTimeout(() => {
            const hp = cy.getElementById(homepageUrl);
            if (hp.length) {
                cy.center(hp);
            }
        }, 100);
    }
}

function setupFilterListeners() {
    ['graph-filter-link-type', 'graph-filter-directory', 'graph-filter-top-pages', 'graph-filter-sim-direction'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', rebuildGraph);
    });

    const simSlider = document.getElementById('graph-filter-similarity');
    const simValue = document.getElementById('graph-sim-value');
    if (simSlider) {
        simSlider.addEventListener('input', () => {
            if (simValue) simValue.textContent = parseFloat(simSlider.value).toFixed(2);
        });
        simSlider.addEventListener('change', rebuildGraph);
    }
}

function updateStats() {
    if (!cy) return;
    const nodesCount = document.getElementById('graph-stats-nodes');
    const edgesCount = document.getElementById('graph-stats-edges');
    if (nodesCount) nodesCount.textContent = cy.nodes().length + ' pages';
    if (edgesCount) edgesCount.textContent = cy.edges().length + ' liens';
}

// ==================== BOUTONS ====================

function setupButtonListeners() {
    // Réorganiser
    const resetBtn = document.getElementById('graph-reset-layout');
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            if (cy) {
                cy.layout(getLayout(cy.nodes().length)).run();
                // Recentrer sur homepage
                if (homepageUrl) {
                    setTimeout(() => {
                        const hp = cy.getElementById(homepageUrl);
                        if (hp.length) cy.center(hp);
                    }, 100);
                }
            }
        });
    }

    // Ajuster la vue
    const fitBtn = document.getElementById('graph-fit');
    if (fitBtn) {
        fitBtn.addEventListener('click', () => {
            if (cy) cy.fit(undefined, 30);
        });
    }

    // Annuler la création de lien
    const cancelBtn = document.getElementById('graph-cancel-link');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', cancelLinkCreation);
    }

    // Export CSV
    const exportBtn = document.getElementById('graph-export-csv');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportModificationsCSV);
    }
}

// ==================== EXPORT CSV ====================

function exportModificationsCSV() {
    const navRemoved = getDisabledNavRemovedLinks();
    const hasManualMods = modifications.added.length > 0 || modifications.removed.length > 0;
    const hasNavMods = navRemoved.length > 0;

    if (!hasManualMods && !hasNavMods) {
        alert('Aucune modification à exporter.');
        return;
    }

    const BOM = '\uFEFF';
    const separator = ';';

    let csvContent = '';

    if (modifications.added.length > 0) {
        csvContent += '=== LIENS A AJOUTER ===' + '\n';
        csvContent += ['Page Source', 'Page Cible', 'Ancre', 'Type de lien'].map(h => `"${h}"`).join(separator) + '\n';
        modifications.added.forEach(link => {
            csvContent += [link.source, link.target, '', link.link_type].map(v => `"${v}"`).join(separator) + '\n';
        });
    }

    if (modifications.removed.length > 0) {
        if (csvContent) csvContent += '\n';
        csvContent += '=== LIENS A SUPPRIMER (contenu) ===' + '\n';
        csvContent += ['Page Source', 'Page Cible'].map(h => `"${h}"`).join(separator) + '\n';
        modifications.removed.forEach(link => {
            csvContent += [link.source, link.target].map(v => `"${v}"`).join(separator) + '\n';
        });
    }

    if (hasNavMods) {
        if (csvContent) csvContent += '\n';
        csvContent += '=== PAGES RETIREES DU MENU NAVIGATION ===' + '\n';
        csvContent += ['Page retirée du menu'].map(h => `"${h}"`).join(separator) + '\n';
        disabledNavPages.forEach(url => {
            csvContent += `"${url}"\n`;
        });
    }

    const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const domain = analyzedDomain || 'export';
    const date = new Date().toISOString().slice(0, 10);
    a.href = url;
    a.download = `${domain}_modifications-maillage_${date}.csv`;
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// ==================== HOOK DANS LE TAB NAVIGATION ====================

// Surcharger la fonction de navigation pour initialiser le graphe quand on arrive sur l'onglet
const originalInitTabNav = typeof initializeTabNavigation === 'function' ? initializeTabNavigation : null;

document.addEventListener('DOMContentLoaded', function() {
    // Observer les clics sur le tab graph-viz
    document.querySelectorAll('.sidebar-nav-item[data-tab="graph-viz"]').forEach(link => {
        link.addEventListener('click', function() {
            // Petit délai pour laisser le DOM s'afficher
            setTimeout(initializeGraphTab, 50);
        });
    });
});
