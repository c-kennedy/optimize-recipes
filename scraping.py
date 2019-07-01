#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 12 16:02:59 2019

@author: chris
"""

# This whole module is still under development, as I try to resolve the different outputs I'm
# getting from Wegman's and Giant Eagle. Ideally, GiantEagleScrape will be nixed eventually so
# that Scraper is the general scraping object for any grocery store, and handling unit prices
# is farmed out to the individual search functions.

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from lxml.html import document_fromstring
import string
import pandas as pd
from utils import QuantityExtractor
from typing import Callable, List

options = Options()
options.headless = True

browser = webdriver.Firefox(options=options)

qe = QuantityExtractor()


def get_GE_search_results(search: str, browser=browser) -> List[tuple]:
    """Grabs info on results for search on Giant Eagle's site,
       returning a list of tuples of properties."""
    items = []
    browser.get('https://www.gianteagle.com/search?q=%s' % (search))
    sale_divs = browser.find_elements_by_css_selector('div[data-bind*=OnSale]')
    sale_mask = [x.text == 'ON SALE' for x in sale_divs]
    doc = document_fromstring(browser.execute_script('return document.body.innerHTML'))
    zipped = zip(doc.find_class('offer-item'), doc.find_class('offer-expires'), 
                 doc.find_class('offer-price'), sale_mask)
    for name, quantity, price, on_sale in zipped:
        name = ' '.join(name.text_content().split())
        [size, unit_price] = quantity.text_content().split(' | ')
        price = price.text_content()
        items.append((search, name, size, price, unit_price, on_sale))
    return items


def get_Weg_search_results(search: str, browser=browser) -> List[tuple]:
    items = []
    browser.get('https://www.wegmans.com/search.html?searchKey={}'.format(search))
    name_spans = browser.find_elements_by_css_selector('span[ng-bind*="product.name"]')
    names = [x.text for x in name_spans]
    price_spans = browser.find_elements_by_css_selector('span[ng-bind^="getPrice"]')
    prices = [x.text for x in price_spans]
    size_spans = browser.find_elements_by_css_selector('span[ng-bind*="product.weight"]')
    sizes = [x.text for x in size_spans]
    on_sale = ['*' in x for x in prices]
    ing_name = [search] * len(names)
    items = list(zip(ing_name, names, sizes, prices, on_sale))
    return items


class GiantEagleScrape(object):
    def __init__(self, stock_list=None, qe=None, exclude_words=None):
        if stock_list:
            self.stock_list = stock_list
        else:
            self.stock_list = pd.read_csv('stock_list_augmented.csv', index_col='ingredient')
        if qe:
            self.qe = qe
        else:
            self.qe = QuantityExtractor()
        if exclude_words:
            self.exclude = exclude_words
        else:
            self.exclude = ['sliced', 'chopped', 'diced', 'minced', 'fresh', 'finely',
                            'freshly', 'halves', 'dried', 'to', 'taste']

        self.scrape_results = pd.DataFrame(columns=['ing_name', 'name', 'size', 'price',
                                                    'unit_price', 'on_sale'])
        self.stock_list['scraped'] = self.stock_list.stocked.map(lambda k: 0 if k != 1 else 1)
        self.browser = webdriver.Firefox(options=options, keep_alive=True)

    def scrape(self, n: int) -> None:
        """Scrape the next n ingredients from stock_list that have scraped == 0"""
        if n <= 0:
            raise ValueError('n must be a positive integer')
        to_scrape = self.stock_list.loc[self.stock_list.scraped != 1].index[:n]
        listings = []
        for ingredient in to_scrape:
            mod_ingredient = ''.join(c for c in ingredient if c not in string.punctuation)
            mod_ingredient = ' '.join(word for word in mod_ingredient.split() if word not in 
                                      self.exclude)
            if mod_ingredient in self.stock_list.index:
                if self.stock_list.loc[ingredient, 'scraped'] == 1:
                    continue
                else:
                    # Selenium doesn't like scraping Giant Eagle's website for some reason,
                    # or at least it used to not, so it would occasionally throw an error and
                    # need to be restarted. I didn't encounter this problem the most recent time
                    # I tried trying to figure out exactly *which* error you get, so there's a
                    # bare except here for now.
                    try:
                        L = get_GE_search_results(mod_ingredient, self.browser)
                        print(mod_ingredient + ' succeeded')
                        listings = listings + L
                        self.stock_list.at[ingredient, 'scraped'] = 1
                        self.stock_list.at[mod_ingredient, 'scraped'] = 1
                    except:
                        self.stock_list.at[ingredient, 'scraped'] = -1
                        print(mod_ingredient + ' failed')
                        self.browser.quit()
                        self.browser = webdriver.Firefox(options=options, keep_alive=True)
        listings = pd.DataFrame(listings, columns=['ing_name', 'name', 'size', 'price',
                                                   'unit_price', 'on_sale'])
        self.scrape_results = pd.concat([self.scrape_results, listings])
    
    def multi_scrape(self, n, m):
        """Run scrape(n) m times--good for catching failed ingredients on subsequent tries"""
        for i in range(m):
            self.scrape(n)
    
    # This function is more here for documentation than use--this is how the last several columns
    # on GE_prices_[date].csv were produced. As noted in other places, the whole process for
    # normalizing prices needs to be reorganized.
    def augment(self):
        """Add columns for normalized unit price and size"""
        self.scrape_results['norm_unit_price'] = self.scrape_results.unit_price.map(lambda price:qe.grocery_item_extract(price)[0])
        self.scrape_results['norm_unit_price_type'] = self.scrape_results.unit_price.map(lambda price:qe.grocery_item_extract(price)[1])
        self.scrape_results['norm_size'] = self.scrape_results['size'].map(lambda size:qe.ingredient_extract(size)[0])
        self.scrape_results['norm_size_type'] = self.scrape_results['size'].map(lambda size:qe.ingredient_extract(size)[1])


# Scraper only works for Wegman's right now--since Wegman's doesn't list unit prices, they need 
# to be computed separately. Some stuff needs to be reorganized to accommodate the fact that, by
# contrast, unit prices are displayed and significant (but also occasionally unreliable!) for 
# Giant Eagle.

class Scraper(object):
    """General class to scrape from grocery store websites and compile results into a DataFrame."""
    def __init__(self, get_search_results: Callable[[str, webdriver], List[tuple]], 
                 stock_list=None, qe=None, exclude_words=None):
        """Creates Scraper object."""
        if not callable(get_search_results):
            raise TypeError('get_search_results must be a function')
        self.get_search_results = get_search_results
        if stock_list:
            self.stock_list = stock_list
        else:
            self.stock_list = pd.read_csv('stock_list_augmented.csv', index_col='ingredient')
        if qe:
            self.qe = qe
        else:
            self.qe = QuantityExtractor()
        if exclude_words:
            self.exclude = exclude_words
        else:
            self.exclude = ['sliced', 'chopped', 'diced', 'minced', 'fresh', 'finely',
                            'freshly', 'halves', 'dried', 'to', 'taste']
        self.scrape_results = pd.DataFrame(columns=['ing_name', 'name', 'size', 'price',
                                                    'unit_price', 'on_sale'])
        self.stock_list['scraped'] = self.stock_list.stocked.map(lambda k: 0 if k != 1 else 1)
        self.browser = webdriver.Firefox(options=options, keep_alive=True)
    
    def scrape(self, n, verbose=False):
        """Scrape the next n ingredients from stock_list that have scraped == 0"""
        to_scrape = self.stock_list.loc[self.stock_list.scraped != 1].index[:n]
        listings = []
        for ingredient in to_scrape:
            mod_ingredient = ''.join(c for c in ingredient if c not in string.punctuation)
            mod_ingredient = ' '.join(word for word in mod_ingredient.split() if 
                                      word not in self.exclude)
            if mod_ingredient in self.stock_list.index:
                if self.stock_list.loc[ingredient, 'scraped'] == 1:
                    self.stock_list.at[mod_ingredient, 'scraped'] = 1
                    continue
                elif self.stock_list.loc[mod_ingredient, 'scraped'] == 1:
                    continue
                else:
                    try:
                        L = self.get_search_results(mod_ingredient, self.browser)
                        if verbose:
                            print(mod_ingredient + ' succeeded')
                        listings = listings + L
                        self.stock_list.at[ingredient, 'scraped'] = 1
                        self.stock_list.at[mod_ingredient, 'scraped'] = 1
                    except:  # This is terrible, but I can't reproduce the error that used to happen here
                        self.stock_list.at[ingredient, 'scraped'] = -1
                        print(mod_ingredient + ' failed')
                        self.browser.quit()
                        self.browser = webdriver.Firefox(options=options, keep_alive=True)
        listings = pd.DataFrame(listings, columns=['ing_name', 'name', 'size', 
                                                   'price', 'on_sale'])
        self.scrape_results = pd.concat([self.scrape_results, listings])