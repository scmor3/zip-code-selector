# Redfin Land Listings Browser Opener

A simple Python script that opens a Redfin page showing land listings sold in the last year between 2-100 acres for a given zip code.

## Installation

1. Install Python dependencies:
   ```bash
   # On Windows (if pip is not in PATH):
   py -m pip install -r requirements.txt
   
   # On Linux/Mac or if pip is in PATH:
   pip install -r requirements.txt
   ```

2. Install Playwright browsers:
   ```bash
   # On Windows (if playwright is not in PATH):
   py -m playwright install chromium
   
   # On Linux/Mac or if playwright is in PATH:
   playwright install chromium
   ```

## Usage

Run the script with a zip code as an argument:

```bash
# On Windows:
py open_redfin.py 90210

# On Linux/Mac or if python is in PATH:
python open_redfin.py 90210
```

This will open a browser window showing all land listings sold in the last year between 2-100 acres for zip code 90210.

The browser will remain open until you press Enter in the terminal, at which point it will close.

## What It Does

The script constructs a Redfin URL with the following filters:
- Property type: Land
- Minimum lot size: 2 acres
- Maximum lot size: 100 acres
- Include: Sold in the last year

The URL format is:
```
https://www.redfin.com/zipcode/{zip-code}/filter/property-type=land,min-lot-size=2-acre,max-lot-size=100-acre,include=sold-1yr
```

## Requirements

- Python 3.7+
- Playwright library
- Chromium browser (installed via `playwright install`)
