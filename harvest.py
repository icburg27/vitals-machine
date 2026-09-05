"""Self-healing harvest: fill the panel from the last known date to today,
walking the source chain until the range is covered."""
import sys, datetime as dt
import pandas as pd
from common import load_watchlist, load_panel, save_panel, merge_rows
from sources import CHAIN

def main():
    _,_,_, universe = load_watchlist()
    panel = load_panel()
    today = dt.date.today()
    start = (panel.index.max().date() + dt.timedelta(days=1)) if len(panel) else dt.date(2025,12,1)
    if start > today:
        print("panel already current"); return 0
    print(f"target range: {start} -> {today}")
    total = 0
    for name, fn in CHAIN:
        rows = fn(start, today, universe)
        panel, added = merge_rows(panel, rows)
        total += added
        print(f"source {name}: +{added} cells")
        # stop early if the most recent trading days are now covered
        recent = panel.index.max().date() if len(panel) else start
        if added and (today - recent).days <= 3:
            break
    save_panel(panel)
    print(f"harvest complete: +{total} cells; panel {panel.shape}; "
          f"latest {panel.index.max().date() if len(panel) else '-'}")
    if total == 0:
        print("WARNING: zero cells added — check RUNBOOK 'source death' if this persists")
    return 0

if __name__ == "__main__":
    sys.exit(main())
