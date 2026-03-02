#!/usr/bin/env python3
"""
Redfin Land Listings Browser Opener - For Sale Properties

Opens a Redfin page showing land listings currently for sale
between 2-100 acres for a given zip code.
"""

import sys
import argparse
import re
import statistics
from playwright.sync_api import sync_playwright


def open_redfin_for_sale_listings(zip_code: str):
    """
    Opens a Redfin land listings page in a browser for the given zip code.
    
    Args:
        zip_code: The zip code to search for land listings
    """
    # Construct the Redfin URL for for-sale properties
    url = (
        f"https://www.redfin.com/zipcode/{zip_code}/"
        f"filter/property-type=land,min-lot-size=2-acre,"
        f"max-lot-size=100-acre"
    )
    
    print(f"Opening Redfin for-sale land listings for zip code: {zip_code}")
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
            
            # Initialize pagination variables
            page_number = 1
            total_properties_clicked = 0
            property_counter = 0  # Global counter for property indexing across pages
            
            # List to store property data for statistics
            properties = []
            
            # List to track processed properties for duplicate detection
            # Each entry: {price, days_on_market, description, lot_size, index}
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
                        property_counter += 1
                        
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
                            except Exception:
                                pass
                            
                            row.click(timeout=5000)
                            
                            # Wait a moment for row to be selected and homecard to update
                            page.wait_for_timeout(500)
                            
                            # Extract zip code from homecard address (primary source)
                            # When a property is selected, there's only one a.bp-Homecard__Address element
                            # This is more reliable than table row href which may have "Unknown" instead of zip code
                            final_zip = None
                            try:
                                # Use the a.bp-Homecard__Address element which is the main address link in the homecard
                                # Note the double underscore in the class name (bp-Homecard__Address)
                                homecard_address_link = page.locator("a.bp-Homecard__Address")
                                
                                if homecard_address_link.count() > 0:
                                    # Get the text content which includes the full address with zip code
                                    # Example: "10404 State Highway 49, Coulterville, CA 95311"
                                    address_text = homecard_address_link.first.inner_text().strip()
                                    
                                    if address_text:
                                        # Extract zip code (5 digits) from address
                                        # Look for state abbreviation (2 letters) followed by zip code (5 digits)
                                        # This avoids matching street numbers like "10902" in "10902 Stout Ln, Coulterville, CA 95311"
                                        zip_match = re.search(r'[A-Z]{2}\s+(\d{5})\b', address_text)
                                        if zip_match:
                                            final_zip = zip_match.group(1)
                            except Exception:
                                pass
                            
                            # Fallback: Extract zip code from selected row's href if homecard extraction failed
                            if final_zip is None:
                                try:
                                    selected_row = page.locator("tr.selected.tableRow")
                                    if selected_row.count() > 0:
                                        address_link = selected_row.locator("td.col_address a.address")
                                        if address_link.count() > 0:
                                            href = address_link.first.get_attribute("href") or ""
                                            # Extract zip code from href like "/CA/Coulterville/10902-Stout-Ln-95311/home/119805132"
                                            # Look for pattern: -{5digits}/home/
                                            zip_match = re.search(r'-(\d{5})/home/', href)
                                            if zip_match:
                                                final_zip = zip_match.group(1)
                                                print(f"      (Using fallback: extracted zip from selected row href)")
                                except Exception:
                                    pass
                            
                            # Extract days on market from selected table row
                            days_on_market = None
                            try:
                                selected_row = page.locator("tr.selected.tableRow")
                                if selected_row.count() > 0:
                                    days_cell = selected_row.locator("td.col_days")
                                    if days_cell.count() > 0:
                                        days_text = days_cell.first.inner_text().strip()
                                        # Extract number from text like "836 days" or "836 days == $0"
                                        match = re.search(r'(\d+)\s*days', days_text, re.IGNORECASE)
                                        if match:
                                            days_on_market = int(match.group(1))
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
                            except Exception:
                                pass
                            
                            # Extract property description from homecard
                            description = None
                            try:
                                # The description is in div.ListingRemarks > p
                                description_element = page.locator("div.ListingRemarks p")
                                
                                if description_element.count() > 0:
                                    description = description_element.first.inner_text().strip()
                            except Exception:
                                pass
                            
                            # Print property information
                            price_display = f"${price:,.0f}" if price is not None else "N/A"
                            lot_size_display = f"{lot_size} acres" if lot_size is not None else "N/A"
                            zip_display = final_zip if final_zip else "N/A"
                            days_display = f"{days_on_market} days" if days_on_market is not None else "N/A"
                            description_display = description if description else "N/A"
                            print(f"    Property {property_counter}: Price = {price_display}, Lot size = {lot_size_display}, Zip code = {zip_display}, Days on market = {days_display}")
                            print(f"      Description: {description_display}")
                            
                            # Store property data for statistics (only if we have price, lot_size, and days_on_market)
                            if price is not None and lot_size is not None and days_on_market is not None:
                                # Check for duplicates: same price, days_on_market, description, and lot_size
                                # Normalize description to empty string if None for comparison
                                description_normalized = description if description else ""
                                
                                is_duplicate = False
                                duplicate_index = None
                                
                                for i, processed in enumerate(processed_properties):
                                    if (processed['price'] == price and 
                                        processed['days_on_market'] == days_on_market and 
                                        processed['description'] == description_normalized and
                                        processed['lot_size'] == lot_size):
                                        is_duplicate = True
                                        duplicate_index = i
                                        break
                                
                                if is_duplicate:
                                    # Duplicate found, skip this property
                                    print(f"      Skipped - Duplicate of Property {processed_properties[duplicate_index]['index']}")
                                else:
                                    # Not a duplicate, add to lists
                                    properties.append({
                                        'price': price,
                                        'lot_size': lot_size,
                                        'days_on_market': days_on_market
                                    })
                                    processed_properties.append({
                                        'price': price,
                                        'days_on_market': days_on_market,
                                        'description': description_normalized,
                                        'lot_size': lot_size,
                                        'index': property_counter
                                    })
                        except Exception as click_error:
                            print(f"Warning: Could not click row {property_counter}: {click_error}")
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
            
            # Calculate and print statistics
            if properties:
                print("\n" + "="*60)
                print("STATISTICS")
                print("="*60)
                
                # Extract lists for calculations
                prices = [p['price'] for p in properties]
                lot_sizes = [p['lot_size'] for p in properties]
                days_on_market_list = [p['days_on_market'] for p in properties]
                
                # Calculate averages
                avg_price = statistics.mean(prices)
                avg_lot_size = statistics.mean(lot_sizes)
                avg_days = statistics.mean(days_on_market_list)
                
                # Calculate medians
                median_price = statistics.median(prices)
                median_lot_size = statistics.median(lot_sizes)
                median_days = statistics.median(days_on_market_list)
                
                # Round and display
                print(f"Average sale price: ${round(avg_price):,}")
                print(f"Median sale price: ${round(median_price):,}")
                print(f"Average lot size: {round(avg_lot_size, 1)} acres")
                print(f"Median lot size: {round(median_lot_size, 1)} acres")
                print(f"Average days on market: {round(avg_days)} days")
                print("="*60)
            else:
                print("\nNo complete property data collected for statistics.")
        except Exception as e:
            print(f"Warning: Could not complete pagination for {zip_code}: {e}")
            print("Continuing anyway...")
        
        browser.close()


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Open Redfin for-sale land listings for a zip code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python open_redfin_for_sale.py 90210
  python open_redfin_for_sale.py 95667
        """
    )
    parser.add_argument(
        "zip_code",
        type=str,
        help="Zip code to search for for-sale land listings"
    )
    
    args = parser.parse_args()
    
    # Validate zip code
    zip_code = args.zip_code.strip()
    if not zip_code:
        print("Error: Zip code is required", file=sys.stderr)
        sys.exit(1)
    
    try:
        open_redfin_for_sale_listings(zip_code)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
