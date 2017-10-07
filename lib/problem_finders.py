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


_tor_process = None
_tor_proxies = None
def start_tor_process(tor_port):
    global _tor_process
    global _tor_proxies
    def print_all_lines(line):
        sys.stderr.write(line + '\n')
    def stop_tor_process():
        sys.stderr.write('stopping the Tor process...\n')
        _tor_process.kill()
        sys.stderr.write('the Tor process stopped\n')
    import stem.process
    import atexit
    sys.stderr.write('starting the Tor process at port %d...\n' % tor_port)
    _tor_process = stem.process.launch_tor_with_config(
        config = { 'SocksPort': str(tor_port) },
        init_msg_handler = print_all_lines)
    _tor_proxies = {
        'http': 'socks5://localhost:' + str(tor_port),
        'https': 'socks5://localhost:' + str(tor_port)
    }
    atexit.register(stop_tor_process)


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
    item_id = _try_find_webid(url) or "web id not found"
    if ("product is currently unavailable" in page.text):
        logging.info('page says "product is currently unavailable"')
        return ProductProblem(STOCKOUT, "product is currently unavailable", item_id)
    if (re.search("availabilityMsg.*order: usually ships within", page.text)):
        logging.info('page says "availabilityMsg.*order: usually ships within"', item_id)
        return ProductProblem(STOCKOUT, "product not immediately available ('backorder: usually ships within blah blah')", item_id)
    if ("lmost sold out" in page.text):
        logging.info('page says "lmost sold out"')
        return ProductProblem(ALMOST_STOCKOUT, "almost sold out", item_id)
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
    sku = _group0(re.search('[?&;]skuId=(\d+)', url))
    if not sku:
        logging.info('url does not contain "skuId=(\d+)"')
        return ProductProblem(CONFIG_ERROR, 'link must contain "skuId=", try clicking on a product size to expand the link')
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
            return ProductProblem(STOCKOUT, stockout_type, "sku: " + sku)
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
_problem_finders["sephora ca"] = sephora_problem_finder

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
    review_count = re.search('<span.*itemprop="reviewCount">(\d+)</span>', page.text)
    if not review_count:
        review_count = 0
        average_rating = 5.0
    else:
        review_count = int(review_count.groups()[0])
        average_rating = re.search('<span.*itemprop="ratingValue">([0-9]*\.[0-9]+|[0-9]+)</span>', page.text)
        if not average_rating:
            ProductProblem(CONFIG_ERROR, "page has reviews, but does not have average rating")
        average_rating = float(average_rating.groups()[0])
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
Boscovs
'''
def boscovs_problem_finder(url, config):
    # 1. load the product page
    page = _load_product_page(url, config)
    # 2. find the availability and review information
    availability_problem = re.search('itemprop="availability"([^>]+)>', page.text)    
    if availability_problem:
        availability_detail = availability_problem.groups()[0]
        if ("InStock" not in availability_detail) and ("nstock" not in availability_detail):
            return ProductProblem(STOCKOUT, 'no sure, but most likely out of stock')
    add_to_cart_button = re.search('<img[^>]+addToCartButton[^>]+>', page.text)
    if (not add_to_cart_button):
        return ProductProblem(CONFIG_ERROR, 'page does not have an "add to cart" button')
    add_to_cart_button = add_to_cart_button.group()
    if ("disabled" in add_to_cart_button) or ("Disabled" in add_to_cart_button):
        return ProductProblem(STOCKOUT, '"add to cart" button is disabled')
    review_count = re.search('<[^>]+itemprop="reviewCount"[^>]*>(\d+)<', page.text)
    if not review_count:
        review_count = 0
        average_rating = 5.0
    else:
        review_count = int(review_count.groups()[0])
        average_rating = re.search('<[^>]+itemprop="ratingValue"[^>]*>([0-9]*\.[0-9]+|[0-9]+)</span>', page.text)
        if not average_rating:
            ProductProblem(CONFIG_ERROR, "page has reviews, but does not have average rating")
        average_rating = float(average_rating.groups()[0])
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
_problem_finders["boscovs"] = boscovs_problem_finder


'''
Neiman
'''
def neiman_problem_finder(url, config):
    # 1. load the product page
    page = _load_product_page(url, config)

    # 2. find the availability and review information
    availability = re.search("product_inventory_status.*:.*\[([^\]]+)\]", page.text)
    if not availability:
        return ProductProblem(CONFIG_ERROR, "product availability information missing")
    availability = availability.groups()[0].replace('\\', '')
    try:
        availability_list = json.loads('[' + availability + ']')
        for i in availability_list:
            if (i != "Instock" and i != "InStock"):
                return ProductProblem(STOCKOUT, i)
    except:
        return ProductProblem(CONFIG_ERROR, "errors when parsing availability information: " + availability)

    # 3. since Neiman-Marcus has no ratings or reviews, we are already done
    return None
_problem_finders["neiman-marcus"] = neiman_problem_finder
_problem_finders["neiman marcus"] = neiman_problem_finder
_problem_finders["neimanmarcus"] = neiman_problem_finder


'''
Ulta
'''
def ulta_problem_finder(url, config):
    # 1. load the product page
    page = _load_product_page(url, config)
    sku = _group0(re.search('property="og:url"[^>]+[&;?]sku=(\d+)', page.text)) or\
          _group0(re.search('>Item\s+#:\s+(\d+)<', page.text))
    if not sku:
        return ProductProblem(CONFIG_ERROR, "cannot find a SKU for that product")
    # 2. search for typical problems
    review_count = -1
    average_rating = -1
    if ("his product is no longer available" in page.text):
        return ProductProblem(STOCKOUT, "product no longer available", "sku: " + sku)
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
        'user-agent': 'Estee Lauder Availability Checker/0.0.1',\
    #    'Accept': 'application/json',\
    #    'X-Macys-Webservice-Client-Id': 'ubmqtbg8k3kmwuszkcv2ng5z'\
    }
    page = requests.get(url, headers=headers, timeout=10)
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
        web_id = _group0(re.search("[&?;]ID=(\d+)", url))
        web_id = ("web_id: " + str(web_id)) if web_id else ""
        if (0 != len(upcs_not_available)):
            return ProductProblem(STOCKOUT, "some UPCs are not in stock (" + ", ".join(upcs_not_available) + ")", "upc: [" + ', '.join(upcs_not_available) + "], " + web_id)
        if (low_availability):
            return ProductProblem(ALMOST_STOCKOUT, "some UPCs almost sold out", web_id)
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
            item_id = "item: " + str(product_info.get('styleNumber', 'UNKNOWN')) + ", productID: " + str(product_info.get('productID', 'UNKNOWN'))
            return ProductProblem(STOCKOUT, "product not available", item_id)
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
Dillards
'''
def dillards_problem_finder(url, config):
    # 1. load the product page
    page = _load_product_page(url, config)
    # 2. find availability information and all
    item_id = _group0(re.search("[?;&]di=(\d+)", url)) or "unknown"
    if ("item is not currently available" in page.text):
        return ProductProblem(STOCKOUT, "item not currently available", "item # " + item_id)
    availability_info = _find_script_containing(page.text, "@type")
    if not availability_info:
        return ProductProblem(CONFIG_ERROR, "page does not contain a product information JSON blob")
    for availability in re.findall('"availability"\s*:\s*"([^"]+)"', availability_info):
        if ('InStock' not in availability) and ('OnlineOnly' not in availability):
            availability = availability.split('/')[-1]
            if (availability == 'LimitedAvailability'):
                return ProductProblem(ALMOST_STOCKOUT, "only a few left", "item # " + item_id)
            return ProductProblem(STOCKOUT, "for one of the SKUs availability is '" + availability + "'", "item # " + item_id)
    # 3. ok, availability is not an issue, so let's see if the reviews are a problem
    average_rating = re.search('"ratingValue"\s*:\s*"([0-9]*\.[0-9]+|[0-9]+)"', page.text)
    average_rating = float(average_rating.groups()[0]) if average_rating else 5.0
    review_count = re.search('"reviewCount"\s*:\s*"(\d+)"', page.text)
    review_count = int(review_count.groups()[0]) if review_count else 0
    return _is_it_a_review_problem(review_count, average_rating)
