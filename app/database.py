"""
Module de gestion de la base de données SQLite pour l'historique des analyses.
Permet de sauvegarder, récupérer et comparer les analyses SEO.
"""
import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

# Chemin de la base de données
DB_PATH = Path(__file__).parent.parent / 'data' / 'analyses.db'
MAX_ANALYSES = 50  # Nombre maximum d'analyses conservées


@contextmanager
def get_db_connection():
    """Context manager pour les connexions à la base de données."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialise la base de données et crée les tables si nécessaire."""
    # Créer le dossier data s'il n'existe pas
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Table des analyses
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_id TEXT UNIQUE NOT NULL,
                domain TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_urls INTEGER,
                total_internal_links INTEGER,
                total_backlinks INTEGER,
                median_seo_score REAL,
                error_juice_rate REAL,
                has_gsc_data INTEGER DEFAULT 0,
                config_json TEXT,
                summary_json TEXT
            )
        ''')

        # Table des métriques par URL (pour comparaison détaillée)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS url_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_id TEXT NOT NULL,
                url TEXT NOT NULL,
                seo_score REAL,
                backlinks_count INTEGER,
                internal_links_received INTEGER,
                internal_links_received_content INTEGER,
                internal_links_received_navigation INTEGER,
                internal_links_sent INTEGER,
                status_code INTEGER,
                category TEXT,
                gsc_best_position REAL,
                gsc_best_keyword TEXT,
                FOREIGN KEY (analysis_id) REFERENCES analyses(analysis_id) ON DELETE CASCADE
            )
        ''')

        # Table pour les Quick Wins (pour suivre l'évolution)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quick_wins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_id TEXT NOT NULL,
                url TEXT NOT NULL,
                keyword TEXT NOT NULL,
                position REAL,
                impressions INTEGER,
                clicks INTEGER,
                seo_score REAL,
                FOREIGN KEY (analysis_id) REFERENCES analyses(analysis_id) ON DELETE CASCADE
            )
        ''')

        # Table pour les pages en erreur
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS error_pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_id TEXT NOT NULL,
                url TEXT NOT NULL,
                status_code INTEGER,
                internal_links_received INTEGER,
                seo_score REAL,
                FOREIGN KEY (analysis_id) REFERENCES analyses(analysis_id) ON DELETE CASCADE
            )
        ''')

        # Index pour les recherches fréquentes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_analyses_domain ON analyses(domain)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_analyses_created ON analyses(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_url_metrics_analysis ON url_metrics(analysis_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_url_metrics_url ON url_metrics(url)')

        conn.commit()
        logger.info("Base de données initialisée avec succès")


