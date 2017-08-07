from product_problems import *

import product_config
import requests
import logging
import json
import sys
import pdb
import re


# this is the direction for version 1
WE_CARE_ABOUT_REVIEW_COUNT = False



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
    review_count_found = re.search('"reviewCount":\s*"(\d+)"', seo_droplet)
    if (rating_found and review_count_found):
        try:
            rating = float(rating_found.groups()[0])
            if (rating < 4):
                return ProductProblem(LOW_RATING, "average rating only %.2f" % rating)
        except:
            logging.error("failed parse rating for '%s': %s" % (url, str(sys.exc_info())))
    if WE_CARE_ABOUT_REVIEW_COUNT:
        if not review_count_found:
            return ProductProblem(NO_REVIEWS, "no reviews found")
        try:
            review_count = int(review_count_found.groups()[0])
            if (review_count == 0):
                return ProductProblem(NO_REVIEWS, "no reviews found")
            if (review_count < 15):
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
            if ('InStock' in availability) or ('OnlineOnly' in availability) or ('PreOrder' in availability) or ('LimitedAvailability' in availability):
                logging.info('found "%s" inside SEO droplet for this SKU' % availability)
                sku_found = True
                break # found this SKU and its availability is good
            stockout_type = availability.split('/')[-1]
            return ProductProblem(STOCKOUT, stockout_type)
    reviews_found = re.search('(\d+)\s+reviews', page.text)
    if WE_CARE_ABOUT_REVIEW_COUNT:
        if (not reviews_found):
            return ProductProblem(NO_REVIEWS, "no reviews found on page")
        review_count = int(reviews_found.groups()[0])
        if (review_count == 0):
            return ProductProblem(NO_REVIEWS, "no reviews found on page")
    rating_found = re.search('"rating":\s*([0-9]*\.[0-9]+|[0-9]+)', page.text)
    if (rating_found and reviews_found):
        rating = float(rating_found.groups()[0])
        if (rating < 4):
            return ProductProblem(LOW_RATING, "average rating only %.2f" % rating)
    if WE_CARE_ABOUT_REVIEW_COUNT:
        if (review_count < 15):
            return ProductProblem(FEW_REVIEWS, "only %d reviews found on page" % review_count)
    # 4. if we are here, we failed to find that specific SKU on the page
    if (not sku_found):
        return ProductProblem(CONFIG_ERROR, "SEO droplet has no availability information for this skuId")
    else:
        return None # no problem
_problem_finders["sephora"] = sephora_problem_finder

'''
Bonton
'''
def bonton_problem_finder(url, config):
    # 1. load the product page
    page = _load_product_page(url, config)
    # 2. find the availability and review information
    availability = re.search('<input.*="itemAvailability" value="([^"]+)"', page.text)
    if not availability:
        return ProductProblem(PRODUCT_NOT_ON_PAGE, 'page text does not contain availability information')
    availability = availability.groups()[0]
    if ("WEB" not in availability):
        return ProductProblem(STOCKOUT, 'not available for online purchases')
    review_count = 0
    average_rating = 5
    review_data = re.search('<div .*data-rating="([0-9]*\.[0-9]+|[0-9]+)" data-reviewcount="(\d+)"', page.text)
    if review_data:
        average_rating = float(review_data.groups()[0])
        review_count = int(review_data.groups()[1])
    if WE_CARE_ABOUT_REVIEW_COUNT:
        if (review_count == 0):
            return ProductProblem(NO_REVIEWS, "no reviews found on page")
    if (0 < review_count) and (average_rating < 4):
        return ProductProblem(LOW_RATING, "average rating only %.2f" % average_rating)
    if WE_CARE_ABOUT_REVIEW_COUNT:
        if (review_count < 15):
            return ProductProblem(FEW_REVIEWS, "only %d reviews found on page" % review_count)
    # 3. if we are here, all is good with this listing
    return None
