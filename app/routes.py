"""
Routes de l'application Flask
"""
from flask import Blueprint, render_template, request, jsonify, session, current_app
from werkzeug.utils import secure_filename
import os
from pathlib import Path
import logging
import uuid

from app.parsers import ScreamingFrogParser, AhrefsParser
from app.analyzer import SEOJuiceAnalyzer
from app.utils import get_csv_preview, detect_column_mapping

bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

# Stockage temporaire des résultats (en production, utiliser Redis ou une BDD)
analysis_results = {}
# Stockage temporaire des fichiers uploadés
uploaded_files_storage = {}


def allowed_file(filename):
    """Vérifie si le fichier est un CSV"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'csv'


@bp.route('/')
def index():
    """Page d'accueil"""
    return render_template('index.html')


@bp.route('/upload-preview', methods=['POST'])
def upload_preview():
    """Upload des fichiers et prévisualisation pour le mapping des colonnes"""
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
            'ahrefs': str(ahrefs_path)
        }

        # Prévisualiser les CSV
        sf_columns, sf_rows = get_csv_preview(str(sf_path), num_rows=3)
        ahrefs_columns, ahrefs_rows = get_csv_preview(str(ahrefs_path), num_rows=3)

        # Détecter automatiquement les colonnes pertinentes
        sf_mapping = detect_column_mapping(sf_columns, 'screaming_frog')
        ahrefs_mapping = detect_column_mapping(ahrefs_columns, 'ahrefs')

        return jsonify({
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
        })

    except Exception as e:
        logger.error(f"Erreur lors de la prévisualisation: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Erreur lors de la prévisualisation: {str(e)}'
        }), 500


@bp.route('/analyze', methods=['POST'])
def analyze():
    """Lancer l'analyse complète avec mapping de colonnes"""
    try:
        # Récupérer les données JSON
        data = request.get_json()

        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Données manquantes'
            }), 400

        upload_id = data.get('upload_id')
        if not upload_id or upload_id not in uploaded_files_storage:
            return jsonify({
                'status': 'error',
                'message': 'Fichiers non trouvés. Veuillez les re-uploader.'
            }), 400

        # Récupérer les chemins des fichiers
        file_paths = uploaded_files_storage[upload_id]
        sf_path = file_paths['screaming_frog']
        ahrefs_path = file_paths['ahrefs']

        # Créer un ID unique pour cette analyse
        analysis_id = str(uuid.uuid4())

        logger.info(f"Lancement de l'analyse {analysis_id} avec upload {upload_id}")

        # Récupérer le mapping des colonnes
        sf_mapping = data.get('screaming_frog_mapping', {})
        ahrefs_mapping = data.get('ahrefs_mapping', {})

        # Récupérer la configuration
        config_data = data.get('config', {})
        config = {
            'backlink_score': int(config_data.get('backlink_score', 10)),
            'iterations': int(config_data.get('iterations', 3)),
            'transmission_rate': float(config_data.get('transmission_rate', 85)) / 100,
            'content_link_rate': float(config_data.get('content_rate', 90)) / 100,
        }
        config['navigation_link_rate'] = 1 - config['content_link_rate']

        logger.info(f"Configuration: {config}")
        logger.info(f"Mapping SF: {sf_mapping}")
        logger.info(f"Mapping Ahrefs: {ahrefs_mapping}")

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

        # Stocker les résultats
        analysis_results[analysis_id] = results

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
