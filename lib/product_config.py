FIELD_LINK = "Link"
FIELD_EXPECTED_TITLE = "ExpectedTitle"
FIELD_RETAILER = "Retailer"
FIELD_BRAND = "Brand"
FIELD_FAMILY = "Family"

import csv
import logging
import product_problems

def load(filename, error_list):
    result = dict()
    with open(filename) as csvfile:
        reader = csv.DictReader(csvfile)
        line_no = 0
        for row in reader:
            ++line_no
            error = None
            if (FIELD_LINK not in row):
                error = "field '%s' not specified in %s on line number %d" % (FIELD_LINK, filename, line_no)
            elif (FIELD_EXPECTED_TITLE not in row):
                error = "field '%s' not specified in %s on line number %d" % (FIELD_EXPECTED_TITLE, filename, line_no)
            elif (FIELD_BRAND not in row):
                error = "field '%s' not specified in %s on line number %d" % (FIELD_BRAND, filename, line_no)
            elif (FIELD_FAMILY not in row):
                error = "field '%s' not specified in %s on line number %d" % (FIELD_FAMILY, filename, line_no)
            elif (FIELD_RETAILER not in row):
                error = "field '%s' not specified in %s on line number %d" % (FIELD_RETAILER, filename, line_no)
            if (error is not None):
                error_list.append(ProductProblem(CONFIG_ERROR, error))
                logging.warning(detail)
                continue
            id = row[FIELD_LINK]
            result[id] = row
    logging.info("done reading %d products from %s" % (len(result), filename))
    return result

