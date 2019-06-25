Recipe Optimizer 
===============

This repository includes:

**app_ajax.py**: Controller for the Flask app.

**utils.py**: Includes the `SimilarityCalculator` and `QuantityExtractor` classes used to build the list of recipe similarities and extract ingredient quantities from strings.

**pricing.py**: Defines the `PricedRecipe` class and the `get_GE_search_results` function that are required to built the grocery list output for `app_ajax`.
