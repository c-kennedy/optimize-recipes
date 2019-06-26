OptiMeal
===============

This repository includes:

Python scripts
-------------
**app_ajax.py**: Controller for the Flask app.

**utils.py**: Includes the `SimilarityCalculator` and `QuantityExtractor` classes used to build the list of recipe similarities and extract ingredient quantities from strings.

**pricing.py**: Defines the `PricedRecipe` class and the `get_GE_search_results` function that are required to built the grocery list output for `app_ajax`.

Web pages
---------
**templates/index_ajax.html.j2**: HTML/JavaScript for the actual web page.

Data
----
**small_recipe_data.csv**: Table of recipe information and original ingredients for 9000 Yummly recipes.

**smaller_sc.pickle**: Pickled `SimilarityCalculator` object with pairwise recipe similarities for the ~5000 under consideration.

**good_mains_with_ingredient_amounts.csv**: Stored in ``smaller_sc`` as ``info_df``, with recipes and amounts extracted from original strings.

**stock_list_augmented.csv**: Stored in ``smaller_sc`` as ``stock_list``, with hand-coded information about whether an ingredient should be treated as "in stock" (i.e., not to included on grocery list).

**GE_prices_061819.csv**: Results of scraping Giant Eagle's website for ~200 ingredients on the given date.


