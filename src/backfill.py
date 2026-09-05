"""Full rebuild of the panel from 2025-12-01 to today. Run once at install, or to self-heal."""
import sys, datetime as dt
from concurrent.futures import ThreadPoolExecutor
from common import load_watchlist, eod_rows_for_file, load_panel, save_panel, merge_rows

START = dt.date(2025, 12, 1)

def main():
    _,_,_, universe = load_watchlist()
    panel = load_panel()
    days = []
    d = START
    while d <= dt.date.today():
        if d.weekday() in (1,2,3,4,5):   # Tue-Sat filenames hold Mon-Fri data
            days.append(d)
        d += dt.timedelta(days=1)
    def one(day):
        return eod_rows_for_file(day.year, day.month, day.isoformat(), universe)
    total = 0
    with ThreadPoolExecutor(max_workers=10) as ex:
        for rows in ex.map(one, days):
            panel, added = merge_rows(panel, rows)
            total += added
    save_panel(panel)
    print(f"backfill complete: +{total} cells; panel {panel.shape} "
          f"{panel.index.min().date() if len(panel) else '-'} -> {panel.index.max().date() if len(panel) else '-'}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
