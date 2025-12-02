"""
Analyseur de maillage interne - Calcul du "jus SEO"
"""
import logging
from typing import Dict, List, Tuple
from collections import defaultdict, Counter
import numpy as np

logger = logging.getLogger(__name__)


class SEOJuiceAnalyzer:
    """
    Calcule le score de "jus SEO" pour chaque page d'un site web
    en fonction des backlinks externes et du maillage interne
    """

    def __init__(self, config: Dict = None):
        """
        Initialize l'analyseur

        Args:
            config: Configuration de l'algorithme
        """
        self.config = config or {}

        # Paramètres par défaut
        self.backlink_score = self.config.get('backlink_score', 10)
        self.transmission_rate = self.config.get('transmission_rate', 0.85)
        self.content_link_rate = self.config.get('content_link_rate', 0.90)
        self.navigation_link_rate = self.config.get('navigation_link_rate', 0.10)
        self.iterations = self.config.get('iterations', 3)
        self.normalize_max = self.config.get('normalize_max', 100)

        # Données
        self.url_scores = {}  # {url: score}
        self.url_data = {}    # {url: {backlinks, internal_links_received, anchors, etc.}}
        self.internal_links = {}  # {source_url: [liste de liens sortants]}
        self.backlinks = {}   # {url: nombre de backlinks}

    def analyze(self, sf_parser, ahrefs_parser) -> Dict:
        """
        Lance l'analyse complète

        Args:
            sf_parser: ScreamingFrogParser avec les liens internes
            ahrefs_parser: AhrefsParser avec les backlinks

        Returns:
            Dictionnaire avec tous les résultats
        """
        logger.info("=" * 60)
        logger.info("ANALYSE DU MAILLAGE INTERNE - DEBUT")
        logger.info("=" * 60)

        # Étape 1: Initialiser les données
        self._initialize_data(sf_parser, ahrefs_parser)

        # Étape 2: Calculer les scores initiaux (backlinks)
        self._calculate_initial_scores()

        # Étape 3: Itérations de distribution du jus
        self._run_iterations()

        # Étape 4: Normaliser les scores
        self._normalize_scores()

        # Étape 5: Calculer les statistiques
        results = self._calculate_statistics(sf_parser, ahrefs_parser)

        logger.info("=" * 60)
        logger.info("ANALYSE DU MAILLAGE INTERNE - FIN")
        logger.info("=" * 60)

        return results

    def _initialize_data(self, sf_parser, ahrefs_parser):
        """Initialise les structures de données"""
        logger.info("\n1. INITIALISATION DES DONNEES")
        logger.info("-" * 60)

        # Récupérer toutes les URLs du site
        all_urls = sf_parser.get_all_urls()
        logger.info(f"URLs uniques trouvees: {len(all_urls)}")

        # Initialiser les scores à 0
        for url in all_urls:
            self.url_scores[url] = 0.0
            self.url_data[url] = {
                'backlinks_count': 0,
                'internal_links_received': 0,
                'internal_links_sent': 0,
                'anchors': [],
                'status_code': 200,  # Par défaut
                'is_error': False
            }

        # Récupérer les liens internes groupés par source
        self.internal_links = sf_parser.get_links_by_source()
        logger.info(f"Pages sources (qui font des liens): {len(self.internal_links)}")

        # Récupérer les backlinks
        self.backlinks = ahrefs_parser.get_backlink_count_by_url()
        logger.info(f"URLs avec backlinks externes: {len(self.backlinks)}")

        # Mettre à jour les données avec les backlinks
        for url, count in self.backlinks.items():
            if url in self.url_data:
                self.url_data[url]['backlinks_count'] = count

        # Compter les liens internes reçus et récupérer les ancres
        for source_url, links in self.internal_links.items():
            # Compter les liens sortants
            if source_url in self.url_data:
                self.url_data[source_url]['internal_links_sent'] = len(links)

            for link in links:
                dest_url = link['destination']

                # Compter les liens reçus
                if dest_url in self.url_data:
                    self.url_data[dest_url]['internal_links_received'] += 1

                    # Stocker l'ancre si elle n'est pas vide
                    if link['anchor']:
                        self.url_data[dest_url]['anchors'].append(link['anchor'])

                    # Stocker le code de statut
                    if link['status_code']:
                        self.url_data[dest_url]['status_code'] = link['status_code']
                        self.url_data[dest_url]['is_error'] = link['status_code'] != 200

    def _calculate_initial_scores(self):
        """Calcule les scores initiaux basés sur les backlinks"""
        logger.info("\n2. CALCUL DES SCORES INITIAUX")
        logger.info("-" * 60)

        total_backlinks = 0
        for url, count in self.backlinks.items():
            if url in self.url_scores:
                score = count * self.backlink_score
                self.url_scores[url] = score
                total_backlinks += count

        logger.info(f"Total backlinks: {total_backlinks}")
        logger.info(f"Score par backlink: {self.backlink_score}")

        # Top 5 des pages avec le plus de jus initial
        sorted_scores = sorted(self.url_scores.items(), key=lambda x: x[1], reverse=True)[:5]
        logger.info("\nTop 5 scores initiaux:")
        for url, score in sorted_scores:
            logger.info(f"  - {url[:60]}... : {score:.1f}")

    def _run_iterations(self):
        """Exécute les itérations de distribution du jus"""
        logger.info(f"\n3. ITERATIONS DE DISTRIBUTION DU JUS ({self.iterations} passes)")
        logger.info("-" * 60)

        for iteration in range(self.iterations):
            logger.info(f"\nIteration {iteration + 1}/{self.iterations}")

            # Créer une copie des scores pour cette itération
            new_scores = {url: score for url, score in self.url_scores.items()}

            # Pour chaque page source
            for source_url, links in self.internal_links.items():
                if source_url not in self.url_scores:
                    continue

                current_score = self.url_scores[source_url]

                # Jus à transmettre (85% du score actuel)
                juice_to_transmit = current_score * self.transmission_rate

                if juice_to_transmit <= 0:
                    continue

                # Séparer les liens par position (Contenu vs Navigation)
                content_links = [l for l in links if l['link_position'] in ['Contenu', 'Content']]
                navigation_links = [l for l in links if l['link_position'] not in ['Contenu', 'Content']]

                # Nombre de liens de chaque type
                num_content = len(content_links)
                num_navigation = len(navigation_links)

                # Distribuer le jus
                # 90% pour les liens de contenu
                if num_content > 0:
                    juice_per_content_link = (juice_to_transmit * self.content_link_rate) / num_content
                    for link in content_links:
                        dest_url = link['destination']
                        if dest_url in new_scores:
                            new_scores[dest_url] += juice_per_content_link

                # 10% pour les liens de navigation
                if num_navigation > 0:
                    juice_per_nav_link = (juice_to_transmit * self.navigation_link_rate) / num_navigation
                    for link in navigation_links:
                        dest_url = link['destination']
                        if dest_url in new_scores:
                            new_scores[dest_url] += juice_per_nav_link

            # Mettre à jour les scores
            self.url_scores = new_scores

            # Afficher quelques stats
            total_juice = sum(self.url_scores.values())
            max_score = max(self.url_scores.values()) if self.url_scores else 0
            logger.info(f"  Total jus: {total_juice:.1f} | Max score: {max_score:.1f}")

    def _normalize_scores(self):
        """Normalise les scores sur 100"""
        logger.info(f"\n4. NORMALISATION DES SCORES (max = {self.normalize_max})")
        logger.info("-" * 60)

        max_score = max(self.url_scores.values()) if self.url_scores else 1

        if max_score > 0:
            for url in self.url_scores:
                self.url_scores[url] = (self.url_scores[url] / max_score) * self.normalize_max

        logger.info(f"Score maximum avant normalisation: {max_score:.2f}")
        logger.info(f"Score maximum apres normalisation: {self.normalize_max}")

    def _calculate_statistics(self, sf_parser, ahrefs_parser) -> Dict:
        """Calcule toutes les statistiques pour les résultats"""
        logger.info("\n5. CALCUL DES STATISTIQUES")
        logger.info("-" * 60)

        results = {
            'urls': [],
            'total_urls': len(self.url_scores),
            'total_internal_links': len(sf_parser.df),
            'total_backlinks': len(ahrefs_parser.df),
            'config': {
                'backlink_score': self.backlink_score,
                'transmission_rate': self.transmission_rate,
                'content_link_rate': self.content_link_rate,
                'iterations': self.iterations
            }
        }

        # Pour chaque URL, créer un dictionnaire complet
        for url, score in self.url_scores.items():
            url_info = self.url_data[url]

            # Top 3 des ancres
            anchors = url_info['anchors']
            anchor_counts = Counter(anchors)
            top_3_anchors = anchor_counts.most_common(3)

            url_result = {
                'url': url,
                'seo_score': round(score, 2),
                'backlinks_count': url_info['backlinks_count'],
                'internal_links_received': url_info['internal_links_received'],
                'internal_links_sent': url_info['internal_links_sent'],
                'status_code': url_info['status_code'],
                'is_error': url_info['is_error'],
                'top_3_anchors': [{'anchor': anchor, 'count': count} for anchor, count in top_3_anchors],
                'category': self._get_url_category(url)
            }

            results['urls'].append(url_result)

        # Trier par score décroissant
        results['urls'].sort(key=lambda x: x['seo_score'], reverse=True)

        # Stats par catégorie
        results['categories'] = self._calculate_category_stats(results['urls'])

        # Pages sources de jus (celles avec le plus de backlinks)
        results['top_juice_sources'] = sorted(
            [u for u in results['urls'] if u['backlinks_count'] > 0],
            key=lambda x: x['backlinks_count'],
            reverse=True
        )[:10]

        # Pages en erreur recevant des liens
        results['error_pages_with_links'] = [
            u for u in results['urls']
            if u['is_error'] and u['internal_links_received'] > 0
        ]

        # Calcul du taux de jus envoyé sur des erreurs
        total_links_to_errors = sum(u['internal_links_received'] for u in results['error_pages_with_links'])
        results['error_juice_rate'] = (total_links_to_errors / results['total_internal_links'] * 100) if results['total_internal_links'] > 0 else 0

        logger.info(f"URLs analysees: {results['total_urls']}")
        logger.info(f"Pages sources de jus: {len(results['top_juice_sources'])}")
        logger.info(f"Pages en erreur recevant des liens: {len(results['error_pages_with_links'])}")
        logger.info(f"Taux de jus sur erreurs: {results['error_juice_rate']:.2f}%")

        return results

    def _get_url_category(self, url: str) -> str:
        """Détermine la catégorie d'une URL basée sur son chemin"""
        try:
            from urllib.parse import urlparse
            path = urlparse(url).path

            if not path or path == '/':
                return 'Homepage'

            # Extraire le premier segment du chemin
            segments = [s for s in path.split('/') if s]
            if segments:
                return segments[0].capitalize()

            return 'Autre'
        except:
            return 'Autre'

    def _calculate_category_stats(self, urls: List[Dict]) -> Dict:
        """Calcule les statistiques par catégorie"""
        categories = defaultdict(lambda: {'count': 0, 'total_score': 0, 'avg_score': 0})

        for url_data in urls:
            category = url_data['category']
            categories[category]['count'] += 1
            categories[category]['total_score'] += url_data['seo_score']

        # Calculer les moyennes
        for category in categories:
            categories[category]['avg_score'] = round(
                categories[category]['total_score'] / categories[category]['count'], 2
            )

        return dict(categories)
