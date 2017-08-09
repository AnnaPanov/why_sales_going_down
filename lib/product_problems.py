# four classes of product problems
PROBLEM_WITH_CONFIGURATION = "configuration"
PROBLEM_WITH_AVAILABILITY = "availability"
PROBLEM_WITH_REVIEWS = "reviews"
PROBLEM_WITH_ASSETS = "assets"

# known product problems (and their severity)
CONFIG_ERROR = ("configuration error", PROBLEM_WITH_CONFIGURATION, 1)
WEBSCRAPER_ERROR = ("web scraper error", PROBLEM_WITH_CONFIGURATION, 2)
RETAILER_NOT_SUPPORTED = ("retailer not supported", PROBLEM_WITH_CONFIGURATION, 2)
PAGE_NOT_LOADED = ("page not loaded", PROBLEM_WITH_CONFIGURATION, 100)
PRODUCT_NOT_ON_PAGE = ("product not on page", PROBLEM_WITH_CONFIGURATION, 99)
STOCKOUT = ("stockout", PROBLEM_WITH_AVAILABILITY, 98)
ALMOST_STOCKOUT = ("almost stockout", PROBLEM_WITH_AVAILABILITY, 97)
NO_REVIEWS = ("no reviews", PROBLEM_WITH_REVIEWS, 52)
LOW_RATING = ("low review rating", PROBLEM_WITH_REVIEWS, 51)
FEW_REVIEWS = ("few reviews", PROBLEM_WITH_REVIEWS, 50)
#...
NO_PROBLEM = ("", "no problem", 0)


# what a problem description looks like
class ProductProblem:
    def __init__(self, text_class_severity, detail, item_id = None):
        assert(len(text_class_severity) == 3)
        self.problem = text_class_severity[0]
        self.problem_class = text_class_severity[1]
        self.problem_severity = text_class_severity[2]
        self.problem_detail = detail
        self.item_id = item_id or ""
            

    def __str__(self):
        return "%s-%d : '%s'" % (self.problem_class, self.problem_severity, self.problem)

    def __repr__(self):
        return "%s-%d : '%s'" % (self.problem_class, self.problem_severity, self.problem)


# and a problem description in form of an exception
class ProductProblemException(Exception):
    def __init__(self, problem):
        self.problem = problem

