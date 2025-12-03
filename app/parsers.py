"""
Modules de parsing pour les fichiers CSV (Screaming Frog et Ahrefs)
"""
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class ScreamingFrogParser:
    """Parser pour les fichiers CSV de Screaming Frog (liens internes)"""

    REQUIRED_COLUMNS = [
        'Source',
        'Destination',
        'Ancrage',
        'Code de statut',
        'Position du lien'
    ]

    def __init__(self, file_path: str):
        """
        Initialize le parser

        Args:
            file_path: Chemin vers le fichier CSV Screaming Frog
        """
        self.file_path = Path(file_path)
        self.df = None
        self.internal_links = []

    def parse(self) -> pd.DataFrame:
        """
        Parse le fichier CSV Screaming Frog

        Returns:
            DataFrame pandas avec les liens internes
        """
        logger.info(f"Parsing Screaming Frog CSV: {self.file_path}")

        try:
            # Lire le CSV
            self.df = pd.read_csv(self.file_path, encoding='utf-8')

            # Vérifier les colonnes requises
            missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in self.df.columns]
            if missing_cols:
                raise ValueError(f"Colonnes manquantes dans le CSV Screaming Frog: {missing_cols}")

            # Nettoyer les données
            logger.info(f"Nombre de lignes brutes: {len(self.df)}")

            # Filtrer uniquement les hyperliens (pas les images, etc.)
            if 'Type' in self.df.columns:
                self.df = self.df[self.df['Type'] == 'Hyperlien'].copy()
                logger.info(f"Après filtrage hyperliens: {len(self.df)}")

            # Supprimer les lignes avec des valeurs manquantes dans les colonnes critiques
            self.df = self.df.dropna(subset=['Source', 'Destination'])

            # Normaliser les URLs (enlever les espaces, etc.)
            self.df['Source'] = self.df['Source'].str.strip()
            self.df['Destination'] = self.df['Destination'].str.strip()

            # S'assurer que Position du lien est bien définie
            if 'Position du lien' not in self.df.columns:
                # Si la colonne n'existe pas, on met "Contenu" par défaut
                self.df['Position du lien'] = 'Contenu'
            else:
                # Remplacer les valeurs manquantes par "Contenu"
                self.df['Position du lien'].fillna('Contenu', inplace=True)

            # Remplir les ancres vides
            self.df['Ancrage'].fillna('', inplace=True)

            logger.info(f"Nombre de liens internes parsés: {len(self.df)}")

            return self.df

        except Exception as e:
            logger.error(f"Erreur lors du parsing Screaming Frog: {e}")
            raise

    def get_links_by_source(self) -> Dict[str, List[Dict]]:
        """
        Groupe les liens par page source

        Returns:
            Dictionnaire {url_source: [liste de liens sortants]}
        """
        if self.df is None:
            raise ValueError("Le CSV n'a pas encore été parsé. Appelez parse() d'abord.")

        links_by_source = {}

        for _, row in self.df.iterrows():
            source = row['Source']
            if source not in links_by_source:
                links_by_source[source] = []

            links_by_source[source].append({
                'destination': row['Destination'],
                'anchor': row['Ancrage'],
                'status_code': row['Code de statut'],
                'link_position': row['Position du lien']  # Contenu ou Navigation
            })

        return links_by_source

    def get_all_urls(self) -> set:
        """
        Récupère toutes les URLs uniques (sources + destinations)

        Returns:
            Set de toutes les URLs du site
        """
        if self.df is None:
            raise ValueError("Le CSV n'a pas encore été parsé. Appelez parse() d'abord.")

        sources = set(self.df['Source'].unique())
        destinations = set(self.df['Destination'].unique())

        return sources.union(destinations)


