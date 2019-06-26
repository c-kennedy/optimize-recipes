#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 19 11:30:48 2019

@author: chris
"""
import pandas as pd
import string
from utils import SimilarityCalculator
import pickle


with open('smaller_sc.pickle', 'rb') as f:
    sc = pickle.load(f)

prices = pd.read_csv('GE_prices_062519.csv', index_col='Unnamed: 0')
prices['name_lower'] = prices['name'].map(lambda s:s.lower())

#recipes = pd.read_csv('recipe_data.csv', index_col='Unnamed: 0')

def clean_name(ingredient, exclude=None):
    if not exclude:
        exclude=exclude_list
    else:
        exclude=exclude
    ingredient_name = ''.join(c for c in ingredient if c not in string.punctuation)
    ingredient_name = ' '.join(word for word in ingredient.split() if word not in exclude_list)
    return ingredient_name

exclude_list = ['sliced','chopped','diced','minced','fresh','finely','freshly','halves','ground','dried','to','taste']

def get_GE_recipe_price(ind):
    """For recipe with index ind based on quantities in sc.info_df and 
       prices in prices, return a PricedRecipe object"""
    row = sc.info_df.loc[ind]
    failed = False
    title = row['name']
    ingredients = []
    ingredient_items = dict()
    for n in range(row.number_of_ingredients):
        ingredient_name = row['ingredient%d'%(n)]
        cleaned_name = clean_name(ingredient_name)
        ingredients.append(ingredient_name)
        if sc.stock_list.loc[ingredient_name,'stocked']==1:
            continue
        if cleaned_name in sc.stock_list.index:
            if sc.stock_list.loc[cleaned_name,'stocked']==1: 
                continue
        ingredient_qty = row['ingredient%dqty'%(n)]
        ingredient_type = row['ingredient%dtype'%(n)]
        servings = row.servings
        if ingredient_qty == 0 or pd.isnull(ingredient_qty):
            failed = True
            break
        ingredient_type_set = set(['wt','vol']) if ingredient_type in ['wt','vol'] else ('whole',)
        condition = (prices.name==cleaned_name)
        condition = condition & (prices.norm_unit_price_type.isin(ingredient_type_set))
        if 'sauce' not in cleaned_name:
            condition = condition & ~(prices.name_lower.str.contains('sauce'))
        if 'marinade' not in cleaned_name:
            condition = condition & ~(prices.name_lower.str.contains('marinade'))
        to_try = prices.loc[condition][:5]
        item_unit_price = to_try.norm_unit_price.min()
        item_price = item_unit_price*ingredient_qty/servings
        to_use = to_try.loc[to_try.norm_unit_price==item_unit_price]
        if to_use.empty:
            failed = True
            break
        if isinstance(to_use, pd.DataFrame): to_use = to_use.iloc[0]
        item_name, on_sale = to_use['name'], to_use['on_sale']
        ingredient_items[ingredient_name] = (item_name, item_price, on_sale)
    if failed:
        return False
    else:
        price = sum(p[1] for p in ingredient_items.values())
        return PricedRecipe(ind, title, ingredients, ingredient_items, price)

def get_full_item_GE_recipe_price(ind, n_servings=None):
    """For recipe with index ind based on quantities in sc.info_df and
       prices in prices, return a PricedRecipe object where the price
       corresponds to the least amount you would need to pay for enough
       distinct items to go over the amount needed."""
    row = sc.info_df.loc[ind]
    failed = False
    title = row['name']
    if not n_servings:
        n_servings = row['servings']
    ingredients = []
    ingredient_items = dict()
    for n in range(row.number_of_ingredients):
        ingredient_name = row['ingredient%d'%(n)]
        cleaned_name = clean_name(ingredient_name)
        ingredients.append(ingredient_name)
        if sc.stock_list.loc[ingredient_name,'stocked']==1:
            continue
        if cleaned_name in sc.stock_list.index:
            if sc.stock_list.loc[cleaned_name,'stocked']==1: 
                continue
        ingredient_qty = row['ingredient%dqty'%(n)]
        ingredient_type = row['ingredient%dtype'%(n)]
        servings = row.servings
        if ingredient_qty == 0 or pd.isnull(ingredient_qty):
            failed = True
            break
        ingredient_type_set = set(['wt','vol']) if ingredient_type in ['wt','vol'] else ('whole',)
        condition = (prices.name_lower.str.contains(cleaned_name))
        condition = condition & (prices.norm_unit_price_type.isin(ingredient_type_set))
        if 'sauce' not in cleaned_name:
            condition = condition & ~(prices.name_lower.str.contains('sauce'))
        if 'marinade' not in cleaned_name:
            condition = condition & ~(prices.name_lower.str.contains('marinade'))
        to_try = prices.loc[condition]
        item_unit_price = to_try.norm_unit_price.min()
        item_price = item_unit_price*ingredient_qty/servings
        to_use = to_try.loc[to_try.norm_unit_price==item_unit_price]
        if to_use.empty:
            failed = True
            break
        if isinstance(to_use, pd.DataFrame): to_use = to_use.iloc[0]
        item_name, on_sale = to_use['name'], to_use['on_sale']
        ingredient_items[ingredient_name] = (item_name, item_price, on_sale)
    if failed:
        return False
    else:
        price = sum(p[1] for p in ingredient_items.values())
        return PricedRecipe(ind, title, ingredients, ingredient_items, price)

class PricedRecipe(object):
    """Container class for recipes with priced ingredients
       The price itself is self.price"""
    def __init__(self, ind, title, ingredients, ingredient_items, price):
        self.index = ind
        self.title = title
        self.ingredients = ingredients
        self.ingredient_items = ingredient_items
        self.price = price

