import problem_finders as pf
import product_problems as pp
import product_config as pc
import product_availability as pa
import pivot_page

import time
import random
import datetime as dt
import argparse
import csv
import sys
import os

import pdb

import logging

def local_now_str():
    return dt.datetime.strftime(dt.datetime.now(), pa.TIME_FORMAT)
def utc_now_str():
    return dt.datetime.strftime(dt.datetime.utcnow(), pa.TIME_FORMAT)
def unfinished_name(filename):
    return filename + ".unfinished"
def pick_id(n_attempts_by_id, preferred_domain):
    if preferred_domain is not None:
        with_this_domain = [ id for (id, n_attempts) in n_attempts_by_id.items() if (preferred_domain in id) ]
        if 0 < with_this_domain:
            id = random.choice(with_this_domain)
            return (id, n_attempts_by_id[id])
    highest_n_attempts = max(n_attempts for (id, n_attempts) in n_attempts_by_id.items())
    with_highest_n_attempts = [ id for (id, n_attempts) in n_attempts_by_id.items() if (n_attempts == highest_n_attempts) ]
    id = random.choice(with_highest_n_attempts)
    return (id, n_attempts_by_id[id])


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s: %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    logging.getLogger().setLevel(logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("--product_config", type=str, required=True, help="the csv config file with product listings")
    parser.add_argument("--hours", type=float, required=False, default=8.0, help="for how many hours to run (to not overload retailer websites)")
    parser.add_argument("--limit", type=int, required=False, default=999999, help="maximum number of rows to output")
    parser.add_argument("--tor_port", type=int, required=False, default=0, help="port on which to run tor (default=0, don't run)")
    parser.add_argument("--socks_proxy", type=str, required=False, default=None, help="spcks proxy in the format of username:password@host:port")
    args = parser.parse_args()

    # decide on configuration
    errors = []
    listings = pc.load(args.product_config, errors)
    if (0 < len(errors)):
        for error in errors:
            logging.error(error.detail)
            sys.exit(1)
    logging.info("product config loaded successfully from '%s' (total of %d listings)" % (args.product_config, len(listings)))
    results_file = "availability_" + utc_now_str().replace(":", "").replace("-", "").replace(" ", "-") + ".csv"
    pivot_file = results_file + ".html"
    logging.info("results will be written into '%s' and '%s'" % (results_file, pivot_file))
    original_ids = []
    for id in listings:
        original_ids.append(id)
    random.shuffle(original_ids)

    # start the tor
    if (args.tor_port != 0):
        pf.start_tor_process(args.tor_port)
    if (args.socks_proxy is not None):
        logging.info("will be using socks proxy %s" % args.socks_proxy)
        pf._socks_proxy = args.socks_proxy

    # work!
    rows_written = 0
    rows_with_problems = []
    n_items = len(original_ids)
    n_attempts_by_id = dict()
    for id in original_ids:
        n_attempts_by_id[id] = 3 # three attempts for each id
    with open(unfinished_name(results_file), "w") as result_stream:
        results_fields = pa.AVAILABILITY_FIELDS
        results_writer = None
        retry_list = []
        retry_again_list = []
        duration = -1
        preferred_domain = None
        while 0 < len(n_attempts_by_id):
                if (rows_written > args.limit):
                    break
                # 0. pick an id using preferred_domain if necessary
                (id, attempts_left) = pick_id(n_attempts_by_id, preferred_domain)
                if (preferred_domain is None) or (preferred_domain not in id):
                    if (0 < args.hours) and (duration != -1):
                        sleep_seconds = (3000 * args.hours / (1.0 + n_items)) if (attempts_left > 1) else (9000 * args.hours / (1.0 + n_items))
                        logging.info("sleeping for %g seconds, minus %g" % (sleep_seconds, duration))
                        if (sleep_seconds > duration): time.sleep(sleep_seconds - duration)
                n_attempts_by_id.pop(id, None)
                preferred_domain = None
                # 1. try to load this listing
                logging.info("trying: %s" % id)
                product_definition = listings[id]
                result = dict(product_definition, **{ 'utc_time' : utc_now_str(), 'local_time' : local_now_str()})
                start = time.time()
                try:
                    problems = pf.find_problems(product_definition)
                    logging.info("^^^ verdict: %s" % ((problems.problem + " (" + str(problems.problem_detail) + ")") if problems is not None else "product available"))
                except:
                    logging.error("failed to load product availability for '%s': %s" % (id, str(sys.exc_info())))
                    problems = pp.ProductProblem(pp.WEBSCRAPER_ERROR, str(sys.exc_info()))
                # 2. if temporarily failing to load this listing, possibly try again later
                if (0 < attempts_left) and (problems and ((problems.problem == pp.PAGE_NOT_LOADED[0]) or (problems.problem == pp.WEBSCRAPER_ERROR[0]))):
                    logging.error("=> will retry loading this listing later again (%d attempts left)" % attempts_left)
                    n_attempts_by_id[id] = attempts_left
                    continue
                # 3. record the results in any case
                duration = time.time() - start
                if (results_writer is None):
                    results_writer = csv.DictWriter(result_stream, fieldnames=results_fields, extrasaction='ignore', lineterminator='\n')
                    results_writer.writeheader()
                result = result if problems is None else dict(result, **problems.__dict__)
                result = { f:result.get(f, '') for f in results_fields } # only leave the fields we need + use space for blanks
                results_writer.writerow(result)
                if (problems is not None):
                    rows_with_problems.append(result)
                rows_written = rows_written + 1
                if ('macys.com' in id):
                    logging.info("will now retry another listing with macys.com...")
                    preferred_domain = "macys.com"
                    continue
                if ('jcpenney.com' in id):
                    logging.info("will now retry another listing with jcpenney.com...")
                    preferred_domain = "jcpenney.com"
                    continue

    pivot_table_text = pivot_page.generate_pivot_page("Stockout Action Items @ " + local_now_str(), rows_with_problems, ["problem","Brand","Retailer","Link"], [])
    with open(pivot_file, "w") as pivot_stream:
        pivot_stream.write(pivot_table_text)
    os.rename(unfinished_name(results_file), results_file)
    logging.info("wrote %d data rows into '%s' and %d data rows into '%s'" % (rows_written, results_file, len(rows_with_problems), pivot_file))
