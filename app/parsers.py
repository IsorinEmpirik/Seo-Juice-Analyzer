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

            # Exclure les liens canoniques, hreflang et autres positions non pertinentes
            # On ne garde que : Contenu, Navigation, En-tête, Pied de page
            excluded_positions = ['canonique', 'canonical', 'hreflang', 'pagination', 'meta']
            before_count = len(self.df)
            self.df = self.df[~self.df['Position du lien'].str.lower().str.strip().isin(excluded_positions)].copy()
            excluded_count = before_count - len(self.df)
            if excluded_count > 0:
                logger.info(f"Liens canoniques/hreflang/meta exclus: {excluded_count}")

            # Exclure les self-links (source == destination)
            before_count = len(self.df)
            self.df = self.df[self.df['Source'] != self.df['Destination']].copy()
            selflink_count = before_count - len(self.df)
            if selflink_count > 0:
                logger.info(f"Self-links exclus (source == destination): {selflink_count}")

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
        Agrège les métriques par URL avec TOUS les mots-clés individuels

        Returns:
            Dictionnaire {url: {total_clicks, total_impressions, queries_count, keywords: [...]}}
        """
        if self.df is None:
            raise ValueError("Le CSV n'a pas encore été parsé. Appelez parse() d'abord.")

        aggregated = {}

        for url, group in self.df.groupby('Page'):
            # Garder TOUS les mots-clés avec leurs données individuelles
            keywords = []
            for _, row in group.iterrows():
                keywords.append({
                    'query': row['Query'],
                    'clicks': int(row.get('Clicks', 0)),
                    'impressions': int(row.get('Impressions', 0)),
                    'position': round(row['Position'], 1),
                    'ctr': round(row.get('CTR', 0), 2) if 'CTR' in row else 0
                })

            # Trier par clics décroissants
            keywords.sort(key=lambda x: x['clicks'], reverse=True)

            aggregated[url] = {
                'total_clicks': int(group['Clicks'].sum()),
                'total_impressions': int(group['Impressions'].sum()),
                'queries_count': len(group),
                'keywords': keywords  # TOUS les mots-clés, pas juste top 5
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


class EmbeddingsParser:
    """Parser pour les fichiers CSV d'embeddings (compatible Gemini et OpenAI)"""

    # Alias pour la colonne URL
    URL_ALIASES = ['adresse', 'address', 'url', 'page', 'page_url', 'uri']

    # Alias pour la colonne embeddings (Gemini + OpenAI + génériques)
    EMBEDDING_ALIASES = [
        'extract embeddings from page content',  # Gemini via Screaming Frog
        'embeddings', 'embedding', 'page_embedding',
        'content_embedding', 'content_embeddings',
        'vector', 'vectors', 'embedding_vector',
        'text_embedding', 'openai_embedding', 'gemini_embedding',
    ]

    # Seuil minimum de valeurs pour considérer une cellule comme un embedding
    MIN_EMBEDDING_DIMENSIONS = 50

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.df = None
        self.embeddings = {}  # {url: [vecteur]}
        self.detected_provider = None  # 'gemini', 'openai', or 'unknown'
        self.embedding_dimensions = None
        self.parse_warnings = []
        self.parse_stats = {}

    def _find_url_column(self, columns: List[str]) -> str:
        """Trouve la colonne URL parmi les colonnes du CSV"""
        for col in columns:
            col_clean = col.strip().lower()
            for alias in self.URL_ALIASES:
                if alias == col_clean:
                    return col
        return None

    def _find_embedding_column(self, columns: List[str]) -> str:
        """Trouve la colonne embedding par nom d'alias"""
        for col in columns:
            col_clean = col.strip().lower()
            for alias in self.EMBEDDING_ALIASES:
                if alias == col_clean:
                    return col
        return None

    def _detect_embedding_column(self, df: pd.DataFrame, exclude_col: str = None) -> str:
        """
        Auto-détection de la colonne embedding en analysant le contenu.
        Cherche une colonne contenant des chaînes de nombres flottants séparés par des virgules.
        """
        best_col = None
        best_score = 0

        for col in df.columns:
            if col == exclude_col:
                continue
            # Tester les premières lignes non-vides
            sample = df[col].dropna().head(5)
            if len(sample) == 0:
                continue

            match_count = 0
            for val in sample:
                val_str = str(val).strip()
                # Retirer les crochets JSON si présents [...]
                if val_str.startswith('[') and val_str.endswith(']'):
                    val_str = val_str[1:-1]
                parts = val_str.split(',')
                if len(parts) >= self.MIN_EMBEDDING_DIMENSIONS:
                    try:
                        [float(x.strip()) for x in parts[:10]]
                        match_count += 1
                    except (ValueError, AttributeError):
                        pass

            if match_count > best_score:
                best_score = match_count
                best_col = col

        if best_score >= 2:  # Au moins 2 lignes valides sur 5
            return best_col
        return None

    def _detect_provider(self, embedding_col_name: str, dimensions: int) -> str:
        """Détecte le fournisseur d'embeddings probable"""
        col_lower = embedding_col_name.strip().lower()
        if 'gemini' in col_lower or col_lower == 'extract embeddings from page content':
            return 'gemini'
        if 'openai' in col_lower:
            return 'openai'
        # Détection par dimensions typiques
        if dimensions == 768:
            return 'gemini'  # text-embedding-004
        if dimensions in (1536, 3072):
            return 'openai'  # ada-002 (1536), text-embedding-3-large (3072)
        return 'auto-détecté'

    def _parse_embedding_vector(self, embedding_str: str) -> List[float]:
        """
        Parse une chaîne d'embeddings en vecteur de floats.
        Gère les formats : "0.1,0.2,0.3" et "[0.1, 0.2, 0.3]"
        """
        if pd.isna(embedding_str) or not embedding_str:
            return None

        try:
            val_str = str(embedding_str).strip()
            # Retirer les crochets JSON si présents
            if val_str.startswith('[') and val_str.endswith(']'):
                val_str = val_str[1:-1]
            values = [float(x.strip()) for x in val_str.split(',') if x.strip()]
            return values if len(values) >= self.MIN_EMBEDDING_DIMENSIONS else None
        except (ValueError, AttributeError) as e:
            logger.warning(f"Erreur parsing embedding: {e}")
            return None

    def _read_csv_flexible(self) -> pd.DataFrame:
        """Lit le CSV en essayant plusieurs encodages et séparateurs"""
        errors = []
        for encoding in ['utf-8', 'utf-8-sig', 'latin-1']:
            for sep in [',', ';', '\t']:
                try:
                    df = pd.read_csv(self.file_path, encoding=encoding, sep=sep)
                    if len(df.columns) >= 2 and len(df) > 0:
                        return df
                except Exception as e:
                    errors.append(f"{encoding}/{sep}: {e}")
        raise ValueError(
            f"Impossible de lire le fichier CSV. Formats testés : UTF-8, Latin-1 avec séparateurs virgule/point-virgule/tab. "
            f"Vérifiez que le fichier est un CSV valide avec au minimum 2 colonnes (URL + embedding)."
        )

    def parse(self) -> pd.DataFrame:
        """
        Parse le fichier CSV des embeddings (compatible Gemini et OpenAI).
        Auto-détecte les colonnes et valide les données.
        """
        logger.info(f"Parsing Embeddings CSV: {self.file_path}")

        try:
            # Lecture flexible du CSV
            self.df = self._read_csv_flexible()

            columns = list(self.df.columns)
            logger.info(f"Colonnes trouvées: {columns}")
            logger.info(f"Nombre de lignes brutes: {len(self.df)}")

            # 1. Trouver la colonne URL
            url_col = self._find_url_column(columns)
            if not url_col:
                raise ValueError(
                    f"Colonne URL non trouvée. Colonnes détectées : {columns}. "
                    f"Noms acceptés : {', '.join(self.URL_ALIASES)}"
                )

            # 2. Trouver la colonne embedding (par nom ou auto-détection)
            embedding_col = self._find_embedding_column(columns)
            detection_method = 'alias'

            if not embedding_col:
                # Auto-détection par contenu
                embedding_col = self._detect_embedding_column(self.df, exclude_col=url_col)
                detection_method = 'auto-détection'

            if not embedding_col:
                raise ValueError(
                    f"Colonne d'embeddings non trouvée. Colonnes détectées : {columns}. "
                    f"Noms acceptés : {', '.join(self.EMBEDDING_ALIASES)}. "
                    f"L'auto-détection par contenu n'a pas trouvé de colonne contenant des vecteurs de nombres."
                )

            logger.info(f"Colonne URL: '{url_col}', Colonne embedding: '{embedding_col}' (méthode: {detection_method})")

            # Renommer les colonnes
            self.df = self.df.rename(columns={
                url_col: 'url',
                embedding_col: 'embedding_raw'
            })

            # Parser les embeddings
            self.df['embedding'] = self.df['embedding_raw'].apply(self._parse_embedding_vector)

            # Supprimer les lignes sans embedding valide
            initial_count = len(self.df)
            self.df = self.df.dropna(subset=['embedding'])
            self.df = self.df[self.df['embedding'].apply(lambda x: x is not None and len(x) > 0)]
            valid_count = len(self.df)
            removed_count = initial_count - valid_count

            if valid_count == 0:
                raise ValueError(
                    f"Aucun embedding valide trouvé dans la colonne '{embedding_col}'. "
                    f"Sur {initial_count} lignes, aucune ne contient un vecteur de nombres valide "
                    f"(minimum {self.MIN_EMBEDDING_DIMENSIONS} dimensions attendues). "
                    f"Vérifiez le format : nombres séparés par des virgules, ex: 0.123,-0.456,0.789,..."
                )

            if removed_count > 0:
                self.parse_warnings.append(
                    f"{removed_count} ligne(s) ignorée(s) car embedding invalide ou manquant"
                )
                logger.info(f"Lignes sans embedding valide supprimées: {removed_count}")

            # Vérifier la cohérence des dimensions
            dimensions = self.df['embedding'].apply(len)
            unique_dims = dimensions.unique()

            if len(unique_dims) > 1:
                # Garder uniquement la dimension majoritaire
                main_dim = dimensions.mode()[0]
                mismatched = len(self.df[dimensions != main_dim])
                self.df = self.df[dimensions == main_dim]
                self.parse_warnings.append(
                    f"{mismatched} embedding(s) avec dimensions incohérentes ignoré(s) "
                    f"(attendu: {main_dim}, trouvé: {', '.join(str(d) for d in unique_dims)})"
                )
                logger.warning(f"Dimensions incohérentes détectées: {unique_dims}. Conservation de la dimension {main_dim}")

            self.embedding_dimensions = int(dimensions.mode()[0])

            # Nettoyer les URLs
            self.df['url'] = self.df['url'].str.strip()

            # Détecter le fournisseur
            self.detected_provider = self._detect_provider(embedding_col, self.embedding_dimensions)

            # Construire le dictionnaire {url: embedding}
            for _, row in self.df.iterrows():
                self.embeddings[row['url']] = row['embedding']

            # Stats de parsing
            self.parse_stats = {
                'total_rows': initial_count,
                'valid_embeddings': len(self.embeddings),
                'removed_rows': removed_count,
                'dimensions': self.embedding_dimensions,
                'provider': self.detected_provider,
                'detection_method': detection_method,
                'embedding_column': embedding_col,
                'warnings': self.parse_warnings,
            }

            logger.info(
                f"Parsing OK: {len(self.embeddings)} embeddings valides, "
                f"{self.embedding_dimensions} dimensions, "
                f"fournisseur détecté: {self.detected_provider}"
            )

            return self.df

        except Exception as e:
            logger.error(f"Erreur lors du parsing Embeddings: {e}")
            raise

    def get_embeddings_by_url(self) -> Dict[str, List[float]]:
        """Retourne le dictionnaire des embeddings par URL"""
        if not self.embeddings:
            raise ValueError("Le CSV n'a pas encore été parsé. Appelez parse() d'abord.")
        return self.embeddings

    def get_embedding(self, url: str) -> List[float]:
        """Retourne l'embedding pour une URL spécifique"""
        return self.embeddings.get(url)

    def get_parse_stats(self) -> dict:
        """Retourne les statistiques de parsing pour le feedback utilisateur"""
        return self.parse_stats


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calcule la similarité cosinus entre deux vecteurs

    Args:
        vec1: Premier vecteur
        vec2: Deuxième vecteur

    Returns:
        Score de similarité entre -1 et 1
    """
    if not vec1 or not vec2:
        return 0.0

    if len(vec1) != len(vec2):
        logger.warning(f"Tailles de vecteurs différentes: {len(vec1)} vs {len(vec2)}")
        return 0.0

    import math

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


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
