#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
from utils import SimilarityCalculator
import pickle
import json
from pricing import PricedRecipe, get_recipe_price

# sc is a SimilarityCalculator, and can return indices of similar recipes
# It also has the recipe table baked in as .info_df
# This is also why we need utils.SimilarityCalculator
with open('smaller_sc2.pickle', 'rb') as f:
    sc = pickle.load(f)

# Load data for lookups
sc.info_df['name_lower'] = sc.info_df.name.map(lambda name: name.lower())

# This is a clumsy way to access multiple stores' worth of data, but at least it's
# extensible to more grocery stores in a pretty clear way
multiindex = pd.MultiIndex.from_product([['GE', 'Weg'], ['has_price', 'has_nearby_price']])

# Now tack on columns to sc.info_df telling whether a recipe has a price at each store
sc.info_df = sc.info_df.join(pd.read_csv('nearby_prices_tupled.csv', header=0, names=multiindex))

# And finally, the actual prices of ingredients, which can be queried by get_recipe_price
GE_prices = pd.read_csv('GE_prices_062519.csv')
Weg_prices = pd.read_csv('Weg_prices_062719.csv')

# Only need original recipe DF for the unparsed ingredient phrases and which words in them
# to highlight
recipes = pd.read_csv('smaller_recipe_data_with_indices.csv', index_col='Unnamed: 0')

app = Flask(__name__)

# Stores available to search in, plus their aliases as used in the data
stores_to_use = ['Giant Eagle', "Wegman's"]
stores_dict = {'Giant Eagle': 'GE', "Wegman's": 'Weg'}
stores_reverse_dict = {'GE': 'Giant Eagle', 'Weg': "Wegman's"}


# Since almost everything got transferred over to AJAX, this is now very simple!
@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template("index_ajax.html.j2", stores=stores_to_use)


@app.route('/search', methods=['POST'])
def search():
    """Get search results from the search box and pass back to be displayed in the selector"""
    data = request.get_json(force=True)
    text_to_search = data['text'].lower()
    # Convert real store names to aliases:
    stores = [stores_dict[store] for store in data['stores']]
    # Now we need to select the recipes that (1) contain the text we want to search for...
    condition = sc.info_df.name_lower.str.contains(text_to_search)
    # ...and (2) are close to recipes in any of the stores the user has selected. This is the
    # most generalizable way I could think of, but there's almost certainly a less clunky way to
    # do it instead of repeatedly or-ing stuff like this:
    store_possibilities = 0
    for store in stores:
        store_possibilities = store_possibilities | (sc.info_df[(store, 'has_nearby_price')])
    condition = condition & store_possibilities
    recipe_choices = sc.info_df.loc[condition]['name'].to_list()
    recipe_ids = sc.info_df.loc[condition].index.to_list()
    recipe_list = {'size': min(len(recipe_choices), 8),
                   'recipes': dict(zip(recipe_ids, recipe_choices))}
    return jsonify(recipe_list)


@app.route('/generate', methods=['POST'])
def generate():
    """Find and display the lowest-priced recipe"""
    # We're getting a JSON object with keys selector1, selector2, servings, stores
    # selector2 is left over from when there were 2 search boxes
    # TODO: remove selector2-related stuff
    data = request.get_json(force=True)
    n_servings = int(data['servings'])
    # Convert real store names to aliases:
    stores = [stores_dict[store] for store in data['stores']]
    recipe_selections = [int(n) for n in data['selector1']]
    similar_recipes = sum(([x[1] for x in sc.get_similar_indices(ind) if x[0] >= 0.5] for 
                           ind in recipe_selections), [])
    potentials = [get_recipe_price(ind, store) for ind in similar_recipes for store in stores
                  if get_recipe_price(ind, store)]
    potentials.sort(key=lambda pr: pr.price)
    if potentials == []:
        return jsonify({'title': 'Could not find any recipes!', 'ingredients': [], 'price': None})
    else:
        final_recipe = FormattedPricedRecipe(potentials[0])
        return jsonify(final_recipe.display(n_servings))


def highlight_word(string: str) -> str:
    return '<b><font color="green">{}</font></b>'.format(string)


class FormattedPricedRecipe(object):
    """Object with display method customized to be fed into and nicely read by the web page."""
    def __init__(self, PR: PricedRecipe):
        self.index = PR.index
        self.title = PR.title
        self.ingredients = PR.ingredients
        self.ingredient_items = PR.ingredient_items
        self.price = PR.price
        self.store = PR.store

    def display(self, n_servings=None) -> dict:
        """Return dict that can be jsonified."""
        # For better or worse, we're doing all the formatting on this side.
        # In the future, one would obviously like to use CSS with the JS on the other end instead.
        if not n_servings:
            n_servings = sc.info_df.loc[self.index, 'servings']
        result = dict()
        result['title'] = self.title
        price = sum(item[1] for item in self.ingredient_items.values()) * n_servings
        result['price'] = '<b><font color="blue">$%.2f</font></b>' % (price)
        ingredients_to_buy = []
        ingredients_in_pantry = []
        # Generate the formatted list of ingredients, with the words picked out by the parser
        # highlighted in green, and the stocked ingredients displayed without prices
        for number, ingredient in enumerate(self.ingredients):
            raw_ingredient = recipes.loc[self.index, 'ingredient{}'.format(number)]
            indices_to_use = json.loads(recipes.loc[self.index, 'ingredient{}inds'.format(number)])
            output = []
            for num, word in enumerate(raw_ingredient.split()):
                if num in indices_to_use:
                    output.append(highlight_word(word))
                else:
                    output.append(word)
            output_string = ' '.join(output)
            on_sale = ' <b><font color="blue">On Sale!</font></b>'
            if ingredient in self.ingredient_items:
                sale_text = on_sale if self.ingredient_items[ingredient][2] else ''
                price_string = '${:.2f}{}'.format(self.ingredient_items[ingredient][1] * 
                                                  n_servings, sale_text)
                ingredients_to_buy.append({'original_name': output_string,
                                           'tobuy': self.ingredient_items[ingredient][0],
                                           'price': price_string})
            else:
                ingredients_in_pantry.append({'original_name': output_string, 
                                              'tobuy': None,
                                              'price': None})
        result['ingredients'] = ingredients_to_buy + ingredients_in_pantry
        result['servings'] = n_servings
        result['original_servings'] = sc.info_df.loc[self.index, 'servings']
        result['store'] = stores_reverse_dict[self.store]
        return result
        

if __name__ == "__main__":
    app.run(debug=True, port=5957)
