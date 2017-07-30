from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse as up
from http import cookies
import traceback
import pdb

import product_availability_web_page as pa_page
import product_availability as pa

availability_data = pa.load_latest()

class S(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        self._set_headers()
        try:
            parsed_path = up.urlparse(self.path)
            parsed_query = up.parse_qs(parsed_path.query)
            report_type = parsed_query.get('report_type',[''])[0]
            username = None
            if "Cookie" in self.headers:
                c = cookies.SimpleCookie(self.headers["Cookie"])
                if "username" in c: username = c["username"].value
                if username == '': username = None # empty username does not count
            result = pa_page.availability_report(availability_data, report_type, username)
            self.wfile.write(''.join(result).encode('utf-8'))
        except:
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
            redirect_url = parsed_query.get('follow', ['/'])[0]
            if ('logout' in parsed_query) or ('username' in parsed_query):
                new_cookie = cookies.SimpleCookie()
                new_cookie["username"] = "" if ('logout' in parsed_query) else (parsed_query["username"][0])
                new_cookie_headers = [tuple(kvp.split(':')) for kvp in new_cookie.output().split("\r\n")]
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

        
def run(server_class=HTTPServer, handler_class=S, port=80):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print('Starting httpd...')
    httpd.serve_forever()

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2:
        run(port=int(sys.argv[1]))
    else:
        run()
