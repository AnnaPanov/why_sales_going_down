import logging
import datetime
from dateutil.relativedelta import relativedelta
import requests
import json
import time
import sys
import csv
import os

bearer = None
instrument_headers = ('symbol', 'underlying', 'root_symbol', 'expiration_date', 'strike', 'option_type', 'open_interest')
quote_headers = ('time', 'symbol', 'underlying', 'bid', 'ask', 'bidsize', 'asksize')

def http_headers():
    return { "Accept" : "application/json", "Authorization" : "Bearer " + bearer }

def get_instruments(underlying):
    result = list()
    today = datetime.datetime.today()
    in_one_month = today + relativedelta(months=1)
    response = requests.get('https://sandbox.tradier.com/v1/markets/options/expirations?symbol=' + underlying, timeout=30, headers=http_headers())
    logging.info('get_expirations("' + underlying + '"): response status ' + str(response.status_code))
    if (response.status_code != 200):
        logging.info("response: " + response.text)
        return []
    expirations = json.loads(response.text)['expirations']['date']
    for expiration in expirations:
        if (expiration > in_one_month.strftime("%Y-%m-%d")):
            continue
        response = requests.get('https://sandbox.tradier.com/v1/markets/options/chains?symbol=' + underlying + '&expiration=' + expiration, timeout=30, headers=http_headers())
        logging.info('get_chains("' + underlying + '", "' + expiration + '"): response status ' + str(response.status_code))
        if (response.status_code != 200):
            logging.info("response: " + response.text)
            continue
        options = json.loads(response.text)['options']['option']
        for option in options:
            definition = dict((k, option[k]) for k in instrument_headers)
            result.append(definition)
    return result

def get_quotes(underlying, instruments):
    result = list()
    symbols = list()
    symbols.append(underlying)
    for option in instruments:
        symbols.append(option['symbol'])
    def chunks(l, n):
        for i in range(0, len(l), n): yield l[i:i + n]
    for chunk in chunks(symbols, 200):
        logging.info("loading quotes for " + str(len(chunk)) + " " + underlying + " symbols...")
        r = 'https://sandbox.tradier.com/v1/markets/quotes?symbols=' + ','.join(chunk)
        response = requests.get(r, timeout=120, headers=http_headers())
        logging.info("status: " + str(response.status_code))
        if (response.status_code == 200):
            for q in json.loads(response.text)['quotes']['quote']:
                try:
                    t = max(q['bid_date'], q['ask_date'])
                    t = datetime.datetime.fromtimestamp(int(t / 1000))
                    t = t.strftime('%Y%m%dT%H%M%S')
                    q['time'] = t
                    q['underlying'] = underlying
                    quote = dict((k, q[k]) for k in quote_headers)
                    result.append(quote)
                except:
                    logging.error("error: " + str(sys.exc_info()))
    return result

def save(filename, instruments, headers):
    with open(filename + ".tmp", "w") as f:
        writer = csv.DictWriter(f, fieldnames=headers, dialect='unix')
        writer.writeheader()
        for i in instruments:
            writer.writerow(i)
    try:
        os.remove(filename)
    except:
        pass
    os.rename(filename + ".tmp", filename)    

def main(underlyings):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s')
    logging.info("starting...")
    # 1. get the instrument definitions
    instruments = list()
    instruments_by_und = dict()
    for u in set(underlyings):
        logging.info("getting instruments for " + u + " ...")
        try:
            i = get_instruments(u)
        except:
            logging.error("error: " + str(sys.exc_info()))
            continue
        logging.info("got " + str(len(i)) + " instruments")
        instruments_by_und[u] = i
        instruments.extend(i)
        logging.info("sleeping for 10s...")
        time.sleep(10)
    save("instruments.csv", instruments, instrument_headers)

    # 2. keep cycliing through all underlyings to get their quotes
    while True:
        for u in underlyings:
            start = time.time()
            try:
                quotes = get_quotes(u, instruments_by_und[u])
                save(u + ".quotes.csv", quotes, quote_headers)
            except:
                logging.error("error: " + str(sys.exc_info()))
            finish = time.time()
            cycle_time = 600 / len(underlyings)
            sleep_time = cycle_time - (finish - start)
            logging.info("whole thing for " + u + " took " + str(finish - start) + " seconds: sleeping for " + str(sleep_time) + " seconds")
            time.sleep(sleep_time)

if __name__ == "__main__":
    if (len(sys.argv) < 3):
        sys.exit("usage: tradier.py BEARER SYMBOL1 [SYMBOL2 [SYMBOL3 ...] ]\n");
    bearer = sys.argv[1]
    main(sys.argv[2:])
