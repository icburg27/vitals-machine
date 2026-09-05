# vitals-machine
The Formation Vitals observatory: a self-running market-geometry instrument.
Daily harvest (GitHub Actions) -> weekly metrics + tripwires -> monthly reading
with a draft report and an issue awaiting the CEO's verdict.

## Install (one time, ~20 minutes, human required)
1. Create a **private** GitHub repo (suggested name: `vitals-machine`) under your account/org.
2. Push these files to it (or upload the zip contents via web UI).
3. Actions tab -> enable workflows.
4. Run **backfill** locally once OR run `daily-harvest` manually a few times after
   seeding: this repo ships with `data/panel.csv` seeded through Sep 2026, so you
   can simply run `weekly-metrics` (workflow_dispatch) to verify, then let the
   crons take over.
5. Watch the repo (Settings -> Notifications): tripwire and monthly issues are your alerts.

## Trains
- daily-harvest: Tue-Sat 12:00 UTC - appends new closes to data/panel.csv
- weekly-metrics: Sat 13:00 UTC - recomputes vitals; opens an issue if a tripwire fires
- monthly-vitals: last Saturday - full reading, prediction-grading pass, card + report
  draft in reports/, issue for CEO verdict

## Governance
Metric definitions change only at quarterly review (comparability is the spine).
Grades in ledger/grades.csv are append-only. The machine drafts; the CEO verdicts.
