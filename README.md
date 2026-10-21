# Pig vacancy alert

Checks THE PIG-in the Cotswolds every 15 minutes for a room on Dec 18 to 23, 2026 (whole stay, plus each night on its own).
When something opens, it opens an issue in this repo, which emails you, and sends an ntfy push if the `NTFY_TOPIC` secret is set.

- Run it now: Actions tab, "Pig vacancy alert", Run workflow.
- Stop it: Actions tab, "Pig vacancy alert", the "..." menu, Disable workflow. It also stops checking on Dec 18 by itself.
- Change dates: edit `TRIP_START` / `TRIP_END` in `check_pig.py`.
