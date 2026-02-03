"""
Routes de l'application Flask
"""
from flask import Blueprint, render_template, request, jsonify, session, current_app
from werkzeug.utils import secure_filename
import os
from pathlib import Path
import logging
import uuid

from app.parsers import ScreamingFrogParser, AhrefsParser, GSCParser, EmbeddingsParser, cosine_similarity
from app.analyzer import SEOJuiceAnalyzer
from app.utils import get_csv_preview, detect_column_mapping
from app import database as db

bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

# Stockage temporaire des résultats (en production, utiliser Redis ou une BDD)
analysis_results = {}
# Stockage temporaire des fichiers uploadés
uploaded_files_storage = {}

import random
from urllib.parse import urlparse


def extract_slug_as_anchor(url):
    """
    Extrait le slug d'une URL et le transforme en ancre lisible.
    Ex: /blog/mon-super-article/ -> "mon super article"
    """
    try:
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        if not path:
            return None
        # Prendre le dernier segment du chemin
        slug = path.split('/')[-1]
        if not slug:
            # Si le dernier segment est vide, prendre l'avant-dernier
            segments = [s for s in path.split('/') if s]
            slug = segments[-1] if segments else None
        if not slug:
            return None
        # Nettoyer le slug : remplacer tirets/underscores par des espaces
        anchor = slug.replace('-', ' ').replace('_', ' ')
        # Supprimer les extensions de fichiers (.html, .php, etc.)
        if '.' in anchor:
            anchor = anchor.rsplit('.', 1)[0]
        return anchor.strip() if anchor.strip() else None
    except Exception:
        return None


def generate_link_recommendations(priority_urls, embeddings_data, sf_parser, gsc_data=None, brand_keywords=None, max_links_per_priority=50):
    """
    Génère des recommandations de liens internes vers les pages prioritaires
    basées sur la similarité sémantique des embeddings.

    Args:
        priority_urls: Liste des URLs prioritaires
        embeddings_data: Dictionnaire {url: embedding_vector}
        sf_parser: Parser Screaming Frog (pour les liens existants)
        gsc_data: Données GSC agrégées par URL (optionnel)
        brand_keywords: Liste des mots-clés marque à exclure (optionnel)
        max_links_per_priority: Nombre maximum de liens par page prioritaire (garde-fou serveur)

    Returns:
        Liste de recommandations de liens
    """
    recommendations = []
    brand_keywords = [kw.lower() for kw in (brand_keywords or [])]

    # Récupérer les liens existants par source
    existing_links_by_source = sf_parser.get_links_by_source()

    # Construire un ensemble des liens existants DANS LE CONTENU ET LE FIL D'ARIANE
    # On ignore les liens dans Navigation (menu) et Pied de page - ils ne comptent pas pour le maillage
    existing_content_links_set = set()
    # Contenu + En-tête (breadcrumb/fil d'Ariane) - on exclut seulement Navigation et Pied de page
    content_positions = ['content', 'contenu', 'body', 'en-tête', 'header']

    for source, links in existing_links_by_source.items():
        for link in links:
            link_position = str(link.get('link_position', '')).lower().strip()
            # Ne compter que les liens dans le contenu
            if any(pos in link_position for pos in content_positions):
                existing_content_links_set.add((source, link['destination']))

    logger.info(f"Liens existants dans le contenu: {len(existing_content_links_set)}")

    # Pour chaque page prioritaire
    for priority_url in priority_urls:
        priority_embedding = embeddings_data.get(priority_url)
        if not priority_embedding:
            logger.warning(f"Pas d'embedding trouvé pour l'URL prioritaire: {priority_url}")
            continue

        # Récupérer les mots-clés GSC de la page prioritaire (pour les ancres)
        priority_keywords = []
        if gsc_data and priority_url in gsc_data:
            url_gsc = gsc_data[priority_url]
            # Filtrer les mots-clés marque et trier par clics
            for kw in url_gsc.get('keywords', []):
                query_lower = kw['query'].lower()
                is_brand = any(brand in query_lower for brand in brand_keywords) if brand_keywords else False
                if not is_brand and kw.get('clicks', 0) > 0:
                    priority_keywords.append(kw)

        # Trier par clics décroissants pour favoriser les meilleurs mots-clés
        priority_keywords.sort(key=lambda x: x.get('clicks', 0), reverse=True)
        max_keywords = min(len(priority_keywords), 10)  # Utiliser jusqu'à 10 mots-clés différents

        # Collecter TOUTES les pages candidates avec leur similarité
        candidates = []

        for source_url, source_embedding in embeddings_data.items():
            # Ignorer la page prioritaire elle-même
            if source_url == priority_url:
                continue

            # Vérifier si un lien existe déjà DANS LE CONTENU
            if (source_url, priority_url) in existing_content_links_set:
                continue

            # Calculer la similarité cosinus
            similarity = cosine_similarity(priority_embedding, source_embedding)

            # Garder toutes les pages avec une similarité > 0 (le filtrage fin sera en JS)
            if similarity > 0:
                candidates.append({
                    'source_url': source_url,
                    'similarity': round(similarity, 4)
                })

        # Trier par similarité décroissante
        candidates.sort(key=lambda x: x['similarity'], reverse=True)

        # Limiter au max_links_per_priority (garde-fou serveur)
        candidates = candidates[:max_links_per_priority]

        # Assigner les ancres avec variation (cycler à travers les mots-clés)
        for i, candidate in enumerate(candidates):
            if priority_keywords and max_keywords > 0:
                # Cycler à travers les mots-clés pour maximiser la variation
                selected_kw = priority_keywords[i % max_keywords]
                suggested_anchor = selected_kw['query']
            else:
                # Fallback: extraire l'ancre du slug de l'URL cible
                suggested_anchor = extract_slug_as_anchor(priority_url) or ""

            recommendations.append({
                'source_url': candidate['source_url'],
                'target_url': priority_url,
                'similarity': candidate['similarity'],
                'suggested_anchor': suggested_anchor,
            })

    # Trier globalement par similarité décroissante
    recommendations.sort(key=lambda x: x['similarity'], reverse=True)

    logger.info(f"Recommandations générées: {len(recommendations)} pour {len(priority_urls)} pages prioritaires")

    return recommendations


