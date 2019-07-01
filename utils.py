#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 12 15:41:20 2019

@author: chris
"""
import pandas as pd
import numpy as np
import string
import unicodedata
import re
from itertools import combinations
from typing import List, Tuple


class SimilarityCalculator(object):
    """Computes similarity between recipes based on common perishable ingredients and cuisines."""
    def __init__(self, ignore_cutoff=0.15, save_cutoff=0.75, info_df=None, stock_list=None):
        if ignore_cutoff >= save_cutoff:
            raise ValueError("ignore_cutoff must be < save_cutoff")
        if info_df is not None:
            self.info_df = info_df
        else:
            self.info_df = pd.read_csv('good_mains_with_ingredient_amounts.csv',
                                       low_memory=False, index_col='Unnamed: 0')
        if stock_list is not None:
            self.stock_list = stock_list
        else:
            self.stock_list = pd.read_csv('stock_list_augmented.csv',
                                          index_col='ingredient')
        self.ingredient_list_dict = dict()
        for ind in self.info_df.index:
            n_ingreds = self.info_df.loc[ind, 'number_of_ingredients']
            raw_ingredients = list(self.info_df.loc[ind, ingredient_cols(n_ingreds)])
            self.ingredient_list_dict[ind] = [(ing, clean_name(ing)) for ing in raw_ingredients]
        self.similarity_dict = dict()
        self.saved_pairs = []
        # For each cuisine, compute the similarity between each pair of recipes, retaining
        # only the pairs for which the similarity is above ignore_cutoff.
        for cuisine in self.info_df.cuisine0.unique():
            for ind1, ind2 in combinations(self.info_df[self.info_df.cuisine0 == cuisine].index, 2):
                def f(item):
                    if item not in self.stock_list.index:
                        return True
                    else:
                        return self.stock_list.loc[item, 'stocked'] != 1
                ind1_ingredients = set(filter(f, (ing[1] for ing in 
                                                  self.ingredient_list_dict[ind1])))
                ind2_ingredients = set(filter(f, (ing[1] for ing in 
                                                  self.ingredient_list_dict[ind2])))
                intersection = ind1_ingredients.intersection(ind2_ingredients)
                union = ind1_ingredients.union(ind2_ingredients)
                jaccard = len(intersection) / len(union)
                if jaccard <= ignore_cutoff:
                    continue
                # Note: saved_pairs is only for exploratory purposes--not actually used in the app
                if jaccard >= save_cutoff:
                    self.saved_pairs.append((ind1, ind2))
                self.similarity_dict[(ind1, ind2)] = jaccard
    
    def similarity(self, ind1: int, ind2: int) -> float:
        """Similarity score for recipes number ind1 and ind2. Largely precomputed, 
           so this is very fast."""
        if ind1 == ind2:
            return 1
        if ind1 > ind2:
            ind1, ind2 = ind2, ind1
        if (ind1, ind2) not in self.similarity_dict:
            return 0
        return self.similarity_dict[(ind1, ind2)]
    
    def get_similar_indices(self, ind: int, n=10) -> List[Tuple[float, int]]:
        """Return a list of indices of recipes similar to recipe number ind,
           including itself."""
        similarities = [(self.similarity(ind, other), other) for other in self.info_df.index]
        similarities.sort(reverse=True)
        return similarities[:n]


def clean_name(ingredient: str, exclude=None) -> str:
    if not exclude:
        exclude = exclude_list
    else:
        exclude = exclude
    ingredient_name = ingredient.replace('-', ' ')
    ingredient_name = ''.join(c for c in ingredient_name if 
                              c not in string.punctuation)
    ingredient_name = ' '.join(word for word in ingredient_name.split() if 
                               word not in exclude)
    return ingredient_name


exclude_list = ['sliced', 'chopped', 'diced', 'minced', 'fresh', 'finely', 'freshly',
                'halves', 'dried', 'to', 'taste', 'large', 'medium', 'small']


def ingredient_cols(n: int) -> List[str]:
    return ['ingredient{}'.format(i) for i in range(n)]


class QuantityExtractor(object):
    """QuantityExtractor object, with ingredient_extract and 
    grocery_item_extract methods."""
    def __init__(self):
        """
        Creates a QuantityExtractor object, with ingredient_extract and
        grocery_item_extract methods.
        """
        self.measurement_dict = {'teaspoon': ['vol', 4.929],
                                 'tsp': ['vol', 4.929],
                                 'tablespoon': ['vol', 14.787],
                                 'tbsp': ['vol', 14.787],
                                 'tbs': ['vol', 14.787],
                                 'ounce': ['wt', 28.35],
                                 'oz': ['wt', 28.35],
                                 'fluid ounce': ['vol', 29.57],
                                 'fl oz': ['vol', 29.57],
                                 'fl. oz': ['vol', 29.57],
                                 'floz': ['vol', 29.57],
                                 'pound': ['wt', 453.6],
                                 'lb': ['wt', 453.6],
                                 'cup': ['vol', 236.59],
                                 'c. ': ['vol', 236.59],
                                 'pint': ['vol', 473.18],
                                 'pt': ['vol', 473.18],
                                 'quart': ['vol', 946.35],
                                 'qt': ['vol', 946.35],
                                 'gallon': ['vol', 3785],
                                 'gal': ['vol', 3785],
                                 'g ': ['wt', 1],
                                 'gr': ['wt', 1],
                                 'kg': ['wt', 1000],
                                 'mg': ['wt', 0.001]}
        self.units = '|'.join(unit for unit in self.measurement_dict.keys())
        self.units = self.units.replace('.', r'\.')
        # I haven't yet figured out the right way to mix string formatting with regexes, so I'm
        # left with these last couple % formats instead of .format()s, which is also why these
        # aren't raw strings like you'd normally throw into re.compile()
        self.ingredient_regex = re.compile('([\d\.]+ )?(\s*\d/\d+)?(\s*[\u00BC-\u00BE\u2150-\u215E\u2189])?[- ]*(%s){1}'%(self.units))
        self.item_regex = re.compile('\$?(\d*\.?\d{0,2})/(%s)' % (self.units))

    def ingredient_extract(self, ingredient: str) -> Tuple[float, str]:
        '''From an ingredient phrase, extract the quantity in mL or g
           and return a pair (amount, type) where type is 'wt', 'vol', or 'whole'
           depending on whether the unit is weight, volume, or whole units'''
        if pd.isnull(ingredient):
            return '', ''
        ingredient = ingredient.lower()
        search = self.ingredient_regex.search(ingredient)
        # First, see if we can find a match with units, using the regex compiled above:
        if search:
            qty, rawfrac, unicodefrac, unit = search.groups()
            if not qty:
                qty = 0
            if unicodefrac:
                try:
                    qty = float(qty) + unicodedata.numeric(unicodefrac.strip(' '))
                except ValueError:
                    print(ingredient)
            if rawfrac:
                loc = rawfrac.find('/')
                qty = float(qty) + int(rawfrac[loc - 1:loc]) / int(rawfrac[loc + 1:loc + 2])
            else:
                qty = float(qty)
            return (qty * self.measurement_dict[unit][1],
                    self.measurement_dict[unit][0])
        # Otherwise, assume we're being given "whole" units, like "1 onion"
        else:
            search = re.search('([\d\.]+)?(\s*\d/\d+)?(\s*[\u00BC-\u00BE\u2150-\u215E\u2189])?',
                               ingredient)
            if search:
                qty, rawfrac, unicodefrac = search.groups()
                if not qty:
                    qty = 0
                if unicodefrac:
                    try:
                        qty = float(qty) + unicodedata.numeric(unicodefrac.strip(' '))
                    except:  # TODO: see if this still happens?
                        print(ingredient)
                if rawfrac:
                    loc = rawfrac.find('/')
                    qty = float(qty) + int(rawfrac[loc - 1:loc]) / int(rawfrac[loc + 1:loc + 2])
                else:
                    qty = float(qty)
                return qty, 'whole'
            else:
                return np.nan, 'whole'

    def grocery_item_extract(self, item: str) -> Tuple[float, str]:
        '''From a grocery item unit price, extract a pair (price, type) where
           price is unit price per mL, g, or whole, and type is 'wt', 'vol', or
           'whole' depending on unit'''
        search = self.item_regex.search(item)
        if search:
            price, unit = search.groups()
            return float(price) / self.measurement_dict[unit][1], self.measurement_dict[unit][0]
        else:
            r = re.search('(\d*\.\d{0,2})', item)
            if r:
                return float(r.groups(1)[0]), 'whole'
            else:
                return np.nan, 'whole'



