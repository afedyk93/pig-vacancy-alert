#!/usr/bin/env python3
"""One-off: check Booking.com availability for a few hotels and write results into issue #3 (edits send no email)."""
import json, os, re, urllib.request, urllib.parse, html
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-GB,en;q=0.9", "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "ignore")
Q = "checkin=2026-12-18&checkout=2026-12-23&no_rooms=1&selected_currency=GBP&lang=en-gb"
parties = {"2 adults + baby": "group_adults=2&group_children=1&age=0", "2 adults": "group_adults=2&group_children=0"}
def slug_for(name):
    h = get(f"https://www.booking.com/searchresults.en-gb.html?ss={urllib.parse.quote(name)}&{Q}&group_adults=2")
    m = re.search(r'https://www\.booking\.com/hotel/gb/([a-z0-9\-]+)\.(?:en-gb\.)?html', h)
    t = re.search(r'data-testid="title"[^>]*>([^<]+)<', h)
    return (m.group(1) if m else None), (html.unescape(t.group(1)) if t else None), len(h)
def check(slug, party):
    h = get(f"https://www.booking.com/hotel/gb/{slug}.en-gb.html?{Q}&{party}")
    table = 'hprt-table' in h
    rooms = [html.unescape(x).strip() for x in re.findall(r'class="hprt-roomtype-icon-link[^"]*"[^>]*>\s*([^<]+?)\s*<', h)]
    prices = re.findall(r'(?:bui-price-display__value|prco-valign-middle-helper)[^>]*>\s*([^<]+?)\s*<', h)
    noav = bool(re.search(r'no availability|unavailable on our site|sold out', h, re.I))
    title = re.search(r'<title>([^<]+)</title>', h)
    return {"has_room_table": table, "rooms": list(dict.fromkeys(rooms))[:8], "prices": prices[:6], "says_unavailable": noav, "page_title": title.group(1)[:80] if title else None, "len": len(h)}
out = {}
hotels = {"The Manor House, Castle Combe": "themnorhousehotel1"}
for name in ["The Painswick hotel Painswick", "Cotswold House Hotel Chipping Campden", "The Old Stocks Inn Stow-on-the-Wold"]:
    try:
        s, t, n = slug_for(name); out[f"search {name}"] = {"slug": s, "first_title": t, "len": n}
        if s: hotels[t or name] = s
    except Exception as e:
        out[f"search {name}"] = str(e)
for hname, slug in hotels.items():
    for pname, p in parties.items():
        try:
            out[f"{hname} [{slug}] {pname}"] = check(slug, p)
        except Exception as e:
            out[f"{hname} [{slug}] {pname}"] = f"ERROR {e}"
body = "PROBE (ignore)\n\n```json\n" + json.dumps(out, indent=1)[:60000] + "\n```"
repo, tok = os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_TOKEN"]
req = urllib.request.Request(f"https://api.github.com/repos/{repo}/issues/3", data=json.dumps({"body": body}).encode(),
                             headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}, method="PATCH")
urllib.request.urlopen(req, timeout=30).read()
print("done")
