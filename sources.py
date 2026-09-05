"""Data source adapters with fallback chain. All return DataFrame[date, Ticker, Close].
A: MapleFrogStudio minute-file tails (primary; free; may lapse)
B: Stooq daily CSV endpoint (per-ticker; ~31 req/run)
C: Yahoo Finance via yfinance (batch)
The harvester walks the chain per missing date-range until filled.
"""
import datetime as dt
import urllib.request
import pandas as pd
from common import eod_rows_for_file

def from_maplefrog(start, end, tickers):
    frames = []
    d = start
    while d <= end + dt.timedelta(days=1):   # +1: filename = data date + 1
        if d.weekday() in (1,2,3,4,5):
            r = eod_rows_for_file(d.year, d.month, d.isoformat(), tickers)
            if len(r): frames.append(r)
        d += dt.timedelta(days=1)
    out = pd.concat(frames) if frames else pd.DataFrame(columns=["date","Ticker","Close"])
    return out[(out["date"] >= start.isoformat()) & (out["date"] <= end.isoformat())] if len(out) else out

def from_stooq(start, end, tickers):
    rows = []
    for t in tickers:
        url = (f"https://stooq.com/q/d/l/?s={t.lower()}.us"
               f"&d1={start.strftime('%Y%m%d')}&d2={end.strftime('%Y%m%d')}&i=d")
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                df = pd.read_csv(r)
            if "Close" in df and len(df):
                for _, x in df.iterrows():
                    rows.append((str(x["Date"]), t, float(x["Close"])))
        except Exception:
            continue
    return pd.DataFrame(rows, columns=["date","Ticker","Close"])

def from_yahoo(start, end, tickers):
    try:
        import yfinance as yf
    except ImportError:
        return pd.DataFrame(columns=["date","Ticker","Close"])
    try:
        data = yf.download(tickers, start=start.isoformat(),
                           end=(end + dt.timedelta(days=1)).isoformat(),
                           progress=False, auto_adjust=False)["Close"]
        if isinstance(data, pd.Series):
            data = data.to_frame(tickers[0])
        data = data.dropna(how="all")
        rows = [(d.strftime("%Y-%m-%d"), t, float(v))
                for d, r in data.iterrows() for t, v in r.dropna().items()]
        return pd.DataFrame(rows, columns=["date","Ticker","Close"])
    except Exception:
        return pd.DataFrame(columns=["date","Ticker","Close"])

CHAIN = [("maplefrog", from_maplefrog), ("stooq", from_stooq), ("yahoo", from_yahoo)]
