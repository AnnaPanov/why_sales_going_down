import product_config as pc

import pytz
import datetime as dt
import logging
import glob
import csv
import os
import re

FIELD_UTC_TIME = 'utc_time'
FIELD_LOCAL_TIME = 'local_time'
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
AVAILABILITY_FIELDS = [FIELD_UTC_TIME,FIELD_LOCAL_TIME,pc.FIELD_RETAILER,pc.FIELD_LINK,pc.FIELD_BRAND,pc.FIELD_FAMILY,'problem_class','problem','problem_detail']

# how does a product listing appear on the web?
class ListingAppearance:
    def __init__(self):
        self.values = {}
        
    def load_latest(self):
        utc = pytz.timezone('UTC')
        file_names = sorted(glob.glob('availability*.csv'))
        if not file_names:
            logging.warn("failed to find any availability observations (files matching availability*.csv)")
            return {}
        result = {}
        self.file_name = file_names[-1]
        with open(self.file_name) as csvfile:
            reader = csv.DictReader(csvfile)
            line_no = 0
            for row in reader:
                line_no = line_no + 1
                if pc.FIELD_LINK not in row:
                    logging.warn("line %d in '%s' does not define column '%s'" % (line_no, self.file_name, pc.FIELD_LINK))
                    continue
                row[FIELD_LOCAL_TIME] = dt.datetime.strptime(row[FIELD_LOCAL_TIME], TIME_FORMAT)
                row[FIELD_UTC_TIME] = utc.localize(dt.datetime.strptime(row[FIELD_UTC_TIME], TIME_FORMAT))
                id = row[pc.FIELD_LINK]
                result[id] = row
        self.values = result


LISTING_STATUS_FIELDS = ['utc_time', 'local_time', 'username', 'id', 'status', 'expiration']

# what did we do to a listing
class ListingStatus:
    def __init__(self):
        self.values = {}


    def load_latest(self):
        utc = pytz.timezone('UTC')
        file_names = sorted(glob.glob('listing_status*.csv'))
        if not file_names:
            logging.warn("failed to find any listing status data (files matching listing_status*.csv)")
            return {}
        result = {}
        for file_name in file_names:
            try:
                with open(file_name) as csvfile:
                    reader = csv.DictReader(csvfile)
                    line_no = 0
                    for row in reader:
                        line_no = line_no + 1
                        if 'id' not in row:
                            logging.warn("line %d in '%s' does not define column '%s'" % (line_no, file_name, 'id'))
                            continue
                        row['utc_time'] = dt.datetime.strptime(row['utc_time'], TIME_FORMAT)
                        row['local_time'] = dt.datetime.strptime(row['local_time'], TIME_FORMAT)
                        row['expiration'] = dt.datetime.strptime(row['expiration'], TIME_FORMAT)
                        result[row['id']] = row
            except:
                print("in load_latest: " + "\n".join([''] + traceback.format_tb(sys.exc_info()[2])))
        self.values = result


    def change_status(self, id, status, expiration, username):
        if not username:
            username = "Anonymous User"
        # figure out the file name
        def unfinished_name(filename):
            return filename + ".unfinished"
        utc_time = dt.datetime.utcnow()
        local_time = dt.datetime.now()
        results_file = "listing_status_" + utc_time.strftime("%Y%m%d-%H%M%S%f") + ".csv"
        # figure out the expiration time for this status
        if not isinstance(expiration, dt.datetime):
            for_x_days_from_now = re.match("for (\d+) days", str(expiration))
            if for_x_days_from_now:
                print('expiration "%s" parsed successfully' % str(expiration))
                expiration = utc_time + dt.timedelta(days=int(for_x_days_from_now.groups()[0]))
            elif (expiration == "forever"):
                print('expiration "%s" parsed successfully' % str(expiration))
                expiration = dt.datetime.max
            elif (expiration == "now"):
                print('expiration "%s" parsed successfully' % str(expiration))
                expiration = utc_time
            else:
                raise ValueError("expiration '%s' is not valid" % str(expiration))
        # create a new status entry
        entry = { 'utc_time' : utc_time, 'local_time' : local_time, 'username' : username, 'id' : id, 'status' : status, 'expiration' : expiration }
        self.values[id] = entry
        # write it all to the disk
        with open(unfinished_name(results_file), "w") as result_stream:
            results_writer = csv.DictWriter(result_stream, fieldnames=LISTING_STATUS_FIELDS, extrasaction='ignore', lineterminator='\n')
            results_writer.writeheader()
            write_me = dict(entry)
            write_me['utc_time'] = entry['utc_time'].strftime(TIME_FORMAT)
            write_me['local_time'] = entry['local_time'].strftime(TIME_FORMAT)
            write_me['expiration'] = entry['expiration'].strftime(TIME_FORMAT)
            results_writer.writerow(write_me)
        os.rename(unfinished_name(results_file), results_file)
        logging.info("finished writing into '" + results_file + "'")

    def modify_appearance(self, product_config, listing_appearance, utc_time):
        result = ListingAppearance()
        for id in product_config:
            row = listing_appearance.values.get(id)
            if not row:
                continue
            # add the title
            title = product_config[id].get(pc.FIELD_TITLE, None)
            if (title):
                row[pc.FIELD_TITLE] = title
            status_known = self.values.get(row[pc.FIELD_LINK], None)
            if (not status_known):
                result.values[id] = row
                continue # no modifications required
            elif (status_known['status'] == 'deleted') and (dt.timedelta(hours=1) > (dt.datetime.max - status_known['expiration'])):
                row = dict(row)
                row['problem_class'] = 'deleted'
                result.values[id] = row
                continue # modified to appear in a wastebasket
            elif (status_known['expiration'] > utc_time):
                row = dict(row)
                if (status_known['status'] == 'deleted'):
                    row['addressed'] = "%s: %s said that issue had been already addressed" % (status_known['local_time'].strftime('%b %d, %I:%M %p'), status_known['username'])
                elif (status_known['status'] == 're-opened'):
                    row['re-opened'] = "%s: %s re-opened the issue back" % (status_known['local_time'].strftime('%b %d, %I:%M %p'), status_known['username'])
                result.values[id] = row
                continue # modified to provide more information
        return result
