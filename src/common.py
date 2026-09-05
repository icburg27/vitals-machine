import io, os, calendar, datetime as dt
import urllib.request
import pandas as pd, yaml

BASE = "https://raw.githubusercontent.com/MapleFrogStudio/DATA-{y}-{m:02d}/main/{c}-{d}.csv"
CHUNKS = ["amex1","nasdaq1","nasdaq2","nasdaq3","nasdaq4","nasdaq5","nyse1","nyse2","nyse3"]
COLS = ["Datetime","Ticker","AdjClose","Close","High","Low","Open","Volume"]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data", "panel.csv")

def load_watchlist():
    with open(os.path.join(ROOT, "watchlist.yml")) as f:
        w = yaml.safe_load(f)
    sectors = {t: s for s, ts in w["core20"].items() for t in ts}
    core = list(sectors)
    universe = sorted(set(core) | set(w["pocket"]) | set(w["frontier_watch"])
                      | set(w["context"]) | {w["pair"]["a"], w["pair"]["b"]})
    return w, sectors, core, universe

def fetch_tail(url, nbytes=400_000, timeout=30):
    req = urllib.request.Request(url, headers={"Range": f"bytes=-{nbytes}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "ignore")
    except Exception:
        return ""

def eod_rows_for_file(y, m, dstr, tickers):
    """All chunk tails for one filename-date -> last 15:45-16:00 bar per (actual_date, ticker)."""
    pat = set(tickers)
    rows = []
    for c in CHUNKS:
        txt = fetch_tail(BASE.format(y=y, m=m, c=c, d=dstr))
        for line in txt.splitlines():
            parts = line.split(",")
            if len(parts) != 8 or parts[1] not in pat:
                continue
            t = parts[0]
            if " 15:4" in t or " 15:5" in t or " 16:00" in t:
                rows.append(parts)
    if not rows:
        return pd.DataFrame(columns=["date","Ticker","Close"])
    df = pd.DataFrame(rows, columns=COLS)
    df["Datetime"] = pd.to_datetime(df["Datetime"], errors="coerce")
    df = df.dropna(subset=["Datetime"])
    df["date"] = df["Datetime"].dt.date.astype(str)
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
    last = df.sort_values("Datetime").groupby(["date","Ticker"], as_index=False).last()
    return last[["date","Ticker","Close"]]

def load_panel():
    if os.path.exists(PANEL):
        p = pd.read_csv(PANEL, index_col=0, parse_dates=True)
        p.index.name = "date"
        return p
    return pd.DataFrame()

def save_panel(p):
    os.makedirs(os.path.dirname(PANEL), exist_ok=True)
    p.sort_index().to_csv(PANEL)

def merge_rows(panel, rows):
    if rows.empty:
        return panel, 0
    wide = rows.pivot(index="date", columns="Ticker", values="Close")
    wide.index = pd.to_datetime(wide.index)
    added = 0
    for d, r in wide.iterrows():
        for t, v in r.dropna().items():
            have = (d in panel.index) and (t in panel.columns) and pd.notna(panel.at[d, t])
            if not have:
                panel.at[d, t] = v
                added += 1
    return panel.sort_index(), added

def last_saturday(today=None):
    today = today or dt.date.today()
    last_day = calendar.monthrange(today.year, today.month)[1]
    d = dt.date(today.year, today.month, last_day)
    while d.weekday() != 5:
        d -= dt.timedelta(days=1)
    return d
