#!/usr/bin/env python3
"""Локальный сервер: раздаёт приложение и берёт живое расписание из API Яндекс.Расписаний.
Ключ читается из переменной YANDEX_RASP_KEY или из файла .env рядом с этим файлом (в git не попадает).
Запуск: python3 app/server.py  ->  http://localhost:8000
"""
import json, os, re, sys, time, threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from pathlib import Path

HERE = Path(__file__).parent
API = os.environ.get("YANDEX_API_BASE", "https://api.rasp.yandex.net/v3.0")
CITY = {"nsk": os.environ.get("CODE_NSK", "c65"), "brn": os.environ.get("CODE_BRN", "c197")}  # коды городов Яндекса
TYPES = {"bus": "bus", "train": "train", "suburban": "suburban", "plane": "plane"}
TTL = 600
_cache, _lock = {}, threading.Lock()

def load_env():
    f = HERE / ".env"
    if f.exists():
        for line in f.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"\''))

def call(path, **params):
    key = os.environ.get("YANDEX_RASP_KEY")
    if not key:
        raise PermissionError("no_key")
    params.update(apikey=key, format="json", lang="ru_RU")
    url = f"{API}/{path}/?{urlencode(params)}"
    with _lock:
        hit = _cache.get(url)
        if hit and time.time() - hit[0] < TTL:
            return hit[1]
    with urlopen(Request(url, headers={"User-Agent": "nsk-brn-app"}), timeout=20) as r:
        data = json.load(r)
    with _lock:
        _cache[url] = (time.time(), data)
    return data

def hhmm(s):
    m = re.search(r"(\d{2}):(\d{2})", s or "")
    return f"{m.group(1)}:{m.group(2)}" if m else None

def price_of(seg):
    best = None
    for p in ((seg.get("tickets_info") or {}).get("places") or []):
        pr = p.get("price") or {}
        if pr.get("whole") is not None and (best is None or pr["whole"] < best):
            best = pr["whole"]
    return best

def trips(direction, date):
    a, b = ("nsk", "brn") if direction == "nsk-brn" else ("brn", "nsk")
    out, offset = [], 0
    while True:
        d = call("search", **{"from": CITY[a], "to": CITY[b], "date": date, "limit": 100, "offset": offset,
                              "transport_types": "bus,train,suburban,plane"})
        segs = d.get("segments") or []
        for s in segs:
            if s.get("has_transfers"):
                continue
            th = s.get("thread") or {}
            tt = th.get("transport_type")
            if tt not in TYPES:
                continue
            dep = hhmm(s.get("departure"))
            if not dep:
                continue
            sub = (th.get("transport_subtype") or {}).get("title")
            out.append({
                "type": TYPES[tt], "dir": direction, "dep": dep, "arr": hhmm(s.get("arrival")),
                "dur": round((s.get("duration") or 0) / 60), "price": price_of(s),
                "carrier": (th.get("carrier") or {}).get("title") or "Перевозчик не указан",
                "vehicle": " · ".join(x for x in [sub, th.get("number"), th.get("title")] if x),
                "uid": th.get("uid"), "from": (s.get("from") or {}).get("title"), "to": (s.get("to") or {}).get("title"),
                "date": date,
            })
        offset += 100
        total = (d.get("pagination") or {}).get("total", 0)
        if offset >= total or not segs:
            break
    out.sort(key=lambda t: t["dep"])
    return out

def stops(uid, date):
    d = call("thread", uid=uid, date=date)
    res = []
    for s in d.get("stops") or []:
        t = hhmm(s.get("departure")) or hhmm(s.get("arrival"))
        res.append({"t": t, "name": (s.get("station") or {}).get("title")})
    return res

class H(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        u = urlparse(self.path); q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path in ("/", "/index.html"):
                body = (HERE / "index.html").read_bytes()
                self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            elif u.path == "/api/trips":
                if q.get("dir") not in ("nsk-brn", "brn-nsk") or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", q.get("date", "")):
                    return self._json(400, {"error": "bad_params"})
                self._json(200, {"trips": trips(q["dir"], q["date"])})
            elif u.path == "/api/stops":
                if not re.fullmatch(r"[\w.:|-]+", q.get("uid", "")) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", q.get("date", "")):
                    return self._json(400, {"error": "bad_params"})
                self._json(200, {"stops": stops(q["uid"], q["date"])})
            else:
                self._json(404, {"error": "not_found"})
        except PermissionError:
            self._json(503, {"error": "no_key"})
        except HTTPError as e:
            self._json(502, {"error": "upstream", "status": e.code})
        except (URLError, TimeoutError) as e:
            self._json(502, {"error": "network", "detail": str(e)})
    def log_message(self, *a): pass

if __name__ == "__main__":
    load_env()
    port = int(os.environ.get("PORT", "8000"))
    print(("Ключ найден." if os.environ.get("YANDEX_RASP_KEY") else "ВНИМАНИЕ: нет YANDEX_RASP_KEY, будут демо-данные.") + f" Открой http://localhost:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
