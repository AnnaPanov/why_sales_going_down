from http.server import BaseHTTPRequestHandler, HTTPServer
from http import cookies
import urllib.parse as up
import datetime as dt
import traceback
import logging
import pdb

import product_availability_web_page as pa_page
import product_availability as pa
import product_config as pc

class S(BaseHTTPRequestHandler):
    # global variables
    last_time_listings_loaded = dt.datetime.min # never
    listing_appearance = pa.ListingAppearance()
    listing_status = pa.ListingStatus()
    listings = None
    
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def username(self):
        username = None
        if "Cookie" in self.headers:
            c = cookies.SimpleCookie(self.headers["Cookie"])
            if "username" in c: username = c["username"].value
            if username == '': username = None # empty username does not count
        return username

    def do_GET(self):
        try:
            now = dt.datetime.now()
            if (now > S.last_time_listings_loaded + dt.timedelta(minutes=1)):
                print("Re-loading the listing appearances (last time loaded was %s)" % (S.last_time_listings_loaded.strftime("%H:%M:%S")))
                S.last_time_listings_loaded = now
                S.listing_appearance.load_latest()
                S.listing_status.load_latest()
            parsed_path = up.urlparse(self.path)
            if ("/download" in parsed_path.path) and (S.listing_appearance.file_name):
                self.respond_with_file(S.listing_appearance.file_name, "text/csv")
                return
            parsed_query = up.parse_qs(parsed_path.query)
            result = pa_page.availability_report(S.listings, S.listing_appearance, S.listing_status, self.username())
            self._set_headers()
            self.wfile.write(''.join(result).encode('utf-8'))
        except ConnectionAbortedError as e:
            pass # this happens with web browsers, and it's not a problem
        except:
            self._set_headers()
            self.wfile.write(str(sys.exc_info()).encode('utf-8'))
            self.wfile.write(("\n".join([''] + traceback.format_tb(sys.exc_info()[2]))).replace('\n','<br>\n').encode('utf-8'))
            return

    def do_HEAD(self):
        self._set_headers()
        
    def do_POST(self):
        # try to process cookies
        new_cookie_headers = None
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            parsed_query = up.parse_qs(post_data)
            print("post data: " + str(parsed_query))
            redirect_url = parsed_query.get('follow', ['/'])[0]
            if ('logout' in parsed_query) or ('username' in parsed_query):
                new_cookie = cookies.SimpleCookie()
                new_cookie["username"] = "" if ('logout' in parsed_query) else (parsed_query["username"][0])
                new_cookie_headers = [tuple(kvp.split(':')) for kvp in new_cookie.output().split("\r\n")]
                if ('username' in parsed_query):
                    print("%s signed in" % str(parsed_query["username"][0]))
                if ('logout' in parsed_query):
                    print("%s signed out" % str(self.username()))
            if ('deleteId' in parsed_query) and ('deleteForHowLong' in parsed_query):
                S.listing_status.change_status(parsed_query['deleteId'][0], "deleted", parsed_query['deleteForHowLong'][0], self.username())
            if ('reopenId' in parsed_query):
                S.listing_status.change_status(parsed_query['reopenId'][0], "re-opened", "forever", self.username())
        except ConnectionAbortedError as e:
            pass # this happens with web browsers, and it's not a problem
        except:
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(("failed to process post data: " + str(sys.exc_info())).encode('utf-8'))
            return
        # if successful, respond (possibly by setting a new cookie)
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        if new_cookie_headers:
            for (key, value) in new_cookie_headers:
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(('<html><head><meta http-equiv="refresh" content="0;url='\
                              + redirect_url + '"></head></html>').encode('utf-8'))

    def respond_with_file(self, file_name, content_type):
        with open(file_name) as f:
            download_filename = file_name.split('/')[-1].split('\\')[-1]
            self.send_response(200)
            self.send_header('Content-type', content_type)
            self.send_header("Content-Disposition", "attachment; filename=\"" + download_filename +"\"")
            self.end_headers()
            self.wfile.write(f.read().encode('utf-8'))
            f.close()
            return
        
def run(server_class=HTTPServer, handler_class=S, port=80):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print('Starting httpd...')
    httpd.serve_forever()


if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--product_config", type=str, required=True, help="the csv config file with product listings")
    parser.add_argument("--port", type=int, required=False, default=80, help="on which port to listen")
    args = parser.parse_args()

    errors = []
    S.listings = pc.load(args.product_config, errors)
    if (0 < len(errors)):
        for error in errors:
            print(error.detail)
            sys.exit(1)
    print("product config loaded successfully from '%s' (total of %d listings)" % (args.product_config, len(S.listings)))

    args = parser.parse_args()
    run(port=args.port)
