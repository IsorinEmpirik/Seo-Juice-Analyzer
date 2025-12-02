"""
Routes de l'application Flask
"""
from flask import Blueprint, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
from pathlib import Path

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """Page d'accueil"""
    return render_template('index.html')

@bp.route('/upload', methods=['POST'])
def upload_files():
    """Upload des fichiers CSV"""
    # TODO: Implémenter l'upload
    return jsonify({'status': 'success', 'message': 'Upload en cours de développement'})

@bp.route('/analyze', methods=['POST'])
def analyze():
    """Lancer l'analyse"""
    # TODO: Implémenter l'analyse
    return jsonify({'status': 'success', 'message': 'Analyse en cours de développement'})

@bp.route('/results')
def results():
    """Page de résultats"""
    # TODO: Afficher les résultats
    return render_template('results.html')

@bp.route('/export-sheets', methods=['POST'])
def export_to_sheets():
    """Exporter vers Google Sheets"""
    # TODO: Implémenter l'export
    return jsonify({'status': 'success', 'message': 'Export en cours de développement'})
