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

bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

# Stockage temporaire des résultats (en production, utiliser Redis ou une BDD)
analysis_results = {}


def allowed_file(filename):
    """Vérifie si le fichier est un CSV"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'csv'


@bp.route('/')
def index():
    """Page d'accueil"""
    return render_template('index.html')


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
