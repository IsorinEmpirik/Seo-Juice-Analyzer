# Outil d'Analyse de Maillage Interne SEO

## Description

Outil d'analyse de maillage interne pour optimiser la distribution du "jus SEO" sur votre site web.

## Fonctionnalités

- Import des liens internes (Screaming Frog) et backlinks externes (Ahrefs/SEObserver)
- Calcul du score de puissance SEO de chaque page
- Algorithme itératif de distribution du jus SEO
- Distinction liens de contenu (90%) vs navigation (10%)
- Export automatique vers Google Sheets avec graphiques
- Analyse des erreurs et pages importantes
- Top 3 des ancres par page

## Installation

### 1. Créer un environnement virtuel Python

```bash
python -m venv venv
```

### 2. Activer l'environnement virtuel

**Windows :**
```bash
venv\Scripts\activate
```

**Mac/Linux :**
```bash
source venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

## Configuration

### Google Sheets API

1. Suivez le guide dans `/docs` pour configurer l'API Google Sheets
2. Placez votre fichier `credentials.json` à la racine du projet

## Utilisation

### Lancer l'application

```bash
python run.py
```

L'application sera accessible sur : `http://localhost:5000`

### Préparer vos fichiers CSV

1. **Screaming Frog** : Exportez les liens internes (voir `/docs/export screaming frog tuto.png`)
2. **Ahrefs** : Exportez les backlinks (voir `/docs/export ahrefs tuto.png`)

### Lancer une analyse

1. Uploadez vos 2 fichiers CSV
2. Configurez les paramètres (optionnel)
3. Lancez l'analyse
4. Exportez vers Google Sheets

## Structure du projet

```
maillage-interne-analyzer/
├── app/                  # Code de l'application
├── static/              # CSS, JS, images
├── templates/           # Templates HTML
├── uploads/             # CSV uploadés (temporaire)
├── examples/            # Exemples de CSV
├── docs/                # Documentation et tutoriels
├── app_script/          # Code Google Apps Script
└── run.py              # Point d'entrée
```

## Technologies

- Python 3.10+
- Flask (web framework)
- Pandas (traitement de données)
- Google Sheets API
- Bootstrap 5 (interface)
- Chart.js (graphiques)

## Licence

Usage personnel - La micro by Flo