_problem_finders["dillards"] = dillards_problem_finder


'''
Von Maur
'''
def vonmaur_problem_finder(url, config):
    # 1. load the product page
    page = _load_product_page(url, config)
    availability_error_box = re.search('id="diverr"\s*>([^<]*)<', page.text)
    if not availability_error_box:
        return ProductProblem(CONFIG_ERROR, "availability information box is not found on page")
    availability_error = availability_error_box.groups()[0]
    if (availability_error != ""):
        return ProductProblem(STOCKOUT, availability_error)
    review_count = re.search('itemprop="reviewCount">(\d+)<', page.text)
    if not review_count:
        review_count = 0
        average_rating = 5.0
    else:
        review_count = int(review_count.groups()[0])
        average_rating = re.search('itemprop="ratingValue">([0-9]*\.[0-9]+|[0-9]+)<', page.text)
        if not average_rating:
            ProductProblem(CONFIG_ERROR, "page has reviews, but does not have average rating")
        average_rating = float(average_rating.groups()[0])
    return _is_it_a_review_problem(review_count, average_rating)
_problem_finders["vonmaur"] = vonmaur_problem_finder
_problem_finders["von maur"] = vonmaur_problem_finder


'''
JC Penney
'''
def jcpenney_problem_finder(url, config):
    url = url.split('&')[0]
    # 1. load the page
    page = _load_product_page(url, config)
    # 2. load availability from jcpenney API
    sku = re.search('/([^/?]+)\?', url)
    if (not sku):
        sku = re.search('/([^/?]+)$', url)
        if (not sku):
            return ProductProblem(CONFIG_ERROR, "url does not have a '/blahblah?' in it, so I cannot determine the SKU")
    sku = sku.groups()[0]
    inventory_url = "http://www.jcpenney.com/v1/product-aggregator/%s/inventory" % sku
    inventory_response = requests.get(inventory_url, timeout=10)
    if (inventory_response.text.strip() == ""):
        return ProductProblem(STOCKOUT, "item cannot be added to bag")
    try:
        inventory_response = json.loads(inventory_response.text)
        for inventory_state in inventory_response:
            if ('atp' not in inventory_state):
                return ProductProblem(CONFIG_ERROR, "one of the items doesn't have 'atp' in " + inventory_response)
            if ('id' not in inventory_state):
                return ProductProblem(CONFIG_ERROR, "one of the items doesn't have 'id' in " + inventory_response)
            available_to_purchase = inventory_state['atp']
            if not available_to_purchase:
                return ProductProblem(STOCKOUT, "UPC=%s is out of stock at %s" % (str(inventory_state['id']), inventory_url))
    except:
        return ProductProblem(CONFIG_ERROR, "garbled inventory response from " + inventory_url)
    # 3. check the reviews
    review_info = _find_script_containing(page.text, '"reviewCount"\s*:\s*(\d+)')
    if not review_info:
        review_count = 0
        average_rating = 5
    else:
        review_count = re.search('"reviewCount"\s*:\s*"?(\d+)', page.text)
        review_count = int(review_count.groups()[0]) if review_count else 0
        average_rating = re.search('"ratingValue"\s*:\s*"?([0-9]*\.[0-9]+|[0-9]+)', page.text)
        average_rating = float(average_rating.groups()[0]) if average_rating else 5.0
    return _is_it_a_review_problem(review_count, average_rating)
    # 4. data in jcpenney format (more correct)
    #jcp_availability_info = _find_script_containing(page.text, 'productJSON\s*=')    