def save_analysis(analysis_id: str, results: dict) -> bool:
    """
    Sauvegarde une analyse complète dans la base de données.

    Args:
        analysis_id: Identifiant unique de l'analyse
        results: Dictionnaire des résultats de l'analyse

    Returns:
        True si la sauvegarde a réussi, False sinon
    """
    try:
        # Extraire le domaine depuis les URLs
        domain = extract_domain(results.get('urls', []))

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Préparer le résumé JSON (métriques agrégées)
            summary = {
                'categories': results.get('categories', {}),
                'juice_by_status': results.get('juice_by_status', {}),
                'top_juice_sources': results.get('top_juice_sources', [])[:10],
                'recommendations_count': len(results.get('recommendations', [])),
            }

            # Insérer l'analyse principale
            cursor.execute('''
                INSERT OR REPLACE INTO analyses
                (analysis_id, domain, created_at, total_urls, total_internal_links,
                 total_backlinks, median_seo_score, error_juice_rate, has_gsc_data,
                 config_json, summary_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                analysis_id,
                domain,
                datetime.now().isoformat(),
                results.get('total_urls', 0),
                results.get('total_internal_links', 0),
                results.get('total_backlinks', 0),
                results.get('median_seo_score', 0),
                results.get('error_juice_rate', 0),
                1 if results.get('has_gsc_data') else 0,
                json.dumps(results.get('config', {})),
                json.dumps(summary)
            ))

            # Supprimer les anciennes métriques pour cette analyse (au cas où)
            cursor.execute('DELETE FROM url_metrics WHERE analysis_id = ?', (analysis_id,))
            cursor.execute('DELETE FROM quick_wins WHERE analysis_id = ?', (analysis_id,))
            cursor.execute('DELETE FROM error_pages WHERE analysis_id = ?', (analysis_id,))

            # Insérer les métriques par URL
            for url_data in results.get('urls', []):
                gsc_best = url_data.get('gsc_best_keyword')
                cursor.execute('''
                    INSERT INTO url_metrics
                    (analysis_id, url, seo_score, backlinks_count, internal_links_received,
                     internal_links_received_content, internal_links_received_navigation,
                     internal_links_sent, status_code, category, gsc_best_position, gsc_best_keyword)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    analysis_id,
                    url_data.get('url', ''),
                    url_data.get('seo_score', 0),
                    url_data.get('backlinks_count', 0),
                    url_data.get('internal_links_received', 0),
                    url_data.get('internal_links_received_content', 0),
                    url_data.get('internal_links_received_navigation', 0),
                    url_data.get('internal_links_sent', 0),
                    url_data.get('status_code', 0),
                    url_data.get('category', ''),
                    gsc_best.get('position') if gsc_best else None,
                    gsc_best.get('query') if gsc_best else None
                ))

                # Sauvegarder les Quick Wins
                for kw in url_data.get('gsc_keywords', []):
                    if 5 <= kw.get('position', 0) <= 12 and kw.get('impressions', 0) >= 50:
                        cursor.execute('''
                            INSERT INTO quick_wins
                            (analysis_id, url, keyword, position, impressions, clicks, seo_score)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            analysis_id,
                            url_data.get('url', ''),
                            kw.get('query', ''),
                            kw.get('position', 0),
                            kw.get('impressions', 0),
                            kw.get('clicks', 0),
                            url_data.get('seo_score', 0)
                        ))

            # Sauvegarder les pages en erreur
            for error_page in results.get('error_pages_with_links', []):
                cursor.execute('''
                    INSERT INTO error_pages
                    (analysis_id, url, status_code, internal_links_received, seo_score)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    analysis_id,
                    error_page.get('url', ''),
                    error_page.get('status_code', 0),
                    error_page.get('internal_links_received', 0),
                    error_page.get('seo_score', 0)
                ))

            conn.commit()

            # Nettoyer les anciennes analyses si nécessaire
            cleanup_old_analyses()

            logger.info(f"Analyse {analysis_id} sauvegardée pour le domaine {domain}")
            return True

    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde de l'analyse: {e}", exc_info=True)
        return False


def extract_domain(urls: list) -> str:
    """Extrait le domaine principal depuis la liste des URLs."""
    if not urls:
        return "unknown"

    try:
        from urllib.parse import urlparse
        first_url = urls[0].get('url', '') if isinstance(urls[0], dict) else urls[0]
        parsed = urlparse(first_url)
        domain = parsed.netloc.replace('www.', '')
        return domain or "unknown"
    except Exception:
        return "unknown"


def cleanup_old_analyses():
    """Supprime les analyses les plus anciennes au-delà de MAX_ANALYSES."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Compter le nombre d'analyses
            cursor.execute('SELECT COUNT(*) FROM analyses')
            count = cursor.fetchone()[0]

            if count > MAX_ANALYSES:
                # Supprimer les plus anciennes
                to_delete = count - MAX_ANALYSES
                cursor.execute('''
                    DELETE FROM analyses
                    WHERE id IN (
                        SELECT id FROM analyses
                        ORDER BY created_at ASC
                        LIMIT ?
                    )
                ''', (to_delete,))
                conn.commit()
                logger.info(f"Nettoyage: {to_delete} anciennes analyses supprimées")

    except Exception as e:
        logger.error(f"Erreur lors du nettoyage: {e}")


def get_analyses_for_domain(domain: str = None, limit: int = 50) -> list:
    """
    Récupère la liste des analyses pour un domaine donné (ou tous).

    Args:
        domain: Filtre par domaine (optionnel)
        limit: Nombre maximum de résultats

    Returns:
        Liste des analyses avec leurs métadonnées
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            if domain:
                cursor.execute('''
                    SELECT analysis_id, domain, created_at, total_urls,
                           total_internal_links, total_backlinks, median_seo_score,
                           error_juice_rate, has_gsc_data
                    FROM analyses
                    WHERE domain = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (domain, limit))
            else:
                cursor.execute('''
                    SELECT analysis_id, domain, created_at, total_urls,
                           total_internal_links, total_backlinks, median_seo_score,
                           error_juice_rate, has_gsc_data
                    FROM analyses
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (limit,))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des analyses: {e}")
        return []


