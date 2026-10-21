# Pig vacancy alert

Checks THE PIG-in the Cotswolds every 15 minutes for Dec 18 to 23, 2026: the whole stay plus every shorter run of nights.

- **Live status** issue: always shows what's open right now (updated quietly each check, no emails).
- **Alert** issues: a new one opens, and GitHub emails you, only when dates open up that weren't open before. The title says WHOLE stay if all five nights open.
- Optional phone push: add a repo secret `NTFY_TOPIC` and subscribe to that topic in the free ntfy app.

Run it now: Actions tab, "Pig vacancy alert", Run workflow.
Stop it: Actions tab, "Pig vacancy alert", "..." menu, Disable workflow. It also stops checking on Dec 18 by itself.
Change dates: edit `TRIP_START` / `TRIP_END` in `check_pig.py`.
