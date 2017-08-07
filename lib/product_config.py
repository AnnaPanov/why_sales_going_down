FIELD_LINK = "Link"
FIELD_EXPECTED_TITLE = "ExpectedTitle"
FIELD_RETAILER = "Retailer"
FIELD_BRAND = "Brand"
FIELD_FAMILY = "Family"
FIELD_TITLE = "Title"

import csv
import xlrd
import logging
import product_problems

def load(filename, error_list):
    if (filename[-4:] == ".csv"):
        return _load_csv(filename, error_list)
    if (filename[-4:] == ".xls") or (filename[-5:] == ".xlsx"):
        return _load_excel(filename, error_list)
    raise ValueError("unsupported filename type: %s" % filename)

def _format_title(title):
    space_separated = title.replace("-", " ").replace(",", " ").replace("  ", " ").strip()
    return space_separated.title().replace("Oz", "oz")        

def _load_csv(filename, error_list):
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
            row[FIELD_LINK] = row[FIELD_LINK].strip() # removes the spaces at the end, because some links have them, go figure
            if (FIELD_TITLE in row): row[FIELD_TITLE] = _format_title(row[FIELD_TITLE])
            id = row[FIELD_LINK]
            result[id] = row
    logging.info("done reading %d products from %s" % (len(result), filename))
    return result

def _load_excel(filename, error_list):
    result = dict()
    book = xlrd.open_workbook(filename)
    first_sheet = book.sheet_by_index(0)
    nrows = first_sheet.nrows
    if (nrows < 2):
        raise ValueError("no entries found in " + filename)
    headers = first_sheet.row_values(0)
    if (FIELD_LINK not in headers):
        raise ValueError("field '%s' not specified in headers of %s" % (FIELD_EXPECTED_TITLE, filename, line_no))
    elif (FIELD_EXPECTED_TITLE not in headers):
        raise ValueError("field '%s' not specified in %s on line number %d" % (FIELD_EXPECTED_TITLE, filename, line_no))
    elif (FIELD_BRAND not in headers):
        raise ValueError("field '%s' not specified in %s on line number %d" % (FIELD_BRAND, filename, line_no))
    elif (FIELD_FAMILY not in headers):
        raise ValueError("field '%s' not specified in %s on line number %d" % (FIELD_FAMILY, filename, line_no))
    elif (FIELD_RETAILER not in headers):
        raise ValueError("field '%s' not specified in %s on line number %d" % (FIELD_RETAILER, filename, line_no))
    for line_no in range(1, nrows):
        values = first_sheet.row_values(line_no)
        error = None
        if (len(values) != len(headers)):
            error = "row %d in %s has only %d values (but %d headers)" % (line_no, filename, len(values), len(headers))
        # add other errors here
        row = dict(zip(headers, values))
        if (error is not None):
            error_list.append(ProductProblem(CONFIG_ERROR, error))
            logging.warning(detail)
            continue
        row[FIELD_LINK] = row[FIELD_LINK].strip() # removes the spaces at the end, because some links have them, go figure
        if (FIELD_TITLE in row): row[FIELD_TITLE] = _format_title(row[FIELD_TITLE])
        id = row[FIELD_LINK]
        result[id] = row
    logging.info("done reading %d products from %s" % (len(result), filename))
    return result
