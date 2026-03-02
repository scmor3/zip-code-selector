# Redfin Land Zip Code Analysis

Tools to analyze **sold** and **for-sale** land listings on Redfin (2–100 acre lots) by zip code, and to generate a **combined summary CSV** with sell-through rates and price-per-acre metrics.

There are three main scripts:

- `redfin_sold.py` – Scrapes **sold** land listings (last 12 months, 2–100 acres) for one or more zip codes and writes per-zip statistics to CSV/JSON.
- `redfin_for_sale.py` – Scrapes **for-sale** land listings (2–100 acres) for one or more zip codes and writes per-zip statistics to CSV/JSON.
- `redfin_combine.py` – Runs both scrapers for one or more zip codes and produces a **combined CSV/JSON** with sell-through rate and other derived metrics.

## Installation

1. **Install Python dependencies**

   ```bash
   # On Windows (if pip is not in PATH):
   py -m pip install -r requirements.txt
   
   # On Linux/Mac or if pip is in PATH:
   pip install -r requirements.txt
   ```

2. **Install Playwright browsers**

   ```bash
   # On Windows (if playwright is not in PATH):
   py -m playwright install chromium
   
   # On Linux/Mac or if playwright is in PATH:
   playwright install chromium
   ```

## Usage

### 1. Sold properties (last 12 months, 2–100 acres)

Runs the sold scraper and writes a timestamped CSV/JSON with per-zip statistics.

```bash
# Single zip
py redfin_sold.py 90210

# Multiple zips
py redfin_sold.py 95667 90210 10001
```

### 2. For-sale properties (2–100 acres)

Runs the for-sale scraper and writes a timestamped CSV/JSON with per-zip statistics (including days on market).

```bash
# Single zip
py redfin_for_sale.py 90210

# Multiple zips
py redfin_for_sale.py 95667 90210 10001
```

### 3. Combined summary (sold + for-sale)

Runs both scrapers for each zip and writes a combined CSV/JSON containing:

- Zip Code  
- For Sale (12 months, 2–100 acres)  
- Sold (12 months, 2–100 acres)  
- Sell Through Rate (sold / for sale)  
- Average/Median Listing Price  
- Average/Median Acreage (for sale)  
- Average/Median Price per Acre (for sale)  
- Average/Median Days on Market (for sale)  
- Average/Median Sale Price (sold)  
- Average/Median Acreage (sold)  
- Average/Median Price per Acre (sold)  
- Error (if the zip had row-click/automation issues and was zeroed out)

```bash
# Single zip
py redfin_combine.py 90210

# Multiple zips
py redfin_combine.py 95667 90210 10001
```

To keep logs in a file instead of the terminal, you can redirect output:

```bash
py redfin_combine.py 95667 90210 > output.log 2>&1
```

## Data Filters

All scripts target **land** listings in Redfin with:

- **Property type**: Land  
- **Minimum lot size**: 2 acres  
- **Maximum lot size**: 100 acres  

Additional filter:

- `redfin_sold.py`: Sold in the **last 12 months**  
- `redfin_for_sale.py`: Currently **for sale**  

## Requirements

- Python 3.7+
- Playwright library
- Chromium browser (installed via `playwright install`)
