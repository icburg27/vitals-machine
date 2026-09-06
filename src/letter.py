"""Draft The Reading — the weekly letter (and the monthly one on the last Saturday).

The machine drafts; the CEO verdicts. This script only writes a DRAFT:
  letters/drafts/YYYY-MM-DD.md   (markdown, with a VERDICT placeholder)
  letters/drafts/YYYY-MM-DD.png  (the constellation, this week)
The weekly-letter workflow opens an issue labeled `reading` carrying the draft.
A comment on that issue beginning with VERDICT: (from the repo owner) publishes it — see publish.py.
Nothing here sends anything.
"""
import os, sys, json, argparse, datetime as dt
import numpy as np, pandas as pd, yaml
from common import ROOT, load_watchlist, load_panel, last_saturday

RAW = "https://raw.githubusercontent.com/icburg27/vitals-machine/main/"
SITE = "https://icburg27.github.io/market-dimensions/"
WIN = 60
SECTOR_COLORS = {"Tech": "#c98500", "Financial": "#d55181", "Consumer": "#3987e5",
                 "Energy": "#d95926", "Industrial": "#9085e9", "Health": "#199e70"}
ARMS = {"Feeding ground": ["TSM", "VRT", "AVGO", "ANET", "ETN"], "AI pocket": ["NVDA", "AMD"],
        "Pruned": ["VST", "CEG"], "Plumbing": ["JPM"]}
ENTRY = "2026-08-25"

def read_dim(d):
    if d >= 9: return "wide — differentiated, plenty of room"
    if d >= 7: return "healthy — sectors keep their own neighborhoods"
    if d >= 5: return "narrowing — watch the trend, not the level"
    if d >= 3.5: return "compressed — the 2007 territory"
    return "a huddle — the market moving as one object"

def weather(vix):
    if vix is None: return "unknown"
    return "storm" if vix > 25 else "weather" if vix > 18 else "sunlight"

def clean(panel, core):
    p = panel.copy(); keep = p.index[p[core].isna().sum(axis=1) <= 6]
    return p.loc[keep].ffill(limit=3)

def corr_at(rets, end_idx):
    return rets.iloc[max(0, end_idx - WIN):end_idx].corr()

def movers(rets, core, n=3):
    """Largest week-over-week changes in pairwise 60-day correlation."""
    now = corr_at(rets, len(rets)); prev = corr_at(rets, len(rets) - 5)
    d = (now - prev); rows = []
    for i, a in enumerate(core):
        for b in core[i + 1:]:
            if pd.notna(d.loc[a, b]): rows.append((a, b, float(now.loc[a, b]), float(d.loc[a, b])))
    rows.sort(key=lambda r: r[3])
    return rows[-n:][::-1], rows[:n]

def arms_table(panel):
    if pd.Timestamp(ENTRY) not in panel.index: return "_entry row not in panel_"
    e, l = panel.loc[ENTRY], panel.iloc[-1]; out = ["| Arm | Names | Paper return since 8/25 |", "|---|---|---|"]
    for arm, names in ARMS.items():
        have = [t for t in names if t in panel.columns and pd.notna(e.get(t)) and pd.notna(l.get(t))]
        if not have: continue
        r = ((l[have] / e[have] - 1) * 100)
        out.append(f"| {arm} | {', '.join(have)} | {r.mean():+.1f}% ({', '.join(f'{t} {x:+.1f}' for t, x in r.items())}) |")
    return "\n".join(out)

def ledger_summary(today):
    preds = yaml.safe_load(open(os.path.join(ROOT, "ledger", "predictions.yml")))
    gpath = os.path.join(ROOT, "ledger", "grades.csv")
    grades = pd.read_csv(gpath) if os.path.exists(gpath) else pd.DataFrame(columns=["id", "date", "grade", "evidence"])
    soon = []
    for p in preds:
        due = str(p.get("due"))
        try:
            dd = dt.date.fromisoformat(due)
            if 0 <= (dd - today).days <= 45: soon.append(f"{p['id']} due {due}")
        except ValueError:
            pass
    final = grades[~grades["id"].str.contains("-status", na=False)]
    return len(preds), len(final), soon

