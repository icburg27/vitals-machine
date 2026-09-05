"""Grade due predictions mechanically where possible; emit needs-CEO items for judgment.
Appends to ledger/grades.csv. Grades are append-only."""
import os, sys, json, datetime as dt
import pandas as pd, yaml
from common import ROOT, load_panel, load_watchlist

def main():
    with open(os.path.join(ROOT,"ledger","predictions.yml")) as f:
        preds = yaml.safe_load(f)
    gpath = os.path.join(ROOT,"ledger","grades.csv")
    graded = pd.read_csv(gpath) if os.path.exists(gpath) else pd.DataFrame(columns=["id","date","grade","evidence"])
    panel = load_panel(); w,_,core,_ = load_watchlist()
    latest = json.load(open(os.path.join(ROOT,"data","latest.json")))
    today = dt.date.today().isoformat()
    new = []
    for p in preds:
        if p["id"] in set(graded["id"]): continue
        due = p.get("due","standing")
        if due not in ("standing","conditional") and due > today: continue
        if p["id"] == "PAIR-1":
            new.append(dict(id="PAIR-1-status", date=today, grade="tracking",
                            evidence=f"ratio={latest['pair_ratio']}, dim={latest['eff_dim']}, vort={latest['vorticity']}"))
        elif due <= today and due not in ("standing","conditional"):
            new.append(dict(id=p["id"], date=today, grade="NEEDS-GRADING",
                            evidence="due date reached; run grading analysis"))
    if new:
        graded = pd.concat([graded, pd.DataFrame(new)], ignore_index=True)
        graded.to_csv(gpath, index=False)
    print(f"grading pass: {len(new)} entries appended")
    return 0

if __name__ == "__main__":
    sys.exit(main())