def allowed_file(filename):
    """Vérifie si le fichier est un CSV"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'csv'


@bp.route('/')
def index():
    """Page d'accueil"""
    return render_template('index.html')


@bp.route('/algo')
def algo():
    """Page explicative de l'algorithme"""
    return render_template('algo.html')


@bp.route('/preview/<upload_id>')
def preview(upload_id):
    """Page de prévisualisation avec mapping des colonnes"""
    if upload_id not in uploaded_files_storage:
        return render_template('error.html', message="Fichiers introuvables"), 404

    try:
        file_paths = uploaded_files_storage[upload_id]

        # Prévisualiser les CSV
        sf_columns, sf_rows = get_csv_preview(file_paths['screaming_frog'], num_rows=5)
        ahrefs_columns, ahrefs_rows = get_csv_preview(file_paths['ahrefs'], num_rows=5)

        # Détecter automatiquement les colonnes pertinentes
        sf_mapping = detect_column_mapping(sf_columns, 'screaming_frog')
        ahrefs_mapping = detect_column_mapping(ahrefs_columns, 'ahrefs')

        preview_data = {
            'screaming_frog': {
                'columns': sf_columns,
                'preview': sf_rows,
                'detected_mapping': sf_mapping
            },
            'ahrefs': {
                'columns': ahrefs_columns,
                'preview': ahrefs_rows,
                'detected_mapping': ahrefs_mapping
            }
        }

        # Ajouter prévisualisation GSC si présent
        if file_paths.get('gsc'):
            gsc_columns, gsc_rows = get_csv_preview(file_paths['gsc'], num_rows=5)
            preview_data['gsc'] = {
                'columns': gsc_columns,
                'preview': gsc_rows,
                'brand_keywords': file_paths.get('brand_keywords', [])
            }

        return render_template('preview.html', preview_data=preview_data, upload_id=upload_id)

    except Exception as e:
        logger.error(f"Erreur lors de la prévisualisation: {e}", exc_info=True)
        return render_template('error.html', message=f"Erreur: {str(e)}"), 500


