#!/usr/bin/env python3
"""
Redfin Land Listings Browser Opener - For Sale Properties

Opens a Redfin page showing land listings currently for sale
between 2-100 acres for a given zip code.
"""

import sys
import argparse
import re
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
        
        # Wait for table to load and click through each property row
        try:
            print("Waiting for table to load...")
            
            # Give the table a moment to render after switching to table view
            page.wait_for_timeout(2000)
            
            # Get the first tbody with class "tableList" from the correct hierarchy
            # Structure: div.TableBody.reversePosition > div.ReactDataTable.tableBody > table > tbody.tableList
            all_tbodies = page.locator("div.TableBody.reversePosition div.ReactDataTable.tableBody tbody.tableList")
            tbody_count = all_tbodies.count()
            
            if tbody_count == 0:
                print("No table body found.")
            else:
                first_table_body = all_tbodies.first
                
                # Get rows from the first tbody
                first_tbody_table_rows = first_table_body.locator("tr.tableRow")
                row_count = first_tbody_table_rows.count()
                
                # If empty, wait a bit and try again
                if row_count == 0:
                    page.wait_for_timeout(2000)
                    row_count = first_tbody_table_rows.count()
                
                if row_count > 0:
                    print(f"Found {row_count} property rows in the first table.")
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
                            
                            # Print property information
                            price_display = f"${price:,.0f}" if price is not None else "N/A"
                            lot_size_display = f"{lot_size} acres" if lot_size is not None else "N/A"
                            zip_display = final_zip if final_zip else "N/A"
                            print(f"    Property {idx + 1}/{row_count}: Price = {price_display}, Lot size = {lot_size_display}, Zip code = {zip_display}")
                        except Exception as click_error:
                            print(f"Warning: Could not click row {idx + 1}: {click_error}")
                            continue
                    
                    print(f"Finished clicking through {row_count} properties.")
                else:
                    print("No property rows found in the first table.")
        except Exception as e:
            print(f"Warning: Could not complete property clicking: {e}")
            print("Continuing anyway...")
        
        print("\nBrowser opened. Close the browser window when done.")
        input("Press Enter to close the browser...")
        
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
