# Autonomous Web Scraper & Data Extractor

A Python learning project that scrapes book listings from [Books to Scrape](https://books.toscrape.com/), a website created for scraping practice.

## Features

- Discovers categories from the homepage.
- Scrapes all pages in each category.
- Extracts book title, displayed price, numeric price, category, and URL.
- Uses request retries for temporary HTTP/network failures.
- Avoids duplicate books using their URLs.
- Sorts by price (lowest first by default).
- Exports records to CSV and JSON.
- Offers command-line options for output folder, request delay, test runs, and descending price sort.
- Logs progress and summarizes results.

## Project structure

```text
autonomous-web-scraper/
├── scraper.py
├── requirements.txt
├── README.md
├── .gitignore
├── tests/
│   └── test_scraper.py
└── output/              # created automatically when the scraper runs
    ├── books.csv
    └── books.json
```

## Requirements

- Python 3.10 or newer
- Internet connection

## Setup in VS Code (Windows)

Open the project folder in VS Code, then open Terminal → New Terminal.

### 1. Create a virtual environment (recommended)

```powershell
py -m venv .venv
```

Activate it in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, you can skip activation and use the virtual environment's Python directly, or use Command Prompt with:

```bat
.venv\Scripts\activate.bat
```

### 2. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

If the `python` command is not available, use the Python interpreter selected in VS Code or run pip through that interpreter.

### 3. Run a quick test scrape

This scrapes just the first two categories:

```powershell
python scraper.py --limit-categories 2
```

### 4. Run all categories

```powershell
python scraper.py
```

The script creates an `output` folder and saves:

- `output/books.csv`
- `output/books.json`

### Optional commands

Use a custom output directory:

```powershell
python scraper.py --output-dir results
```

Increase the delay between pages:

```powershell
python scraper.py --delay 1
```

Sort from highest price to lowest:

```powershell
python scraper.py --descending
```

Combine options:

```powershell
python scraper.py --limit-categories 3 --delay 0.5 --output-dir test-output
```

## Output fields

| Field | Meaning |
|---|---|
| `title` | Book title |
| `price` | Price as displayed on the website |
| `price_numeric` | Price converted to a number for sorting |
| `category` | Category where the book was first discovered |
| `url` | Absolute URL of the book listing |

## Run the tests

```powershell
python -m unittest discover -s tests -v
```

## Notes

- This project is intended for learning on the practice site. Before scraping any other website, review its terms, robots.txt, and access rules, and keep request rates modest.
- The scraper retries selected temporary HTTP errors. If an entire category fails, it logs the error and continues with other categories.
- A category label represents the first category in which a duplicate book URL was found.
- Website HTML can change; if selectors stop matching, inspect the page and update the selectors in `scraper.py`.
