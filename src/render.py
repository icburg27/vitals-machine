"""Render the monthly vitals card PNG + report draft md into reports/."""
import os, sys, json, datetime as dt
import pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from common import ROOT

def main():
    M = pd.read_csv(os.path.join(ROOT,"data","metrics.csv"), parse_dates=["date"]).set_index("date")
    latest = json.load(open(os.path.join(ROOT,"data","latest.json")))
    alerts = json.load(open(os.path.join(ROOT,"data","alerts.json"))) if os.path.exists(os.path.join(ROOT,"data","alerts.json")) else {"alerts":[],"notes":[]}
    tag = dt.date.today().strftime("%Y-%m")
    plt.rcParams.update({"figure.facecolor":"#0d1117","axes.facecolor":"#0d1117",
        "text.color":"#e6edf3","axes.labelcolor":"#e6edf3","xtick.color":"#8b949e",
        "ytick.color":"#8b949e","axes.edgecolor":"#30363d"})
    fig, axes = plt.subplots(2,2, figsize=(10,7))
    panels = [("eff_dim","Effective dimension","#4FC3F7"),
              ("mean_corr","Mean pairwise rho","#EF5350"),
              ("separation","Cluster separation","#4DB6AC"),
              ("mst_len","MST length","#81C784")]
    for ax,(col,title,c) in zip(axes.flat, panels):
        ax.plot(M.index, M[col], color=c, lw=1.8)
        ax.set_title(f"{title}: {latest.get(col, M[col].iloc[-1]):.2f}" if col in latest else title,
                     fontsize=10, loc="left")
        ax.grid(alpha=0.12); ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    fig.suptitle(f"Formation Vitals - {latest['asof']} - vort {latest['vorticity']} - VIX {latest['vix']} - pair {latest['pair_ratio']}", fontsize=11)
    fig.tight_layout()
    png = os.path.join(ROOT,"reports",f"vitals-{tag}.png")
    fig.savefig(png, dpi=140)
    md = os.path.join(ROOT,"reports",f"vitals-{tag}.md")
    with open(md,"w") as f:
        f.write(f"# Formation Vitals - {tag}\n\n*Data through {latest['asof']}. "
                f"DRAFT - awaiting CEO verdict.*\n\n"
                f"| metric | value |\n|---|---|\n"
                + "".join(f"| {k} | {v} |\n" for k,v in latest.items() if k != "frontier_scores")
                + "\n## Frontier scores\n"
                + "".join(f"- {t}: {s}\n" for t,s in sorted(latest["frontier_scores"].items(), key=lambda x:-x[1]))
                + "\n## Alerts\n" + ("".join(f"- {a}\n" for a in alerts["alerts"]) or "- none\n")
                + "\n## Notes\n" + ("".join(f"- {n}\n" for n in alerts["notes"]) or "- none\n")
                + "\n## VERDICT (CEO writes this)\n\n> _\n")
    print(f"rendered {png} and {md}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
