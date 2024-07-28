from playwright.sync_api import sync_playwright
from dataclasses import dataclass, asdict, field

import pandas as pd
import argparse
import os

@dataclass
class Business:
    name: str = None
    address: str = None
    phone: str = None
    website: str = None
    email: str = None


@dataclass
class BusinessList:
    business_list: list[Business] = field(default_factory=list)
    
    def dataframe(self):
        """transform business_list to pandas dataframe

        Returns: pandas dataframe
        """
        return pd.json_normalize(
            (asdict(business) for business in self.business_list), sep="_"
        )

    def save_to_excel(self, filename):
        """saves pandas dataframe to excel (xlsx) file

        Args:
            filename (str): filename
        """
        outputFilePath = os.path.join(os.getcwd(), 'results.xlsx')
        self.dataframe().to_excel(outputFilePath, index=False)

def main():
    parser = argparse.ArgumentParser(description='Scrape business data from a website')
    parser.add_argument('-s', '--search', type=str, default="", help='Search')
    # parser.add_argument('-l', type=str, help='Location')
    parser.add_argument('-t', '--total', type=int, help='Total')
    args = parser.parse_args()
    
    if args.search:
        search_list = [args.search]
    else:
        search_list = []
        # read the input from file
        inp_file_path = os.path.join(os.getcwd(), 'input.txt')
        if os.path.exists(inp_file_path) is False:
            print("failed. Try passing -s argument or create input.txt file and add all search string in each line")
            exit(1)
        with open(inp_file_path, 'r') as f:
            search_list = [line.strip() for line in f]
    
    if args.total:
        total = args.total
    else:
        total = 1_000_000
    
    # start scraping
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto("https://www.google.com/maps/search/", timeout=60000)
        page.wait_for_timeout(2000)

        for index, search_str in enumerate(search_list):
            print(f"\n ---- Searching for query {index}: {search_str} ---")

            page.locator('//input[@id="searchboxinput"]').fill(search_str)
            page.wait_for_timeout(1000)

            page.keyboard.press("Enter")
            page.wait_for_timeout(2000)

            # scrolling
            href_query = '//a[contains(@href, "https://www.google.com/maps/place")]'
            page.hover(href_query)

            scrape_counter = 0
            while True:
                page.mouse.wheel(0, 10000)
                page.wait_for_timeout(3000)

                count = page.locator(href_query).count()

                # slicing to have only selected num of query items
                if count >= total:
                    listing = page.locator(href_query).all()[:total]
                    listings = [listing.locator("xpath=..") for listing in listings]
                    print(f"Total Scraped: {len(listings)}")
                else:
                    # logic to break from the loop and prevent running infinitely
                    if count == scrape_counter:
                        listings = page.locator(href_query).all()
                        print(f"Arrived at all available: {len(listings)}")
                        break
                    else:
                        scrape_counter = page.locator(href_query).count()
                        print('Currently scraped:', scrape_counter)

        business_list = BusinessList()


        # scrapping
        for listing in listings:
            try:
                listing.click()
                page.wait_for_timeout(1000)

                name_xpath = '//h1[contains(@class, "fontHeadingLarge")]/span[2]'
                address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
                website_xpath = '//a[@data-item-id="authority"]//div[contains(@class, "fontBodyMedium")]'
                phone_number_xpath = '//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]'
                review_count_xpath = '//button[@jsaction="pane.reviewChart.moreReviews"]//span'
                reviews_average_xpath = '//div[@jsaction="pane.reviewChart.moreReviews"]//div[@role="img"]'

                business = Business()
                xpaths = {
                    "name": name_xpath,
                    'address': address_xpath, 
                    "website": website_xpath, 
                    "phone": phone_number_xpath
                }

                # name
                s = '{:<20} {:<10} {:<10} {:<10}'
                if len(listing.get_attribute('aria-label')) >= 1:
                    business.name = listing.get_attribute('aria-label')
                    print('name: ', business.name)
                else:
                    business.name = ""
                
                for label, xpath in xpaths.items():
                    v = ""
                    if page.locator(xpath).count() > 0:
                        v = page.locator(address_xpath).inner_text()

                    if label == 'name' and business.name == "":
                        business.name = v
                    elif label == 'address':
                        business.address = v
                    elif label == 'website':
                        business.website = v
                    elif label == 'phone':
                        business.phone = v
                    
                    print(f'label:{label} = {v}')
                s.format(business.name, business.address, business.website, business.phone)
                print(s)
                business_list.business_list.append(business)
            except Exception as e:
                print(f'Error occured... {e}')
        
        # save to excel
        business_list.save_to_excel(f"google_maps_data_{search_str}".replace(' ', '_'))

    browser.close()


if __name__ == "__main__":
    main()