#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
from utils import SimilarityCalculator
import pickle
import json
from pricing import PricedRecipe, get_GE_recipe_price
#import spacy

#nlp = spacy.load('en_core_web_sm')

with open('smaller_sc.pickle', 'rb') as f:
    sc = pickle.load(f)
    
sc.info_df['name_lower'] = sc.info_df.name.map(lambda name: name.lower())

sc.info_df['has_price'] = sc.info_df.index.map(lambda ind: bool(get_GE_recipe_price(ind)))
    
prices = pd.read_csv('GE_prices_062519.csv', index_col='Unnamed: 0')

recipes = pd.read_csv('smaller_recipe_data_with_indices.csv', index_col='Unnamed: 0')

# sc is a SimilarityCalculator, and can return indices of similar recipes
# it also has the recipe table baked in as .info_df

app = Flask(__name__)
#bootstrap = Bootstrap(app)


stores = ['Giant Eagle Victorian Village']

@app.route("/", methods=['GET','POST'])
def home():
    box_length=0
    recipes_to_use=None
    similar_recipes = []
    headers=[]
    if request.method == 'POST':
        #use_stores = [request.form.get(store) for store in stores]
        recipe_text = request.form.get('recipe_search')
        if recipe_text:
            text_to_search = recipe_text
            condition = sc.info_df.name_lower.str.contains(text_to_search)
            recipe_choices = list(sc.info_df.loc[condition].name)
            recipe_ids = list(sc.info_df.loc[condition].index)
            recipes_to_use = zip(recipe_choices, recipe_ids)
            box_length = min(len(recipe_choices),8)
        recipe_selections = request.form.getlist('recipe_select')
        if recipe_selections:
            recipe_selections = [int(x) for x in recipe_selections]
            similar_recipes = [[x[1] for x in sc.get_similar_indices(int(ind))] for ind in
                               recipe_selections]
            headers = sc.info_df.loc[recipe_selections, 'name'].values
            similar_recipes = pd.DataFrame([sc.info_df.loc[List,'name'] for 
                                            List in similar_recipes], index=headers)
            
    return render_template("index_ajax.html.j2", stores=stores, box_length=box_length,
                           recipes=recipes_to_use, similar_recipes=similar_recipes,
                           headers=headers)

@app.route('/search', methods=['POST'])
def search():
    """Get search results from the search box and pass back
       to be displayed in the selector"""
    text_to_search = request.form['text']
    condition = sc.info_df.name_lower.str.contains(text_to_search)
    condition = condition & sc.info_df.has_price
    recipe_choices = list(sc.info_df.loc[condition]['name'])
    recipe_ids = list(sc.info_df.loc[condition].index)
    recipes = {'size':min(len(recipe_choices),8), 
               'recipes':dict(zip(recipe_ids,recipe_choices))}
    return jsonify(recipes)

@app.route('/generate', methods=['POST'])
def generate():
    """Find and display the lowest-priced recipe"""
    #We're getting a JSON object with keys selector1 and selector2
    potentials = []
    data = request.get_json(force=True)
    print(data)
    n_servings = int(data['servings'])
    for i in [1,2]:
        try:
            recipe_selections = [int(n) for n in data['selector%d'%(i)]]
        except:
            continue
        similar_recipes = sum(([x[1] for x in sc.get_similar_indices(ind) if x[0]>0.5] for
                            ind in recipe_selections), [])
        potentials += [get_GE_recipe_price(ind) for ind in similar_recipes if
                       get_GE_recipe_price(ind)]
        potentials.sort(key=lambda pr:pr.price)
    if potentials == []:
        return jsonify({'title':'Could not find any recipes!', 'ingredients':[], 'price':None})
    else:
        final_recipe = FormattedPricedRecipe(potentials[0])
        return jsonify(final_recipe.display(n_servings))
        
        
#    default = {'title':'Title',
#               'ingredients':[{'original_name':'<font color="green">Name</font>of thing',
#                              'tobuy':'Grocery item',
#                              'price':'$3.45 <font color="red">On sale!</font>'},
#                              {'original_name':'Two',
#                               'tobuy':'Thing',
#                               'price':'Other thing'}],
#                'price':'$3.45'}

@app.route("/recipe_history")
def recipe_history():
    return render_template("recipe_history.html.j2")

def highlight_word(string):
    return '<b><font color="green">%s</font></b>'%(string)

class FormattedPricedRecipe(object):
    """Object with display method customized to be fed into and nicely
       read by web page."""
    def __init__(self, PR):
        self.index = PR.index
        self.title = PR.title
        self.ingredients = PR.ingredients
        self.ingredient_items = PR.ingredient_items
        self.price = PR.price
    
    def display(self, n_servings=None):
        """Return dict that can be jsonified."""
        if not n_servings:
            n_servings = sc.info_df.loc[self.index, 'servings']
        result = dict()
        result['title'] = self.title
        price = sum(item[1] for item in self.ingredient_items.values())*n_servings
        result['price'] = '<b><font color="blue">$%.2f</font></b>' % (price)
        ingredients_to_buy = []
        ingredients_in_pantry = []
        for number, ingredient in enumerate(self.ingredients):
            raw_ingredient = recipes.loc[self.index, 'ingredient%d'%(number)]
            indices_to_use = json.loads(recipes.loc[self.index, 'ingredient%dinds'%(number)])
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
                price_string = '$%.2f%s'%(self.ingredient_items[ingredient][1]*n_servings,
                                          sale_text)
                ingredients_to_buy.append({'original_name':output_string,
                                           'tobuy':self.ingredient_items[ingredient][0],
                                           'price':price_string})
            else:
                ingredients_in_pantry.append({'original_name':output_string, 
                                              'tobuy':None,
                                              'price':None})
        result['ingredients'] = ingredients_to_buy + ingredients_in_pantry
        result['servings'] = n_servings
        return result
        
if __name__ == "__main__":
    app.run(debug=True, port=5957)
