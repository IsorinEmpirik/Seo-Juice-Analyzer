#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour les parsers CSV
"""
import sys
import io

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from pathlib import Path
from app.parsers import ScreamingFrogParser, AhrefsParser, parse_csv_files

def test_parsers():
    """Teste les parsers avec les fichiers d'exemple"""

    # Chemins vers les fichiers d'exemple
    sf_file = "examples/mmicrofloliens_entrants_tous - 1 - Liens entrants Tous.csv"
    ahrefs_file = "examples/lamicrobyflo.fr-backlinks-subdomains_2025-12-02_19-18-32 - Sheet1.csv"

    print("=" * 60)
    print("TEST DES PARSERS CSV")
    print("=" * 60)

    # Test Screaming Frog
    print("\n1. PARSING SCREAMING FROG")
    print("-" * 60)

    sf_parser = ScreamingFrogParser(sf_file)
    sf_df = sf_parser.parse()

    print(f"✓ Fichier parsé avec succès")
    print(f"  - Nombre de liens internes: {len(sf_df)}")
    print(f"  - Colonnes: {list(sf_df.columns)}")

    # Statistiques
    all_urls = sf_parser.get_all_urls()
    print(f"  - Nombre d'URLs uniques: {len(all_urls)}")

    links_by_source = sf_parser.get_links_by_source()
    print(f"  - Nombre de pages sources: {len(links_by_source)}")

    # Compter les liens Contenu vs Navigation
    if 'Position du lien' in sf_df.columns:
        position_counts = sf_df['Position du lien'].value_counts()
        print(f"\n  Répartition des liens:")
        for position, count in position_counts.items():
            print(f"    - {position}: {count}")

    # Codes de statut
    if 'Code de statut' in sf_df.columns:
        status_counts = sf_df['Code de statut'].value_counts()
        print(f"\n  Codes de statut:")
        for status, count in list(status_counts.items())[:5]:
            print(f"    - {status}: {count}")

    # Test Ahrefs
    print("\n\n2. PARSING AHREFS")
    print("-" * 60)

    ahrefs_parser = AhrefsParser(ahrefs_file)
    ahrefs_df = ahrefs_parser.parse()

    print(f"✓ Fichier parsé avec succès")
    print(f"  - Nombre de backlinks: {len(ahrefs_df)}")
    print(f"  - Colonnes: {list(ahrefs_df.columns)}")

    # Compter les backlinks par URL
    backlinks_count = ahrefs_parser.get_backlink_count_by_url()
    print(f"  - Nombre d'URLs ayant des backlinks: {len(backlinks_count)}")

    # Top 5 des URLs avec le plus de backlinks
    print(f"\n  Top 5 URLs avec le plus de backlinks:")
    sorted_urls = sorted(backlinks_count.items(), key=lambda x: x[1], reverse=True)[:5]
    for url, count in sorted_urls:
        print(f"    - {url[:80]}... : {count} backlinks")

    # Test de la fonction combinée
    print("\n\n3. TEST PARSE COMBINÉ")
    print("-" * 60)

    sf_parser2, ahrefs_parser2 = parse_csv_files(sf_file, ahrefs_file)
    print(f"✓ Les deux fichiers ont été parsés avec succès")
    print(f"  - Liens internes: {len(sf_parser2.df)}")
    print(f"  - Backlinks: {len(ahrefs_parser2.df)}")

    print("\n" + "=" * 60)
    print("✓ TOUS LES TESTS SONT PASSÉS !")
    print("=" * 60)

if __name__ == '__main__':
    try:
        test_parsers()
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
