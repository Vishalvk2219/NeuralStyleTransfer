"""Static server for the bench page.

Adds the cross-origin isolation headers that multi-threaded WebAssembly needs.
"""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


ThreadingHTTPServer(("", 8000), Handler).serve_forever()