_problem_finders["jcpenney"] = jcpenney_problem_finder
_problem_finders["jc penney"] = jcpenney_problem_finder
_problem_finders["jc penney/sephora"] = jcpenney_problem_finder
_problem_finders["jc penney/ sephora"] = jcpenney_problem_finder


def lord_and_taylor_problem_finder(url, config):
    # 1. load the page
    page = _load_product_page(url, config)
    # 2. check the availability
    if ("product__limited-inventory" in page.text):
        return ProductProblem(ALMOST_STOCKOUT, "limited inventory left")
    availability = re.search('itemprop="availability"[^>]+>([^<]+)<', page.text)
    if not availability:
        return ProductProblem(CONFIG_ERROR, "availability information not found on page")
    availability = availability.groups()[0]
    if ('InStock' not in availability) and ('OnlineOnly' not in availability) and ('In Stock' not in availability) and ('Online Only' not in availability):
        return ProductProblem(STOCKOUT, availability.split('/')[-1])
    # 3. lord&taylor doesn't provide reviews, so we are done here
    return None
_problem_finders["lord&taylor"] = lord_and_taylor_problem_finder
    

def sdm_bb_problem_finder(url, config):
    # 1. load the page
    page = _load_product_page(url, config)
    # 2. check the availability
    sku = _group0(re.search('"productSKU"\s*:\s*\(?"?(\d+)', page.text)) or _group0(re.search('[&;\?]variantCode=(\d+)', url))
    if not sku:
        return ProductProblem(CONFIG_ERROR, "cannot find product sku on the page or in the link")
    out_of_stock = _group0(re.search('"outofStock"\s*:\s*\(?"?(\w+)', page.text))
    if out_of_stock.lower() == "true":
        return ProductProblem(STOCKOUT, "out of stock", "sku: " + sku)
    # 3. check the reviews
    ratings = []
    for ratingValue in re.findall('itemprop="?ratingValue"?\s*>(\d+)<', page.text):
        ratings.append(float(ratingValue))
    review_count = len(ratings)
    average_rating = sum(ratings)/len(ratings) if 0 < len(ratings) else 5.0
    if (3.8 < average_rating) and (average_rating < 4.0): average_rating = 4.0 # because they only display it graphically at SDM
    return _is_it_a_review_problem(review_count, average_rating)
