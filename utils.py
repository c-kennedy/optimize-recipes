#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 12 15:41:20 2019

@author: chris
"""
# code-review: general comment, there are far too many if-else blocks here,
#   there must be a way to streamline this logic.

import pandas as pd
import numpy as np
#import matplotlib.pyplot as plt
#import seaborn as sns
#import os
#import json
#import spacy
import string
#import time
import unicodedata
import re
from itertools import combinations



class SimilarityCalculator(object):
    """Computes similarity between recipes based on
       common perishable ingredients and cuisines."""
    def __init__(self, ignore_cutoff=0.15, save_cutoff=0.75, info_df=None, stock_list=None):
        # code-review: your doctstring should define the meaning of these
        #   inputs
        if ignore_cutoff >= save_cutoff:
            raise ValueError("ignore_cutoff must be < save_cutoff")

        # code-review: a slightly more svelt approach:
        # if not info_df:
        #     info_df = pd.read_csv(
        #         'good_mains_with_ingredient_amounts.csv', low_memory=False, index_col='Unnamed: 0')
        # self.info_df = info_df
        if info_df is not None:
            self.info_df = info_df
        else:
            self.info_df = pd.read_csv('good_mains_with_ingredient_amounts.csv',
                                       low_memory=False, index_col='Unnamed: 0')
        
        # code-review: these filenames are used all over the place, would be
        #   nice to have a module where they are defined as constants, and
        #   imported where needed.

        if stock_list is not None:
            self.stock_list = stock_list
        else:
            self.stock_list = pd.read_csv('stock_list_augmented.csv',
                                          index_col='ingredient')
        self.ingredient_list_dict = dict()
        for ind in self.info_df.index:
            n_ingreds = self.info_df.loc[ind,'number_of_ingredients']
            raw_ingredients = list(self.info_df.loc[ind, ingredient_cols(n_ingreds)])  # code-review: .tolist()
            self.ingredient_list_dict[ind] = [(ing,clean_name(ing)) for ing in raw_ingredients]
        
        # code-review: you need to break up this wall of code with judicious
        #   use of blank lines and explanitory comments

        self.similarity_dict = dict()
        self.saved_pairs = []
        for cuisine in self.info_df.cuisine0.unique():
            for ind1, ind2 in combinations(self.info_df[self.info_df.cuisine0
                                                        ==cuisine].index, 2):  # code-review: this line break will not do

                # code-review: dying for a comment here on what this helper does
                def f(item):
                    if item not in self.stock_list.index:
                        return True
                    else:
                        return self.stock_list.loc[item,'stocked']!=1  # code-review: else is not needed
                ind1_ingredients = set(filter(f, (ing[1] for ing in self.ingredient_list_dict[ind1])))
                ind2_ingredients = set(filter(f, (ing[1] for ing in self.ingredient_list_dict[ind2])))
                intersection = ind1_ingredients.intersection(ind2_ingredients)
                union = ind1_ingredients.union(ind2_ingredients)
                jaccard = len(intersection)/len(union)
                if jaccard <= ignore_cutoff:
                    continue  # code-review: if this does nothing, don't do it at all
                if jaccard >= save_cutoff:
                    self.saved_pairs.append((ind1, ind2))
                self.similarity_dict[(ind1, ind2)] = jaccard
    
    def similarity(self, ind1, ind2):
        """Similarity score for recipes number ind1 and ind2. Largely precomputed, 
           so this is very fast."""
        # code-review: would be useful to indicate *where* they are precomputed
        #   so I can follow 
        if ind1 == ind2:
            return 1
        if ind1 > ind2:
            ind1, ind2 = ind2, ind1
        if (ind1, ind2) not in self.similarity_dict:
            return 0
        return self.similarity_dict[(ind1, ind2)]
    
    def get_similar_indices(self, ind, n=10):
        """Return a list of indices of recipes similar to recipe number ind,
           including itself."""
        similarities = [(self.similarity(ind, other), other) for other in self.info_df.index]
        similarities.sort(reverse=True)
        return similarities[:n]

def clean_name(ingredient, exclude=None):
    if not exclude:
        exclude=exclude_list
    else:
        exclude=exclude
    ingredient_name = ingredient.replace('-',' ')
    ingredient_name = ''.join(
        c for c in ingredient_name if c not in string.punctuation)
    ingredient_name = ' '.join(
        word for word in ingredient_name.split() if word not in exclude)
    return ingredient_name

# code-review: if this is a constant, make it immutable (a tuple), and define
#   it at the top of the file
exclude_list = ['sliced','chopped','diced','minced','fresh','finely','freshly',
                'halves','dried','to','taste','large','medium','small']

def ingredient_cols(n):
    return ['ingredient%d'%(i) for i in range(n)]  # code-review: f-strings


class QuantityExtractor(object):
    """QuantityExtractor object, with ingredient_extract and 
    grocery_item_extract methods."""

    # code-review: class constants can just get defined here, but be sure to 
    #   use immutable classes (e.g., frozendict, and not dict)

    def __init__(self):
        """
        Creates a QuantityExtractor object, with ingredient_extract and
        grocery_item_extract methods.
        """
        # code-review: I don't like this data structure. It will make you
        #   check strings to get the unit type, and remember which value
        #   lives in which index. You can make things
        #   nicer if you create a simple namedtuple class for wt and vol
        # 
        # Volume = namedtuple('Volume', ['name', 'conversion'])
        # Weight = namedtuple('Weight', ['name', 'conversion'])
        # teaspoon = Volume(name='teaspoon', conversion=4.929)
        # measurements = {'teaspoon': teaspoon, 'tsp', teaspoon, ...}
        #
        # You can check unit type with isinstance.       
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
                            'g ': ['wt',1],
                            'gr': ['wt',1],
                            'kg': ['wt',1000],
                            'mg': ['wt',0.001]}
        # code-review: what the devil is all this?
        self.units = '|'.join(unit for unit in self.measurement_dict.keys())
        self.units = self.units.replace('.','\.')
        self.ingredient_regex = re.compile('([\d\.]+ )?(\s*\d/\d+)?(\s*[\u00BC-\u00BE\u2150-\u215E\u2189])?[- ]*(%s){1}'%(self.units))
        self.item_regex = re.compile('\$?(\d*\.?\d{0,2})/(%s)'%(self.units))

    def ingredient_extract(self, ingredient):
        '''From an ingredient phrase, extract the quantity in mL or g
           and return a pair (amount, type) where type is 'wt', 'vol', or 'whole'
           depending on whether the unit is weight, volume, or whole units'''
        if pd.isnull(ingredient):
            return '', ''  # code-review: why are these both strings if one is an amount?
        
        ingredient = ingredient.lower()
        search = self.ingredient_regex.search(ingredient)
        # code-review: there has got to be a more straightforward way to code
        #   this, I cannot reason about all these branching paths without
        #   getting a headache.
        if search:
            qty, rawfrac, unicodefrac, unit = search.groups()  # code-review: can this just return 0 so you can avoid the if below?
            if not qty:
                qty = 0
            if unicodefrac:
                try:
                    qty = float(qty) + unicodedata.numeric(unicodefrac.strip(' '))
                except:  # code-review: NOOOOOO! handle specific exceptions or fail
                    print(ingredient)
            if rawfrac:
                location = rawfrac.find('/')
                qty = float(qty) + int(rawfrac[location-1:location])/int(rawfrac[location+1:location+2])
            else:
                qty = float(qty)
            return (qty*self.measurement_dict[unit][1], 
                    self.measurement_dict[unit][0])
        else:
            search = re.search('([\d\.]+)?(\s*\d/\d+)?(\s*[\u00BC-\u00BE\u2150-\u215E\u2189])?',ingredient)
            if search:
                qty, rawfrac, unicodefrac = search.groups()
                if not qty:
                    qty = 0
                if unicodefrac:
                    try:
                        qty = float(qty) + unicodedata.numeric(unicodefrac.strip(' '))
                    except:
                        print(ingredient)
                if rawfrac:
                    location = rawfrac.find('/')
                    qty = float(qty) + int(rawfrac[location-1:location])/int(rawfrac[location+1:location+2])
                else:
                    qty = float(qty)
                return qty, 'whole'
            else:
                return np.nan, 'whole'
    
    def grocery_item_extract(self, item):
        '''From a grocery item unit price, extract a pair (price, type) where
           price is unit price per mL, g, or whole, and type is 'wt', 'vol', or
           'whole' depending on unit'''
        search = self.item_regex.search(item)
        if search:
            price, unit = search.groups()
            return float(price)/self.measurement_dict[unit][1], self.measurement_dict[unit][0]
        else:  # code-review: no need for else given that the block above returns
            r = re.search('(\d*\.\d{0,2})', item)
            if r:
                return float(r.groups(1)[0]), 'whole'
            else:  # code-review: same.
                return np.nan, 'whole'

qe = QuantityExtractor()
