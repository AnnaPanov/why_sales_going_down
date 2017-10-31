import re
import os
import csv
import logging
import calendar
import parsedatetime
import logging
import time

import xlrd
from xlrd.sheet import ctype_text   

class WklyPlansSheet:
    def __init__(self, filename, sheetname):
        self.data = list()
        self.sheetname = sheetname
        self.product = sheetname
        import datetime
        self.filename = filename.split('/')[-1].split('\\')[-1]
        year_found = re.search("(20[0-9]{2})", filename)
        if (year_found):
            self.year = int(year_found.groups()[0])
        else:
            self.year = datetime.datetime.fromtimestamp(os.stat(filename).st_ctime).year
        self.retailer = re.sub("[0-9]{1,4}\.[0-9]{1,2}\.[0-9]{1,2}", "", self.filename)
        self.retailer = self.retailer.split('.')[-2].split('-')[-1].strip().upper()
        self.retailer = self.retailer.replace("-REVISED", "").replace("- REVISED", "").replace(" REVISED", "").strip()
        logging.warning("filename '%s' was mapped to retailer '%s'" % (self.filename, self.retailer))
        self.col2doortype = dict()
        self.col2valuetype = dict()

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
            if (str(cell.value).upper() == 'ACTUAL TY'): return 'value headers'
        for index, cell in enumerate(row):
            if ('-AUDITED' in str(cell.value).upper()) or ('- AUDITED' in str(cell.value).upper()): return 'door type headers'
        for cell in row:
            if cell.ctype == xlrd.XL_CELL_NUMBER: return 'numbers'
        return 'unknown'

    def parse_row(self, row):
        current_row_type = self.row_type(row)
        if current_row_type == 'door type headers':
            self.parse_door_type_headers(row)
        elif current_row_type == 'value headers':
            self.parse_value_headers(row)
        elif current_row_type == 'numbers':
            self.parse_numbers(row)

    def parse_door_type_headers(self, row):
        self.col2doortype = dict()
        last_door_type = None
        for index, cell in enumerate(row):
            header = cell.value.strip().upper()
            if header and ("AUDITED" in header):
                last_door_type = header.replace("- AUDITED", "").replace("-AUDITED", "").strip()
                if ("STORE" in header): last_door_type = "STORE"
                if ("BOUTIQUE" in header): last_door_type = "BOUTIQUE"
                if ("OUTLET" in header): last_door_type = "OUTLET"
                if ("DIRECT" in header): last_door_type = "DIRECT"
            if last_door_type is not None:
                self.col2doortype[index] = last_door_type

    def parse_value_headers(self, row):
        self.col2valuetype = dict()
        for index, cell in enumerate(row):
            if cell.value:
                valueheader = cell.value.strip().upper()
                for h in ("WEEK ENDING", "PLAN", "ACTUAL TY", "ACTUAL LY"):
                    if h in valueheader:
                        self.col2valuetype[index] = h
                        break

    def parse_numbers(self, row):
        week_ending = None
        by_door_type = dict()
        for index, cell in enumerate(row):
            if index not in self.col2valuetype:
                continue
            value_type = self.col2valuetype[index]
            if value_type == "WEEK ENDING":
                week_ending = cell.value + ", " + str(self.year) if (cell.ctype == xlrd.XL_CELL_TEXT) else cell.value
                continue
            if index not in self.col2doortype:
                continue
            door_type = self.col2doortype[index]
            if (door_type not in by_door_type) and (week_ending is not None):
                by_door_type[door_type] = {
                    "week_ending" : week_ending,
                    "retailer" : self.retailer,
                    "product" : self.product,
                    "door_type" : door_type,
                    "source_file" : self.filename,
                    "source_sheet" : self.sheetname
                }
            entry = by_door_type[door_type]
            entry[value_type] = cell.value
        for door_type, entry in by_door_type.items():
            self.data.append(entry)


def read(filename):
    result = list()

    if ("Wkly Plans" in filename):
        logging.info("opening %s in 'Wkly Plans' format" % filename)
        book = xlrd.open_workbook(filename)
        sheet_names = book.sheet_names()
        for name in sheet_names:
            if ("TTL" in name) or ("total" in name.lower()) or ("WOMEN" in name.upper()): continue
            sheet = book.sheet_by_name(name)
            sheet_data = WklyPlansSheet(filename, name)
            for row_idx in range(0, sheet.nrows):
                row = sheet.row(row_idx)
                sheet_data.parse_row(row)
            result.extend(sheet_data.data)

    if ("SALES GOALS BY WEEK" in filename):
        pass

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
    convert_all("*Wkly Plans*.xlsx", "_planned_sales_plaindata.csv")