class AhrefsParser:
    """Parser pour les fichiers CSV d'Ahrefs (backlinks externes)"""

    REQUIRED_COLUMNS = [
        'Target URL',
        'Nofollow'
    ]

    def __init__(self, file_path: str):
        """
        Initialize le parser

        Args:
            file_path: Chemin vers le fichier CSV Ahrefs
        """
        self.file_path = Path(file_path)
        self.df = None

    def parse(self) -> pd.DataFrame:
        """
        Parse le fichier CSV Ahrefs

        Returns:
            DataFrame pandas avec les backlinks
        """
        logger.info(f"Parsing Ahrefs CSV: {self.file_path}")

        try:
            # Lire le CSV (skip la première ligne si c'est un #)
            self.df = pd.read_csv(self.file_path, encoding='utf-8')

            # Vérifier les colonnes requises
            missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in self.df.columns]
            if missing_cols:
                raise ValueError(f"Colonnes manquantes dans le CSV Ahrefs: {missing_cols}")

            # Nettoyer les données
            logger.info(f"Nombre de backlinks bruts: {len(self.df)}")

            # Filtrer les backlinks nofollow (on ne les compte pas)
            self.df = self.df[self.df['Nofollow'] == False].copy()
            logger.info(f"Après filtrage nofollow: {len(self.df)}")

            # Supprimer les lignes avec Target URL manquante
            self.df = self.df.dropna(subset=['Target URL'])

            # Normaliser les URLs
            self.df['Target URL'] = self.df['Target URL'].str.strip()

            # S'assurer que Anchor existe
            if 'Anchor' not in self.df.columns:
                self.df['Anchor'] = ''
            else:
                self.df['Anchor'].fillna('', inplace=True)

            logger.info(f"Nombre de backlinks valides: {len(self.df)}")

            return self.df

        except Exception as e:
            logger.error(f"Erreur lors du parsing Ahrefs: {e}")
            raise

    def get_backlinks_by_url(self) -> Dict[str, List[Dict]]:
        """
        Groupe les backlinks par URL cible

        Returns:
            Dictionnaire {url_cible: [liste de backlinks]}
        """
        if self.df is None:
            raise ValueError("Le CSV n'a pas encore été parsé. Appelez parse() d'abord.")

        backlinks_by_url = {}

        for _, row in self.df.iterrows():
            target = row['Target URL']
            if target not in backlinks_by_url:
                backlinks_by_url[target] = []

            backlink_info = {
                'anchor': row.get('Anchor', ''),
            }

            # Ajouter des infos supplémentaires si disponibles
            if 'Referring page URL' in row:
                backlink_info['referring_url'] = row['Referring page URL']
            if 'Domain rating' in row:
                backlink_info['domain_rating'] = row['Domain rating']

            backlinks_by_url[target].append(backlink_info)

        return backlinks_by_url

    def get_backlink_count_by_url(self) -> Dict[str, int]:
        """
        Compte le nombre de backlinks par URL

        Returns:
            Dictionnaire {url: nombre_de_backlinks}
        """
        if self.df is None:
            raise ValueError("Le CSV n'a pas encore été parsé. Appelez parse() d'abord.")

        return self.df['Target URL'].value_counts().to_dict()


