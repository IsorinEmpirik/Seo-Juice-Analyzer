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
        self.backlink_score = self.config.get('backlink_score', 3)
        self.transmission_rate = self.config.get('transmission_rate', 0.85)
        self.content_link_weight = self.config.get('content_link_weight', 9)
        self.navigation_link_weight = self.config.get('navigation_link_weight', 1)
        self.iterations = self.config.get('iterations', 3)
        self.normalize_max = self.config.get('normalize_max', 100)

        # Données
        self.url_scores = {}  # {url: score}
        self.url_data = {}    # {url: {backlinks, internal_links_received, anchors, etc.}}
        self.internal_links = {}  # {source_url: [liste de liens sortants]}
        self.backlinks = {}   # {url: nombre de backlinks}

    @staticmethod
    def _should_exclude_url(url: str) -> bool:
        """
        Détermine si une URL doit être exclue de l'analyse

        Args:
            url: L'URL à vérifier

        Returns:
            True si l'URL doit être exclue, False sinon
        """
        # Exclure les URLs en .pdf
        if url.lower().endswith('.pdf'):
            return True

        # Exclure les URLs avec paramètres GET
        if '?' in url:
            return True

        return False

    def analyze(self, sf_parser, ahrefs_parser, gsc_data: Dict = None) -> Dict:
        """
        Lance l'analyse complète

        Args:
            sf_parser: ScreamingFrogParser avec les liens internes
            ahrefs_parser: AhrefsParser avec les backlinks
            gsc_data: Données GSC agrégées par URL (optionnel)

        Returns:
            Dictionnaire avec tous les résultats
        """
        logger.info("=" * 60)
        logger.info("ANALYSE DU MAILLAGE INTERNE - DEBUT")
        logger.info("=" * 60)

        # Stocker les données GSC pour utilisation dans _calculate_statistics
        self.gsc_data = gsc_data or {}
        if self.gsc_data:
            logger.info(f"Données GSC disponibles pour {len(self.gsc_data)} URLs")

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
        logger.info(f"URLs uniques trouvees avant filtrage: {len(all_urls)}")

        # Déterminer le domaine principal (celui qui apparaît le plus)
        from urllib.parse import urlparse
        from collections import Counter

        domains = [urlparse(url).netloc for url in all_urls]
        domain_counts = Counter(domains)
        main_domain = domain_counts.most_common(1)[0][0] if domain_counts else None

        logger.info(f"Domaine principal detecte: {main_domain}")

        # Filtrer uniquement les URLs du domaine principal
        all_urls = [url for url in all_urls if urlparse(url).netloc == main_domain]
        logger.info(f"URLs du domaine principal: {len(all_urls)}")

        # Filtrer les URLs à exclure (.pdf et paramètres GET)
        excluded_count = sum(1 for url in all_urls if self._should_exclude_url(url))
        all_urls = [url for url in all_urls if not self._should_exclude_url(url)]
        logger.info(f"URLs exclues (.pdf et parametres GET): {excluded_count}")
        logger.info(f"URLs retenues pour l'analyse: {len(all_urls)}")

        # Initialiser les scores à 0
        for url in all_urls:
            self.url_scores[url] = 0.0
            self.url_data[url] = {
                'backlinks_count': 0,
                'internal_links_received': 0,
                'internal_links_received_content': 0,
                'internal_links_received_navigation': 0,
                'internal_links_sent': 0,
                'anchors': [],
                'status_code': 200,  # Par défaut
                'is_error': False
            }

        # Stocker le domaine principal pour filtrage ultérieur
        self.main_domain = main_domain

        # Récupérer les liens internes groupés par source
        self.internal_links = sf_parser.get_links_by_source()
        logger.info(f"Pages sources (qui font des liens): {len(self.internal_links)}")

        # Récupérer les backlinks
        raw_backlinks = ahrefs_parser.get_backlink_count_by_url()

        # Filtrer les backlinks vers des URLs exclues
        self.backlinks = {url: count for url, count in raw_backlinks.items()
                         if not self._should_exclude_url(url)}

        excluded_backlinks = len(raw_backlinks) - len(self.backlinks)
        logger.info(f"URLs avec backlinks externes (brut): {len(raw_backlinks)}")
        logger.info(f"Backlinks vers URLs exclues: {excluded_backlinks}")
        logger.info(f"URLs avec backlinks retenus: {len(self.backlinks)}")

        # Mettre à jour les données avec les backlinks
        for url, count in self.backlinks.items():
            if url in self.url_data:
                self.url_data[url]['backlinks_count'] = count

        # Compter les liens internes reçus et récupérer les ancres
        for source_url, links in self.internal_links.items():
            # Filtrer seulement les liens vers le domaine principal ET exclure .pdf et paramètres GET
            links = [l for l in links
                    if urlparse(l['destination']).netloc == main_domain
                    and not self._should_exclude_url(l['destination'])]

            # Compter les liens sortants
            if source_url in self.url_data:
                self.url_data[source_url]['internal_links_sent'] = len(links)

            for link in links:
                dest_url = link['destination']

                # Compter les liens reçus
                if dest_url in self.url_data:
                    self.url_data[dest_url]['internal_links_received'] += 1

                    # Compter séparément contenu vs navigation
                    if link['link_position'] in ['Contenu', 'Content']:
                        self.url_data[dest_url]['internal_links_received_content'] += 1
                    else:
                        self.url_data[dest_url]['internal_links_received_navigation'] += 1

                    # Stocker l'ancre si elle n'est pas vide
                    if link['anchor']:
                        self.url_data[dest_url]['anchors'].append(link['anchor'])

                    # Stocker le code de statut
                    if link['status_code']:
                        self.url_data[dest_url]['status_code'] = link['status_code']
                        self.url_data[dest_url]['is_error'] = link['status_code'] != 200

    def _calculate_initial_scores(self):
        """Prépare les scores initiaux (tous à zéro)"""
        logger.info("\n2. PREPARATION DES SCORES INITIAUX")
        logger.info("-" * 60)

        # Les scores sont déjà initialisés à 0 dans _initialize_data
        # Les backlinks seront injectés à CHAQUE itération (pas seulement au début)

        total_backlinks = sum(self.backlinks.values())
        logger.info(f"Total backlinks: {total_backlinks}")
        logger.info(f"Score par backlink (à chaque itération): {self.backlink_score}")

        # Top 5 des pages avec le plus de backlinks
        sorted_backlinks = sorted(self.backlinks.items(), key=lambda x: x[1], reverse=True)[:5]
        logger.info("\nTop 5 pages avec le plus de backlinks:")
        for url, count in sorted_backlinks:
            logger.info(f"  - {url[:60]}... : {count} backlinks ({count * self.backlink_score:.1f} jus/itération)")

    def _run_iterations(self):
        """Exécute les itérations avec conservation du jus et convergence"""
        logger.info(f"\n3. ITERATIONS DE DISTRIBUTION DU JUS (avec convergence)")
        logger.info("-" * 60)

        from urllib.parse import urlparse

        # Calculer le jus injecté par les backlinks à chaque itération
        backlinks_juice_per_iteration = sum(count * self.backlink_score for count in self.backlinks.values())
        logger.info(f"Jus injecté par itération (backlinks): {backlinks_juice_per_iteration:.2f}")
        logger.info(f"Modèle: Flux avec perte de 15% à chaque transmission")
        logger.info(f"Poids des liens: Contenu = {self.content_link_weight}, Navigation = {self.navigation_link_weight}")

        # Identifier la homepage (page avec le plus de backlinks) pour debug
        homepage_url = max(self.backlinks.items(), key=lambda x: x[1])[0] if self.backlinks else None
        if homepage_url:
            logger.info(f"\n📍 Page suivie (+ de backlinks): {homepage_url}")
            logger.info(f"   Backlinks: {self.backlinks.get(homepage_url, 0)}")
            logger.info(f"   Liens sortants: {len(self.internal_links.get(homepage_url, []))}")
            logger.info(f"   Liens entrants: {self.url_data.get(homepage_url, {}).get('internal_links_received', 0)}")

        # Paramètres de convergence
        max_iterations = 20
        tolerance = 0.01

        for iteration in range(max_iterations):
            logger.info(f"\nIteration {iteration + 1}/{max_iterations}")

            # Initialiser les nouveaux scores à ZÉRO (pas une copie!)
            new_scores = {url: 0.0 for url in self.url_scores}

            # Étape 1: Injecter le jus des backlinks (à CHAQUE itération)
            for url, count in self.backlinks.items():
                if url in new_scores:
                    backlink_juice = count * self.backlink_score
                    new_scores[url] += backlink_juice

            # Étape 2: Distribuer les 85% transmis (15% perdus dans le vide)
            for source_url, links in self.internal_links.items():
                if source_url not in self.url_scores:
                    continue

                current_score = self.url_scores[source_url]

                # Jus à transmettre (85% du score actuel, 15% sont PERDUS)
                juice_to_transmit = current_score * self.transmission_rate

                if juice_to_transmit <= 0:
                    continue

                # Filtrer uniquement les liens vers le domaine principal ET exclure .pdf et paramètres GET
                links = [l for l in links
                        if urlparse(l['destination']).netloc == self.main_domain
                        and not self._should_exclude_url(l['destination'])]

                # Séparer les liens par position (Contenu vs Navigation)
                content_links = [l for l in links if l['link_position'] in ['Contenu', 'Content']]
                navigation_links = [l for l in links if l['link_position'] not in ['Contenu', 'Content']]

                # Nombre de liens de chaque type
                num_content = len(content_links)
                num_navigation = len(navigation_links)

                # Calculer le poids total (contenu = 9x, navigation = 1x)
                total_weight = (num_content * self.content_link_weight) + (num_navigation * self.navigation_link_weight)

                if total_weight > 0:
                    # Jus par unité de poids
                    juice_per_weight_unit = juice_to_transmit / total_weight

                    # Distribuer aux liens de contenu (poids 9)
                    if num_content > 0:
                        juice_per_content_link = juice_per_weight_unit * self.content_link_weight
                        for link in content_links:
                            dest_url = link['destination']
                            if dest_url in new_scores:
                                new_scores[dest_url] += juice_per_content_link

                    # Distribuer aux liens de navigation (poids 1)
                    if num_navigation > 0:
                        juice_per_nav_link = juice_per_weight_unit * self.navigation_link_weight
                        for link in navigation_links:
                            dest_url = link['destination']
                            if dest_url in new_scores:
                                new_scores[dest_url] += juice_per_nav_link
                # Si total_weight == 0 (pas de liens sortants), les 85% sont perdus dans le vide

            # Vérifier la convergence
            max_change = max(abs(new_scores[url] - self.url_scores[url]) for url in self.url_scores)

            # Calculer le jus total (à l'équilibre)
            current_total_juice = sum(new_scores.values())

            # Afficher les stats
            max_score = max(new_scores.values()) if new_scores else 0
            logger.info(f"  Jus total: {current_total_juice:.2f}")
            logger.info(f"  Max score: {max_score:.2f} | Max changement: {max_change:.4f}")

            # Debug de la homepage
            if homepage_url and homepage_url in new_scores:
                old_score = self.url_scores.get(homepage_url, 0)
                new_score = new_scores.get(homepage_url, 0)
                logger.info(f"  📍 Homepage: {old_score:.2f} → {new_score:.2f} (Δ {new_score - old_score:+.2f})")

            # Mettre à jour les scores
            self.url_scores = new_scores

            # Vérifier si convergence atteinte
            if max_change < tolerance:
                logger.info(f"✓ Convergence atteinte à l'itération {iteration + 1} (changement < {tolerance})")
                break
        else:
            logger.info(f"✓ Nombre maximum d'itérations atteint ({max_iterations})")

    def _normalize_scores(self):
        """Normalise les scores sur 100"""
        logger.info(f"\n4. NORMALISATION DES SCORES (max = {self.normalize_max})")
        logger.info("-" * 60)

        max_score = max(self.url_scores.values()) if self.url_scores else 1

        # Identifier la page avec le score max
        max_url = max(self.url_scores.items(), key=lambda x: x[1])[0] if self.url_scores else None

        if max_url:
            logger.info(f"\n📊 Page avec score maximum:")
            logger.info(f"   URL: {max_url}")
            logger.info(f"   Score brut: {max_score:.2f}")
            logger.info(f"   Backlinks: {self.url_data.get(max_url, {}).get('backlinks_count', 0)}")
            logger.info(f"   Liens sortants: {self.url_data.get(max_url, {}).get('internal_links_sent', 0)}")
            logger.info(f"   Liens entrants: {self.url_data.get(max_url, {}).get('internal_links_received', 0)}")

        if max_score > 0:
            for url in self.url_scores:
                self.url_scores[url] = (self.url_scores[url] / max_score) * self.normalize_max

        logger.info(f"\nScore maximum avant normalisation: {max_score:.2f}")
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
            'has_gsc_data': bool(self.gsc_data),
            'gsc_urls_count': len(self.gsc_data) if self.gsc_data else 0,
            'config': {
                'backlink_score': self.backlink_score,
                'transmission_rate': self.transmission_rate,
                'content_link_weight': self.content_link_weight,
                'navigation_link_weight': self.navigation_link_weight,
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
                'internal_links_received_content': url_info['internal_links_received_content'],
                'internal_links_received_navigation': url_info['internal_links_received_navigation'],
                'internal_links_sent': url_info['internal_links_sent'],
                'status_code': url_info['status_code'],
                'is_error': url_info['is_error'],
                'top_3_anchors': [{'anchor': anchor, 'count': count} for anchor, count in top_3_anchors],
                'category': self._get_url_category(url)
            }

            # Ajouter les données GSC si disponibles
            if url in self.gsc_data:
                gsc_info = self.gsc_data[url]
                url_result['gsc_clicks'] = gsc_info.get('total_clicks', 0)
                url_result['gsc_impressions'] = gsc_info.get('total_impressions', 0)
                url_result['gsc_queries_count'] = gsc_info.get('queries_count', 0)
                # Stocker TOUS les mots-clés avec leurs données individuelles
                url_result['gsc_keywords'] = gsc_info.get('keywords', [])
                # Calculer le meilleur mot-clé (position la plus basse)
                if url_result['gsc_keywords']:
                    url_result['gsc_best_keyword'] = min(
                        url_result['gsc_keywords'],
                        key=lambda x: x['position']
                    )
                else:
                    url_result['gsc_best_keyword'] = None
            else:
                url_result['gsc_clicks'] = None
                url_result['gsc_impressions'] = None
                url_result['gsc_queries_count'] = None
                url_result['gsc_keywords'] = []
                url_result['gsc_best_keyword'] = None

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

        # Distribution du jus SEO par code de statut
        results['juice_by_status'] = self._calculate_juice_by_status(results['urls'])

        logger.info(f"URLs analysees: {results['total_urls']}")
        logger.info(f"Pages sources de jus: {len(results['top_juice_sources'])}")
        logger.info(f"Pages en erreur recevant des liens: {len(results['error_pages_with_links'])}")
        logger.info(f"Taux de jus sur erreurs: {results['error_juice_rate']:.2f}%")

        return results

    def _calculate_juice_by_status(self, urls: List[Dict]) -> Dict:
        """Calcule la distribution du jus SEO par code de statut"""
        status_groups = {
            '200': 0,
            '3xx': 0,
            '4xx': 0,
            '5xx': 0,
            'Autre': 0
        }

        for url_data in urls:
            status_code = url_data['status_code']
            juice = url_data['seo_score']

            if status_code == 200:
                status_groups['200'] += juice
            elif 300 <= status_code < 400:
                status_groups['3xx'] += juice
            elif 400 <= status_code < 500:
                status_groups['4xx'] += juice
            elif 500 <= status_code < 600:
                status_groups['5xx'] += juice
            else:
                status_groups['Autre'] += juice

        # Arrondir les valeurs
        for key in status_groups:
            status_groups[key] = round(status_groups[key], 2)

        return status_groups

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