@bp.route('/upload-preview', methods=['POST'])
def upload_preview():
    """Upload des fichiers et prévisualisation pour le mapping des colonnes"""
    try:
        # Vérifier que les fichiers requis sont présents
        if 'screamingfrog' not in request.files or 'ahrefs' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'Les deux fichiers CSV sont requis'
            }), 400

        sf_file = request.files['screamingfrog']
        ahrefs_file = request.files['ahrefs']

        # Vérifier que les fichiers ne sont pas vides
        if sf_file.filename == '' or ahrefs_file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'Les fichiers ne peuvent pas être vides'
            }), 400

        # Vérifier que ce sont des CSV
        if not allowed_file(sf_file.filename) or not allowed_file(ahrefs_file.filename):
            return jsonify({
                'status': 'error',
                'message': 'Seuls les fichiers CSV sont acceptés'
            }), 400

        # Créer un ID unique pour cet upload
        upload_id = str(uuid.uuid4())

        # Sauvegarder les fichiers temporairement
        upload_folder = Path(current_app.config['UPLOAD_FOLDER'])
        upload_folder.mkdir(exist_ok=True)

        sf_path = upload_folder / f"{upload_id}_screaming_frog.csv"
        ahrefs_path = upload_folder / f"{upload_id}_ahrefs.csv"

        sf_file.save(str(sf_path))
        ahrefs_file.save(str(ahrefs_path))

        logger.info(f"Fichiers uploadés pour preview {upload_id}")

        # Stocker les chemins
        uploaded_files_storage[upload_id] = {
            'screaming_frog': str(sf_path),
            'ahrefs': str(ahrefs_path),
            'gsc': None,
            'brand_keywords': [],
            'embeddings': None,
            'priority_urls': []
        }

        # Gérer le fichier GSC (optionnel)
        if 'gsc' in request.files:
            gsc_file = request.files['gsc']
            if gsc_file.filename != '' and allowed_file(gsc_file.filename):
                gsc_path = upload_folder / f"{upload_id}_gsc.csv"
                gsc_file.save(str(gsc_path))
                uploaded_files_storage[upload_id]['gsc'] = str(gsc_path)
                logger.info(f"Fichier GSC uploadé pour {upload_id}")

                # Récupérer les mots-clés marque
                brand_keywords = request.form.get('brand_keywords', '')
                if brand_keywords:
                    # Séparer par lignes et nettoyer
                    keywords_list = [kw.strip() for kw in brand_keywords.split('\n') if kw.strip()]
                    uploaded_files_storage[upload_id]['brand_keywords'] = keywords_list
                    logger.info(f"Mots-clés marque: {keywords_list}")

        # Gérer le fichier Embeddings (optionnel, pour pages prioritaires)
        if 'embeddings' in request.files:
            embeddings_file = request.files['embeddings']
            if embeddings_file.filename != '' and allowed_file(embeddings_file.filename):
                embeddings_path = upload_folder / f"{upload_id}_embeddings.csv"
                embeddings_file.save(str(embeddings_path))
                uploaded_files_storage[upload_id]['embeddings'] = str(embeddings_path)
                logger.info(f"Fichier Embeddings uploadé pour {upload_id}")

        # Récupérer les URLs prioritaires (optionnel)
        priority_urls = request.form.get('priority_urls', '')
        if priority_urls:
            # Séparer par lignes et nettoyer
            urls_list = [url.strip() for url in priority_urls.split('\n') if url.strip()]
            uploaded_files_storage[upload_id]['priority_urls'] = urls_list
            logger.info(f"URLs prioritaires: {len(urls_list)} URLs")

        # Prévisualiser les CSV
        sf_columns, sf_rows = get_csv_preview(str(sf_path), num_rows=3)
        ahrefs_columns, ahrefs_rows = get_csv_preview(str(ahrefs_path), num_rows=3)

        # Détecter automatiquement les colonnes pertinentes
        sf_mapping = detect_column_mapping(sf_columns, 'screaming_frog')
        ahrefs_mapping = detect_column_mapping(ahrefs_columns, 'ahrefs')

        response_data = {
            'status': 'success',
            'upload_id': upload_id,
            'screaming_frog': {
                'columns': sf_columns,
                'preview': sf_rows,
                'detected_mapping': sf_mapping
            },
            'ahrefs': {
                'columns': ahrefs_columns,
                'preview': ahrefs_rows,
                'detected_mapping': ahrefs_mapping
            }
        }

        # Ajouter prévisualisation GSC si présent
        if uploaded_files_storage[upload_id]['gsc']:
            gsc_columns, gsc_rows = get_csv_preview(uploaded_files_storage[upload_id]['gsc'], num_rows=3)
            response_data['gsc'] = {
                'columns': gsc_columns,
                'preview': gsc_rows,
                'brand_keywords': uploaded_files_storage[upload_id]['brand_keywords']
            }

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Erreur lors de la prévisualisation: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Erreur lors de la prévisualisation: {str(e)}'
        }), 500


