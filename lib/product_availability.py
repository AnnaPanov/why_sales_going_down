import product_config as pc

import pytz
import datetime as dt
import logging
import glob
import csv

FIELD_UTC_TIME = 'utc_time'
FIELD_LOCAL_TIME = 'local_time'
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
AVAILABILITY_FIELDS = [FIELD_UTC_TIME,FIELD_LOCAL_TIME,pc.FIELD_RETAILER,pc.FIELD_LINK,pc.FIELD_BRAND,pc.FIELD_FAMILY,'problem_class','problem','problem_detail']

def load_latest():
    utc = pytz.timezone('UTC')
    file_names = sorted(glob.glob('availability*.csv'))
    if not file_names:
        logging.warn("failed to find any availability observations (files matching availability*.csv)")
        return {}
    result = {}
    file_name = file_names[-1]
    with open(file_name) as csvfile:
        reader = csv.DictReader(csvfile)
        line_no = 0
        for row in reader:
            line_no = line_no + 1
            if pc.FIELD_LINK not in row:
                logging.warn("line %d in '%s' does not define column '%s'" % (line_no, file_name, pc.FIELD_LINK))
                continue
            row[FIELD_LOCAL_TIME] = dt.datetime.strptime(row[FIELD_LOCAL_TIME], TIME_FORMAT)
            row[FIELD_UTC_TIME] = utc.localize(dt.datetime.strptime(row[FIELD_UTC_TIME], TIME_FORMAT))
            id = row[pc.FIELD_LINK]
            result[id] = row
    return result