_problem_finders["sdm - bb"] = sdm_bb_problem_finder


def jean_contu_problem_finder(url, config):
    # 1. load the page
    page = _load_product_page(url, config)
    item_id = _group0(re.search('class="[^">]*js-upc-code"[^>]+>(\d+)<', page.text))
    if (item_id):
        item_id = "upc: " + item_id
    else:
        item_id = _group0(re.search('/(\d+)/', url))
        if not item_id:
            return ProductProblem(CONFIG_ERROR, "cannot find product UPC or even SKU on the page or in the link")
        item_id = "sku: " + item_id
    # 2. check the availability
    limited_quantity = _group0(re.search('(<div[^>]+class=\"problem[^"]* limited-quantity[^>]+>)', page.text))
    if limited_quantity and (("hidden" not in limited_quantity) and ("display:none" not in limited_quantity)):
        return ProductProblem(ALMOST_STOCKOUT, "just a few left", item_id)
    out_stock = _group0(re.search('(<div[^>]+class=\"problem[^"]* out-stock[^>]+>)', page.text))
    if out_stock and (("hidden" not in out_stock) and ("display:none" not in out_stock)):
        return ProductProblem(STOCKOUT, "just a few left", item_id)
    # 3. no ratings on Jean Contu, so we are done
    return None
_problem_finders["jean coutu"] = jean_contu_problem_finder


def beauty_brands_problem_finder(url, config):
    # 1. load the page
    page = _load_product_page(url, config)
    # 2. find the availability blob
    availability_blob = _find_script_containing(page.text, "MarketLive.P2P.buildEnhancedDependentOptionMenuObjects")
    if not availability_blob:
        return ProductProblem(CONFIG_ERROR, "page does not have product availability in JSON format")
    availability_blob = availability_blob.replace("MarketLive.P2P.buildEnhancedDependentOptionMenuObjects", "").strip()
    if ('(' == availability_blob[0]): availability_blob = availability_blob[1:]
    if (';' == availability_blob[-1]): availability_blob = availability_blob[0:(len(availability_blob) - 1)]
    if (')' == availability_blob[-1]): availability_blob = availability_blob[0:(len(availability_blob) - 1)]
    try:
        availability_blob = json.loads(availability_blob)
    except:
        return ProductProblem(CONFIG_ERROR, "availability information in JSON format seems to be garbled")
    availability_by_sku = availability_blob.get('aOptionSkus', None)
    if (not availability_by_sku):
        return ProductProblem(CONFIG_ERROR, "availability information in JSON does not have 'aOptionSkus'")
    if (0 == len(availability_by_sku)):
        return ProductProblem(CONFIG_ERROR, "availability information by SKU is empty")
    for i in availability_by_sku:
        availability = availability_by_sku[i]
        if ('inStock' in availability):
            if (availability['inStock']):
                continue # this SKU is in stock
        sku = availability.get('iSkuPk', None)
        if not sku:
            return ProductProblem(CONFIG_ERROR, "one of the items is not in stock, but its SKU is missing")
        return ProductProblem(STOCKOUT, "not in stock", "sku: " + str(sku))
    # 3. there are no reviews, so we are done
    return None    
