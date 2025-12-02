import os
from pathlib import Path

# Chemins de base
BASE_DIR = Path(__file__).parent
UPLOAD_FOLDER = BASE_DIR / 'uploads'
EXAMPLES_FOLDER = BASE_DIR / 'examples'
DOCS_FOLDER = BASE_DIR / 'docs'

# Configuration Flask
SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100 MB max pour les uploads

# Extensions autorisées
ALLOWED_EXTENSIONS = {'csv'}

# Configuration de l'algorithme
DEFAULT_CONFIG = {
    'backlink_score': 10,           # Score par backlink reçu
    'transmission_rate': 0.85,       # 85% du jus est transmis
    'content_link_rate': 0.90,       # 90% pour les liens de contenu
    'navigation_link_rate': 0.10,    # 10% pour les liens de navigation
    'iterations': 3,                 # Nombre d'itérations
    'normalize_max': 100             # Normalisation du score sur 100
}

# Configuration Google Sheets
GOOGLE_CREDENTIALS_FILE = BASE_DIR / 'credentials.json'
GOOGLE_TOKEN_FILE = BASE_DIR / 'token.json'

# Colonnes CSV Screaming Frog attendues
SCREAMING_FROG_COLUMNS = {
    'source': 'Source',
    'destination': 'Destination',
    'anchor': 'Ancrage',
    'status_code': 'Code de statut',
    'link_position': 'Position du lien',  # Contenu ou Navigation
    'follow': 'Suivre'
}

# Colonnes CSV Ahrefs attendues
AHREFS_COLUMNS = {
    'target_url': 'Target URL',
    'referring_url': 'Referring page URL',
    'anchor': 'Anchor',
    'nofollow': 'Nofollow',
    'domain_rating': 'Domain rating'
}
