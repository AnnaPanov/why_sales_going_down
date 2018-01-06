import datetime
import sys
import re

def get_future_earnings(d):
    today = (datetime.datetime.now() - datetime.timedelta(hours=18)).date()
    filename = "future_earnings_" + str(d) + "_" + str(today) + ".csv"
    try:
        with open(filename, "r") as f:
            sys.stderr.write('get_future_earnings("' + str(d) + '"): file already found ' + str(filename) + '\n')
            return f.read()
    except:
        pass
    import glob
    delete_us = glob.glob("future_earnings_" + str(d) + "_" + str('*') + ".csv")
    if 0 < len(delete_us):
        sys.stderr.write('get_future_earnings(): deleting files ' + str(delete_us) + '\n')
        import os
        for f in delete_us:
            os.unlink(f)
    sys.stderr.write('get_future_earnings("' + str(d) + '"): sleeping for 4 seconds in order to throttle requests...\n')
    import time
    time.sleep(4)
    import requests
    response = requests.get('https://finance.yahoo.com/calendar/earnings?day=' + d, timeout=30)
    sys.stderr.write('get_future_earnings("' + str(d) + '"): response status ' + str(response.status_code) + '\n')
    if (response.status_code != 200):
        sys.stderr.write("response: " + response.text.replace('\n', '\\n')[:200] + '\n')
        return None
    for table in response.text.split('<table'):
        table = table.split('</table')[0]
        if '>Earnings Call Time<' in table:
            rows = [r.split('</tr>')[0] for r in table.split('<tr')[1:]]
            rows = ['>'.join(r.split('>')[1:]) for r in rows]
            rows = [r.replace('\n','') for r in rows]
            result = '\n'.join(rows)
            sys.stderr.write('get_future_earnings("' + str(d) + '"): got ' + str(len(rows)) + ' worth of results\n')
            with open(filename, "w") as f:
                f.write(result)
            return result
    # otherwise, got no results
    sys.stderr.write('get_future_earnings("' + str(d) + '"): got NO results\n')
    return None

_extractor = re.compile(">([^<>]+)<")
def extract(cell):
    found = _extractor.search(cell)
    return found.group(1) if found else ''
def extract_all(cells):
    return [extract(x) for x in cells]

if __name__ == "__main__":
    if (len(sys.argv) != 2):
        sys.exit("usage: future_earnings.py DATE\n");
    result = get_future_earnings(sys.argv[1])
    if result is not None:
        rows = result.split('\n')
        headers = [extract(cell) for cell in rows[0].split("</th>")[:-1]]
        records = [extract_all(row.split("</td>")[:-1]) for row in rows[1:]]
        sys.stdout.write(','.join(headers) + '\n')
        for record in records:
            sys.stdout.write(','.join(record) + '\n')
