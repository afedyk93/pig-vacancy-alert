#!/usr/bin/env python3
"""One-off: compact dump of The Pig's booking flags into issue #1's body (editing sends no email)."""
import json, os, urllib.request
H = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
     "Accept": "application/json", "Referer": "https://book.thepighotel.com/book/"}
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=30) as r:
        return json.load(r)
B = "https://book.thepighotel.com/v1/stay"
lines = []
for s, e in [("2027-01-12", "2027-01-13"), ("2027-01-19", "2027-01-21"), ("2026-12-18", "2026-12-21"), ("2026-12-18", "2026-12-19"), ("2026-12-22", "2026-12-23"), ("2026-12-18", "2026-12-23")]:
    d = get(f"{B}/availability?hotel_id=PVP&start={s}&end={e}&room_qty=1&adults=2")
    lines.append(f"## {s} to {e}")
    ups = d.get("upstream", {})
    vals = {}
    for ha in ups.get("hotelAvailability", []):
        lines.append("hotelAvailability keys: " + ", ".join(k for k in ha if k != "roomStays") + " | " + json.dumps({k: v for k, v in ha.items() if k != "roomStays"})[:400])
        for rs in ha.get("roomStays", []):
            for rr in rs.get("roomRates", []):
                key = rr.get("availability")
                vals[key] = vals.get(key, 0) + 1
                if rr.get("ratePlanCode") == "BAR" or not str(key).startswith("Restricted"):
                    lines.append(f"- {rr.get('roomType')} {rr.get('ratePlanCode')} {rr.get('start')}..{rr.get('end')} {key} total={rr.get('total',{}).get('amountBeforeTax')} units={rr.get('numberOfUnits')} suppress={rr.get('suppressRate')}")
    lines.append(f"availability value counts: {vals}")
    av = [(o.get('room_type_code'), o.get('rate_plan_code'), o.get('amount_before_tax')) for o in d.get('offers', []) if o.get('available')]
    lines.append(f"offers marked available: {av}")
    lines.append(f"offer keys: {sorted({k for o in d.get('offers', []) for k in o})}")
    lines.append(f"upstream top keys: {list(ups.keys())}")
    lines.append("")
body = "DEBUG DUMP (ignore)\n\n```\n" + "\n".join(lines)[:60000] + "\n```"
repo, tok = os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_TOKEN"]
req = urllib.request.Request(f"https://api.github.com/repos/{repo}/issues/1", data=json.dumps({"body": body}).encode(),
                             headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}, method="PATCH")
urllib.request.urlopen(req, timeout=30).read()
print("dumped", len(body))
