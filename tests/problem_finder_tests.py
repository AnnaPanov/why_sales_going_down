import pdb
import product_config as pc
from problem_finders import *

# Macy's tests
assert(macys_problem_finder("file://macys_currently-unavailable.html", {}).problem_text == "stockout")
assert(macys_problem_finder("file://macys_backorder.html", {}).problem_text == "stockout")
assert(macys_problem_finder("file://macys_almost-sold-out.html", {}).problem_text == "almost stockout")

# Sephora tests
assert(sephora_problem_finder("file://sephora_productNotCarried.txt", {}).problem_text == "stockout")
assert(sephora_problem_finder("file://sephora_out-of-stock.html", {}).problem_text == "stockout")
assert(sephora_problem_finder("file://sephora_only-a-few-left.html", {}).problem_text == "almost stockout")

# Ulta tests
assert(ulta_problem_finder("file://ulta_no-longer-available.html", {}).problem_text == "stockout")

# Bloomingdales tests
assert(bloomingdales_problem_finder("file://bloomingdales_out-of-stock.html", {}).problem_text == "stockout")

# Nordstrom tests
assert(nordstrom_problem_finder("file://nordstrom_backordered.html", {}).problem_text == "stockout")
