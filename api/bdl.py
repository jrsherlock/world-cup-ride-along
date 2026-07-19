"""BALLDONTLIE proxy as a Vercel serverless function.

Mirrors serve.py's /api/bdl/ route: keeps the key server-side, adds the
Authorization header, and lets Vercel's CDN cache responses 45s
(s-maxage) so polling stays under the GOAT trial's 5 req/min.

Reached via vercel.json rewrites:
  /api/bdl/<path>?<qs>  ->  /api/bdl?bdlpath=<path>&<qs>
  /api/health           ->  /api/bdl?health=1
"""
import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qsl, urlencode, urlparse

BDL_BASE = "https://api.balldontlie.io/fifa/worldcup/v1"


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        qs = parse_qsl(urlparse(self.path).query, keep_blank_values=True)
        key = os.environ.get("BDL_API_KEY", "").strip()

        if any(k == "health" for k, _ in qs):
            return self._send(200, {"ok": True, "bdl_key_set": bool(key)}, cache=False)
        if not key:
            return self._send(503, {"error": "BDL_API_KEY not set. Add it in Vercel: Project Settings -> Environment Variables, then redeploy."}, cache=False)

        path = next((v for k, v in qs if k == "bdlpath"), "").lstrip("/")
        params = [(k, v) for k, v in qs if k != "bdlpath"]
        url = f"{BDL_BASE}/{path}" + (f"?{urlencode(params)}" if params else "")
        req = urllib.request.Request(url, headers={"User-Agent": "wc-companion/1.0", "Authorization": key})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                self._raw(r.status, r.read())
        except urllib.error.HTTPError as e:
            self._raw(e.code, e.read(), cache=False)
        except Exception as e:  # network down, DNS, timeout
            self._send(502, {"error": str(e)}, cache=False)

    def _raw(self, status, body, cache=True):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "s-maxage=45, stale-while-revalidate=60" if cache else "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send(self, status, obj, cache=True):
        self._raw(status, json.dumps(obj).encode(), cache=cache)
