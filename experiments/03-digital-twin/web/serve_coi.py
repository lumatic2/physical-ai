"""Local static server with cross-origin isolation headers (COOP/COEP),
required by the MuJoCo WASM module. Run: python serve_coi.py [port]"""
import sys
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8132

class H(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

print(f"serving on http://127.0.0.1:{PORT}  (Ctrl+C to stop)")
ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
