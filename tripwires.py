"""Check the registered tripwires against data/metrics.csv + latest.json.
Writes data/alerts.json; exits 2 if any alert fired (workflow opens an issue)."""
import os, json, sys
import pandas as pd
from common import ROOT

def main():
    M = pd.read_csv(os.path.join(ROOT,"data","metrics.csv"), parse_dates=["date"]).set_index("date")
    latest = json.load(open(os.path.join(ROOT,"data","latest.json")))
    alerts, notes = [], []
    v = latest.get("vorticity")
    if v is not None and v > 0.92:
        alerts.append(f"T1 vorticity {v} > 0.92 - migration complete; river dissolving into rotation")
    if len(M) >= 40:
        base = M.eff_dim.rolling(40).max()
        rel = (M.eff_dim/base).iloc[-3:]
        if (rel < 0.75).all():
            alerts.append(f"T2 DISEASE SIGNATURE: eff_dim < 75% of trailing max for 3 consecutive readings "
                          f"(now {latest['eff_dim']}) - the 2007 pattern")
    if len(M) >= 4:
        d_sep = M.separation.iloc[-1] - M.separation.iloc[-4]
        d_dim = M.eff_dim.iloc[-1] - M.eff_dim.iloc[-4]
        if M.separation.iloc[-1] > 1.4 and d_dim < 0:
            alerts.append(f"T3 fusion pattern: separation {M.separation.iloc[-1]:.2f} rising while dimension falls")
    pr = latest.get("pair_ratio")
    if pr and abs(pr - 1.0) > 0.10:
        notes.append(f"356.69 pair ratio at {pr:.3f} (moved >10% from parity)")
    vix = latest.get("vix")
    if vix and vix > 25:
        notes.append(f"VIX {vix} > 25 - fear regime; storms-vs-sunlight rule in effect")
    out = dict(asof=latest["asof"], alerts=alerts, notes=notes)
    with open(os.path.join(ROOT,"data","alerts.json"),"w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))
    return 2 if alerts else 0

if __name__ == "__main__":
    sys.exit(main())
