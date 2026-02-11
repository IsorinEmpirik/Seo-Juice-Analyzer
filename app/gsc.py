"""
Client Google Search Console via OAuth 2.0.
Permet la connexion à un compte Google et la récupération des données GSC.
"""
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

# Chemins pour stocker les tokens GSC
GSC_TOKENS_DIR = Path(__file__).parent.parent / 'data' / 'gsc_tokens'

# Scopes nécessaires
SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']


class GSCClient:
    """Client pour l'API Google Search Console."""

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

        # Créer le dossier de tokens
        GSC_TOKENS_DIR.mkdir(parents=True, exist_ok=True)

    def get_auth_url(self, state: str = None) -> str:
        """
        Génère l'URL d'autorisation OAuth.

        Args:
            state: State parameter pour le callback

        Returns:
            URL de consentement Google
        """
        flow = self._create_flow()
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
            state=state,
        )
        return auth_url

    def exchange_code(self, code: str) -> dict:
        """
        Échange le code d'autorisation contre des tokens.

        Args:
            code: Code retourné par Google après consentement

        Returns:
            Dict avec les informations de credentials
        """
        import os
        os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
        flow = self._create_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Sauvegarder les tokens
        token_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': list(credentials.scopes or []),
            'expiry': credentials.expiry.isoformat() if credentials.expiry else None,
        }

        return token_data

    def save_token(self, account_id: str, token_data: dict):
        """Sauvegarde un token pour un compte."""
        token_path = GSC_TOKENS_DIR / f'{account_id}.json'
        with open(token_path, 'w') as f:
            json.dump(token_data, f, indent=2)
        logger.info(f"Token GSC sauvegardé pour {account_id}")

    def load_token(self, account_id: str) -> Optional[dict]:
        """Charge un token sauvegardé."""
        token_path = GSC_TOKENS_DIR / f'{account_id}.json'
        if token_path.exists():
            with open(token_path) as f:
                return json.load(f)
        return None

    def list_saved_accounts(self) -> List[str]:
        """Liste les comptes GSC avec tokens sauvegardés."""
        accounts = []
        for f in GSC_TOKENS_DIR.glob('*.json'):
            accounts.append(f.stem)
        return accounts

    def remove_account(self, account_id: str):
        """Supprime un token de compte."""
        token_path = GSC_TOKENS_DIR / f'{account_id}.json'
        if token_path.exists():
            token_path.unlink()
            logger.info(f"Token GSC supprimé pour {account_id}")

    def get_credentials(self, token_data: dict) -> Optional[Credentials]:
        """
        Crée des Credentials depuis les token_data.
        Rafraîchit le token si expiré.
        """
        try:
            credentials = Credentials(
                token=token_data.get('token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=token_data.get('client_id', self.client_id),
                client_secret=token_data.get('client_secret', self.client_secret),
                scopes=token_data.get('scopes', SCOPES),
            )

            # Rafraîchir si expiré
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                logger.info("Token GSC rafraîchi")

            return credentials

        except Exception as e:
            logger.error(f"Erreur credentials GSC: {e}")
            return None

    def list_properties(self, credentials: Credentials) -> List[dict]:
        """
        Liste les propriétés Search Console accessibles.

        Returns:
            Liste de {site_url, permission_level}
        """
        from googleapiclient.discovery import build

        try:
            service = build('searchconsole', 'v1', credentials=credentials)
            response = service.sites().list().execute()

            properties = []
            for site in response.get('siteEntry', []):
                properties.append({
                    'site_url': site.get('siteUrl', ''),
                    'permission_level': site.get('permissionLevel', ''),
                })

            return properties

        except Exception as e:
            logger.error(f"Erreur listing propriétés GSC: {e}")
            return []

    def fetch_data(
        self,
        credentials: Credentials,
        property_url: str,
        start_date: str = None,
        end_date: str = None,
        country: str = None,
        row_limit: int = 25000,
    ) -> Dict[str, dict]:
        """
        Récupère les données GSC agrégées par URL.
        Format compatible avec GSCParser.get_aggregated_by_url().

        Args:
            credentials: Credentials Google
            property_url: URL de la propriété GSC
            start_date: Date de début (YYYY-MM-DD), défaut: 3 mois
            end_date: Date de fin (YYYY-MM-DD), défaut: hier
            country: Code pays ISO (ex: 'FRA', 'USA'), None = tous
            row_limit: Nombre max de lignes (max 25000 par requête)

        Returns:
            {url: {total_clicks, total_impressions, queries_count, keywords: [...]}}
        """
        from googleapiclient.discovery import build

        if not start_date:
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        try:
            service = build('searchconsole', 'v1', credentials=credentials)

            # Construire la requête
            request_body = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': ['query', 'page'],
                'rowLimit': row_limit,
                'startRow': 0,
            }

            # Filtre pays si spécifié
            if country:
                request_body['dimensionFilterGroups'] = [{
                    'filters': [{
                        'dimension': 'country',
                        'operator': 'equals',
                        'expression': country,
                    }]
                }]

            # Récupérer toutes les données (pagination)
            all_rows = []
            start_row = 0

            while True:
                request_body['startRow'] = start_row
                response = service.searchanalytics().query(
                    siteUrl=property_url,
                    body=request_body,
                ).execute()

                rows = response.get('rows', [])
                if not rows:
                    break

                all_rows.extend(rows)
                start_row += len(rows)

                if len(rows) < row_limit:
                    break

            logger.info(f"GSC: {len(all_rows)} lignes récupérées pour {property_url}")

            # Agréger par URL (même format que GSCParser)
            gsc_data = {}

            for row in all_rows:
                keys = row.get('keys', [])
                if len(keys) < 2:
                    continue

                query = keys[0]
                page = keys[1]
                clicks = row.get('clicks', 0)
                impressions = row.get('impressions', 0)
                position = row.get('position', 0)
                ctr = row.get('ctr', 0)

                if page not in gsc_data:
                    gsc_data[page] = {
                        'total_clicks': 0,
                        'total_impressions': 0,
                        'queries_count': 0,
                        'keywords': [],
                    }

                gsc_data[page]['total_clicks'] += clicks
                gsc_data[page]['total_impressions'] += impressions
                gsc_data[page]['queries_count'] += 1
                gsc_data[page]['keywords'].append({
                    'query': query,
                    'clicks': clicks,
                    'impressions': impressions,
                    'position': round(position, 1),
                    'ctr': round(ctr * 100, 2),
                })

            # Trier les keywords par clics décroissants pour chaque URL
            for url_data in gsc_data.values():
                url_data['keywords'].sort(key=lambda x: x['clicks'], reverse=True)

            logger.info(f"GSC: {len(gsc_data)} URLs avec données de position")

            return gsc_data

        except Exception as e:
            logger.error(f"Erreur récupération données GSC: {e}")
            return {}

    def _create_flow(self) -> Flow:
        """Crée un Flow OAuth depuis les credentials."""
        client_config = {
            'web': {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'redirect_uris': [self.redirect_uri],
            }
        }

        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=self.redirect_uri,
        )

        return flow
