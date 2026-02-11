"""
Application Flask pour l'analyse de maillage interne
"""
from flask import Flask
from pathlib import Path
import os


def create_app():
    """Factory pour créer l'application Flask"""
    # Définir les chemins vers templates et static à la racine du projet
    base_dir = Path(__file__).parent.parent
    template_dir = base_dir / 'templates'
    static_dir = base_dir / 'static'

    app = Flask(__name__,
                template_folder=str(template_dir),
                static_folder=str(static_dir))

    # Charger la configuration
    app.config.from_object('config')

    # Créer les dossiers nécessaires s'ils n'existent pas
    for folder in ['uploads', 'static/css', 'static/js', 'static/img', 'templates',
                    'data', 'data/gsc_tokens']:
        folder_path = Path(app.root_path).parent / folder
        folder_path.mkdir(parents=True, exist_ok=True)

    # Créer le fichier .gitkeep dans uploads
    gitkeep_path = Path(app.root_path).parent / 'uploads' / '.gitkeep'
    gitkeep_path.touch(exist_ok=True)

    # Enregistrer les routes principales
    from app import routes
    app.register_blueprint(routes.bp)

    # Enregistrer les routes OAuth (Google Search Console)
    from app.oauth_routes import oauth_bp
    app.register_blueprint(oauth_bp)

    return app
