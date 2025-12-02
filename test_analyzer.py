#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour l'analyseur de maillage interne
"""
import sys
import io

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import logging
from pathlib import Path
from app.parsers import ScreamingFrogParser, AhrefsParser
from app.analyzer import SEOJuiceAnalyzer

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)

def test_analyzer():
    """Teste l'analyseur avec les fichiers d'exemple"""

    # Chemins vers les fichiers d'exemple
    sf_file = "examples/mmicrofloliens_entrants_tous - 1 - Liens entrants Tous.csv"
    ahrefs_file = "examples/lamicrobyflo.fr-backlinks-subdomains_2025-12-02_19-18-32 - Sheet1.csv"

    print("\n" + "=" * 60)
    print("TEST DE L'ANALYSEUR DE MAILLAGE INTERNE")
    print("=" * 60)

    # 1. Parser les CSV
    print("\n>> Parsing des fichiers CSV...")
    sf_parser = ScreamingFrogParser(sf_file)
    sf_parser.parse()

    ahrefs_parser = AhrefsParser(ahrefs_file)
    ahrefs_parser.parse()

    print(f"   - {len(sf_parser.df)} liens internes")
    print(f"   - {len(ahrefs_parser.df)} backlinks")

    # 2. Lancer l'analyse
    print("\n>> Lancement de l'analyse...")

    analyzer = SEOJuiceAnalyzer(config={
        'backlink_score': 10,
        'transmission_rate': 0.85,
        'content_link_rate': 0.90,
        'navigation_link_rate': 0.10,
        'iterations': 3,
        'normalize_max': 100
    })

    results = analyzer.analyze(sf_parser, ahrefs_parser)

    # 3. Afficher les résultats
    print("\n" + "=" * 60)
    print("RESULTATS DE L'ANALYSE")
    print("=" * 60)

    print(f"\nTotal URLs analysees: {results['total_urls']}")
    print(f"Total liens internes: {results['total_internal_links']}")
    print(f"Total backlinks: {results['total_backlinks']}")

    # Top 10 des pages avec le meilleur score SEO
    print("\n" + "-" * 60)
    print("TOP 10 PAGES AVEC LE MEILLEUR SCORE SEO")
    print("-" * 60)

    for i, url_data in enumerate(results['urls'][:10], 1):
        print(f"\n{i}. Score: {url_data['seo_score']:.2f}/100")
        print(f"   URL: {url_data['url'][:70]}...")
        print(f"   Backlinks: {url_data['backlinks_count']} | Liens internes reçus: {url_data['internal_links_received']}")
        if url_data['top_3_anchors']:
            anchors = ", ".join([f"{a['anchor'][:30]}({a['count']})" for a in url_data['top_3_anchors'][:3]])
            print(f"   Top ancres: {anchors}")

    # Top 10 des sources de jus (pages avec le plus de backlinks)
    print("\n" + "-" * 60)
    print("TOP 10 SOURCES DE JUS SEO (pages avec le + de backlinks)")
    print("-" * 60)

    for i, url_data in enumerate(results['top_juice_sources'][:10], 1):
        print(f"{i}. {url_data['url'][:60]}...")
        print(f"   Backlinks: {url_data['backlinks_count']} | Score SEO: {url_data['seo_score']:.2f}")

    # Stats par catégorie
    print("\n" + "-" * 60)
    print("SCORE MOYEN PAR CATEGORIE")
    print("-" * 60)

    sorted_categories = sorted(
        results['categories'].items(),
        key=lambda x: x[1]['avg_score'],
        reverse=True
    )

    for category, stats in sorted_categories[:10]:
        print(f"  {category:20s} : {stats['avg_score']:6.2f} ({stats['count']} pages)")

    # Pages en erreur recevant des liens
    print("\n" + "-" * 60)
    print("PAGES EN ERREUR RECEVANT DES LIENS INTERNES")
    print("-" * 60)

    error_pages = results['error_pages_with_links'][:10]
    if error_pages:
        for url_data in error_pages:
            print(f"\n  URL: {url_data['url'][:70]}...")
            print(f"  Code: {url_data['status_code']} | Liens reçus: {url_data['internal_links_received']}")
    else:
        print("  Aucune page en erreur ne reçoit de liens. C'est parfait!")

    print(f"\nTaux de jus SEO envoye sur des erreurs: {results['error_juice_rate']:.2f}%")

    # Statistiques globales
    print("\n" + "=" * 60)
    print("STATISTIQUES GLOBALES")
    print("=" * 60)

    avg_score = sum(u['seo_score'] for u in results['urls']) / len(results['urls'])
    max_score = max(u['seo_score'] for u in results['urls'])
    min_score = min(u['seo_score'] for u in results['urls'])

    print(f"Score moyen: {avg_score:.2f}")
    print(f"Score maximum: {max_score:.2f}")
    print(f"Score minimum: {min_score:.2f}")

    pages_with_backlinks = sum(1 for u in results['urls'] if u['backlinks_count'] > 0)
    print(f"\nPages avec backlinks: {pages_with_backlinks}")
    print(f"Pages sans backlinks: {results['total_urls'] - pages_with_backlinks}")

    print("\n" + "=" * 60)
    print(">> TEST TERMINE AVEC SUCCES !")
    print("=" * 60)

if __name__ == '__main__':
    try:
        test_analyzer()
    except Exception as e:
        print(f"\n[ERREUR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