def render_png(rets, core, sectors, dim, date, out_png):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    C = corr_at(rets, len(rets)).values; C = np.nan_to_num(C); np.fill_diagonal(C, 1)
    D = np.sqrt(np.maximum(2 * (1 - C), 0)); n = len(core); J = np.eye(n) - 1 / n
    B = -0.5 * J @ (D ** 2) @ J; w, v = np.linalg.eigh(B); idx = np.argsort(w)[::-1][:2]
    X = v[:, idx] * np.sqrt(np.maximum(w[idx], 0))
    fig = plt.figure(figsize=(8, 8), dpi=110); fig.patch.set_facecolor("#0d0a15")
    ax = fig.add_axes([0.03, 0.03, 0.94, 0.86]); ax.set_facecolor("#0d0a15"); ax.set_xlim(-1.35, 1.35); ax.set_ylim(-1.35, 1.35); ax.axis("off")
    for i in range(n):
        for j in range(i + 1, n):
            r = C[i, j]
            if r > 0.35: ax.plot([X[i, 0], X[j, 0]], [X[i, 1], X[j, 1]], color="#e4b84a", alpha=0.08 + 0.5 * (r - 0.35) / 0.65, lw=0.6 + 1.6 * (r - 0.35) / 0.65)
    ax.add_patch(plt.Circle((0, 0), 0.105 * dim, fill=False, ls=(0, (3, 5)), ec="#a78bfa", alpha=0.4))
    for (x, y), t in zip(X, core):
        c = SECTOR_COLORS.get(sectors[t], "#e4b84a")
        ax.scatter([x], [y], s=300, color=c, alpha=0.18, edgecolors="none"); ax.scatter([x], [y], s=55, color=c, edgecolors="#0d0a15", linewidths=1.2)
        ax.text(x, y + 0.08, t, color="#f2eefa", ha="center", fontsize=8, fontweight="bold")
    fig.text(0.05, 0.94, "MARKET DIMENSIONS · THE READING", color="#e4b84a", fontsize=10, fontweight="bold")
    fig.text(0.05, 0.905, f"Effective dimension {dim:.2f} · data through {date} · 60-day window, core-20", color="#c9c1dc", fontsize=9.5)
    fig.savefig(out_png, facecolor=fig.get_facecolor()); plt.close(fig)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--kind", choices=["auto", "weekly", "monthly"], default="auto")
    ap.add_argument("--date", default=None); a = ap.parse_args()
    today = dt.date.fromisoformat(a.date) if a.date else dt.date.today()
    kind = a.kind if a.kind != "auto" else ("monthly" if today == last_saturday(today) else "weekly")
    w, sectors, core, _ = load_watchlist(); panel = clean(load_panel(), core)
    rets = np.log(panel[core] / panel[core].shift(1)).dropna(how="all")
    M = pd.read_csv(os.path.join(ROOT, "data", "metrics.csv"), parse_dates=["date"]).set_index("date")
    latest = json.load(open(os.path.join(ROOT, "data", "latest.json")))
    alerts = json.load(open(os.path.join(ROOT, "data", "alerts.json"))) if os.path.exists(os.path.join(ROOT, "data", "alerts.json")) else {"alerts": [], "notes": []}
    cur = M.iloc[-1]; prev = M.iloc[-2] if len(M) > 1 else cur
    wk = M[M.index <= M.index[-1] - pd.Timedelta(days=6)]; week_ago = wk.iloc[-1] if len(wk) else prev
    dim, ddim = float(cur.eff_dim), float(cur.eff_dim - week_ago.eff_dim)
    vix = latest.get("vix"); vort = latest.get("vorticity")
    tight, loose = movers(rets, core)
    npred, ngraded, soon = ledger_summary(today)
    t2_n = len(M); t2_arm = "armed" if t2_n >= 40 else f"arming — {t2_n}/40 readings of history; cannot fire before ~late Oct 2026"
    os.makedirs(os.path.join(ROOT, "letters", "drafts"), exist_ok=True)
    stem = today.isoformat(); md_path = os.path.join(ROOT, "letters", "drafts", f"{stem}.md"); png_path = md_path[:-3] + ".png"
    render_png(rets, core, sectors, dim, latest["asof"], png_path)
    title = f"The Reading — {today.strftime('%B %-d, %Y')}" + (" — the monthly physical" if kind == "monthly" else "")
    lines = [f"# {title}", "",
             f"*Data through {latest['asof']}. Conditions: **{weather(vix)}** (VIX {vix}). Paper experiment; research and education, not investment advice.*", "",
             "## In one breath", "",
             f"Effective dimension **{dim:.2f}** ({ddim:+.2f} on the week) — {read_dim(dim)}. Mean correlation {latest['mean_corr']:.3f}; separation {latest['separation']:.3f}; vorticity {vort if vort is not None else '—'} ({'migration still underway' if vort is not None and vort < 0.92 else 'migration complete / rotation' if vort is not None else 'not computed'}).", "",
             f"![The constellation, data through {latest['asof']}]({RAW}letters/drafts/{stem}.png)", "",
             "## Movers — who drifted toward whom", "",
             "Largest week-over-week changes in 60-day pairwise correlation:", "",
             *[f"- **{a}–{b}** tightened: ρ {r:.2f} ({d:+.2f})" for a, b, r, d in tight],
             *[f"- **{a}–{b}** loosened: ρ {r:.2f} ({d:+.2f})" for a, b, r, d in loose], "",
             "## Tripwires", "",
             *( [f"- ⚠ {x}" for x in alerts.get("alerts", [])] or ["- None fired."] ),
             f"- T1 vorticity > 0.92: armed (now {vort}).", f"- T2 disease signature: {t2_arm}.", f"- T3 fusion: armed (separation {latest['separation']:.2f}).",
             *[f"- note: {x}" for x in alerts.get("notes", [])], "",
             "## The paper experiment", "", "**Pretend dollars, no real positions.** Since entry on 2026-08-25:", "", arms_table(panel), "",
             f"356.69 pair (AVGO/JPM): **{latest['pair_ratio']:.4f}** ({(latest['pair_ratio'] - 1) * 100:+.2f}% vs parity) — PAIR-1 says it rises in sunlight.", "",
             "## Ledger", "",
             f"{npred} registered claims, {ngraded} final grades. " + (f"Coming due: {'; '.join(soon)}." if soon else "Nothing comes due in the next 45 days."), "",
             f"Grades are append-only. [Read the ledger]({SITE}ledger/) · [source]({RAW.replace('raw.githubusercontent.com', 'github.com').replace('/main/', '')})", ""]
    if kind == "monthly":
        tag = today.strftime("%Y-%m"); rp = os.path.join(ROOT, "reports", f"vitals-{tag}.md")
        lines += ["## The monthly physical", "", f"![Vitals card]({RAW}reports/vitals-{tag}.png)", "",
                  "Frontier scores (correlation to the AI pocket minus correlation to the body):", "",
                  *[f"- {t}: {s}" for t, s in sorted(latest.get("frontier_scores", {}).items(), key=lambda x: -x[1])], "",
                  (open(rp).read().split("## VERDICT")[0] if os.path.exists(rp) else "_monthly report not found in reports/_"), ""]
    lines += ["## VERDICT", "", "_The CEO writes this. Reply on the issue with a comment beginning `VERDICT:` and the letter publishes with that text here._", "",
              "---", "", f"*Market Dimensions is research and education, not investment advice. The portfolio above is a paper experiment. Operated under the AI Formation Governance Standard by The AI Governance Company — self-governed in public, not third-party certified.* [Unsubscribe]({{{{ unsubscribe_url }}}})", ""]
    open(md_path, "w").write("\n".join(lines))
    meta = dict(kind=kind, date=stem, title=title, draft=f"letters/drafts/{stem}.md", png=f"letters/drafts/{stem}.png", asof=latest["asof"])
    json.dump(meta, open(md_path[:-3] + ".json", "w"), indent=1)
    print(json.dumps(meta)); return 0

if __name__ == "__main__":
    sys.exit(main())