_problem_finders["beauty brands"] = beauty_brands_problem_finder



def ssi_stages_problem_finder(url, config):
    # 1. load the page
    page = _load_product_page(url, config)
    web_id = _group0(re.search(">WEB\s+ID\s*:\s*(\d+)<", page.text))
    if not web_id:
        return ProductProblem(CONFIG_ERROR, "cannot find product WEB ID in page text")
    # 2. check for availability problems
    out_of_stock_sku = _group0(re.search('out-of-stck[^>]+data-size-id="(\d+)"', page.text))
    if out_of_stock_sku:
        return ProductProblem(STOCKOUT, "one of SKUs is out of stock", "sku: " + out_of_stock_sku + ", web_id: " + web_id)
    if "OUT OF STOCK" in page.text:
        return ProductProblem(STOCKOUT, "out of stock", "web_id: " + web_id)        
    # 3. not checking for review problems: is too complicated here, because have to interact with bazaarvoice systems
    return None
_problem_finders["ssi stages"] = ssi_stages_problem_finder


def hudsons_bay_problem_finder(url, config):
    # 1. load the page
    page = _load_product_page(url, config)
    # 2. find the availability information with UPCs
    availability_blob = _find_div_containing(page.text, "catentry_id")
    if not availability_blob:
        return ProductProblem(CONFIG_ERROR, "cannot find availability information on page")
    try:
        availability_blob = json.loads(availability_blob)
    except:
        return ProductProblem(CONFIG_ERROR, "availability information on page is garbled")
    if not isinstance(availability_blob, list):
        return ProductProblem(CONFIG_ERROR, "availability information on page is not a list")
    if 0 == len(availability_blob):
        return ProductProblem(CONFIG_ERROR, "availability information on page is found, but empty")
    for item in availability_blob:
        if ('outOfStock' in item) and item['outOfStock']:
            return ProductProblem(STOCKOUT, "out of stock", "upc: " + (item.get('ItemThumbUPC', None) or ('"none", catalog id: ' + str(item.get('catentry_id', None)))))
        if ('inventoryStatus' in item) and (item['inventoryStatus'] != "In Stock"):
            return ProductProblem(STOCKOUT, str(item['inventoryStatus']), "upc: " + (item.get('ItemThumbUPC', None) or ('"none", catalog id: ' + str(item.get('catentry_id', None)))))
    # 3. ratings and reviews
    average_rating = _group0(re.search('<span class="pr-rating[^>"]+average"[^>]*>([0-9]*\.[0-9]+|[0-9]+)</span>', page.text)) or '5.0'
    average_rating = float(average_rating)
    review_count = _group0(re.search('>(\d+)</span>\s*reviews', page.text)) or '0'
    review_count = int(review_count)
    return _is_it_a_review_problem(review_count, average_rating)
_problem_finders["hudson's bay"] = hudsons_bay_problem_finder
_problem_finders["hudsons bay"] = hudsons_bay_problem_finder


def aafes_problem_finder(url, config):
    # 1. load the page
    sku = _group0(re.search("/(\d+)\?", url)) or _group0(re.search("/(\d+)$", url))
    if not sku:
        return ProductProblem(CONFIG_ERROR, "URL does not contain SKU")
    page = _load_product_page(url, config)
    # 2. look for stockouts
    limited_availability = _group0(re.search("(only\s+[^<]+\s+items?\s+left)", page.text))
    if (limited_availability):
        return ProductProblem(ALMOST_STOCKOUT, limited_availability, "sku: " + sku)
    if ("ut of Stock" in page.text) or ("ut of stock" in page.text):
        return ProductProblem(STOCKOUT, "out of stock", "sku: " + sku)
    if ("encountered some technical issues" in page.text):
        return ProductProblem(STOCKOUT, "technical issues with the product", "sku: " + sku)
    # 3. reviews are ignored, because they must be loaded from bazaarvoice and it's not straightforward
    return None
