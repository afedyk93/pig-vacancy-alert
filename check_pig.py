#!/usr/bin/env python3
"""Vacancy alert for THE PIG-in the Cotswolds.

Checks The Pig's own booking feed and sends a push notification (via the free
ntfy app) when a room opens for the dates below. Uses only the Python standard
library. Run it on a schedule (GitHub Actions workflow included).

Test the notification:   NTFY_TOPIC=your-topic python3 check_pig.py --test
"""
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request

# ---------------------------------------------------------------- settings
HOTEL_ID = "PVP"  # THE PIG-in the Cotswolds
ADULTS = 2
TRIP_START = dt.date(2026, 12, 18)
TRIP_END = dt.date(2026, 12, 23)  # check-out day
# Also alert on single nights, so a stay can be stitched together room by room.
CHECK_SINGLE_NIGHTS = True

FEED = "https://book.thepighotel.com/v1/stay/availability"
BOOK_URL = (f"https://book.thepighotel.com/book/?type=stay&loc={HOTEL_ID}"
            f"&guests={ADULTS}&dates={TRIP_START}_{TRIP_END}")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()
STATE_FILE = os.environ.get("STATE_FILE", ".pig_state.json")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://book.thepighotel.com/book/",
}


def windows():
    """Date ranges to check: the whole trip first, then each night."""
    out = [(TRIP_START, TRIP_END)]
    if CHECK_SINGLE_NIGHTS:
        d = TRIP_START
        while d < TRIP_END:
            out.append((d, d + dt.timedelta(days=1)))
            d += dt.timedelta(days=1)
    return out


def fetch(start, end):
    url = (f"{FEED}?hotel_id={HOTEL_ID}&start={start}&end={end}"
           f"&room_qty=1&adults={ADULTS}")
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def open_rooms(data):
    """Cheapest available price per room type."""
    best = {}
    for o in data.get("offers", []):
        if not o.get("available"):
            continue
        name = o.get("room_type_label") or o.get("room_type_code", "Room")
        price = o.get("amount_before_tax")
        if name not in best or (price is not None and price < best[name]):
            best[name] = price
    return best


def label(start, end):
    nights = (end - start).days
    if nights == 1:
        return f"Night of {start:%a %b %-d}"
    return f"{start:%b %-d} to {end:%b %-d} ({nights} nights)"


def email_via_github_issue(title, body):
    """Opening an issue in your own repo makes GitHub email you (and push via the GitHub app)."""
    token, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    if not (token and repo):
        return
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/issues",
        data=json.dumps({"title": title, "body": f"{body}\n\nBook: {BOOK_URL}"}).encode(),
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=30).read()


def notify(title, body, priority="high"):
    try:
        email_via_github_issue(title, body)
    except urllib.error.URLError as e:
        print("GitHub issue alert failed:", e)
    if not NTFY_TOPIC:
        print("NTFY_TOPIC not set; alert text:\n", title, "\n", body)
        return
    req = urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=body.encode("utf-8"),
        headers={"Title": title, "Priority": priority, "Tags": "pig,bell",
                 "Click": BOOK_URL},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=30).read()


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def main():
    if "--test" in sys.argv:
        notify("Pig alert test", "Notifications are working. Tap to open The Pig's booking page.",
               priority="default")
        print("Test notification sent.")
        return 0

    state = load_state()
    if dt.date.today() >= TRIP_START:
        print("Trip has started; nothing to check.")
        save_state(state)
        return 0

    found = {}
    for start, end in windows():
        try:
            rooms = open_rooms(fetch(start, end))
        except (urllib.error.URLError, ValueError, TimeoutError) as e:
            print(f"Could not check {start} to {end}: {e}")
            save_state(state)
            return 1  # a failed run makes GitHub email you
        if rooms:
            found[label(start, end)] = rooms
        print(f"{label(start, end)}: {', '.join(rooms) if rooms else 'full'}")

    signature = json.dumps(found, sort_keys=True)
    if found and signature != state.get("last_alert"):
        full = label(TRIP_START, TRIP_END)
        title = "The Pig: whole stay is open!" if full in found else "The Pig: a room opened up"
        lines = []
        for when, rooms in found.items():
            cheapest = min(rooms.items(), key=lambda kv: kv[1] if kv[1] is not None else 1e9)
            price = f"£{cheapest[1]:,.0f}" if cheapest[1] is not None else ""
            lines.append(f"{when}: {cheapest[0]} {price}".strip())
        notify(title, "\n".join(lines) + "\nTap to book. Call 0345 225 9494 to stitch nights.")
        print("Alert sent.")
    state["last_alert"] = signature if found else ""
    state["last_check"] = dt.datetime.utcnow().isoformat(timespec="seconds")
    save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