@bp.route('/analyze', methods=['POST'])
def analyze():
    """Lancer l'analyse complète"""
    try:
        # Vérifier que les fichiers sont présents
        if 'screamingfrog' not in request.files or 'ahrefs' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'Les deux fichiers CSV sont requis'
            }), 400

        sf_file = request.files['screamingfrog']
        ahrefs_file = request.files['ahrefs']

        # Vérifier que les fichiers ne sont pas vides
        if sf_file.filename == '' or ahrefs_file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'Les fichiers ne peuvent pas être vides'
            }), 400

        # Vérifier que ce sont des CSV
        if not allowed_file(sf_file.filename) or not allowed_file(ahrefs_file.filename):
            return jsonify({
                'status': 'error',
                'message': 'Seuls les fichiers CSV sont acceptés'
            }), 400

        # Créer un ID unique pour cette analyse
        analysis_id = str(uuid.uuid4())

        # Sauvegarder les fichiers temporairement
        upload_folder = Path(current_app.config['UPLOAD_FOLDER'])
        upload_folder.mkdir(exist_ok=True)

        sf_path = upload_folder / f"{analysis_id}_screaming_frog.csv"
        ahrefs_path = upload_folder / f"{analysis_id}_ahrefs.csv"

        sf_file.save(str(sf_path))
        ahrefs_file.save(str(ahrefs_path))

        logger.info(f"Fichiers uploadés pour l'analyse {analysis_id}")

        # Récupérer la configuration
        config = {
            'backlink_score': int(request.form.get('backlink_score', 10)),
            'iterations': int(request.form.get('iterations', 3)),
            'transmission_rate': float(request.form.get('transmission_rate', 85)) / 100,
            'content_link_rate': float(request.form.get('content_rate', 90)) / 100,
        }
        config['navigation_link_rate'] = 1 - config['content_link_rate']

        logger.info(f"Configuration: {config}")

        # Parser les CSV
        logger.info("Parsing Screaming Frog...")
        sf_parser = ScreamingFrogParser(str(sf_path))
        sf_parser.parse()

        logger.info("Parsing Ahrefs...")
        ahrefs_parser = AhrefsParser(str(ahrefs_path))
        ahrefs_parser.parse()

        # Lancer l'analyse
        logger.info("Lancement de l'analyse...")
        analyzer = SEOJuiceAnalyzer(config=config)
        results = analyzer.analyze(sf_parser, ahrefs_parser)

        # Stocker les résultats en mémoire
        analysis_results[analysis_id] = results

        # Sauvegarder dans la base de données pour l'historique
        db.save_analysis(analysis_id, results)

        # Nettoyer les fichiers temporaires
        sf_path.unlink()
        ahrefs_path.unlink()

        logger.info(f"Analyse {analysis_id} terminée avec succès")

        return jsonify({
            'status': 'success',
            'message': 'Analyse terminée avec succès',
            'analysis_id': analysis_id
        })

    except Exception as e:
        logger.error(f"Erreur lors de l'analyse: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Erreur lors de l\'analyse: {str(e)}'
        }), 500