_problem_finders["AAFES Shopmyexchange".lower()] = aafes_problem_finder


def saks_problem_finder(url, config):
    # 1. when loading the page, pretend that we are a web browser on a mobile device
    style_code = _group0(re.search("m.saks.com/pd.jsp\?productCode=(\d+)", url))
    if not style_code:
        return ProductProblem(CONFIG_ERROR, "Saks product URLs must all look like \"http://m.saks.com/pd.jsp?productCode=XXXX\" (where XXXX is the \"style code\" of the product, which you can find on any Saks product page)")
    headers = {\
        'user-agent': 'Estee Lauder Availability Checker/0.0.1',\
    }
    page = requests.get(url, headers=headers, timeout=10)
    if page.status_code != 200:
        raise ProductProblemException(ProductProblem(PAGE_NOT_LOADED, "response code %d" % page.status_code))
    if not isinstance(page.text, str):
        raise ProductProblemException(ProductProblem(PAGE_NOT_LOADED, "response text is not a string"))
    expected_title = config[product_config.FIELD_EXPECTED_TITLE]
    brand = config[product_config.FIELD_BRAND]
    if (not re.search("<h1.*" + expected_title + ".*/h1>", page.text)) and (not re.search("<h1.*" + brand + ".*/h1>", page.text)):
            raise ProductProblemException(ProductProblem(PRODUCT_NOT_ON_PAGE,\
                                                         "are you sure it is the right product? page title does not contain any headers with '%s' or '%s'"\
                                                         % (expected_title, brand)))
    # 2. check availability
    for availability in re.findall('itemprop="availability"[^>]*>([^<]+)<', page.text):
        if (availability == 'In Stock'):
            continue # all is good
        upc = _group0(re.search('"upc"\s*:\s*"?(\d+)', page.text))
        prd_id = _group0(re.search('prd_id=(\d+)', page.text))
        if upc:
            item_id = "upc: " + upc
        elif prd_id:
            item_id = "product_id: " + prd_id
        else:
            item_id = "item_id: \"unknown\""
        return ProductProblem(STOCKOUT, availability, item_id + ", style_code: " + style_code)
    # 3. check the reviews
    average_rating = _group0(re.search('itemprop="ratingValue"[^>]*>([0-9]*\.[0-9]+|[0-9]+)<', page.text)) or '5.0'
    average_rating = float(average_rating)
    if (0 == average_rating):
        average_rating = 5.0
    review_count = _group0(re.search('itemprop="reviewCount"[^>]*>(\d+)<', page.text)) or '0'
    review_count = int(review_count)
    return _is_it_a_review_problem(review_count, average_rating)
_problem_finders["saksfifthavenue"] = saks_problem_finder


def michaelkors_problem_finder(url, config):
    # 1. load the page
    page = _load_product_page(url, config)
    # 2. find the availability information with UPCs
    availability = _group0(re.search('<meta.*property="og:availability".*content="(\w+)"', page.text))
    if not availability:
        return ProductProblem(CONFIG_ERROR, "cannot find availability information on page")
    if ("InStock" in availability) and ("OnlineOnly" in availability) or ("PreOrder" in availability):
        return ProductProblem(STOCKOUT, availability.split('/')[-1])
    # 3. ratings and reviews
    # such information is dynamically populated by React ;(
    return None # availability is good, but ratings and reviews were not checked
_problem_finders["michaelkors"] = michaelkors_problem_finder
_problem_finders["mk com"] = michaelkors_problem_finder
    

def sdm_problem_finder(url, config):
    # 1. load the page
    page = _load_product_page(url, config)
    # 2. find the availability information with UPCs
    out_of_stock = _group0(re.search('"outofStock"\s*:([^,]+)[,\n]', page.text))
    if not out_of_stock:
        return ProductProblem(CONFIG_ERROR, "cannot find availability information on page")
    if ("true" in out_of_stock):
        sku = _group0(re.search('"productSKU"\s*:([^,]+)[,\n]', page.text))
        if sku: sku = (sku.split('"')[1] if 1 < len(sku.split('"')) else sku)
        else: sku = "unknown"
        return ProductProblem(STOCKOUT, "sku: " + sku)
    # 3. ratings and reviews
    ratings = []
    for match in re.finditer('<span.*itemprop="ratingValue">([0-9]*\.[0-9]+|[0-9]+)</span>', page.text):
        ratings.append(float(match.groups()[0]))
    average_rating = 5.0 if 0 == len(ratings) else sum(ratings) / float(len(ratings))
    return _is_it_a_review_problem(len(ratings), average_rating)
