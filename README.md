# SEO Internal Linking Analyzer

A web-based tool that analyzes your website's internal linking structure and calculates SEO scores using a true iterative PageRank algorithm.

## What it does

- Imports data from Screaming Frog (crawl), Ahrefs (backlinks), and optionally Google Search Console
- Calculates a 0-100 SEO score for every page based on link equity distribution
- Differentiates content links (90% weight) from navigation links (10% weight)
- Identifies "Quick Wins" – keywords ranking #5-12 that could reach top 3 with better internal linking
- Detects orphaned pages, link hoarding, and wasted juice on error pages
- Provides semantic link recommendations using embeddings

## Key Features

- **True PageRank implementation** with 0.85 damping factor
- **Interactive dashboard** with sortable tables and charts
- **Historical analysis** tracking and comparison
- **Prioritized recommendations** (Critical → High → Medium → Low)
- **Category-based SEO distribution** analysis

## Tech Stack

- **Backend:** Python 3.10+, Flask, Pandas, NumPy, SQLite
- **Frontend:** Bootstrap 5, DataTables.js, Chart.js

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/seo-internal-linking-analyzer.git
cd seo-internal-linking-analyzer
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

### 3. Activate the virtual environment

**Windows:**
```bash
venv\Scripts\activate
```

**Mac/Linux:**
```bash
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the application

```bash
python run.py
```

Open `http://localhost:5000` in your browser.

## Usage

1. **Export from Screaming Frog:** Internal Links → All Inlinks (CSV)
2. **Export from Ahrefs:** Backlinks report (CSV)
3. **Upload both CSVs** to the analyzer
4. **Review results:** SEO scores, recommendations, and quick wins
5. **Implement suggestions** to boost your rankings

## Project Structure

```
seo-internal-linking-analyzer/
├── app/                  # Application code
│   ├── analyzer.py       # Core PageRank algorithm
│   ├── routes.py         # Flask endpoints
│   ├── parsers.py        # CSV parsing logic
│   └── database.py       # SQLite operations
├── static/               # CSS, JS, images
├── templates/            # HTML templates
├── uploads/              # Temporary CSV storage
├── docs/                 # Documentation & tutorials
└── run.py                # Entry point
```

## Algorithm

The tool implements a true iterative PageRank algorithm:
- External backlinks serve as the initial "teleportation vector"
- Link equity flows through internal links with a 0.85 damping factor
- Content links transfer 9x more value than navigation links
- Scores normalize to a 0-100 scale for easy interpretation

## Use Cases

- SEO audits and site architecture optimization
- Finding under-linked important pages
- Detecting technical issues (404s receiving links)
- Building data-driven internal linking strategies
- Tracking SEO improvements over time

## License

MIT License
