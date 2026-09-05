# Runbook
**Missing days:** source files 404 some days; daily harvest looks back 4 days and
self-heals. Gaps beyond that: run backfill.py (workflow_dispatch or locally).
**Symbol churn:** a watchlist ticker absent >5 consecutive sessions -> note in the
monthly issue; consider substitute (CEO decision; log in tradeoff table).
**Source death:** if harvest adds 0 cells for 5+ consecutive runs, the source may
be gone -> escalate: paid-data-source memo to CEO (Finance seat prices it).
**Metric changes:** ONLY at quarterly review, with public notice; never mid-stream.
**Manual run order:** harvest -> metrics -> tripwires -> grade -> render.
**Autonomy clock:** log founder-minutes on each monthly issue; target < 30.

## Source status at install (Sep 2026)
Primary (MapleFrog) went silent Aug 27, 2026 — the fallback chain (Stooq, Yahoo)
was built in response and carries the load until/unless primary resumes. First
manual run of daily-harvest should fill Aug 27 -> present from fallback; verify
in the run log which source filled it. If primary stays dead 30+ days, remove it
from CHAIN (one line in src/sources.py).
