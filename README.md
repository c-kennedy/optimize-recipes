OptiMeal
===============

An app to perfect your meal planning using local grocery prices. Includes ingredient lists parsed from an archive of 27,000 Yummly recipes, scraped prices from Giant Eagle and Wegman's, a Scraper class to get more, and an app built with Flask and AJAX to allow the user to select a recipe or recipes, then find the recipe that is cheapest per serving.

This is a reasonably stable version of the project, though still a little rough around the edges (in particular, the scraping module is not really in a fit state for use). You should be able to get it to run, though, by cloning the repo and running

`$ python app_ajax.py`

at a terminal. I suggest *curry* and *lasagna* as searches to get a flavor for what it can do...and what odd little errors still happen.




This repository includes:

Python scripts
-------------
**app_ajax.py**: Controller for the Flask app.

**utils.py**: Includes the `SimilarityCalculator` and `QuantityExtractor` classes used to build the list of recipe similarities and extract ingredient quantities from strings.

**pricing.py**: Defines the `PricedRecipe` class and the `get_GE_search_results` function that are required to built the grocery list output for `app_ajax`.

**scraping.py**: Under construction; has a working `GiantEagleScrape` class that can scrape pricing info from Giant Eagle, and a `Scraper` class that currently only works for Wegman's (see documentation).

Web pages
---------
**templates/index_ajax.html.j2**: HTML/JavaScript for the actual web page.

Data
----
Lots. There is a **preprocessing.py** script (or maybe series of scripts) I'm hoping to post at some point that will be able to re-create all the data.

