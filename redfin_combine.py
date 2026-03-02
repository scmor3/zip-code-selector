#!/usr/bin/env python3
"""
Combine Redfin Sold and For-Sale Land Listing Statistics

Runs both:
- redfin_sold.open_redfin_land_listings (sold, last 12 months, 2–100 acres)
- redfin_for_sale.open_redfin_for_sale_listings (for sale, 2–100 acres)

for one or more zip codes, then writes a combined CSV (and JSON) with:

- Zip Code
- For Sale (12 months, 2-100 acres)          -> number of for-sale listings
- Sold (12 months, 2-100 acres)              -> number of sold listings
- Sell Through Rate                          -> Sold / For Sale
- Average Listing Price                      -> for-sale avg price
- Median Listing Price                       -> for-sale median price
- Average Acreage (for sale)                 -> for-sale avg lot size
- Median Acreage (for sale)                  -> for-sale median lot size
- Average price per acre (for sale)          -> for-sale avg price per acre
- Median price per acre (for sale)           -> for-sale median price per acre
- Average days on market (for sale)          -> for-sale avg days on market
- Median days on market (for sale)           -> for-sale median days on market
- Average Sale Price (sold)                  -> sold avg price
- Median Sale Price (sold)                   -> sold median price
- Average Acreage (sold)                     -> sold avg lot size
- Median Acreage (sold)                      -> sold median lot size
- Average price per acre (sold)              -> sold avg price per acre
- Median price per acre (sold)               -> sold median price per acre
"""

import argparse
import csv
import json
import sys
from datetime import datetime

from redfin_sold import open_redfin_land_listings
from redfin_for_sale import open_redfin_for_sale_listings


def safe_get(result: dict | None, key: str, default: float | int = 0):
    """Helper to safely extract a value from a result dict, with default if missing/None."""
    if not result:
        return default
    value = result.get(key, default)
    return value if value is not None else default


def combine_results_for_zip(zip_code: str):
    """Run both scrapers for a single zip code and return a combined metrics dict."""
    print(f"\n{'='*60}")
    print(f"Combining results for zip code: {zip_code}")
    print(f"{'='*60}")

    sold_result = None
    for_sale_result = None

    # Run for-sale script first (listings)
    try:
        for_sale_result = open_redfin_for_sale_listings(zip_code)
    except KeyboardInterrupt:
        raise
    except Exception as e:
        print(f"Error running for-sale script for {zip_code}: {e}", file=sys.stderr)

    # Run sold script (last 12 months)
    try:
        sold_result = open_redfin_land_listings(zip_code)
    except KeyboardInterrupt:
        raise
    except Exception as e:
        print(f"Error running sold script for {zip_code}: {e}", file=sys.stderr)

    # Extract metrics, using zeros when missing
    for_sale_count = safe_get(for_sale_result, "total_properties", 0)
    sold_count = safe_get(sold_result, "total_properties", 0)

    for_sale_row_errors = safe_get(for_sale_result, "row_click_errors", 0)
    sold_row_errors = safe_get(sold_result, "row_click_errors", 0)
    has_row_errors = (for_sale_row_errors > 0) or (sold_row_errors > 0)

    # Sell-through rate: sold / for_sale (0 if denominator is 0)
    sell_through_rate = (sold_count / for_sale_count) if for_sale_count > 0 else 0.0

    error_message = ""
    if has_row_errors:
        error_message = (
            f"Row click errors encountered (for_sale={for_sale_row_errors}, sold={sold_row_errors}). "
            f"Skipping zip code calculations and writing zeros."
        )

    combined = {
        "zip_code": zip_code,
        "error": error_message,
        # Counts
        "for_sale_count": 0 if has_row_errors else for_sale_count,
        "sold_count": 0 if has_row_errors else sold_count,
        "sell_through_rate": 0.0 if has_row_errors else sell_through_rate,
        # For-sale stats
        "avg_listing_price": 0 if has_row_errors else safe_get(for_sale_result, "avg_price", 0),
        "median_listing_price": 0 if has_row_errors else safe_get(for_sale_result, "median_price", 0),
        "avg_acreage_for_sale": 0.0 if has_row_errors else safe_get(for_sale_result, "avg_lot_size", 0.0),
        "median_acreage_for_sale": 0.0 if has_row_errors else safe_get(for_sale_result, "median_lot_size", 0.0),
        "avg_price_per_acre_for_sale": 0.0 if has_row_errors else safe_get(for_sale_result, "avg_price_per_acre", 0.0),
        "median_price_per_acre_for_sale": 0.0 if has_row_errors else safe_get(for_sale_result, "median_price_per_acre", 0.0),
        "avg_days_on_market_for_sale": 0 if has_row_errors else safe_get(for_sale_result, "avg_days_on_market", 0),
        "median_days_on_market_for_sale": 0 if has_row_errors else safe_get(for_sale_result, "median_days_on_market", 0),
        # Sold stats
        "avg_sale_price": 0.0 if has_row_errors else safe_get(sold_result, "avg_price", 0.0),
        "median_sale_price": 0.0 if has_row_errors else safe_get(sold_result, "median_price", 0.0),
        "avg_acreage_sold": 0.0 if has_row_errors else safe_get(sold_result, "avg_lot_size", 0.0),
        "median_acreage_sold": 0.0 if has_row_errors else safe_get(sold_result, "median_lot_size", 0.0),
        "avg_price_per_acre_sold": 0.0 if has_row_errors else safe_get(sold_result, "avg_price_per_acre", 0.0),
        "median_price_per_acre_sold": 0.0 if has_row_errors else safe_get(sold_result, "median_price_per_acre", 0.0),
    }

    return combined


