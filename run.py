#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Point d'entrée de l'application d'analyse de maillage interne
"""
import sys
import io

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from app import create_app

app = create_app()

if __name__ == '__main__':
    print("=" * 60)
    print(">> Outil d'Analyse de Maillage Interne SEO")
    print("=" * 60)
    print("\n>> L'application est accessible sur : http://localhost:5000")
    print("\n>> Appuyez sur CTRL+C pour arreter le serveur\n")
    print("=" * 60)

    app.run(debug=True, host='0.0.0.0', port=5000)
