#!/usr/bin/env python3
"""
Redfin Land Listings Browser Opener

Opens a Redfin page showing land listings sold in the last year
between 2-100 acres for a given zip code.
"""

import sys
import argparse
import re
import statistics
import json
import csv
from datetime import datetime
from playwright.sync_api import sync_playwright


def open_redfin_land_listings(zip_code: str):
    """
    Opens a Redfin land listings page in a browser for the given zip code.
    Collects property data and returns statistics.
    
    Args:
        zip_code: The zip code to search for land listings
    
    Returns:
        dict: Statistics dictionary with keys: zip_code, avg_price, median_price,
              avg_lot_size, median_lot_size, total_properties, pages_processed
              Returns None if no data collected or error occurred.
    """
    # Construct the Redfin URL
    url = (
        f"https://www.redfin.com/zipcode/{zip_code}/"
        f"filter/property-type=land,min-lot-size=2-acre,"
        f"max-lot-size=100-acre,include=sold-1yr"
    )
    
    print(f"Opening Redfin land listings for zip code: {zip_code}")
    print(f"URL: {url}")
    
    # Launch browser and open the URL
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as nav_error:
            print(f"Warning: Page navigation took longer than expected: {nav_error}")
            print("Continuing anyway...")
        
        # Give the page a moment to fully render
        page.wait_for_timeout(2000)
        
        # Close cookie banner if it appears
        try:
            cookie_close_button = page.locator("button.onetrust-close-btn-handler, button[aria-label='Close']")
            if cookie_close_button.count() > 0:
                cookie_close_button.first.wait_for(state="visible", timeout=3000)
                cookie_close_button.first.click(timeout=3000)
                print("Cookie banner closed.")
                page.wait_for_timeout(500)  # Brief delay after closing
        except Exception:
            # Cookie banner may not be present, which is fine
            pass
        
        # Wait for and click the table layout button, then select table view
        try:
            # Step 1: Wait for the layout button to be visible and click it
            page.wait_for_selector(".layout", state="visible", timeout=10000)
            layout_element = page.locator(".layout").first
            
            # Try clicking the SVG element, fallback to parent if needed
            try:
                layout_element.click(timeout=5000)
            except Exception:
                # Try clicking parent button if direct click fails
                parent_button = page.locator("button:has(.layout), [role='button']:has(.layout)").first
                if parent_button.count() > 0:
                    parent_button.click(timeout=5000)
                else:
                    raise
            
            # Small delay to let menu appear
            page.wait_for_timeout(500)
            
            # Step 2: Wait for the table menu item to appear and click it
            page.wait_for_selector(".table-view", state="visible", timeout=5000)
            table_element = page.locator(".table-view").first
            
            # Try clicking the SVG element, fallback to parent if needed
            try:
                table_element.click(timeout=5000)
            except Exception:
                # Try clicking parent button with text "Table" if direct click fails
                parent_table = page.locator("button.MenuItem__item:has-text('Table')").first
                if parent_table.count() > 0:
                    parent_table.click(timeout=5000)
                else:
                    raise
            
            print("Table layout activated.")
        except Exception as e:
            print(f"Warning: Could not activate table layout: {e}")
            print("Continuing anyway...")
        
        # Wait for table to load and click through each property row with pagination
        try:
            print("Waiting for table to load...")
            
            # Give the table a moment to render after switching to table view
            page.wait_for_timeout(2000)
            
            page_number = 1
            total_properties_clicked = 0
            
            # Lists to store property data for statistics
            prices = []
            lot_sizes = []
            
            # List to track processed properties for duplicate detection
            # Each entry: {price, sold_date, lot_size, has_street_address, index}
            processed_properties = []
            
            # Loop through all pages
            while True:
                print(f"\n--- Processing page {page_number} ---")
                
                # Get the first tbody with class "tableList" from the correct hierarchy
                # Structure: div.TableBody.reversePosition > div.ReactDataTable.tableBody > table > tbody.tableList
                all_tbodies = page.locator("div.TableBody.reversePosition div.ReactDataTable.tableBody tbody.tableList")
                tbody_count = all_tbodies.count()
                
                if tbody_count == 0:
                    print("No table body found. Exiting pagination loop.")
                    break
                
                first_table_body = all_tbodies.first
                
                # Get rows from the first tbody
                first_tbody_table_rows = first_table_body.locator("tr.tableRow")
                row_count = first_tbody_table_rows.count()
                
                # If empty, wait a bit and try again
                if row_count == 0:
                    page.wait_for_timeout(2000)
                    row_count = first_tbody_table_rows.count()
                
                if row_count > 0:
                    print(f"Found {row_count} property rows on page {page_number}.")
                    print("Clicking through each property...")
                    
                    # Click through each row from the first tbody
                    for idx in range(row_count):
                        row = first_tbody_table_rows.nth(idx)
                        
                        try:
                            row.scroll_into_view_if_needed()
                            
                            # Extract price from table row before clicking
                            price = None
                            try:
                                price_cell = row.locator("td.col_price")
                                if price_cell.count() > 0:
                                    price_text = price_cell.first.inner_text().strip()
                                    # Extract number from text like "$64,500" or "$57,000"
                                    # Remove $ and commas, then convert to float
                                    price_clean = re.sub(r'[^\d.]', '', price_text)
                                    if price_clean:
                                        price = float(price_clean)
                            except Exception as price_error:
                                # Error extracting price, skip this property
                                continue
                            
                            # If no price found, skip this property
                            if price is None:
                                continue
                            
                            # Click the row to update homecard
                            row.click(timeout=5000)
                            
                            # Wait for homecard to update after row selection
                            page.wait_for_timeout(500)
                            
                            # Extract zip code from address tag in homecard
                            homecard_zip = None
                            has_street_address = False
                            try:
                                address_tag = page.locator("address")
                                if address_tag.count() > 0:
                                    address_text = address_tag.first.inner_text().strip()
                                    # Extract zip code (5 digits) from address like "2650 Swansboro Rd, Placerville, CA 95667"
                                    zip_match = re.search(r'\b(\d{5})\b', address_text)
                                    if zip_match:
                                        homecard_zip = zip_match.group(1)
                                    
                                    # Check if address has a street address (starts with number followed by text)
                                    # This catches "123 Main St" and "3840 State Highway 49" but not "Springfield, MS 12345"
                                    street_address_match = re.match(r'^\d+\s+[A-Za-z]', address_text)
                                    if street_address_match:
                                        has_street_address = True
                            except Exception:
                                pass
                            
                            # Extract sold date from homecard
                            sold_date = None
                            try:
                                # Primary: Try using data-rf-test-id="home-sash"
                                sold_date_element = page.locator("[data-rf-test-id='home-sash']")
                                
                                # Fallback: Try span.Badge--sold if primary doesn't work
                                if sold_date_element.count() == 0:
                                    sold_date_element = page.locator("span.Badge--sold")
                                
                                if sold_date_element.count() > 0:
                                    sold_text = sold_date_element.first.inner_text().strip()
                                    # Extract date pattern like "SOLD DEC 31, 2025" or "SOLD MAY 12, 2025"
                                    # Look for "SOLD" followed by month, day, year
                                    date_match = re.search(r'SOLD\s+([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})', sold_text, re.IGNORECASE)
                                    if date_match:
                                        # Normalize to uppercase format: "DEC 31, 2025"
                                        sold_date = f"{date_match.group(1).upper()} {date_match.group(2)}, {date_match.group(3)}"
                            except Exception:
                                pass
                            
                            # Extract lot size from homecard
                            lot_size = None
                            try:
                                lot_size_element = page.locator("span[data-rf-test-name='homecard-amenities-lot-size']")
                                
                                if lot_size_element.count() > 0:
                                    lot_size_text = lot_size_element.first.inner_text()
                                    
                                    # Extract just the number from text like "3.78 Acres"
                                    match = re.search(r'([\d.]+)', lot_size_text)
                                    if match:
                                        lot_size = float(match.group(1))
                                else:
                                    # Lot size element not found, skip this property
                                    continue
                            except Exception as lot_size_error:
                                # Error extracting lot size, skip this property
                                continue
                            
                            # If we have both price and lot size, validate zip code and check for duplicates
                            if price is not None and lot_size is not None:
                                # Skip property only if we found a zip code AND it doesn't match input zip code
                                # If zip code extraction failed (None), include the property in calculations
                                if homecard_zip is not None and homecard_zip != zip_code:
                                    zip_display = homecard_zip if homecard_zip else "N/A"
                                    print(f"    Property {idx + 1}: Skipped - Zip code mismatch (found {zip_display}, expected {zip_code})")
                                    continue
                                
                                # Check for duplicates
                                # Duplicate exists if: same price AND same sold_date AND same lot_size AND one doesn't have street address
                                duplicate_index = None
                                for i, processed in enumerate(processed_properties):
                                    if (processed['price'] == price and 
                                        processed['sold_date'] == sold_date and 
                                        processed['lot_size'] == lot_size and
                                        (not processed['has_street_address'] or not has_street_address)):
                                        duplicate_index = i
                                        break
                                
                                if duplicate_index is not None:
                                    # Duplicate found
                                    existing = processed_properties[duplicate_index]
                                    
                                    # If existing doesn't have street address and new one does: replace existing
                                    if not existing['has_street_address'] and has_street_address:
                                        # Remove existing from lists
                                        prices.pop(duplicate_index)
                                        lot_sizes.pop(duplicate_index)
                                        # Add new one
                                        prices.append(price)
                                        lot_sizes.append(lot_size)
                                        # Update tracking list
                                        processed_properties[duplicate_index] = {
                                            'price': price,
                                            'sold_date': sold_date,
                                            'lot_size': lot_size,
                                            'has_street_address': has_street_address,
                                            'index': idx + 1
                                        }
                                        zip_display = homecard_zip if homecard_zip else "N/A"
                                        sold_date_display = sold_date if sold_date else "N/A"
                                        print(f"    Property {idx + 1}: Replaced duplicate (Property {existing['index']}) - Has street address")
                                        print(f"      Price = ${price:,.0f}, Lot size = {lot_size} acres, Zip code = {zip_display}, Sold date = {sold_date_display}, Has street address = Yes")
                                    else:
                                        # New one doesn't have street address (or both don't): skip new, keep existing
                                        zip_display = homecard_zip if homecard_zip else "N/A"
                                        sold_date_display = sold_date if sold_date else "N/A"
                                        street_address_display = "Yes" if has_street_address else "No"
                                        print(f"    Property {idx + 1}: Skipped - Duplicate of Property {existing['index']} (kept Property {existing['index']})")
                                        print(f"      Price = ${price:,.0f}, Lot size = {lot_size} acres, Zip code = {zip_display}, Sold date = {sold_date_display}, Has street address = {street_address_display}")
                                else:
                                    # No duplicate found, add to lists
                                    prices.append(price)
                                    lot_sizes.append(lot_size)
                                    processed_properties.append({
                                        'price': price,
                                        'sold_date': sold_date,
                                        'lot_size': lot_size,
                                        'has_street_address': has_street_address,
                                        'index': idx + 1
                                    })
                                    zip_display = homecard_zip if homecard_zip else "N/A"
                                    sold_date_display = sold_date if sold_date else "N/A"
                                    street_address_display = "Yes" if has_street_address else "No"
                                    print(f"    Property {idx + 1}: Price = ${price:,.0f}, Lot size = {lot_size} acres, Zip code = {zip_display}, Sold date = {sold_date_display}, Has street address = {street_address_display}")
                            
                        except Exception as click_error:
                            print(f"Warning: Could not click row {idx + 1}: {click_error}")
                            continue
                    
                    total_properties_clicked += row_count
                    print(f"Finished clicking through {row_count} properties on page {page_number}.")
                else:
                    print(f"No property rows found on page {page_number}.")
                
                # Check for next page button
                next_button = page.locator("button.PageArrow.PageArrow_direction--next, button[aria-label='next']")
                next_button_count = next_button.count()
                
                if next_button_count > 0:
                    # Check if button is visible and not hidden
                    try:
                        is_visible = next_button.first.is_visible()
                        has_hidden_class = next_button.first.evaluate("""
                            el => el.classList.contains('PageArrow--hidden')
                        """)
                        
                        if is_visible and not has_hidden_class:
                            print(f"Next page button found. Clicking to go to page {page_number + 1}...")
                            next_button.first.click(timeout=5000)
                            
                            # Wait for new page to load
                            page.wait_for_timeout(2000)
                            
                            # Wait for table to update (wait for rows to change or page to load)
                            try:
                                page.wait_for_selector("tr.tableRow", state="visible", timeout=10000)
                            except:
                                pass
                            
                            page_number += 1
                            continue
                        else:
                            print("Next button exists but is hidden or not visible. No more pages.")
                            break
                    except Exception as next_error:
                        print(f"Error checking/clicking next button: {next_error}")
                        break
                else:
                    print("No next page button found. Reached last page.")
                    break
            
            print(f"\n=== Pagination complete ===")
            print(f"Processed {page_number} page(s)")
            print(f"Clicked through {total_properties_clicked} total properties.")
            
            # Calculate and return statistics
            if prices and lot_sizes:
                print(f"\n=== Statistics for {zip_code} ===")
                print(f"Total properties with complete data: {len(prices)}")
                
                # Price statistics
                avg_price = statistics.mean(prices)
                median_price = statistics.median(prices)
                print(f"\nPrice Statistics:")
                print(f"  Average price: ${avg_price:,.2f}")
                print(f"  Median price: ${median_price:,.2f}")
                
                # Lot size statistics
                avg_lot_size = statistics.mean(lot_sizes)
                median_lot_size = statistics.median(lot_sizes)
                print(f"\nLot Size Statistics:")
                print(f"  Average lot size: {avg_lot_size:.2f} acres")
                print(f"  Median lot size: {median_lot_size:.2f} acres")
                
                browser.close()
                
                return {
                    "zip_code": zip_code,
                    "avg_price": avg_price,
                    "median_price": median_price,
                    "avg_lot_size": avg_lot_size,
                    "median_lot_size": median_lot_size,
                    "total_properties": len(prices),
                    "pages_processed": page_number
                }
            else:
                print(f"\nNo complete property data collected for {zip_code}.")
                browser.close()
                return None
            
        except Exception as e:
            print(f"Warning: Could not complete pagination for {zip_code}: {e}")
            print("Continuing anyway...")
            browser.close()
            return None


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Process Redfin land listings for one or more zip codes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python open_redfin.py 90210
  python open_redfin.py 95667 90210 10001
        """
    )
    parser.add_argument(
        "zip_codes",
        type=str,
        nargs="+",
        help="One or more zip codes to search for land listings"
    )
    
    args = parser.parse_args()
    
    # Validate zip codes
    zip_codes = [zc.strip() for zc in args.zip_codes if zc.strip()]
    if not zip_codes:
        print("Error: At least one zip code is required", file=sys.stderr)
        sys.exit(1)
    
    # Process each zip code and collect results
    results = []
    
    print(f"\n{'='*60}")
    print(f"Processing {len(zip_codes)} zip code(s)")
    print(f"{'='*60}\n")
    
    for i, zip_code in enumerate(zip_codes, 1):
        print(f"\n{'='*60}")
        print(f"Processing zip code {i}/{len(zip_codes)}: {zip_code}")
        print(f"{'='*60}\n")
        
        try:
            result = open_redfin_land_listings(zip_code)
            if result:
                results.append(result)
        except KeyboardInterrupt:
            print("\n\nInterrupted by user", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error processing {zip_code}: {e}", file=sys.stderr)
            continue
    
    # Write results to files
    if results:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        # Write CSV file
        csv_filename = f"results_{timestamp}.csv"
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['zip_code', 'avg_price', 'median_price', 'avg_lot_size', 
                         'median_lot_size', 'total_properties', 'pages_processed']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in results:
                writer.writerow(result)
        
        # Write JSON file
        json_filename = f"results_{timestamp}.json"
        with open(json_filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(results, jsonfile, indent=2)
        
        # Print summary
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        print(f"\nProcessed {len(results)} zip code(s) successfully:")
        print(f"\n{'Zip Code':<12} {'Avg Price':<15} {'Median Price':<15} {'Avg Lot Size':<15} {'Median Lot Size':<15} {'Properties':<12}")
        print("-" * 90)
        
        for result in results:
            print(f"{result['zip_code']:<12} "
                  f"${result['avg_price']:>12,.0f}  "
                  f"${result['median_price']:>12,.0f}  "
                  f"{result['avg_lot_size']:>12.2f} acres  "
                  f"{result['median_lot_size']:>12.2f} acres  "
                  f"{result['total_properties']:>10}")
        
        print(f"\nResults saved to:")
        print(f"  CSV: {csv_filename}")
        print(f"  JSON: {json_filename}")
    else:
        print("\nNo results collected. No files created.")


if __name__ == "__main__":
    main()
