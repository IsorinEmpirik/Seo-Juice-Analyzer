"""
Routes OAuth pour la connexion Google Search Console.
"""
import logging
import hashlib
import json

from flask import Blueprint, request, jsonify, redirect, url_for, session, current_app

from app.gsc import GSCClient

oauth_bp = Blueprint('oauth', __name__)
logger = logging.getLogger(__name__)


def _get_gsc_client():
    """Crée un GSCClient avec la config de l'app."""
    return GSCClient(
        client_id=current_app.config.get('GOOGLE_CLIENT_ID', ''),
        client_secret=current_app.config.get('GOOGLE_CLIENT_SECRET', ''),
        redirect_uri=current_app.config.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/oauth/callback'),
    )


@oauth_bp.route('/oauth/connect-gsc')
def connect_gsc():
    """Redirige vers la page de consentement Google OAuth."""
    gsc_client = _get_gsc_client()

    if not current_app.config.get('GOOGLE_CLIENT_ID'):
        return jsonify({'status': 'error', 'message': 'Google OAuth non configuré'}), 500

    auth_url = gsc_client.get_auth_url()
    return redirect(auth_url)


@oauth_bp.route('/oauth/callback')
def oauth_callback():
    """Callback OAuth après consentement Google."""
    code = request.args.get('code')
    error = request.args.get('error')

    if error:
        logger.error(f"OAuth error: {error}")
        return redirect('/?oauth_error=' + error)

    if not code:
        return redirect('/?oauth_error=no_code')

    try:
        gsc_client = _get_gsc_client()
        token_data = gsc_client.exchange_code(code)

        # Générer un ID de compte basé sur le token
        account_id = hashlib.md5(
            (token_data.get('token', '') + str(token_data.get('refresh_token', ''))).encode()
        ).hexdigest()[:12]

        # Sauvegarder le token
        gsc_client.save_token(account_id, token_data)

        # Stocker l'account_id dans la session
        session['gsc_account_id'] = account_id
        session['gsc_connected'] = True

        logger.info(f"GSC OAuth connecté: {account_id}")

        return redirect('/?oauth_success=true')

    except Exception as e:
        logger.error(f"Erreur OAuth callback: {e}", exc_info=True)
        return redirect(f'/?oauth_error={str(e)[:100]}')


@oauth_bp.route('/api/gsc/properties')
def gsc_properties():
    """Liste les propriétés Search Console du compte connecté."""
    account_id = request.args.get('account_id') or session.get('gsc_account_id')

    if not account_id:
        return jsonify({'status': 'error', 'message': 'Pas de compte GSC connecté'}), 401

    try:
        gsc_client = _get_gsc_client()
        token_data = gsc_client.load_token(account_id)

        if not token_data:
            return jsonify({'status': 'error', 'message': 'Token expiré, reconnectez-vous'}), 401

        credentials = gsc_client.get_credentials(token_data)
        if not credentials:
            return jsonify({'status': 'error', 'message': 'Credentials invalides'}), 401

        properties = gsc_client.list_properties(credentials)

        return jsonify({
            'status': 'success',
            'properties': properties,
            'account_id': account_id,
        })

    except Exception as e:
        logger.error(f"Erreur listing propriétés: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@oauth_bp.route('/api/gsc/accounts')
def gsc_accounts():
    """Liste les comptes GSC sauvegardés."""
    gsc_client = _get_gsc_client()
    accounts = gsc_client.list_saved_accounts()
    current = session.get('gsc_account_id')

    return jsonify({
        'status': 'success',
        'accounts': accounts,
        'current_account': current,
    })


@oauth_bp.route('/oauth/disconnect-gsc')
def disconnect_gsc():
    """Déconnecte le compte GSC."""
    account_id = request.args.get('account_id') or session.get('gsc_account_id')

    if account_id:
        gsc_client = _get_gsc_client()
        gsc_client.remove_account(account_id)

        if session.get('gsc_account_id') == account_id:
            session.pop('gsc_account_id', None)
            session.pop('gsc_connected', None)

    return redirect('/')
