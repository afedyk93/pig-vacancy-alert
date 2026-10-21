#!/usr/bin/env python3
"""One-off: scan every stay Dec 18-23 for 2 adults + 1 child, dump into issue #1 (edit, no email)."""
import json, os, urllib.request, datetime as dt
H = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
     "Accept": "application/json", "Referer": "https://book.thepighotel.com/book/"}
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=30) as r:
        return json.load(r)
B = "https://book.thepighotel.com/v1/stay"
S, E = dt.date(2026, 12, 18), dt.date(2026, 12, 23)
L = []
for party in ("adults=2&children=1", "adults=2"):
    L.append(f"## {party}")
    days = (E - S).days
    for length in range(days, 0, -1):
        for off in range(0, days - length + 1):
            a = S + dt.timedelta(days=off); b = a + dt.timedelta(days=length)
            d = get(f"{B}/availability?hotel_id=PVP&start={a}&end={b}&room_qty=1&{party}")
            av = [(o.get('room_type_label'), o.get('amount_before_tax'), (o.get('room_type_attributes') or {}).get('maximum_occupancy')) for o in d.get('offers', []) if o.get('available')]
            L.append(f"{a}..{b}: {av if av else 'none'}")
body = "DEBUG DUMP (ignore)\n\n```\n" + "\n".join(L)[:60000] + "\n```"
repo, tok = os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_TOKEN"]
req = urllib.request.Request(f"https://api.github.com/repos/{repo}/issues/1", data=json.dumps({"body": body}).encode(),
                             headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}, method="PATCH")
urllib.request.urlopen(req, timeout=30).read()
