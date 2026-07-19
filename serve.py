#!/usr/bin/env python3
"""
World Cup Final Companion — local server + API proxy.

Serves the PWA and proxies the two data feeds so:
  1. Your BALLDONTLIE key never ships to the browser.
  2. CORS is a non-issue.
  3. A tiny cache protects you from rate limits (BDL trial = 5 req/min).

Usage:
    export BDL_API_KEY="your-key-here"   # optional — app degrades gracefully
    python3 serve.py                      # then open http://localhost:8080
"""
import http.server
import json
import os
import socketserver
import time
import urllib.request
import urllib.error

PORT = int(os.environ.get("PORT", "8080"))
BDL_KEY = os.environ.get("BDL_API_KEY", "").strip()

ESPN_BASE = "https://site.api.espn.com"
BDL_BASE = "https://api.balldontlie.io/fifa/worldcup/v1"

# path-prefix -> (upstream base, extra headers, cache ttl seconds)
ROUTES = {
    "/api/espn/": (ESPN_BASE, {}, 12),
    "/api/bdl/": (BDL_BASE, {"Authorization": BDL_KEY}, 45),
}

_cache = {}  # url -> (expires_at, status, body_bytes)


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        for prefix, (base, headers, ttl) in ROUTES.items():
            if self.path.startswith(prefix):
                if prefix == "/api/bdl/" and not BDL_KEY:
                    return self._send(503, {"error": "BDL_API_KEY not set. Export it and restart serve.py."})
                upstream = base + "/" + self.path[len(prefix):]
                return self._proxy(upstream, headers, ttl)
        if self.path == "/api/health":
            return self._send(200, {"ok": True, "bdl_key_set": bool(BDL_KEY)})
        return super().do_GET()

    def _proxy(self, url, headers, ttl):
        now = time.time()
        hit = _cache.get(url)
        if hit and hit[0] > now:
            return self._raw(hit[1], hit[2], cached=True)
        req = urllib.request.Request(url, headers={"User-Agent": "wc-companion/1.0", **headers})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                body = r.read()
                _cache[url] = (now + ttl, r.status, body)
                return self._raw(r.status, body)
        except urllib.error.HTTPError as e:
            body = e.read()
            # Cache errors briefly too, so a 429 doesn't trigger a retry storm.
            _cache[url] = (now + min(ttl, 30), e.code, body)
            return self._raw(e.code, body)
        except Exception as e:  # network down, DNS, timeout
            if hit:  # serve stale rather than nothing
                return self._raw(hit[1], hit[2], cached=True)
            return self._send(502, {"error": str(e)})

    def _raw(self, status, body, cached=False):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Proxy-Cache", "hit" if cached else "miss")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send(self, status, obj):
        self._raw(status, json.dumps(obj).encode())

    def log_message(self, fmt, *args):
        if "/api/" in (args[0] if args else ""):
            super().log_message(fmt, *args)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print(f"⚽ World Cup Companion → http://localhost:{PORT}")
    print(f"   BDL key: {'set ✓' if BDL_KEY else 'NOT SET — momentum/xG panels will show setup hint'}")
    with socketserver.ThreadingTCPServer(("", PORT), Handler) as httpd:
        httpd.allow_reuse_address = True
        httpd.serve_forever()