_problem_finders["bon-ton"] = bonton_problem_finder
_problem_finders["bon ton"] = bonton_problem_finder
_problem_finders["bonton"] = bonton_problem_finder

    
'''
Belk
'''
def belk_problem_finder(url, config):
    # 1. load the product page
    page = _load_product_page(url, config)
    # 2. find the availability and review information

    #upc = re.search('>UPC:\s*(\d+)<', page.text)
    #if not upc:
    #    logging.info('page text does not contain a UPC code')
    #    return ProductProblem(CONFIG_ERROR, 'page text does not contain a UPC code')
    #upc = upc.groups()[0]

    availability = re.search('<link\s*itemprop="availability"\s*href="([^"]+)"', page.text)    
    if not availability:
        return ProductProblem(PRODUCT_NOT_ON_PAGE, 'page text does not contain availability information')
    availability = availability.groups()[0]
    if ('InStock' in availability) or ('OnlineOnly' in availability) or ('PreOrder' in availability) or ('LimitedAvailability' in availability):
        logging.info('found "%s" in availability for this SKU' % availability)
    else:
        stockout_type = availability.split('/')[-1]
        return ProductProblem(STOCKOUT, stockout_type)
    low_availability = re.search('<div[^>]*class="stock-product"[^>]*>([^<]+)<', page.text)
    if (low_availability):
        return ProductProblem(ALMOST_STOCKOUT, low_availability.groups()[0])

    average_rating = re.search('<span.*itemprop="ratingValue">([0-9]*\.[0-9]+|[0-9]+)</span>', page.text)
    if not average_rating:
        return ProductProblem(CONFIG_ERROR, 'page text does not contain rating information')
    average_rating = float(average_rating.groups()[0])

    review_count = re.search('<span.*itemprop="reviewCount">(\d+)</span>', page.text)
    if not review_count:
        return ProductProblem(CONFIG_ERROR, 'page text does not contain rating information')
    review_count = int(review_count.groups()[0])

    if WE_CARE_ABOUT_REVIEW_COUNT:
        if (review_count == 0):
            return ProductProblem(NO_REVIEWS, "no reviews found on page")
    if (average_rating < 4):
        return ProductProblem(LOW_RATING, "average rating only %.2f" % average_rating)
    if WE_CARE_ABOUT_REVIEW_COUNT:
        if (review_count < 15):
            return ProductProblem(FEW_REVIEWS, "only %d reviews found on page" % review_count)

    # if we are here, the listing is good
    return None # no problem
_problem_finders["belk"] = belk_problem_finder



'''
Ulta
'''
def ulta_problem_finder(url, config):
    # 1. load the product page
    page = _load_product_page(url, config)

    # 2. search for typical problems
    review_count = -1
    average_rating = -1
    if ("his product is no longer available" in page.text):
        return ProductProblem(STOCKOUT, "product no longer available")
    out_of_stock = None
    out_of_stock_found = re.search('"outOfStock"\s*:\s*"?(true|false)"?', page.text)
    if (out_of_stock_found):
        out_of_stock = out_of_stock_found.groups()[0];
    else:
        return ProductProblem(CONFIG_ERROR, "cannot establish whether the product is out of stock or not")
    if (out_of_stock == "true"):
        return ProductProblem(STOCKOUT, "product is out of stock")

    review_count_found = re.search('<meta[^>]*meta_reviewCount[^>]*content="?(\d+)"?', page.text)
    if (review_count_found):
        review_count = int(review_count_found.groups()[0]);
    else:
        return ProductProblem(CONFIG_ERROR, "cannot establish how many reviews the product has")
    average_rating_found = re.search('<meta[^>]*meta_rating[^>]*content="?([0-9]*\.[0-9]+|[0-9]+)"?', page.text)
    if (average_rating_found):
        average_rating = float(average_rating_found.groups()[0])
    else:
        return ProductProblem(CONFIG_ERROR, "cannot find the average rating of the product")
    if WE_CARE_ABOUT_REVIEW_COUNT:
        if (review_count == 0):
            return ProductProblem(NO_REVIEWS, "no reviews")
    if (0 < review_count) and (average_rating < 4):
        return ProductProblem(LOW_RATING, "average rating only %.2f" % average_rating)
    if WE_CARE_ABOUT_REVIEW_COUNT:
        if (review_count < 15):
            return ProductProblem(FEW_REVIEWS, "only %d reviews" % review_count)

    # 3. if problems not found, everything is good!
    return None
_problem_finders["ulta"] = ulta_problem_finder



