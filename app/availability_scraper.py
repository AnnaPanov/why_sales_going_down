import problem_finders as pf
import product_problems as pp
import product_config as pc
import datetime as dt
import argparse
import sys
import csv
import pdb


import logging
logging.basicConfig(format='%(asctime)s: %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logging.getLogger().setLevel(logging.INFO)


def local_now_str():
    return dt.datetime.strftime(dt.datetime.now(), "%Y-%m-%d %H:%M:%S")
def utc_now_str():
    return dt.datetime.strftime(dt.datetime.utcnow(), "%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--product_config", type=str, required=True, help="the csv config file with product listings")
    parser.add_argument("--limit", type=int, required=False, default=999999, help="maximum number of rows to output")
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
    logging.info("results will be written into '%s'" % results_file)

    # work!
    rows_written = 0
    with open(results_file, "w") as result_stream:
        results_fields = ['utc_time','local_time','Retailer','Link','Brand','Family','problem_class','problem','problem_detail']
        results_writer = None
        for id in listings:
            logging.info("trying: %s" % id)
            product_definition = listings[id]
            result = dict(product_definition, **{ 'utc_time' : utc_now_str(), 'local_time' : local_now_str()})
            try:
                problems = pf.find_problems(product_definition)
                logging.info("^^^ verdict: %s" % (problems.problem if problems is not None else "product available"))
            except:
                logging.error("failed to load product availability for '%s': %s" % (id, str(sys.exc_info())))
                continue
            if (results_writer is None):
                results_writer = csv.DictWriter(result_stream, fieldnames=results_fields, extrasaction='ignore', lineterminator='\n')
                results_writer.writeheader()
            results_writer.writerow(result if problems is None else dict(result, **problems.__dict__))
            rows_written = rows_written + 1
            if (rows_written > args.limit):
                break
    logging.info("wrote %d data rows into '%s'" % (rows_written, results_file))
