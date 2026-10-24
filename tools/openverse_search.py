#!/usr/bin/env python3
"""Search + download free CC-licensed images and audio from Openverse (openverse.org).

Defaults to licenses that allow commercial use AND modification, so the
files are safe to cut into reels. Every download gets a .json sidecar and a
line in ATTRIBUTION.md (paste the credit into the caption when the license
is not CC0 / PDM).

Examples:
  python3 openverse_search.py audio "cinematic boom" --category sfx -n 5 --download
  python3 openverse_search.py audio "clock ticking" --category sfx --max-sec 10 --download
  python3 openverse_search.py image "stock market screen" --orientation tall --download
  python3 openverse_search.py image "trader desk" --cc0      # no credit needed

Auth (optional, only for higher rate limits): set OPENVERSE_CLIENT_ID and
OPENVERSE_CLIENT_SECRET (register once with --register NAME EMAIL).
"""
import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request

API = "https://api.openverse.org/v1"
UA = "fahee-reels-openverse/1.0"


def _req(url, data=None, headers=None):
    h = {"User-Agent": UA, "Accept": "application/json"}
    h.update(headers or {})
    if data is not None:
        data = urllib.parse.urlencode(data).encode()
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h), timeout=120) as r:
        return json.load(r)


def _token():
    cid, secret = os.environ.get("OPENVERSE_CLIENT_ID"), os.environ.get("OPENVERSE_CLIENT_SECRET")
    if not (cid and secret):
        return {}
    tok = _req(f"{API}/auth_tokens/token/", data={
        "grant_type": "client_credentials", "client_id": cid, "client_secret": secret})
    return {"Authorization": f"Bearer {tok['access_token']}"}


def register(name, email):
    body = json.dumps({"name": name, "description": "Reel media search", "email": email}).encode()
    r = urllib.request.Request(f"{API}/auth_tokens/register/", data=body,
                               headers={"User-Agent": UA, "Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=30) as resp:
        print(json.dumps(json.load(resp), indent=2))
    print("Verify the email Openverse sends, then export OPENVERSE_CLIENT_ID / _SECRET.")


def search(kind, query, n=10, cc0=False, orientation=None, max_sec=None, category=None, page=1):
    params = {"q": query, "page_size": min(max(20 if max_sec else n, 1), 20), "page": page}
    if cc0:
        params["license"] = "cc0,pdm"
    else:
        params["license_type"] = "commercial,modification"
    if kind == "image":
        if orientation:
            params["aspect_ratio"] = orientation  # tall | wide | square
    elif kind == "audio":
        # Freesound items carry no category tag, so "sfx" filters by source instead
        if category == "sfx":
            params["source"] = "freesound"
        elif category:
            params["category"] = category  # music | podcast | ...
    path = "images" if kind == "image" else "audio"
    data = _req(f"{API}/{path}/?{urllib.parse.urlencode(params)}", headers=_token())
    results = data.get("results", [])
    if max_sec and kind == "audio":
        results = [r for r in results if r.get("duration") and r["duration"] <= max_sec * 1000]
    return results[:n]


def credit(r):
    lic = f"CC {r['license'].upper()} {r.get('license_version') or ''}".strip()
    if r["license"] in ("cc0", "pdm"):
        lic = "Public Domain" if r["license"] == "pdm" else "CC0"
    return f"\"{r.get('title') or 'Untitled'}\" by {r.get('creator') or 'unknown'} ({lic})"


def download(r, kind, out):
    os.makedirs(out, exist_ok=True)
    ext = (r.get("filetype") or os.path.splitext(urllib.parse.urlparse(r["url"]).path)[1].lstrip(".")
           or ("jpg" if kind == "image" else "mp3"))
    slug = re.sub(r"[^a-z0-9]+", "-", (r.get("title") or "untitled").lower()).strip("-")[:40]
    base = os.path.join(out, f"{kind}-{slug}-{r['id'][:8]}")
    req = urllib.request.Request(r["url"], headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp, open(f"{base}.{ext}", "wb") as f:
        f.write(resp.read())
    meta = {k: r.get(k) for k in ("id", "title", "creator", "creator_url", "license", "license_version",
                                  "license_url", "foreign_landing_url", "url", "source", "duration")}
    meta["credit"] = credit(r)
    with open(f"{base}.json", "w") as f:
        json.dump(meta, f, indent=2)
    with open(os.path.join(out, "ATTRIBUTION.md"), "a") as f:
        f.write(f"- {os.path.basename(base)}.{ext}: {credit(r)} {r.get('foreign_landing_url', '')}\n")
    return f"{base}.{ext}"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("kind", nargs="?", choices=["image", "audio"])
    p.add_argument("query", nargs="?")
    p.add_argument("-n", type=int, default=10)
    p.add_argument("--page", type=int, default=1)
    p.add_argument("--cc0", action="store_true", help="only CC0 / public domain (no credit needed)")
    p.add_argument("--orientation", choices=["tall", "wide", "square"])
    p.add_argument("--category", help="audio: sfx (Freesound sound effects), music, podcast...")
    p.add_argument("--max-sec", type=float, help="audio: max duration in seconds")
    p.add_argument("--download", action="store_true")
    p.add_argument("--out", default="openverse_media")
    p.add_argument("--json", action="store_true", help="print raw results as JSON")
    p.add_argument("--register", nargs=2, metavar=("NAME", "EMAIL"))
    a = p.parse_args()
    if a.register:
        return register(*a.register)
    if not (a.kind and a.query):
        p.error("kind and query are required")
    res = search(a.kind, a.query, a.n, a.cc0, a.orientation, a.max_sec, a.category, a.page)
    if a.json:
        print(json.dumps(res, indent=2))
    for i, r in enumerate(res, 1):
        dur = f" {r['duration'] / 1000:.1f}s" if r.get("duration") else ""
        print(f"{i:2}. {credit(r)}{dur}\n    {r['url']}")
        if a.download:
            try:
                print(f"    -> {download(r, a.kind, a.out)}")
            except Exception as e:  # some providers block hotlinking; skip
                print(f"    !! download failed: {e}", file=sys.stderr)
    if not res:
        print("No results.")


if __name__ == "__main__":
    main()
