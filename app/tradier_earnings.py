import datetime
import sys
import re
import csv
import json
import io

host = None
bearer = None

def http_headers():
    return { "Accept" : "application/json", "Authorization" : "Bearer " + bearer }

def get_tradier_earnings(underlying):
    # try to load from a file
    today = (datetime.datetime.now() - datetime.timedelta(hours=18)).date()
    filename = "future_earnings_" + underlying + "_" + str(today) + ".csv"
    try:
        with open(filename, "r") as f:
            sys.stderr.write('get_tradier_earnings("' + underlying + '"): file already found ' + str(filename) + '\n')
            return f.read()
    except:
        pass
    import glob
    delete_us = glob.glob("earnings_" + underlying + "_" + str('*') + ".csv")
    if 0 < len(delete_us):
        sys.stderr.write('get_tradier_earnings("' + underlying + '"): deleting files ' + str(delete_us) + '\n')
        import os
        for f in delete_us:
            os.unlink(f)
    # otherwise, load from the DB
    result = load_future_earnings(underlying)
    if not result: result = ""
    with open(filename, "w") as f:
        f.write(result)
    return result

def load_future_earnings(underlying):
    import requests
    response = requests.get('https://' + host + '/beta/markets/fundamentals/calendars?symbols=' + underlying, timeout=30, headers=http_headers())
    sys.stderr.write('get_tradier_earnings("' + underlying + '"): response status ' + str(response.status_code) + '\n')
    if (response.status_code != 200):
        sys.stderr.write("response: " + response.text + "\n")
        return []
    result = json.loads(response.text)
    try:
        result = result[0]
        result = result['results']
        result = result[0]
        result = result['tables']
        corporate_calendar = result['corporate_calendars']
    except:
        sys.stderr.write(str(sys.exc_info()) + "\n")
        return None
    if len(corporate_calendar) == 0: return None
    headers = set()
    for entry in corporate_calendar:
        for header in entry.keys():
            headers.add(header)
    headers.add("symbol")
    csv_result = io.StringIO()
    writer = csv.DictWriter(csv_result, fieldnames=sorted(headers), dialect="unix")
    writer.writeheader()
    for entry in sorted(corporate_calendar, key=lambda x: x.get("begin_date_time", "")):
        entry["symbol"] = underlying
        writer.writerow(entry)
    return csv_result.getvalue()

if __name__ == "__main__":
    if (len(sys.argv) != 3):
        sys.exit("usage: tradier_earnings.py HOST:BEARER SYMBOL\n");

    host_and_bearer = sys.argv[1].split(':')
    if len(host_and_bearer) != 2:
        sys.exit("error: HOST_AND_BEARER must have format HOST:TOKEN")
    host = host_and_bearer[0]
    bearer = host_and_bearer[1]
    underlying = sys.argv[2]
    
    result = get_tradier_earnings(underlying)
    sys.stdout.write(result)
