#!/usr/bin/env python3
"""One-off: dump restriction details into issue #1's body (editing sends no email)."""
import json, os, urllib.request
H = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
     "Accept": "application/json", "Referer": "https://book.thepighotel.com/book/"}
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=30) as r:
        return json.load(r)
B = "https://book.thepighotel.com/v1/stay"
L = []
d = get(f"{B}/availability?hotel_id=PVP&start=2026-12-18&end=2026-12-21&room_qty=1&adults=2")
for o in d.get("offers", []):
    if o.get("available"):
        L.append("FIELD offer: " + json.dumps({k: o.get(k) for k in ("room_type_code","rate_plan_code","room_class","component","restrictions","cancellation_policy","deposit_policy","per_night","sku","room_type_attributes")})[:3000])
ha = d["upstream"]["hotelAvailability"][0]
L.append("closed: " + json.dumps(ha.get("closed")) + " | redemption: " + json.dumps(ha.get("redemption"))[:300])
for rs in ha.get("roomStays", []):
    L.append("roomStay extra keys: " + json.dumps({k: v for k, v in rs.items() if k != "roomRates"})[:1500])
rps = ha.get("ratePlanSet") or {}
L.append("ratePlanSet sample: " + json.dumps(rps)[:2500])
for q in ["adults=2&children=1", "adults=3", "adults=1"]:
    d2 = get(f"{B}/availability?hotel_id=PVP&start=2026-12-18&end=2026-12-21&room_qty=1&{q}")
    L.append(f"{q}: available offers = {[(o.get('room_type_code'), o.get('rate_plan_code'), o.get('amount_before_tax')) for o in d2.get('offers', []) if o.get('available')]}")
for month, n in [("2026-12", 3), ("2026-11", 3)]:
    c = get(f"{B}/rates/calendar?location_id=PVP&month={month}&nights_stay_number={n}&adults=2")
    for x in c.get("days", []):
        if month == "2026-11" and x.get("date") not in ("2026-11-10", "2026-11-11"):
            continue
        if month == "2026-12" and not ("2026-12-16" <= x.get("date", "") <= "2026-12-22"):
            continue
        house = [(r.get("status"), r.get("rate_plan_code"), r.get("room_type_code"), {k: v for k, v in r.items() if k not in ("status", "house", "rate_plan_code", "room_type_code")}) for r in x.get("restrictions", []) if r.get("house") or (r.get("rate_plan_code") == "BAR" and r.get("room_type_code") in (None, "FIELD"))]
        L.append(f"cal n={n} {x.get('date')} lowest={x.get('lowest_rate')} rp={x.get('rate_plan_code')} | {json.dumps(house)[:700]}")
body = "DEBUG DUMP (ignore)\n\n```\n" + "\n".join(L)[:60000] + "\n```"
repo, tok = os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_TOKEN"]
req = urllib.request.Request(f"https://api.github.com/repos/{repo}/issues/1", data=json.dumps({"body": body}).encode(),
                             headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}, method="PATCH")
urllib.request.urlopen(req, timeout=30).read()
print("dumped", len(body))
