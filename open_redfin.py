#!/usr/bin/env python3
"""
Redfin Land Listings Browser Opener

Opens a Redfin page showing land listings sold in the last year
between 2-100 acres for a given zip code.
"""

import sys
import argparse
from playwright.sync_api import sync_playwright


def open_redfin_land_listings(zip_code: str):
    """
    Opens a Redfin land listings page in a browser for the given zip code.
    
    Args:
        zip_code: The zip code to search for land listings
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
                            row.click(timeout=5000)
                            page.wait_for_timeout(300)
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
            
        except Exception as e:
            print(f"Warning: Could not complete pagination: {e}")
            print("Continuing anyway...")
        
        # Keep browser open until user closes it
        print("\nBrowser opened. Close the browser window when done.")
        input("Press Enter to close the browser...")
        
        browser.close()


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Open Redfin land listings page for a given zip code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python open_redfin.py 90210
  python open_redfin.py 10001
        """
    )
    parser.add_argument(
        "zip_code",
        type=str,
        help="The zip code to search for land listings"
    )
    
    args = parser.parse_args()
    
    # Validate zip code (basic check - should be 5 digits)
    zip_code = args.zip_code.strip()
    if not zip_code:
        print("Error: Zip code cannot be empty", file=sys.stderr)
        sys.exit(1)
    
    try:
        open_redfin_land_listings(zip_code)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
