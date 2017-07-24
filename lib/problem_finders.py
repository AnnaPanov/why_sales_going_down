from product_problems import *

import product_config
import requests
import logging
import sys
import pdb
import re


_problem_finders = dict()
def find_problems(config):
    retailer = config[product_config.FIELD_RETAILER].lower()
    if (not retailer in _problem_finders):
        return ProductProblem(RETAILER_NOT_SUPPORTED, "retailer '%s' is not supported yet" % str(retailer))
    try:
        return _problem_finders[retailer](config[product_config.FIELD_LINK], config)
    except ProductProblemException as e:
        return e.problem




'''
Macy's
'''
def macys_problem_finder(url, config):
    # 1. load the product page
    page = _load_product_page(url, config)
    # 2. search for typical problems
    if ("product is currently unavailable" in page.text):
        return ProductProblem(STOCKOUT, "product is currently unavailable")
    if (re.search("availabilityMsg.*order: usually ships within", page.text)):
        return ProductProblem(STOCKOUT, "product not immediately available ('backorder: usually ships within blah blah')")
    if ("lmost sold out" in page.text):
        return ProductProblem(ALMOST_STOCKOUT, "almost sold out")
    # 3. if problems not found, everything is good!
    return None
_problem_finders["macy's"] = macys_problem_finder
_problem_finders["macys"] = macys_problem_finder



'''
Sephora
'''
def sephora_problem_finder(url, config):
    # 1. load the product page
    page = _load_product_page(url, config)
    # 2. search for typical problems
    if ("productNotCarried" in page.url):
        return ProductProblem(STOCKOUT, "product not carried")
    if (re.search("product not carried", page.text, re.IGNORECASE)):
        return ProductProblem(STOCKOUT, "product not carried")
    if ('"is_in_stock":false' in page.text):
        return ProductProblem(STOCKOUT, "out of stock")
    if (re.search('seph-json-to-js="sku"[^<]*"is_few_left":true', page.text)):
        return ProductProblem(ALMOST_STOCKOUT, "only a few left")
    # 3. if problems not found, everything is good!
    return None
_problem_finders["sephora"] = sephora_problem_finder



'''
Ulta
'''
def ulta_problem_finder(url, config):
    # 1. load the product page
    page = _load_product_page(url, config)
    # 2. search for typical problems
    if ("his product is no longer available" in page.text):
        return ProductProblem(STOCKOUT, "product no longer available")
    # 3. if problems not found, everything is good!
    return None
_problem_finders["ulta"] = ulta_problem_finder



'''
Bloomingdales
'''
def bloomingdales_problem_finder(url, config):
    # 1. load the product page
    page = _load_product_page(url, config)
    # 2. search for typical problems
    if ('"AVAILABILITY_MESSAGE":"ON ORDER' in page.text):
        return ProductProblem(STOCKOUT, "product is on order")
    if ('"AVAILABILITY_MESSAGE":"NOT ' in page.text):
        return ProductProblem(STOCKOUT, "not available")
    # 3. if problems not found, everything is good!
    return None
_problem_finders["bloomingdale's"] = bloomingdales_problem_finder
_problem_finders["bloomingdales"] = bloomingdales_problem_finder



'''
Nordstrom
'''
def nordstrom_problem_finder(url, config):
    # 1. load the product page
    page = _load_product_page(url, config)
    # 2. search for typical problems
    if ('Backordered Item' in page.text):
        return ProductProblem(STOCKOUT, "backordered item")
    # 3. if problems not found, everything is good!
    return None
_problem_finders["nordstrom"] = nordstrom_problem_finder



'''
utilities
'''
_title_finder = re.compile("<title[^>]*>([^<]*)<", re.IGNORECASE)

def _load_product_page(url, config):
    try:
        logging.info("loading from '%s' ..." % str(url))
        if (url[0:7] == "file://"): return LoadFile(url[7:]) # mainly for tests, but who knows
        response = requests.get(url)
        logging.info("^ status_code: %d, content_length: %d" % (response.status_code, len(response.text)))
    except:
        raise ProductProblemException(ProductProblem(PAGE_NOT_LOADED, "%s" % str(sys.exc_info())))
    if response.status_code != 200:
        raise ProductProblemException(ProductProblem(PAGE_NOT_LOADED, "response code %d" % response.status_code))
    if not isinstance(response.text, str):
        raise ProductProblemException(ProductProblem(PAGE_NOT_LOADED, "response text is not a string"))
    title = _title_finder.search(response.text)
    if (not title) or (0 == len(title.groups())):
        raise ProductProblemException(ProductProblem(PRODUCT_NOT_ON_PAGE, "page has no title"))
    if (0 != len(config)):
        title = ' '.join(title.groups()[0].splitlines()).strip()
        logging.info("^^ title: %s" % (str(title)))
        expected_title = config[product_config.FIELD_EXPECTED_TITLE]
        brand = config[product_config.FIELD_BRAND]
        if (expected_title not in title) and (brand not in title):
            raise ProductProblemException(ProductProblem(PRODUCT_NOT_ON_PAGE,\
                                                         "are you sure it is the right product? page title does not contain %s='%s' (instead, the title is: %s)"\
                                                         % (product_config.FIELD_EXPECTED_TITLE, expected_title, title)))
    return response


class LoadFile:
    def __init__(self, filename):
        with open(filename, 'r') as f:
            self.text = f.read().replace('\n', '')
            self.url = "file://" + filename
            self.status_code = 200