@bp.route('/results/<analysis_id>')
def results(analysis_id):
    """Page de résultats"""
    if analysis_id not in analysis_results:
        return render_template('error.html', message="Analyse introuvable"), 404

    results = analysis_results[analysis_id]

    return render_template('results.html', results=results, analysis_id=analysis_id)


@bp.route('/api/results/<analysis_id>')
def api_results(analysis_id):
    """API pour récupérer les résultats en JSON"""
    if analysis_id not in analysis_results:
        return jsonify({'status': 'error', 'message': 'Analyse introuvable'}), 404

    return jsonify({
        'status': 'success',
        'results': analysis_results[analysis_id]
    })


@bp.route('/analyze-with-mapping', methods=['POST'])
def analyze_with_mapping():
    """Lancer l'analyse avec mapping personnalisé des colonnes"""
    try:
        # Récupérer les données JSON
        data = request.get_json()

        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Données manquantes'
            }), 400

        upload_id = data.get('upload_id')
        sf_mapping = data.get('sf_mapping', {})
        ahrefs_mapping = data.get('ahrefs_mapping', {})

        if upload_id not in uploaded_files_storage:
            return jsonify({
                'status': 'error',
                'message': 'Fichiers introuvables'
            }), 404

        file_paths = uploaded_files_storage[upload_id]

        # Créer un ID pour l'analyse
        analysis_id = str(uuid.uuid4())

        logger.info(f"Analyse {analysis_id} avec mapping personnalisé")
        logger.info(f"SF mapping: {sf_mapping}")
        logger.info(f"Ahrefs mapping: {ahrefs_mapping}")

        # Parser les CSV avec les mappings personnalisés
        logger.info("Parsing Screaming Frog...")
        sf_parser = ScreamingFrogParser(file_paths['screaming_frog'])
        sf_parser.parse()

        logger.info("Parsing Ahrefs...")
        ahrefs_parser = AhrefsParser(file_paths['ahrefs'])
        ahrefs_parser.parse()

        # Parser GSC si présent
        gsc_data = None
        gsc_parser = None
        brand_keywords = file_paths.get('brand_keywords', [])
        if file_paths.get('gsc'):
            logger.info("Parsing GSC...")
            gsc_parser = GSCParser(file_paths['gsc'], brand_keywords=brand_keywords)
            gsc_parser.parse()
            gsc_data = gsc_parser.get_aggregated_by_url()
            logger.info(f"GSC: {len(gsc_data)} URLs avec données de position")

        # Parser Embeddings si présent
        embeddings_data = None
        if file_paths.get('embeddings'):
            logger.info("Parsing Embeddings...")
            embeddings_parser = EmbeddingsParser(file_paths['embeddings'])
            embeddings_parser.parse()
            embeddings_data = embeddings_parser.get_embeddings_by_url()
            logger.info(f"Embeddings: {len(embeddings_data)} URLs avec embeddings")

        # Lancer l'analyse
        logger.info("Lancement de l'analyse...")
        analyzer = SEOJuiceAnalyzer()
        results = analyzer.analyze(sf_parser, ahrefs_parser, gsc_data=gsc_data)

        # Générer les recommandations de liens pour les pages prioritaires
        priority_urls = file_paths.get('priority_urls', [])
        if priority_urls and embeddings_data:
            logger.info(f"Génération recommandations pour {len(priority_urls)} pages prioritaires...")
            link_recommendations = generate_link_recommendations(
                priority_urls=priority_urls,
                embeddings_data=embeddings_data,
                sf_parser=sf_parser,
                gsc_data=gsc_data,
                brand_keywords=brand_keywords
            )
            results['link_recommendations'] = link_recommendations
            results['has_priority_urls'] = True
            results['priority_urls'] = priority_urls
            logger.info(f"Recommandations générées: {len(link_recommendations)} liens suggérés")
        else:
            results['has_priority_urls'] = False
            results['link_recommendations'] = []
            results['priority_urls'] = []

        # Stocker les résultats en mémoire
        analysis_results[analysis_id] = results

        # Sauvegarder dans la base de données pour l'historique
        db.save_analysis(analysis_id, results)

        # Nettoyer les fichiers temporaires
        Path(file_paths['screaming_frog']).unlink()
        Path(file_paths['ahrefs']).unlink()
        if file_paths.get('gsc'):
            Path(file_paths['gsc']).unlink()
        if file_paths.get('embeddings'):
            Path(file_paths['embeddings']).unlink()

        # Supprimer de la liste
        del uploaded_files_storage[upload_id]

        logger.info(f"Analyse {analysis_id} terminée avec succès")

        return jsonify({
            'status': 'success',
            'message': 'Analyse terminée avec succès',
            'analysis_id': analysis_id
        })

    except Exception as e:
        logger.error(f"Erreur lors de l'analyse avec mapping: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Erreur lors de l\'analyse: {str(e)}'
        }), 500


