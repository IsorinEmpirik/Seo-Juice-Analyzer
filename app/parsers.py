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
