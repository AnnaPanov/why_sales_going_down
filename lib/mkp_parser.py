import re
import os
import csv
import logging
import calendar
import parsedatetime
import time

import xlrd
from xlrd.sheet import ctype_text   

class MkpDataSheet:
    def __init__(self, filename, sheetname):
        import datetime
        self.data = list()
        self.filename = filename.split('/')[-1].split('\\')[-1]
        self.sheetname = sheetname
        self.retailer = sheetname
        self.year = datetime.datetime.fromtimestamp(os.stat(filename).st_ctime).year
        logging.warn("trying to get month name from '" + filename + "' ...")
        month_name = filename.split('/')[-1].split('\\')[-1].split('-')[-1].split('.')[-2].split(' ')[-3].strip()
        logging.warn("got month name: '" + month_name + "' ...")
        month_map = {v: k for k,v in enumerate(calendar.month_name)}
        self.month_num = month_map.get(month_name, -1)
        if (self.month_num == -1): raise ValueError("month '" + month_name + "' does not exist")
        self.week_num = filename.split('/')[-1].split('\\')[-1].split('-')[-1].split('.')[-2].split(' ')[-1].strip()
        logging.warn("got week number: '" + self.week_num + "' ...")
        self.week_num = int(self.week_num)
        self.door_type = None
        self.asof = None
        self.asof_year = None
        self.asof_month = None
        self.asof_weeknum = None
        self.col2period = dict()
        self.col2valuetype = dict()
        self.category2values_buffer = list()

    def eow_date(self, week_number):
        from datetime import date, timedelta
        single_date = date(self.year, self.month_num, 1)
        end_date = date(self.year, self.month_num + 2, 1) if self.month_num < 11 else date(self.year + 1, self.month_num - 10, 1)
        saturday_count = 0
        while (single_date < end_date):
            if single_date.weekday() == 5: saturday_count = saturday_count + 1
            if saturday_count == week_number: return single_date
            single_date = single_date + timedelta(days=1)
        raise ValueError("cannot find Week %d in month %d of %d", week_number, self.month_num, self.year)
    
    def row_type(self, row):
        for index, cell in enumerate(row):
            if (index == 1) and (cell.value.strip().upper() == "B&M ONLY" or cell.value.strip().upper() == "ONLINE ONLY"):
                return 'period headers'
        for cell in row:
            if 'TY' == str(cell.value).upper(): return 'value headers'
        for cell in row:
            if cell.ctype == xlrd.XL_CELL_NUMBER: return 'numbers'
        return 'unknown'

    def parse_row(self, row):
        current_row_type = self.row_type(row)
        if current_row_type == 'period headers':
            self.parse_period_headers(row)
        elif current_row_type == 'value headers':
            self.parse_value_headers(row)
        elif current_row_type == 'numbers':
            self.parse_numbers(row)

    def parse_period_headers(self, row):
        self.flush_category2values('others')
        logging.warning("parsing period headers from sheet %s ..." % self.retailer)
        self.col2period = dict()
        last_period = None
        for index, cell in enumerate(row):
            header = cell.value.strip().lower()
            if (index == 1):
                if (header.upper() == "B&M ONLY"):
                    self.door_type = "BRICK & MORTAR"
                if (header.upper() == "ONLINE ONLY"):
                    self.door_type = "INTERNET"
            if header and header.startswith("week"):
                if header.split(" ")[-1] == str(self.week_num):
                    last_period = header
                else: last_period = None
            if last_period:
                self.col2period[index] = last_period
        if 0 == len(self.col2period):
            logging.warning("WARNING: no suitable period headers found for %s" % self.retailer)
        else:
            logging.warning("found period headers for retailer %s" % self.retailer)
            self.asof = self.eow_date(self.week_num)
            try:
                self.asof_year = self.asof.year
                self.asof_month = str(self.asof.year) + "_" + str(self.asof.month)
                self.asof_weeknum = str(self.asof.year) + "_" + self.asof.strftime('%U')
            except:
                pass            
            logging.warning("for retailer %s we have a real week number %d, which means %s" % (self.retailer, self.week_num, str(self.asof)))

    def parse_value_headers(self, row):
        self.col2valuetype = dict()
        for index, cell in enumerate(row):
            if index not in self.col2period: continue
            if cell.value:
                valueheader = cell.value.strip()
                if valueheader in ("TY", "LY", "Plan", "Rank TY", "Rank LY"):
                    self.col2valuetype[index] = valueheader

    def parse_numbers(self, row):
        if not self.door_type:
            return # door type is not set for this row
        category = ""
        row_values = dict()
        for index, cell in enumerate(row):
            if index == 1:
                category = cell.value
                if category.endswith("TTL") or category.endswith("otal:"):
                    return # this is a subtotal of previous values, ignore it
                elif category.startswith("Total "):
                    brand = ' '.join(category.split(' ')[1:])
                    self.flush_category2values(brand)
                    break
                else:
                    row_values['product'] = category
                continue
            if index not in self.col2valuetype:
                continue
            row_values[self.col2valuetype[index]] = cell.value
        if 0 != len(row_values):
            self.category2values_buffer.append(row_values)

    def flush_category2values(self, brand):
        for entry in self.category2values_buffer:
            entry['brand'] = brand if brand != 'others' else entry.get('product', '')
            entry['retailer'] = self.retailer
            entry['door_type'] = self.door_type
            entry['now'] = self.asof
            entry['now_year'] = self.asof_year
            entry['now_month'] = self.asof_month
            entry['now_weeknum'] = self.asof_weeknum
            entry['source_file'] = self.filename
            entry['source_worksheet'] = self.sheetname
            self.data.append(entry)
        if (0 != self.category2values_buffer):
            logging.warning("got %d more entries for '%s' @ '%s'" % (len(self.category2values_buffer), str(brand), str(self.retailer)))
        self.category2values_buffer = list()


def read(filename):
    result = list()

    logging.info("opening %s in MKP format" % filename)
    book = xlrd.open_workbook(filename)
    sheet_names = book.sheet_names()
    for name in sheet_names:
        if ("Recap" in name): continue
        sheet = book.sheet_by_name(name)
        sheet_data = MkpDataSheet(filename, name)
        for row_idx in range(0, sheet.nrows):
            row = sheet.row(row_idx)
            sheet_data.parse_row(row)
        sheet_data.flush_category2values('others')
        contains_macys_as_product = False
        for entry in sheet_data.data:
            if ('product' in entry) and ('macy' in entry['product'].lower()):
                contains_macys_as_product = True
        if not contains_macys_as_product:
            result.extend(sheet_data.data)
    return result


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
    convert_all("Audited*.xlsx", "_mkp_plaindata.csv")