'''
Bloomingdales
'''
def bloomingdales_problem_finder(url, config):
    product_id = re.search("\?ID=(\d+)", url)
    if not product_id:
        return ProductProblem(CONFIG_ERROR, "url does not have ID= in it (%s)" % url)
    headers = {\
        'user-agent': 'Availability Checker/0.0.1',\
    #    'Accept': 'application/json',\
    #    'X-Macys-Webservice-Client-Id': 'ubmqtbg8k3kmwuszkcv2ng5z'\
    }
    page = requests.get(url, headers=headers)
    if ("hoose your items" in page.text):
        return ProductProblem(CONFIG_ERROR, "this link is for a collection, but not for specific product")
    for block in page.text.split("</script"):
        if "<script" not in block:
            continue
        script = ">".join((block.split("<script")[-1].split(">")[1:]))
        script = script.strip()
        if "AVAILABILITY_MESSAGE" not in script:
            continue
        # this script must be parseable in json, otherwise we must throw
        availability_data = json.loads(script)
        # and this blob of json must have a "product" entry
        product_entry = availability_data["product"]
        if "sizeColorTypeByUPC" not in product_entry:
            return ProductProblem(STOCKOUT, "most likely, product not available (availability information not on page)")
        upcs_not_available = []
        some_upcs_are_available = False
        availability_by_upc = product_entry["sizeColorTypeByUPC"]
        for upc in availability_by_upc:
            availability = availability_by_upc[upc]
            message = availability["AVAILABILITY_MESSAGE"]
            if ("In Stock:" in message):
                some_upcs_are_available = True
                continue
            logging.warn("availability message for UPC %s does not contain 'In Stock': %s" % (upc, message))
            upcs_not_available.append(upc)
        low_availability = False
        if ("attributes" in product_entry):
            hide_low_availability = product_entry["attributes"].get("HIDE_LOW_AVAILABILITY_MESSAGE","")
            if (1 == len(hide_low_availability)) and (hide_low_availability[0] == 'N'):
                low_availability = True
        if (0 != len(upcs_not_available)):
            return ProductProblem(STOCKOUT, "some UPCs are not in stock (" + ", ".join(upcs_not_available) + ")")
        if (low_availability):
            return ProductProblem(ALMOST_STOCKOUT, "some UPCs almost sold out")
        number_of_reviews = 0
        average_rating = None
        if "numberOfReviews" in product_entry:
            number_of_reviews = int(product_entry["numberOfReviews"])
            average_rating = float(product_entry["custRating"])
        if WE_CARE_ABOUT_REVIEW_COUNT:
            if (0 == number_of_reviews):
                return ProductProblem(NO_REVIEWS, "no reviews found")
        if (0 < number_of_reviews) and (average_rating < 4):
            return ProductProblem(LOW_RATING, "average rating only %.2f" % average_rating)
        if WE_CARE_ABOUT_REVIEW_COUNT:
            if (15 > number_of_reviews):
                return ProductProblem(FEW_REVIEWS, "only %d reviews" % number_of_reviews)
        # if we are here, the product looks good
        return None

    # if we reached here, we failed to find the product info: most likely, we have a configuration problem
    return ProductProblem(CONFIG_ERROR, "availability information in JSON format is not found")
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
    digital_data_found = re.search("window.digitalData = ([^<]+)<", page.text);
    if (not digital_data_found):
        return ProductProblem(CONFIG_ERROR, "cannot find digital data on whether product is available or not")
    data = digital_data_found.groups()[0].strip()
    if (data[-1] == ";"): data = data[0:(len(data)-1)]
    try:
        data = json.loads(data)
        product = data['product']
        if not product:
            return ProductProblem(CONFIG_ERROR, "cannot find product for product info")
        product_info = product['productInfo']
        if not product_info:
            return ProductProblem(CONFIG_ERROR, "cannot find product info within product")
        if ('isAvailable' not in product_info):
            return ProductProblem(CONFIG_ERROR, "product availability information not found")
        is_available = product_info['isAvailable']
        if (not is_available):
            return ProductProblem(STOCKOUT, "product not available")
        if ('reviewsCount' not in product_info):
            return ProductProblem(CONFIG_ERROR, "review count information not found")
        review_count = product_info['reviewsCount']
        if WE_CARE_ABOUT_REVIEW_COUNT:
            if (review_count == 0):
                return ProductProblem(NO_REVIEWS, "no reviews")
        if (review_count) and ('averageRating' not in product_info):
            return ProductProblem(CONFIG_ERROR, "average rating information not found")
        average_rating = product_info['averageRating']
        if (review_count) and (average_rating < 4):
            return ProductProblem(LOW_RATING, "average rating only %.2f" % average_rating)
        if WE_CARE_ABOUT_REVIEW_COUNT:
            if (review_count < 15):
                return ProductProblem(FEW_REVIEWS, "only %d reviews" % review_count)
    except:
        return ProductProblem(CONFIG_ERROR, "problems loading digital data in json")
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
