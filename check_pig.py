#!/usr/bin/env python3
"""Vacancy alert for THE PIG-in the Cotswolds.

Every run checks The Pig's own booking feed for every possible stay inside the
trip dates (the whole trip, plus every shorter run of nights, because some
nights carry a minimum stay). It then:
  * keeps one "Live status" issue in this repo updated (editing it sends no email),
  * opens a new alert issue, which GitHub emails you, only when dates open up that
    weren't open on the previous check, and flags it loudly if the whole trip opens,
  * also sends an ntfy push if the NTFY_TOPIC secret is set.
Python standard library only.
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
CHILDREN = 1  # the baby; every room must fit 2 adults + 1 child
TRIP_START = dt.date(2026, 12, 18)
TRIP_END = dt.date(2026, 12, 23)  # check-out day

FEED = "https://book.thepighotel.com/v1/stay/availability"
BOOK_URL = (f"https://book.thepighotel.com/book/?type=stay&loc={HOTEL_ID}"
            f"&guests={ADULTS}&dates={TRIP_START}_{TRIP_END}")
PHONE = "0345 225 9494"
STATUS_TITLE = f"Live status: The Pig, {TRIP_START:%b %-d} to {TRIP_END:%b %-d}"
PARTY = f"{ADULTS} adults + {CHILDREN} child" if CHILDREN else f"{ADULTS} adults"
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()
GH_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GH_REPO = os.environ.get("GITHUB_REPOSITORY", "")
STATE_FILE = os.environ.get("STATE_FILE", ".pig_state.json")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://book.thepighotel.com/book/",
}


def windows():
    """Every contiguous stay inside the trip, longest first."""
    days = (TRIP_END - TRIP_START).days
    out = []
    for length in range(days, 0, -1):
        for offset in range(0, days - length + 1):
            s = TRIP_START + dt.timedelta(days=offset)
            out.append((s, s + dt.timedelta(days=length)))
    return out


def fetch(start, end):
    url = (f"{FEED}?hotel_id={HOTEL_ID}&start={start}&end={end}"
           f"&room_qty=1&adults={ADULTS}&children={CHILDREN}")
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def cheapest_open(data):
    """(room name, price) of the cheapest available offer, or None if full."""
    best = None
    for o in data.get("offers", []):
        if not o.get("available"):
            continue
        price = o.get("amount_before_tax")
        name = o.get("room_type_label") or o.get("room_type_code", "Room")
        if best is None or (price is not None and (best[1] is None or price < best[1])):
            best = (name, price)
    return best


def label(start, end):
    nights = (end - start).days
    if nights == 1:
        return f"Night of {start:%a %b %-d}"
    return f"{start:%a %b %-d} to {end:%a %b %-d} ({nights} nights)"


def line(start, end, room):
    price = f"£{room[1]:,.0f}" if room[1] is not None else ""
    return f"{label(start, end)}: {room[0]} {price}".strip()


# ---------------------------------------------------------------- GitHub + ntfy
def gh(method, path, body=None):
    if not (GH_TOKEN and GH_REPO):
        return None
    req = urllib.request.Request(
        f"https://api.github.com/repos/{GH_REPO}{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {GH_TOKEN}", "Accept": "application/vnd.github+json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def update_status(body):
    """Edit the single Live status issue (edits don't email); create it once if missing."""
    try:
        issues = gh("GET", "/issues?state=open&per_page=100") or []
        mine = [i for i in issues if i.get("title") == STATUS_TITLE]
        if mine:
            gh("PATCH", f"/issues/{mine[0]['number']}", {"body": body})
        elif GH_TOKEN:
            gh("POST", "/issues", {"title": STATUS_TITLE, "body": body})
    except urllib.error.URLError as e:
        print("Status update failed:", e)


def alert(title, body, loud):
    try:
        gh("POST", "/issues", {"title": title, "body": f"{body}\n\nBook: {BOOK_URL}"})
    except urllib.error.URLError as e:
        print("Alert issue failed:", e)
    if NTFY_TOPIC:
        req = urllib.request.Request(
            f"https://ntfy.sh/{NTFY_TOPIC}", data=body.encode("utf-8"), method="POST",
            headers={"Title": title, "Priority": "urgent" if loud else "high",
                     "Tags": "pig,bell", "Click": BOOK_URL})
        urllib.request.urlopen(req, timeout=30).read()
    print("ALERT:", title, "\n" + body)


# ---------------------------------------------------------------- state
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
    state = load_state()
    if dt.date.today() >= TRIP_START:
        print("Trip has started; nothing to check.")
        save_state(state)
        return 0

    found = {}  # (start, end) -> (room, price)
    for start, end in windows():
        try:
            room = cheapest_open(fetch(start, end))
        except (urllib.error.URLError, ValueError, TimeoutError) as e:
            print(f"Could not check {start} to {end}: {e}")
            save_state(state)
            return 1  # a failed run makes GitHub email you
        print(f"{label(start, end)}: {room[0] if room else 'full'}")
        if room:
            found[(start, end)] = room

    now = dt.datetime.now(dt.timezone.utc).strftime("%b %-d, %H:%M UTC")
    whole = (TRIP_START, TRIP_END)
    keys = {f"{s}_{e}" for s, e in found}

    # Live status board (no email)
    if whole in found:
        headline = f"**The whole stay is OPEN for {PARTY}. Book now.**"
    elif found:
        headline = f"Whole stay still full for {PARTY}. These pieces are open:"
    else:
        headline = f"Nothing open for {PARTY} on any of these dates."
    rows = [f"- {line(s, e, r)}" for (s, e), r in found.items()][:20]
    update_status(f"{headline}\n\n" + "\n".join(rows) +
                  f"\n\nSearching for {PARTY}. Last checked {now}. Checks every 15 minutes.\n"
                  f"Book: {BOOK_URL} (set guests to {PARTY})\nPhone: {PHONE} (ask about a cot; they can also split a stay across rooms)")

    # Email only when something opens that wasn't open last time
    if "open" not in state:
        print("First run with this version: recording a baseline, no alert.")
    else:
        newly = [k for k in found if f"{k[0]}_{k[1]}" not in set(state["open"])]
        if newly:
            loud = whole in newly
            title = ("The Pig: your WHOLE stay just opened" if loud
                     else "The Pig: new dates opened up")
            body = "\n".join(line(s, e, found[(s, e)]) for s, e in newly[:12])
            alert(title, body + f"\n\nBook online or call {PHONE}.", loud)

    state["open"] = sorted(keys)
    state["last_check"] = now
    save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