@bp.route('/export-sheets/<analysis_id>', methods=['POST'])
def export_to_sheets(analysis_id):
    """Exporter vers Google Sheets"""
    if analysis_id not in analysis_results:
        return jsonify({'status': 'error', 'message': 'Analyse introuvable'}), 404

    # TODO: Implémenter l'export vers Google Sheets
    return jsonify({
        'status': 'success',
        'message': 'Export Google Sheets sera implémenté prochainement'
    })


# ==================== ENDPOINTS HISTORIQUE ====================

@bp.route('/api/history/domains')
def api_history_domains():
    """Liste tous les domaines avec historique d'analyses."""
    try:
        domains = db.get_all_domains()
        return jsonify({
            'status': 'success',
            'domains': domains
        })
    except Exception as e:
        logger.error(f"Erreur API domains: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@bp.route('/api/history/analyses')
def api_history_analyses():
    """Liste les analyses historiques, filtrable par domaine."""
    try:
        domain = request.args.get('domain')
        limit = int(request.args.get('limit', 50))

        analyses = db.get_analyses_for_domain(domain, limit)
        return jsonify({
            'status': 'success',
            'analyses': analyses
        })
    except Exception as e:
        logger.error(f"Erreur API analyses: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@bp.route('/api/history/analysis/<analysis_id>')
def api_history_analysis_details(analysis_id):
    """Récupère les détails d'une analyse historique."""
    try:
        analysis = db.get_analysis_details(analysis_id)
        if not analysis:
            return jsonify({'status': 'error', 'message': 'Analyse introuvable'}), 404

        return jsonify({
            'status': 'success',
            'analysis': analysis
        })
    except Exception as e:
        logger.error(f"Erreur API analysis details: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@bp.route('/api/history/compare', methods=['POST'])
def api_history_compare():
    """Compare deux analyses."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'Données manquantes'}), 400

        current_id = data.get('current_id')
        previous_id = data.get('previous_id')

        if not current_id or not previous_id:
            return jsonify({
                'status': 'error',
                'message': 'Les IDs des deux analyses sont requis'
            }), 400

        comparison = db.compare_analyses(current_id, previous_id)

        if 'error' in comparison:
            return jsonify({'status': 'error', 'message': comparison['error']}), 400

        return jsonify({
            'status': 'success',
            'comparison': comparison
        })
    except Exception as e:
        logger.error(f"Erreur API compare: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@bp.route('/api/history/evolution/<domain>')
def api_history_evolution(domain):
    """Récupère l'évolution des métriques pour un domaine."""
    try:
        limit = int(request.args.get('limit', 10))
        evolution = db.get_domain_evolution(domain, limit)

        return jsonify({
            'status': 'success',
            'domain': domain,
            'evolution': evolution
        })
    except Exception as e:
        logger.error(f"Erreur API evolution: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
