from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse as up
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
        parsed_path = up.urlparse(self.path)
        parsed_query = up.parse_qs(parsed_path.query)
        self._set_headers()
        report_type = parsed_query.get('report_type')
        if isinstance(report_type, list): report_type = report_type[0]
        result = pa_page.availability_report(availability_data, report_type)
        self.wfile.write(''.join(result).encode('utf-8'))

    def do_HEAD(self):
        self._set_headers()
        
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        self._set_headers()
        self.wfile.write("<html><body><h1>POST!</h1></body></html>".encode('utf-8'))

        
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
