import os, json, sys, urllib.request
import numpy as np, pandas as pd
from scipy.sparse.csgraph import minimum_spanning_tree
from scipy.cluster.hierarchy import linkage, fcluster
from sklearn.metrics import silhouette_score
from common import ROOT, load_watchlist, load_panel
WIN, STEP = 60, 3
VIX_URL = "https://raw.githubusercontent.com/datasets/finance-vix/main/data/vix-daily.csv"
def clean_panel(panel, core):
 p = panel.copy()
 keep = p.index[p[core].isna().sum(axis=1) <= 6]
 return p.loc[keep].ffill(limit=3)
def eff_dim(C):
 lam = np.clip(np.linalg.eigvalsh(np.nan_to_num((C+C.T)/2, nan=0.0)), 0, None)[::-1]
 return (lam.sum()**2)/max((lam**2).sum(), 1e-12)
def separation(C):
 D = np.sqrt(np.maximum(2*(1-C), 0)); np.fill_diagonal(D, 0)
 Z = linkage(D[np.triu_indices_from(D,1)], method="average")
 best = (-2, None)
 for k in range(2,7):
  lab = fcluster(Z, k, criterion="maxclust")
  if len(set(lab)) < 2: continue
  s = silhouette_score(D, lab, metric="precomputed")
  if s > best[0]: best = (s, lab)
 lab = best[1]
 iu = np.triu_indices_from(D,1); w,b = [],[]
 for i,j in zip(*iu):
  (w if lab[i]==lab[j] else b).append(D[i,j])
 return (np.mean(b)/np.mean(w)) if w and b else np.nan
def sector_shares(px, sectors):
 rets = px.pct_change().fillna(0)
 s = pd.Series(1.0/px.shape[1], index=px.columns)
 out = []
 for t in range(len(px)):
  if t > 0:
   g = s*(1+rets.iloc[t]); s = g/g.sum()
  out.append(s.copy())
 S = pd.DataFrame(out, index=px.index)
 return S.T.groupby(pd.Series(sectors)).sum().T
def vorticity(dS, win=90):
 if len(dS) < win + 2: return np.nan
 X = dS.iloc[-win:]
 n = X.shape[1]; F = np.zeros((n,n))
 a = X.iloc[:-1].reset_index(drop=True); b = X.iloc[1:].reset_index(drop=True)
 for i in range(n):
  for j in range(i+1, n):
   f = a.iloc[:,i].corr(b.iloc[:,j]) - a.iloc[:,j].corr(b.iloc[:,i])
   F[i,j], F[j,i] = f, -f
 phi = F.mean(axis=0); G = phi[None,:]-phi[:,None]; R = F-G
 return float((R**2).sum()/max((F**2).sum(), 1e-12))
def main():
 w, sectors, core, _ = load_watchlist()
 panel = clean_panel(load_panel(), core)
 if len(panel) < WIN + 5:
  print("panel too short; run backfill"); return 1
 rets = np.log(panel[core]/panel[core].shift(1)).dropna()
 rows = []
 for e in range(WIN, len(rets), STEP):
  C = rets.iloc[e-WIN:e].corr().values
  D = np.sqrt(np.maximum(2*(1-C), 0))
  rows.append(dict(date=rets.index[e-1],
      eff_dim=eff_dim(C),
      mean_corr=C[np.triu_indices(len(core),1)].mean(),
      mst_len=minimum_spanning_tree(D).sum(),
      separation=separation(C)))
 M = pd.DataFrame(rows).set_index("date")
 dS = sector_shares(panel[core].dropna(), sectors).diff().dropna()
 M["vorticity"] = np.nan
 M.iloc[-1, M.columns.get_loc("vorticity")] = vorticity(dS)
 r60 = np.log(panel/panel.shift(1)).dropna().iloc[-60:]
 pocket = [t for t in w["pocket"] if t in r60]
 pm = r60[pocket].mean(axis=1)
 fs = {}
 for t in w["frontier_watch"] + pocket:
  if t not in r60: continue
  cp = r60[t].corr(r60[[p for p in pocket if p != t][0]]) if t in pocket else r60[t].corr(pm)
  cb = np.mean([r60[t].corr(r60[b]) for b in core if b != t and b in r60])
  fs[t] = round(float(cp - cb), 3)
 pr = float(panel[w["pair"]["a"]].dropna().iloc[-1] / panel[w["pair"]["b"]].dropna().iloc[-1])
 vix = np.nan
 try:
  with urllib.request.urlopen(VIX_URL, timeout=30) as r:
   v = pd.read_csv(r); vix = float(v["CLOSE"].iloc[-1])
 except Exception:
  pass
 latest = dict(asof=str(M.index[-1].date()),
    eff_dim=round(float(M.eff_dim.iloc[-1]),2),
    mean_corr=round(float(M.mean_corr.iloc[-1]),3),
    separation=round(float(M.separation.iloc[-1]),3),
    vorticity=None if np.isnan(M.vorticity.iloc[-1]) else round(float(M.vorticity.iloc[-1]),3),
    vix=None if np.isnan(vix) else round(vix,2),
    pair_ratio=round(pr,4),
    frontier_scores=fs)
 M.round(4).to_csv(os.path.join(ROOT,"data","metrics.csv"))
 with open(os.path.join(ROOT,"data","latest.json"),"w") as f:
  json.dump(latest, f, indent=2)
 print(json.dumps(latest, indent=2))
 return 0
if __name__ == "__main__":
 sys.exit(main())
