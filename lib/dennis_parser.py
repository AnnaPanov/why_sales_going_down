import re
import csv
import logging
import parsedatetime
import datetime
import time

import xlrd
from xlrd.sheet import ctype_text   

class DennisDataSheet:
    def __init__(self):
        self.data = list()
        self.asof = None
        self.asof_year = None
        self.asof_month = None
        self.asof_weeknum = None
        self.store_panel = None
        self.period_covered = None
        self.current_retailer = None
        self.col2brand = dict()
        self.col2valuetype = dict()
    
    def row_type(self, row):
        for cell in row:
            if cell.ctype == xlrd.XL_CELL_EMPTY: continue # empty cell
            if 'all divisions' in str(cell.value).lower(): return 'brand headers'
        for cell in row:
            if '%chg' == str(cell.value).lower(): return 'value headers'
        for cell in row:
            if cell.ctype == xlrd.XL_CELL_NUMBER: return 'numbers'
        return 'unknown'

    def parse_first_row(self, row):
        for cell in row:
            if (cell.ctype == xlrd.XL_CELL_TEXT):
                self.period_covered = cell.value.strip()
                break

    def parse_row(self, row):
        current_row_type = self.row_type(row)
        if current_row_type == 'brand headers':
            self.parse_brand_headers(row)
        elif current_row_type == 'value headers':
            self.parse_value_headers(row)
        elif current_row_type == 'numbers':
            self.parse_numbers(row)

    def parse_brand_headers(self, row):
        self.col2brand = dict()
        last_brand = None
        first = True
        for index, cell in enumerate(row):
            if first:
                self.asof = cell.value.strip()
                try:
                    calendar = parsedatetime.Calendar()
                    (parsed, success) = calendar.parse(self.asof)
                    if (success):
                        self.asof_year = parsed.tm_year
                        self.asof_month = str(parsed.tm_year) + "_" + str(parsed.tm_mon)
                        self.asof_weeknum = str(parsed.tm_year) + "_" + datetime.date(parsed.tm_year, parsed.tm_mon, parsed.tm_mday).strftime('%U')
                except:
                    pass
                first = False
            elif (cell.ctype == xlrd.XL_CELL_TEXT):
                last_brand = cell.value.strip()
                self.col2brand[index] = last_brand
            else:
                self.col2brand[index] = last_brand

    def parse_value_headers(self, row):
        self.col2valuetype = dict()
        first = True
        for index, cell in enumerate(row):
            if first:
                self.store_panel = cell.value.strip()
                first = False
            else:
                self.col2valuetype[index] = cell.value.strip().upper()

    def parse_numbers(self, row):
        door_type = None
        brands = set()
        ty_by_brand = dict()
        ly_by_brand = dict()
        for index, cell in enumerate(row):
            if index == 0:
                door_type = cell.value.strip()
                if (door_type != "BRICK & MORTAR") and (door_type != "INTERNET"):
                    self.current_retailer = door_type
                    return
                continue
            brand = self.col2brand.get(index, None)
            valuetype = self.col2valuetype.get(index, None)
            if (valuetype is None) or (brand is None): continue
            if valuetype == 'TY':
                ty_by_brand[brand] = cell.value
                brands.add(brand)
            if valuetype == 'LY':
                ly_by_brand[brand] = cell.value
                brands.add(brand)                
        for brand in brands:
            if self.current_retailer.upper().startswith("TOTAL"):
                continue # the decision is to not include totals, to avoid double-counting
            if self.current_retailer.upper() == "ONLINE":
                continue # this is another form of total
            if self.current_retailer.upper() == "RETAIL STORES":
                continue # and this is another form of total
            entry = {
                'retailer' : self.current_retailer,
                'door_type' : door_type,
                'brand' : brand,
                'TY' : ty_by_brand.get(brand, ''),
                'LY' : ly_by_brand.get(brand, ''),
                'now' : self.asof,
                'now_year' : self.asof_year,
                'now_month' : self.asof_month,
                'now_weeknum' : self.asof_weeknum,
                'store_panel' : self.store_panel,
                'period_covered' : self.period_covered,
            }
            self.data.append(entry)


def read(filename):
    logging.info("opening %s in Dennis format" % filename)
    book = xlrd.open_workbook(filename)
    sheet_names = book.sheet_names()

    week_sheet = None
    for name in sheet_names:
        if ("week" in name.lower()) and ("all doors" in name.lower()):
            week_sheet = book.sheet_by_name(name)
            break
    if week_sheet is None:
        logging.warning("garbage in: workbook %s does not have an 'week - all doors' sheet" % filename)
        return None
    num_cols = week_sheet.ncols

    week_sheet_data = DennisDataSheet()
    week_sheet_data.parse_first_row(week_sheet.row(0))
    for row_idx in range(1, week_sheet.nrows):
        row = week_sheet.row(row_idx)
        week_sheet_data.parse_row(row)
    return week_sheet_data.data


def read_all(file_name_pattern):
    result = list()
    import glob
    for filename in glob.glob(file_name_pattern):
        result.extend(read(filename))
    return result

def convert_all(file_name_pattern, result_file_name):
    result = read_all(file_name_pattern)
    if 0 != len(result):
        with open(result_file_name, 'w') as f:
            headers = list(str(h) for h in result[0].keys())
            writer = csv.DictWriter(f, headers, dialect='excel', lineterminator='\n')
            writer.writeheader()
            for row in result:
                writer.writerow(row)

if __name__ == "__main__":
    convert_all("T*.xlsx", "_dennis_plaindata.csv")