_problem_finders["sdm-bb"] = sdm_problem_finder



'''
utilities
'''
_title_finder = re.compile("<title[^>]*>([^<]*)<", re.IGNORECASE)

def _load_product_page(url, config):
    try:
        if (url[0:7] == "file://"): return LoadFile(url[7:]) # mainly for tests, but who knows

        custom_headers = { 'user-agent': 'Estee Lauder Availability Checker/0.0.1' }
        all_headers_and_proxies = [ (custom_headers, None), (None, None)]
        if _tor_proxies:
            all_headers_and_proxies = all_headers_and_proxies + [ (custom_headers, _tor_proxies), (None, _tor_proxies) ]
            if ('shopmyexchange' in url): all_headers_and_proxies = reversed(all_headers_and_proxies) # special case for that website

        response = None
        for headers_and_proxies in all_headers_and_proxies:
            try:
                #sys.stderr.write(requests.get("http://httpbin.org/ip", proxies=headers_and_proxies[1]).text + "\n")
                logging.info("loading from '%s', (headers,proxies)=%s ..." % (str(url), headers_and_proxies))
                response = requests.get(url, timeout=40, headers=headers_and_proxies[0], proxies=headers_and_proxies[1])
                logging.info("^ status_code: %d, content_length: %d" % (response.status_code, len(response.text)))
                if (response.status_code != 403):
                    break # success
            except requests.exceptions.ReadTimeout as e:
                logging.info("encountered a read timeout: %s" % str(e))
            except requests.exceptions.ConnectionError as e:
                logging.info("encountered a connection error: %s" % str(e))
        if response is None:
            raise ProductProblemException(ProductProblem(PAGE_NOT_LOADED, "ran out of ways to load this page"))

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
        if (expected_title.lower() not in title.lower()) and (brand.lower() not in title.lower()):
            raise ProductProblemException(ProductProblem(PRODUCT_NOT_ON_PAGE,\
                                                         "are you sure it is the right product? page title does not contain %s='%s' (instead, the title is: %s)"\
                                                         % (product_config.FIELD_EXPECTED_TITLE, expected_title, title)))
    return response


def _find_script_containing(text, substring):
    expression = re.compile(substring)
    for block in text.split("</script"):
        if "<script" not in block:
            continue
        script = ">".join((block.split("<script")[-1].split(">")[1:]))
        script = script.strip()
        if expression.search(script):
            return script
    return None


def _find_div_containing(text, substring):
    expression = re.compile(substring)
    for block in text.split("</div"):
        if "<div" not in block:
            continue
        script = ">".join((block.split("<div")[-1].split(">")[1:]))
        script = script.strip()
        if expression.search(script):
            return script
    return None


def _is_it_a_review_problem(review_count, average_rating):
    if WE_CARE_ABOUT_REVIEW_COUNT:
        if (review_count == 0):
            return ProductProblem(NO_REVIEWS, "no reviews")
    if (0 < review_count) and (average_rating < 4):
        return ProductProblem(LOW_RATING, "average rating only %.2f" % average_rating)
    if WE_CARE_ABOUT_REVIEW_COUNT:
        if (review_count < 15):
            return ProductProblem(FEW_REVIEWS, "only %d reviews" % review_count)
    return None

def _group0(search_result):
    if (search_result):
        groups = search_result.groups()
        if (0 < len(groups)):
            return groups[0]

def _try_find_upc(text):
    result = _group0(re.search('"upc"\s*:\s*"?(\d+)', text))
    return ("upc: " + str(result)) if result else None

def _try_find_webid(url):
    result = _group0(re.search('[?&;]ID=(\d+)', url))
    return ("web_id: " + str(result)) if result else None

class LoadFile:
    def __init__(self, filename):
        with open(filename, 'r') as f:
            self.text = f.read().replace('\n', '')
            self.url = "file://" + filename
            self.status_code = 200