def get_all_domains() -> list:
    """Récupère la liste de tous les domaines analysés."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT domain, COUNT(*) as count, MAX(created_at) as last_analysis
                FROM analyses
                GROUP BY domain
                ORDER BY last_analysis DESC
            ''')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des domaines: {e}")
        return []


def get_analysis_details(analysis_id: str) -> dict:
    """Récupère les détails complets d'une analyse."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Récupérer l'analyse principale
            cursor.execute('SELECT * FROM analyses WHERE analysis_id = ?', (analysis_id,))
            row = cursor.fetchone()

            if not row:
                return None

            analysis = dict(row)
            analysis['summary'] = json.loads(analysis.get('summary_json') or '{}')
            analysis['config'] = json.loads(analysis.get('config_json') or '{}')

            # Récupérer les métriques par URL
            cursor.execute('''
                SELECT * FROM url_metrics WHERE analysis_id = ?
                ORDER BY seo_score DESC
            ''', (analysis_id,))
            analysis['urls'] = [dict(r) for r in cursor.fetchall()]

            # Récupérer les Quick Wins
            cursor.execute('''
                SELECT * FROM quick_wins WHERE analysis_id = ?
                ORDER BY impressions DESC
            ''', (analysis_id,))
            analysis['quick_wins'] = [dict(r) for r in cursor.fetchall()]

            # Récupérer les pages en erreur
            cursor.execute('''
                SELECT * FROM error_pages WHERE analysis_id = ?
            ''', (analysis_id,))
            analysis['error_pages'] = [dict(r) for r in cursor.fetchall()]

            return analysis

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des détails: {e}")
        return None


