#!/usr/bin/env python3
"""
Simple HTTP server for the Review Evaluation Console.
Handles saving evaluation data back to the JSON file.
"""

import argparse
import json
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs
import urllib.request
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))


class EvaluationHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler for evaluation data."""

    def do_GET(self):
        """Handle GET requests, including serving the JSON file and PDF proxy."""
        if self.path == '/config':
            # Serve configuration from environment variables
            try:
                config = {
                    'showHarmonizedByDefault': os.environ.get('WEBAPP_SHOW_HARMONIZED_BY_DEFAULT', 'true').lower() == 'true',
                    'defaultHarmonizationModel': os.environ.get('WEBAPP_DEFAULT_HARMONIZATION_MODEL', 'gpt-4o-mini'),
                    'enableModelDropdown': os.environ.get('WEBAPP_ENABLE_MODEL_DROPDOWN', 'true').lower() == 'true',
                    'enableSplitView': os.environ.get('WEBAPP_ENABLE_SPLIT_VIEW', 'true').lower() == 'true'
                }

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(config).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f'Error loading config: {str(e)}'.encode('utf-8'))
        elif self.path == '/reviews/evaluation-data-all-venues.json':
            try:
                file_path = '../reviews/evaluation-data-all-venues.json'
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f'Error loading file: {str(e)}'.encode('utf-8'))
        elif self.path.startswith('/pdfs/'):
            # Serve local PDF files
            try:
                # Get the PDF file path
                pdf_path = '..' + self.path  # Path relative to webapp dir

                if not os.path.exists(pdf_path):
                    self.send_response(404)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b'PDF not found')
                    return

                # Read and serve the PDF
                with open(pdf_path, 'rb') as f:
                    pdf_content = f.read()

                self.send_response(200)
                self.send_header('Content-type', 'application/pdf')
                self.send_header('Content-Length', str(len(pdf_content)))
                self.end_headers()
                self.wfile.write(pdf_content)

            except Exception as e:
                print(f"Error serving local PDF: {str(e)}")
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f'Error serving PDF: {str(e)}'.encode('utf-8'))

        elif self.path.startswith('/pdf-proxy?url='):
            # PDF proxy to bypass CORS (for remote URLs)
            try:
                # Extract URL from query parameter
                query = parse_qs(urlparse(self.path).query)
                pdf_url = query.get('url', [None])[0]

                if not pdf_url:
                    self.send_response(400)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b'Missing URL parameter')
                    return

                # Check if this is a local path being incorrectly sent to proxy
                if not pdf_url.startswith('http://') and not pdf_url.startswith('https://'):
                    print(f"ERROR: Local path sent to proxy: {pdf_url}")
                    self.send_response(400)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(f'Local path should not use proxy: {pdf_url}'.encode('utf-8'))
                    return

                print(f"Fetching PDF from: {pdf_url}")

                # Fetch the PDF
                req = urllib.request.Request(
                    pdf_url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': 'application/pdf,*/*'
                    }
                )
                with urllib.request.urlopen(req, timeout=30) as response:
                    pdf_content = response.read()

                print(f"PDF fetched successfully, size: {len(pdf_content)} bytes")

                # Send PDF to client
                self.send_response(200)
                self.send_header('Content-type', 'application/pdf')
                self.send_header('Content-Length', str(len(pdf_content)))
                self.send_header('Accept-Ranges', 'bytes')
                # Don't add CORS header here - end_headers() already does it
                self.end_headers()
                self.wfile.write(pdf_content)
            except (ConnectionResetError, BrokenPipeError):
                # Client disconnected before PDF was sent (user navigated away)
                # This is normal behavior, just log it quietly
                print(f"Client disconnected during PDF fetch")
            except Exception as e:
                print(f"Error fetching PDF: {str(e)}")
                try:
                    self.send_response(500)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(f'Error fetching PDF: {str(e)}'.encode('utf-8'))
                except (ConnectionResetError, BrokenPipeError):
                    # Client already disconnected, can't send error
                    pass
        else:
            # Serve static files normally
            super().do_GET()

    def do_POST(self):
        """Handle POST requests to save evaluation data."""
        if self.path == '/save_evaluation':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)

            try:
                # Parse JSON data
                data = json.loads(post_data.decode('utf-8'))

                # Save to file
                file_path = '../reviews/evaluation-data-all-venues.json'
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {'success': True, 'message': 'Evaluation saved successfully'}
                self.wfile.write(json.dumps(response).encode('utf-8'))

            except Exception as e:
                # Send error response
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {'error': str(e)}
                self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_HEAD(self):
        """Handle HEAD requests."""
        if self.path.startswith('/pdf-proxy?url='):
            # Respond to HEAD requests for PDF proxy
            self.send_response(200)
            self.send_header('Content-type', 'application/pdf')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
        else:
            super().do_HEAD()

    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS, HEAD')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def end_headers(self):
        """Add CORS headers to all responses."""
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in separate threads."""
    daemon_threads = True
    allow_reuse_address = True

def run_server(port=8090):
    """Run the HTTP server."""
    server_address = ('', port)
    httpd = ThreadedHTTPServer(server_address, EvaluationHandler)
    print(f"""
╔══════════════════════════════════════════════════════════╗
║   Review Evaluation Console - Server Running            ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║   Server: http://localhost:{port}                        ║
║   URL:    http://localhost:{port}/index.html             ║
║                                                          ║
║   Press Ctrl+C to stop the server                       ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
        httpd.server_close()


if __name__ == '__main__':
    # Change to the webapp directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    parser = argparse.ArgumentParser(
        description='Run the Review Evaluation Console server.'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=int(os.environ.get('WEBAPP_PORT', 8090)),
        help='Port to bind the HTTP server (default: 8090 or WEBAPP_PORT env).'
    )
    args = parser.parse_args()

    if not (1 <= args.port <= 65535):
        raise ValueError('Port must be between 1 and 65535.')

    run_server(port=args.port)
