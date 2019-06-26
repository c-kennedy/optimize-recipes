OptiMeal
===============

code-review: A few top level comments for you.
code-review: 1) This needs to be a python package, not a collection of scripts. This will improve
    usability and help readers to understand too, and allow you to make some tidy CLIs
code-review: 2) Where the heck did the serialized data come from? Can I reproduce it with the code in this repo?
    If not, then why not!
code-review: 3) It is past time to add more friendly comments to help your readers (including you)

code-review: I'd like to see this README start with a short description of the project. WTF is this thing?

code-review: The next thing to include would be a "getting started" section, that tells me how to set
    up my environment and run the things.

code-review: I am a lot less interested in the detailed contents. I would be most happy if the README
    just listed a few CLIs that automate everything (i.e., data preparation, model build, app run, etc).
    This is not so hard to do, and looks baller. We can talk more about what I mean.

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