def compare_analyses(current_id: str, previous_id: str) -> dict:
    """
    Compare deux analyses et génère un rapport de différences.

    Args:
        current_id: ID de l'analyse actuelle
        previous_id: ID de l'analyse précédente

    Returns:
        Dictionnaire avec les comparaisons et deltas
    """
    try:
        current = get_analysis_details(current_id)
        previous = get_analysis_details(previous_id)

        if not current or not previous:
            return {'error': 'Une ou plusieurs analyses introuvables'}

        # Calculer les deltas globaux
        global_delta = {
            'total_urls': {
                'current': current['total_urls'],
                'previous': previous['total_urls'],
                'delta': current['total_urls'] - previous['total_urls'],
                'percent': calc_percent_change(previous['total_urls'], current['total_urls'])
            },
            'total_internal_links': {
                'current': current['total_internal_links'],
                'previous': previous['total_internal_links'],
                'delta': current['total_internal_links'] - previous['total_internal_links'],
                'percent': calc_percent_change(previous['total_internal_links'], current['total_internal_links'])
            },
            'total_backlinks': {
                'current': current['total_backlinks'],
                'previous': previous['total_backlinks'],
                'delta': current['total_backlinks'] - previous['total_backlinks'],
                'percent': calc_percent_change(previous['total_backlinks'], current['total_backlinks'])
            },
            'median_seo_score': {
                'current': current['median_seo_score'],
                'previous': previous['median_seo_score'],
                'delta': round(current['median_seo_score'] - previous['median_seo_score'], 2),
                'percent': calc_percent_change(previous['median_seo_score'], current['median_seo_score'])
            },
            'error_juice_rate': {
                'current': current['error_juice_rate'],
                'previous': previous['error_juice_rate'],
                'delta': round(current['error_juice_rate'] - previous['error_juice_rate'], 2),
                'percent': calc_percent_change(previous['error_juice_rate'], current['error_juice_rate'])
            }
        }

        # Comparer les URLs (pages communes)
        current_urls = {u['url']: u for u in current['urls']}
        previous_urls = {u['url']: u for u in previous['urls']}

        # Pages communes avec changements
        common_urls = set(current_urls.keys()) & set(previous_urls.keys())
        url_changes = []

        for url in common_urls:
            curr = current_urls[url]
            prev = previous_urls[url]

            score_delta = round((curr['seo_score'] or 0) - (prev['seo_score'] or 0), 2)
            links_delta = (curr['internal_links_received'] or 0) - (prev['internal_links_received'] or 0)

            # Ne garder que les changements significatifs
            if abs(score_delta) >= 0.5 or abs(links_delta) >= 2:
                url_changes.append({
                    'url': url,
                    'seo_score': {
                        'current': curr['seo_score'],
                        'previous': prev['seo_score'],
                        'delta': score_delta
                    },
                    'internal_links_received': {
                        'current': curr['internal_links_received'],
                        'previous': prev['internal_links_received'],
                        'delta': links_delta
                    },
                    'category': curr['category']
                })

        # Trier par delta de score décroissant
        url_changes.sort(key=lambda x: abs(x['seo_score']['delta']), reverse=True)

        # Pages nouvelles et supprimées
        new_urls = set(current_urls.keys()) - set(previous_urls.keys())
        removed_urls = set(previous_urls.keys()) - set(current_urls.keys())

        # Quick Wins comparison
        current_qw = {(q['url'], q['keyword']): q for q in current.get('quick_wins', [])}
        previous_qw = {(q['url'], q['keyword']): q for q in previous.get('quick_wins', [])}

        new_quick_wins = []
        resolved_quick_wins = []

        for key in set(current_qw.keys()) - set(previous_qw.keys()):
            new_quick_wins.append(current_qw[key])

        for key in set(previous_qw.keys()) - set(current_qw.keys()):
            # Vérifier si le keyword a une meilleure position maintenant
            prev_qw = previous_qw[key]
            resolved_quick_wins.append(prev_qw)

        # Erreurs comparison
        current_errors = {e['url']: e for e in current.get('error_pages', [])}
        previous_errors = {e['url']: e for e in previous.get('error_pages', [])}

        new_errors = [current_errors[u] for u in set(current_errors.keys()) - set(previous_errors.keys())]
        fixed_errors = [previous_errors[u] for u in set(previous_errors.keys()) - set(current_errors.keys())]

        return {
            'current': {
                'analysis_id': current_id,
                'domain': current['domain'],
                'created_at': current['created_at']
            },
            'previous': {
                'analysis_id': previous_id,
                'domain': previous['domain'],
                'created_at': previous['created_at']
            },
            'global_delta': global_delta,
            'url_changes': url_changes[:100],  # Top 100 changements
            'new_urls': list(new_urls)[:50],
            'removed_urls': list(removed_urls)[:50],
            'new_urls_count': len(new_urls),
            'removed_urls_count': len(removed_urls),
            'quick_wins': {
                'new': new_quick_wins[:20],
                'resolved': resolved_quick_wins[:20],
                'current_count': len(current.get('quick_wins', [])),
                'previous_count': len(previous.get('quick_wins', []))
            },
            'errors': {
                'new': new_errors,
                'fixed': fixed_errors,
                'current_count': len(current.get('error_pages', [])),
                'previous_count': len(previous.get('error_pages', []))
            }
        }

    except Exception as e:
        logger.error(f"Erreur lors de la comparaison: {e}", exc_info=True)
        return {'error': str(e)}


def calc_percent_change(old_val, new_val) -> float:
    """Calcule le pourcentage de changement."""
    if old_val == 0:
        return 100.0 if new_val > 0 else 0.0
    return round(((new_val - old_val) / old_val) * 100, 1)


def get_domain_evolution(domain: str, limit: int = 10) -> list:
    """
    Récupère l'évolution des métriques pour un domaine.

    Args:
        domain: Nom du domaine
        limit: Nombre d'analyses à récupérer

    Returns:
        Liste des analyses avec métriques pour graphique d'évolution
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT analysis_id, created_at, total_urls, total_internal_links,
                       total_backlinks, median_seo_score, error_juice_rate
                FROM analyses
                WHERE domain = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (domain, limit))

            rows = cursor.fetchall()
            # Inverser pour avoir l'ordre chronologique
            return [dict(r) for r in reversed(rows)]

    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'évolution: {e}")
        return []


# Initialiser la base de données au chargement du module
init_db()
