#!/usr/bin/env python3
"""One-off: dump The Pig's raw booking data into issue #1's body (editing sends no email)."""
import json, os, urllib.request
H = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
     "Accept": "application/json", "Referer": "https://book.thepighotel.com/book/"}
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=30) as r:
        return json.load(r)
B = "https://book.thepighotel.com/v1/stay"
out = {}
for s, e in [("2026-12-18", "2026-12-21"), ("2026-12-18", "2026-12-19"), ("2026-12-22", "2026-12-23")]:
    d = get(f"{B}/availability?hotel_id=PVP&start={s}&end={e}&room_qty=1&adults=2")
    offers = d.get("offers", [])
    out[f"avail {s}_{e}"] = {
        "top_keys": [k for k in d if k != "offers"],
        "top": {k: v for k, v in d.items() if k != "offers"},
        "offer_keys": sorted({k for o in offers for k in o}),
        "n_offers": len(offers),
        "available_true": [{k: v for k, v in o.items() if k not in ("long_description", "short_description", "images")} for o in offers if o.get("available")][:6],
        "sample_unavailable": [{k: v for k, v in o.items() if k not in ("long_description", "short_description", "images")} for o in offers if not o.get("available")][:2],
    }
for n in (1, 3):
    c = get(f"{B}/rates/calendar?location_id=PVP&month=2026-12&nights_stay_number={n}&adults=2")
    days = [x for x in c.get("days", []) if x.get("date", "") >= "2026-12-17" and x.get("date", "") <= "2026-12-23"]
    for x in days:
        x["restrictions"] = [r for r in x.get("restrictions", []) if r.get("house") or r.get("rate_plan_code") in ("BAR", None) or "room_type_code" in r][:40]
    out[f"calendar nights={n}"] = {"top": {k: v for k, v in c.items() if k != "days"}, "days": days}
body = "DEBUG DUMP (ignore)\n\n```json\n" + json.dumps(out, indent=1)[:60000] + "\n```"
repo, tok = os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_TOKEN"]
req = urllib.request.Request(f"https://api.github.com/repos/{repo}/issues/1", data=json.dumps({"body": body}).encode(),
                             headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}, method="PATCH")
urllib.request.urlopen(req, timeout=30).read()
print("dumped", len(body))