class GSCParser:
    """Parser pour les fichiers CSV Google Search Console (via Analytics for Sheets)"""

    REQUIRED_COLUMNS = [
        'Query',
        'Page',
        'Clicks',
        'Impressions',
        'Position'
    ]

    # Colonnes alternatives (anglais/français)
    COLUMN_ALIASES = {
        'Query': ['Query', 'Requête', 'Keyword', 'Mot-clé'],
        'Page': ['Page', 'URL', 'Landing Page'],
        'Clicks': ['Clicks', 'Clics'],
        'Impressions': ['Impressions'],
        'CTR': ['CTR', 'Taux de clics'],
        'Position': ['Position', 'Avg. Position', 'Position moyenne']
    }

    def __init__(self, file_path: str, brand_keywords: List[str] = None):
        """
        Initialize le parser

        Args:
            file_path: Chemin vers le fichier CSV GSC
            brand_keywords: Liste de mots-clés marque à exclure (un par élément)
        """
        self.file_path = Path(file_path)
        self.df = None
        self.brand_keywords = [kw.lower().strip() for kw in (brand_keywords or []) if kw.strip()]

    def _parse_french_number(self, value) -> float:
        """
        Convertit un nombre au format français en float
        Ex: "24 541" -> 24541, "71,6%" -> 71.6, "1,0" -> 1.0
        """
        if pd.isna(value):
            return 0.0

        # Convertir en string
        str_value = str(value).strip()

        # Supprimer le symbole %
        str_value = str_value.replace('%', '')

        # Supprimer les séparateurs de milliers (espaces, espaces insécables, etc.)
        # L'espace insécable UTF-8 est \u00a0 ou \u202f
        str_value = str_value.replace('\u00a0', '').replace('\u202f', '').replace(' ', '').replace(' ', '')

        # Remplacer la virgule décimale par un point
        str_value = str_value.replace(',', '.')

        try:
            return float(str_value)
        except ValueError:
            logger.warning(f"Impossible de convertir '{value}' en nombre")
            return 0.0

    def _find_column(self, columns: List[str], target: str) -> str:
        """
        Trouve la colonne correspondante parmi les alias

        Args:
            columns: Liste des colonnes du CSV
            target: Nom de la colonne cible (clé dans COLUMN_ALIASES)

        Returns:
            Nom de la colonne trouvée ou None
        """
        aliases = self.COLUMN_ALIASES.get(target, [target])
        for col in columns:
            col_lower = col.lower().strip()
            for alias in aliases:
                if alias.lower() == col_lower:
                    return col
        return None

    def _is_brand_query(self, query: str) -> bool:
        """
        Vérifie si une requête contient un mot-clé marque

        Args:
            query: La requête à vérifier

        Returns:
            True si la requête contient un mot-clé marque
        """
        if not self.brand_keywords:
            return False

        query_lower = query.lower()
        for brand_kw in self.brand_keywords:
            if brand_kw in query_lower:
                return True
        return False

    def parse(self) -> pd.DataFrame:
        """
        Parse le fichier CSV GSC

        Returns:
            DataFrame pandas avec les données GSC
        """
        logger.info(f"Parsing GSC CSV: {self.file_path}")

        try:
            # Lire le CSV
            self.df = pd.read_csv(self.file_path, encoding='utf-8')

            logger.info(f"Colonnes trouvées: {list(self.df.columns)}")
            logger.info(f"Nombre de lignes brutes: {len(self.df)}")

            # Mapper les colonnes
            column_mapping = {}
            for target in self.REQUIRED_COLUMNS:
                found_col = self._find_column(list(self.df.columns), target)
                if found_col:
                    column_mapping[found_col] = target
                else:
                    logger.warning(f"Colonne '{target}' non trouvée dans le CSV GSC")

            # Vérifier les colonnes requises minimales
            required_found = ['Query', 'Page', 'Position']
            missing = [col for col in required_found if col not in column_mapping.values()]
            if missing:
                raise ValueError(f"Colonnes manquantes dans le CSV GSC: {missing}")

            # Renommer les colonnes
            self.df = self.df.rename(columns=column_mapping)

            # Convertir les nombres au format français
            if 'Clicks' in self.df.columns:
                self.df['Clicks'] = self.df['Clicks'].apply(self._parse_french_number)
            else:
                self.df['Clicks'] = 0

            if 'Impressions' in self.df.columns:
                self.df['Impressions'] = self.df['Impressions'].apply(self._parse_french_number)
            else:
                self.df['Impressions'] = 0

            if 'Position' in self.df.columns:
                self.df['Position'] = self.df['Position'].apply(self._parse_french_number)

            # Colonne CTR optionnelle
            ctr_col = self._find_column(list(self.df.columns), 'CTR')
            if ctr_col and ctr_col != 'CTR':
                self.df = self.df.rename(columns={ctr_col: 'CTR'})
            if 'CTR' in self.df.columns:
                self.df['CTR'] = self.df['CTR'].apply(self._parse_french_number)

            # Nettoyer les données
            self.df = self.df.dropna(subset=['Query', 'Page'])
            self.df['Query'] = self.df['Query'].str.strip()
            self.df['Page'] = self.df['Page'].str.strip()

            # Filtrer les requêtes marque
            if self.brand_keywords:
                initial_count = len(self.df)
                self.df['is_brand'] = self.df['Query'].apply(self._is_brand_query)
                self.df = self.df[~self.df['is_brand']].copy()
                self.df = self.df.drop(columns=['is_brand'])
                filtered_count = initial_count - len(self.df)
                logger.info(f"Requêtes marque filtrées: {filtered_count} (mots-clés: {self.brand_keywords})")

            logger.info(f"Nombre de lignes après nettoyage: {len(self.df)}")

            return self.df

        except Exception as e:
            logger.error(f"Erreur lors du parsing GSC: {e}")
            raise

    def get_data_by_url(self) -> Dict[str, List[Dict]]:
        """
        Groupe les données par URL

        Returns:
            Dictionnaire {url: [liste de données par requête]}
        """
        if self.df is None:
            raise ValueError("Le CSV n'a pas encore été parsé. Appelez parse() d'abord.")

        data_by_url = {}

        for _, row in self.df.iterrows():
            url = row['Page']
            if url not in data_by_url:
                data_by_url[url] = []

            data_by_url[url].append({
                'query': row['Query'],
                'clicks': row.get('Clicks', 0),
                'impressions': row.get('Impressions', 0),
                'ctr': row.get('CTR', 0),
                'position': row['Position']
            })

        return data_by_url

    def get_aggregated_by_url(self) -> Dict[str, Dict]:
        """
        Agrège les métriques par URL

        Returns:
            Dictionnaire {url: {total_clicks, total_impressions, avg_position, queries_count}}
        """
        if self.df is None:
            raise ValueError("Le CSV n'a pas encore été parsé. Appelez parse() d'abord.")

        aggregated = {}

        for url, group in self.df.groupby('Page'):
            # Position moyenne pondérée par impressions
            if group['Impressions'].sum() > 0:
                avg_position = (group['Position'] * group['Impressions']).sum() / group['Impressions'].sum()
            else:
                avg_position = group['Position'].mean()

            aggregated[url] = {
                'total_clicks': int(group['Clicks'].sum()),
                'total_impressions': int(group['Impressions'].sum()),
                'avg_position': round(avg_position, 1),
                'queries_count': len(group),
                'top_queries': group.nlargest(5, 'Clicks')[['Query', 'Clicks', 'Position']].to_dict('records')
            }

        return aggregated

    def get_quick_wins(self, min_position: float = 5, max_position: float = 12, min_impressions: int = 100) -> pd.DataFrame:
        """
        Identifie les Quick Wins (positions 5-12 avec bonnes impressions)

        Args:
            min_position: Position minimum (incluse)
            max_position: Position maximum (incluse)
            min_impressions: Nombre minimum d'impressions

        Returns:
            DataFrame des opportunités Quick Win
        """
        if self.df is None:
            raise ValueError("Le CSV n'a pas encore été parsé. Appelez parse() d'abord.")

        quick_wins = self.df[
            (self.df['Position'] >= min_position) &
            (self.df['Position'] <= max_position) &
            (self.df['Impressions'] >= min_impressions)
        ].copy()

        # Trier par impressions décroissantes
        quick_wins = quick_wins.sort_values('Impressions', ascending=False)

        return quick_wins


def parse_csv_files(screaming_frog_path: str, ahrefs_path: str) -> Tuple[ScreamingFrogParser, AhrefsParser]:
    """
    Parse les deux fichiers CSV

    Args:
        screaming_frog_path: Chemin vers le CSV Screaming Frog
        ahrefs_path: Chemin vers le CSV Ahrefs

    Returns:
        Tuple (ScreamingFrogParser, AhrefsParser)
    """
    # Parser Screaming Frog
    sf_parser = ScreamingFrogParser(screaming_frog_path)
    sf_parser.parse()

    # Parser Ahrefs
    ahrefs_parser = AhrefsParser(ahrefs_path)
    ahrefs_parser.parse()

    return sf_parser, ahrefs_parser
