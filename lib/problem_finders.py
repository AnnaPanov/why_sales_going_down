from product_problems import *

import product_config
import requests
import logging
import json
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
        logging.info('page says "product is currently unavailable"')
        return ProductProblem(STOCKOUT, "product is currently unavailable")
    if (re.search("availabilityMsg.*order: usually ships within", page.text)):
        logging.info('page says "availabilityMsg.*order: usually ships within"')
        return ProductProblem(STOCKOUT, "product not immediately available ('backorder: usually ships within blah blah')")
    if ("lmost sold out" in page.text):
        logging.info('page says "lmost sold out"')
        return ProductProblem(ALMOST_STOCKOUT, "almost sold out")
    # 3. examine the availability and review information inside of SEO droplet
    seo_droplet = re.search('<script[^>]*json[^>]*>([^<]+"@type"\s*:\s*"Offer"[^<]+)</', page.text)
    if not seo_droplet:
        logging.info('page text does not contain a SEO droplet')
        return ProductProblem(PRODUCT_NOT_ON_PAGE, 'page text does not contain a SEO droplet, maybe product is not on page anymore?')
    seo_droplet = seo_droplet.groups()[0].strip().replace('\n',' ')
    #if ("http://schema.org/InStock" in seo_droplet):
    #    logging.info('found "http://schema.org/InStock" inside SEO droplet')
    #else:
    seo_droplet = json.loads(seo_droplet)
    offers = seo_droplet["offers"]
    if not isinstance(offers, list):
        offers = [ offers ]
    sku_found = False
    for offer in offers:
        if ('availability' in offer):
            sku_found = True
            availability = offer['availability']
            if ('InStock' in availability) or ('OnlineOnly' in availability) or ('PreOrder' in availability):
                return None # found this SKU and its availability is good
            availability = offer.get('availability', 'KeyNotFound')
            logging.info('availability is "%s"' % availability)
            if not (('InStock' in availability) or ('OnlineOnly' in availability) or ('PreOrder' in availability)):
                return ProductProblem(STOCKOUT, availability.split('/')[-1])
    rating_found = re.search('"ratingValue":\s*"([^"]+)"', seo_droplet)
    if (rating_found):
        try:
            rating = float(rating_found.groups()[0])
            if (rating < 3):
                return ProductProblem(LOW_RATING, "average rating only %f" % rating)
        except:
            logging.error("failed parse rating for '%s': %s" % (url, str(sys.exc_info())))
    review_count_found = re.search('"reviewCount":\s*"(\d+)"', seo_droplet)
    if not review_count_found:
        return ProductProblem(NO_REVIEWS, "no reviews found")
    try:
        review_count = int(review_count_found.groups()[0])
        if (review_count == 0):
            return ProductProblem(NO_REVIEWS, "no reviews found")
        if (review_count < 3):
            return ProductProblem(FEW_REVIEWS, "only %d reviews" % review_count)
    except:
        logging.error("failed parse review count for '%s': %s" % (url, str(sys.exc_info())))
    # 4. seo droplet not found on page?
    if (not sku_found):
        return ProductProblem(CONFIG_ERROR, "SEO droplet has no availability information for this skuId")
    # 5. otherwise, we are good
    return None
_problem_finders["macy's"] = macys_problem_finder
_problem_finders["macys"] = macys_problem_finder



'''
Sephora
'''
def sephora_problem_finder(url, config):
    # 1. load the product page
    page = _load_product_page(url, config)
    # 2. find the SEO droplet for a given SKU ID
    sku = re.search('skuId=(\d+)', url)
    if not sku:
        logging.info('url does not contain "skuId=(\d+)"')
        return ProductProblem(CONFIG_ERROR, 'link must contain "skuId=", try clicking on a product size to expand the link')
    sku = sku.groups()[0]
    seo_droplet = re.search('<script[^>]*json[^>]*>([^<]+"@type"\s*:\s*"Offer"[^<]+)</', page.text)
    if not seo_droplet:
        logging.info('page text does not contain a SEO droplet')
        return ProductProblem(PRODUCT_NOT_ON_PAGE, 'page text does not contain a SEO droplet, maybe product is not on page anymore?')
    seo_droplet = seo_droplet.groups()[0].strip().replace('\n',' ')
    seo_droplet = json.loads(seo_droplet)
    offers = seo_droplet["offers"]
    sku_found = False
    for offer in offers:
        if ('sku' in offer) and (str(offer['sku']) == str(sku)): # this is our offer
            availability = offer.get('availability', 'KeyNotFound')
            logging.info('availability for skuId=%s is "%s"' % (sku, availability))
            if ('InStock' in availability) or ('OnlineOnly' in availability) or ('PreOrder' in availability):
                logging.info('found "%s" inside SEO droplet for this SKU' % availability)
                sku_found = True
                break # found this SKU and its availability is good
            return ProductProblem(STOCKOUT, availability.split('/')[-1])
    reviews_found = re.search('(\d+)\s+reviews', page.text)
    if (not reviews_found):
        return ProductProblem(NO_REVIEWS, "no reviews found on page")
    review_count = int(reviews_found.groups()[0])
    if (review_count == 0):
        return ProductProblem(NO_REVIEWS, "no reviews found on page")
    if (review_count < 3):
        return ProductProblem(FEW_REVIEWS, "only %d reviews found on page" % review_count)
    rating_found = re.search('"rating":\s*([0-9]*\.[0-9]+|[0-9]+)', page.text)
    if (rating_found):
        rating = float(rating_found.groups()[0])
        if (rating < 3):
            return ProductProblem(LOW_RATING, "average rating only %f" % rating)
    # 4. if we are here, we failed to find that specific SKU on the page
    if (not sku_found):
        return ProductProblem(CONFIG_ERROR, "SEO droplet has no availability information for this skuId")
    else:
        return None # no problem
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
