import logging
import datetime
from dateutil.relativedelta import relativedelta
import requests
import json
import time
import sys
import csv
import os
import re

host = None
bearer = None
instrument_headers = ('symbol', 'underlying', 'root_symbol', 'expiration_date', 'strike', 'option_type', 'open_interest')
quote_headers = ('time', 'symbol', 'underlying', 'bid', 'ask', 'bidsize', 'asksize')

def http_headers():
    return { "Accept" : "application/json", "Authorization" : "Bearer " + bearer }

def get_instruments(underlying):
    result = list()
    today = datetime.datetime.today()
    in_one_month = today + relativedelta(months=1)
    response = requests.get('https://' + host + '/v1/markets/options/expirations?symbol=' + underlying, timeout=30, headers=http_headers())
    logging.info('get_expirations("' + underlying + '"): response status ' + str(response.status_code))
    if (response.status_code != 200):
        logging.info("response: " + response.text)
        return []
    expirations = json.loads(response.text).get('expirations', None)
    if not expirations:
        return []
    expirations = expirations.get('date', None)
    if not expirations:
        return []
    for expiration in expirations:
        if (expiration > in_one_month.strftime("%Y-%m-%d")):
            continue
        response = requests.get('https://' + host + '/v1/markets/options/chains?symbol=' + underlying + '&expiration=' + expiration, timeout=30, headers=http_headers())
        logging.info('get_chains("' + underlying + '", "' + expiration + '"): response status ' + str(response.status_code))
        if (response.status_code != 200):
            logging.info("response: " + response.text)
            continue
        options = json.loads(response.text).get('options', None)
        if not options:
            continue
        options = options.get('option', None)
        if not options:
            continue
        for option in options:
            symbol = option.get('symbol', None)
            if not symbol:
                continue
            root = re.search('^(\w+)\s*\d{6}[PC]', symbol)
            if root and (root.group(1)[-1] in '123'):
                continue # OCC symbol and its root ends with 1,2 or 3
            option['expiration_date'] = option['expiration_date'].replace('-', '')
            definition = dict((k, option[k]) for k in instrument_headers)
            result.append(definition)
    return result

def get_quotes(underlying, instruments):
    result = list()
    symbols = list()
    symbols.append(underlying)
    max_t = None
    for option in instruments:
        symbols.append(option['symbol'])
    def chunks(l, n):
        for i in range(0, len(l), n): yield l[i:i + n]
    for chunk in chunks(symbols, 200):
        logging.info("loading quotes for " + str(len(chunk)) + " " + underlying + " symbols...")
        r = 'https://' + host + '/v1/markets/quotes?symbols=' + ','.join(chunk)
        response = requests.get(r, timeout=120, headers=http_headers())
        logging.info("status: " + str(response.status_code))
        if (response.status_code == 200):
            quotes = json.loads(response.text).get('quotes', None)
            if not quotes:
                continue
            quotes = quotes.get('quote', None)
            if not quotes:
                continue
            for q in quotes:
                try:
                    t = max(q['bid_date'], q['ask_date'])
                    if (t == 0): continue
                except:
                    logging.error("error in processing get_quotes('" + underlying + "'), part 1: " + str(sys.exc_info()))
                    continue
                try:
                    t = datetime.datetime.fromtimestamp(int(t / 1000))
                    t = t.strftime('%Y%m%dT%H%M%S')
                    q['time'] = t
                    if (not max_t) or (t > max_t): max_t = t
                except:
                    logging.error("error in processing get_quotes('" + underlying + "'), part 2: " + str(sys.exc_info()))
                    continue
                try:                
                    q['underlying'] = underlying
                    quote = dict((k, q[k]) for k in quote_headers)
                    result.append(quote)
                except:
                    logging.error("error in processing get_quotes('" + underlying + "'), part 3: " + str(sys.exc_info()))
                    continue
    logging.info('get_quotes("' + underlying + '"): ' + str(len(result)) + ' quotes @ t=' + str(max_t))
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
        logging.info("sleeping for 4s...")
        time.sleep(4)
    save("instruments.csv", instruments, instrument_headers)

    # 2. keep cycling through all underlyings to get their quotes
    while True:
        for u in underlyings:
            start = time.time()
            try:
                quotes = get_quotes(u, instruments_by_und[u])
                save(u + ".quotes.csv", quotes, quote_headers)
            except:
                logging.error("error: " + str(sys.exc_info()))
            finish = time.time()
            cycle_time = 1800 / len(underlyings)
            sleep_time = cycle_time - (finish - start)
            logging.info("whole thing for " + u + " took " + str(finish - start) + " seconds: sleeping for " + str(sleep_time) + " seconds")
            if (sleep_time > 0):
                time.sleep(sleep_time)

if __name__ == "__main__":
    if (len(sys.argv) < 3):
        sys.exit("usage: tradier.py HOST_AND_BEARER SYMBOL1 [SYMBOL2 [SYMBOL3 ...] ]\n");
    host_and_bearer = sys.argv[1].split(':')
    if len(host_and_bearer) != 2:
        sys.exit("error: HOST_AND_BEARER must have format HOST:TOKEN")
    host = host_and_bearer[0]
    bearer = host_and_bearer[1]
    main(sys.argv[2:])
