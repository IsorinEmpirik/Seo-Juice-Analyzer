"""
Application Flask pour l'analyse de maillage interne
"""
from flask import Flask
from pathlib import Path
import os

def create_app():
    """Factory pour créer l'application Flask"""
    app = Flask(__name__)

    # Charger la configuration
    app.config.from_object('config')

    # Créer les dossiers nécessaires s'ils n'existent pas
    for folder in ['uploads', 'static/css', 'static/js', 'static/img', 'templates']:
        folder_path = Path(app.root_path).parent / folder
        folder_path.mkdir(parents=True, exist_ok=True)

    # Créer le fichier .gitkeep dans uploads
    gitkeep_path = Path(app.root_path).parent / 'uploads' / '.gitkeep'
    gitkeep_path.touch(exist_ok=True)

    # Enregistrer les routes
    from app import routes
    app.register_blueprint(routes.bp)

    return app
