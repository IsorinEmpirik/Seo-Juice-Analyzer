"""
Utilitaires pour l'application
"""
import pandas as pd
from typing import Dict, List, Tuple
import re


def detect_column_mapping(columns: List[str], mapping_type: str) -> Dict[str, str]:
    """
    Détecte automatiquement les colonnes pertinentes basé sur des mots-clés

    Args:
        columns: Liste des noms de colonnes du CSV
        mapping_type: 'screaming_frog' ou 'ahrefs'

    Returns:
        Dictionnaire de mapping {field: column_name}
    """

    if mapping_type == 'screaming_frog':
        return detect_screaming_frog_columns(columns)
    elif mapping_type == 'ahrefs':
        return detect_ahrefs_columns(columns)
    else:
        return {}


def detect_screaming_frog_columns(columns: List[str]) -> Dict[str, str]:
    """Détecte les colonnes Screaming Frog"""

    # Définir les patterns de recherche pour chaque champ
    # Basé sur les noms réels des colonnes CSV Screaming Frog
    patterns = {
        'source': ['source', 'from', 'de', 'origine'],
        'destination': ['destination', 'to', 'target', 'vers', 'cible'],
        'anchor': ['anchor', 'ancrage', 'ancre', 'texte', 'text', 'anchor text'],
        'status_code': ['status', 'code', 'statut', 'http', 'code status'],
        'link_position': ['position', 'location', 'type', 'position du lien', 'link position']
    }

    mapping = {}

    for field, keywords in patterns.items():
        best_match = find_best_column_match(columns, keywords)
        if best_match:
            mapping[field] = best_match

    return mapping


def detect_ahrefs_columns(columns: List[str]) -> Dict[str, str]:
    """Détecte les colonnes Ahrefs"""

    # Basé sur les noms réels des colonnes CSV Ahrefs
    patterns = {
        'target_url': ['target url', 'target', 'url', 'cible', 'destination'],
        'referring_url': ['referring page url', 'referring url', 'referring page', 'referring', 'source', 'from', 'ref']
    }

    mapping = {}

    for field, keywords in patterns.items():
        best_match = find_best_column_match(columns, keywords)
        if best_match:
            mapping[field] = best_match

    return mapping


def find_best_column_match(columns: List[str], keywords: List[str]) -> str:
    """
    Trouve la meilleure correspondance de colonne basée sur des mots-clés

    Args:
        columns: Liste des noms de colonnes disponibles
        keywords: Liste de mots-clés à rechercher

    Returns:
        Nom de la colonne qui correspond le mieux, ou None
    """

    # Normaliser les colonnes pour la recherche
    normalized_columns = [(col, col.lower().replace('_', ' ').replace('-', ' ')) for col in columns]

    # Chercher une correspondance exacte d'abord
    for col, norm_col in normalized_columns:
        for keyword in keywords:
            if keyword.lower() == norm_col:
                return col

    # Chercher une correspondance partielle
    for col, norm_col in normalized_columns:
        for keyword in keywords:
            if keyword.lower() in norm_col:
                return col

    return None


def get_csv_preview(file_path: str, num_rows: int = 5) -> Tuple[List[str], List[List]]:
    """
    Lit un CSV et retourne les en-têtes + un aperçu des données

    Args:
        file_path: Chemin vers le fichier CSV
        num_rows: Nombre de lignes à retourner

    Returns:
        Tuple (colonnes, lignes)
    """

    try:
        # Lire le CSV
        df = pd.read_csv(file_path, nrows=num_rows, encoding='utf-8')

        # Extraire les colonnes
        columns = list(df.columns)

        # Extraire les lignes
        rows = df.values.tolist()

        # Tronquer les valeurs trop longues
        truncated_rows = []
        for row in rows:
            truncated_row = []
            for val in row:
                if isinstance(val, str) and len(val) > 100:
                    truncated_row.append(val[:97] + '...')
                else:
                    truncated_row.append(str(val) if pd.notna(val) else '')
            truncated_rows.append(truncated_row)

        return columns, truncated_rows

    except Exception as e:
        raise Exception(f"Erreur lors de la lecture du CSV: {str(e)}")
