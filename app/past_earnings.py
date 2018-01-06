import datetime
import sys
import re

def get_past_earnings(token, underlying):
    today = (datetime.datetime.now() - datetime.timedelta(hours=18)).date()
    filename = "earnings_" + underlying + "_" + str(today) + ".csv"
    try:
        with open(filename, "r") as f:
            sys.stderr.write('get_past_earnings("' + underlying + '"): file already found ' + str(filename) + '\n')
            return f.read()
    except:
        pass
    import glob
    delete_us = glob.glob("earnings_" + underlying + "_" + str('*') + ".csv")
    if 0 < len(delete_us):
        sys.stderr.write('get_past_earnings("' + underlying + '"): deleting files ' + str(delete_us) + '\n')
        import os
        for f in delete_us:
            os.unlink(f)
    import requests
    response = requests.get('https://www.quandl.com/api/v3/datasets/SF1/' + underlying + '_EBT_ARQ.csv?api_key=' + token, timeout=30)
    sys.stderr.write('get_past_earnings("' + underlying + '"): response status ' + str(response.status_code) + '\n')
    if (response.status_code != 200):
        sys.stderr.write("response: " + response.text.replace('\n', '\\n') + '\n')
        return None
    with open(filename, "w") as f:
        f.write(response.text)
    return response.text

if __name__ == "__main__":
    if (len(sys.argv) != 3):
        sys.exit("usage: past_earnings.py QUANDL_TOKEN SYMBOL\n");
    result = get_past_earnings(sys.argv[1], sys.argv[2])
    if result is not None:
        first_column = '\n'.join(x.split(',')[0] for x in result.split('\n'))
        sys.stdout.write(first_column)