def main():
    parser = argparse.ArgumentParser(
        description="Combine Redfin for-sale and sold land statistics for one or more zip codes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python combine_results.py 90210
  python combine_results.py 95667 90210 10001
        """,
    )
    parser.add_argument(
        "zip_codes",
        type=str,
        nargs="+",
        help="One or more zip codes to process",
    )

    args = parser.parse_args()

    zip_codes = [zc.strip() for zc in args.zip_codes if zc.strip()]
    if not zip_codes:
        print("Error: At least one zip code is required", file=sys.stderr)
        sys.exit(1)

    combined_rows: list[dict] = []

    print(f"\n{'='*60}")
    print(f"Processing {len(zip_codes)} zip code(s) with both scripts")
    print(f"{'='*60}\n")

    for i, zc in enumerate(zip_codes, 1):
        print(f"\n--- Zip code {i}/{len(zip_codes)}: {zc} ---")
        try:
            combined = combine_results_for_zip(zc)
            combined_rows.append(combined)
        except KeyboardInterrupt:
            print("\n\nInterrupted by user", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error combining results for {zc}: {e}", file=sys.stderr)
            continue

    if not combined_rows:
        print("\nNo combined results produced. No files created.")
        sys.exit(0)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    csv_filename = f"combined_results_{timestamp}.csv"
    json_filename = f"combined_results_{timestamp}.json"

    # Write CSV with requested column order/names
    fieldnames = [
        "Zip Code",
        "For Sale (12 months, 2-100 acres)",
        "Sold (12 months, 2-100 acres)",
        "Sell Through Rate",
        "Average Listing Price",
        "Median Listing Price",
        "Average Acreage (for sale)",
        "Median Acreage (for sale)",
        "Average price per acre (for sale)",
        "Median price per acre (for sale)",
        "Average days on market (for sale)",
        "Median days on market (for sale)",
        "Average Sale Price (sold)",
        "Median Sale Price (sold)",
        "Average Acreage (sold)",
        "Median Acreage (sold)",
        "Average price per acre (sold)",
        "Median price per acre (sold)",
        "Error",
    ]

    with open(csv_filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in combined_rows:
            writer.writerow(
                {
                    "Zip Code": row["zip_code"],
                    "For Sale (12 months, 2-100 acres)": row["for_sale_count"],
                    "Sold (12 months, 2-100 acres)": row["sold_count"],
                    "Sell Through Rate": row["sell_through_rate"],
                    "Average Listing Price": row["avg_listing_price"],
                    "Median Listing Price": row["median_listing_price"],
                    "Average Acreage (for sale)": row["avg_acreage_for_sale"],
                    "Median Acreage (for sale)": row["median_acreage_for_sale"],
                    "Average price per acre (for sale)": row[
                        "avg_price_per_acre_for_sale"
                    ],
                    "Median price per acre (for sale)": row[
                        "median_price_per_acre_for_sale"
                    ],
                    "Average days on market (for sale)": row[
                        "avg_days_on_market_for_sale"
                    ],
                    "Median days on market (for sale)": row[
                        "median_days_on_market_for_sale"
                    ],
                    "Average Sale Price (sold)": row["avg_sale_price"],
                    "Median Sale Price (sold)": row["median_sale_price"],
                    "Average Acreage (sold)": row["avg_acreage_sold"],
                    "Median Acreage (sold)": row["median_acreage_sold"],
                    "Average price per acre (sold)": row["avg_price_per_acre_sold"],
                    "Median price per acre (sold)": row[
                        "median_price_per_acre_sold"
                    ],
                    "Error": row.get("error", ""),
                }
            )

    # Also write JSON with the raw combined data
    with open(json_filename, "w", encoding="utf-8") as jsonfile:
        json.dump(combined_rows, jsonfile, indent=2)

    print(f"\nCombined results saved to:")
    print(f"  CSV:  {csv_filename}")
    print(f"  JSON: {json_filename}")


if __name__ == "__main__":
    main()

