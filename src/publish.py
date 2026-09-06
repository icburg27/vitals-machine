"""Publish a Reading after the CEO's verdict.

Invoked by the publish-reading workflow when the repo owner comments `VERDICT: ...` on an issue labeled `reading`.
  1. Reads the draft named in the issue body (<!-- draft: letters/drafts/YYYY-MM-DD.md -->).
  2. Replaces the VERDICT placeholder with the CEO's text.
  3. Writes letters/final/YYYY-MM-DD.md (+ .json meta) — committed by the workflow.
  4. Sends the letter through Buttondown if BUTTONDOWN_API_KEY is set (status about_to_send); otherwise records "not sent".
The machine never publishes without the verdict; the verdict never edits the machine's numbers.
"""
import os, sys, re, json, argparse, urllib.request, datetime as dt
from common import ROOT

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--issue-body", required=True); ap.add_argument("--comment", required=True)
    ap.add_argument("--author", required=True); ap.add_argument("--issue-number", required=True)
    a = ap.parse_args()
    m = re.search(r"<!--\s*draft:\s*(letters/drafts/[\w.-]+\.md)\s*-->", a.issue_body)
    if not m: print("no draft marker in issue body"); return 1
    draft_rel = m.group(1); draft = os.path.join(ROOT, draft_rel)
    if not os.path.exists(draft): print("draft missing:", draft_rel); return 1
    verdict = re.sub(r"^\s*VERDICT:?\s*", "", a.comment.strip(), flags=re.I).strip()
    if not verdict: print("empty verdict"); return 1
    text = open(draft).read()
    placeholder = re.search(r"## VERDICT\n\n_.*?_\n", text, flags=re.S)
    if not placeholder: print("draft has no VERDICT placeholder"); return 1
    signed = f"## VERDICT\n\n{verdict}\n\n— {a.author}, {dt.date.today().isoformat()}\n"
    final = text[:placeholder.start()] + signed + text[placeholder.end():]
    meta = json.load(open(draft[:-3] + ".json"))
    stem = meta["date"]; outdir = os.path.join(ROOT, "letters", "final"); os.makedirs(outdir, exist_ok=True)
    open(os.path.join(outdir, f"{stem}.md"), "w").write(final)
    meta.update(published=dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"), issue=int(a.issue_number), verdict_by=a.author, final=f"letters/final/{stem}.md")
    # ---- send ----
    key = os.environ.get("BUTTONDOWN_API_KEY", "").strip()
    if key:
        body = final.split("\n", 1)[1].lstrip()  # drop the H1; Buttondown uses subject
        req = urllib.request.Request("https://api.buttondown.com/v1/emails", method="POST",
              data=json.dumps({"subject": meta["title"], "body": body, "status": "about_to_send"}).encode(),
              headers={"Authorization": f"Token {key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                resp = json.loads(r.read().decode()); meta["sent"] = {"id": resp.get("id"), "status": resp.get("status")}
        except urllib.error.HTTPError as e:
            meta["sent"] = {"error": e.code, "detail": e.read().decode()[:500]}
    else:
        meta["sent"] = {"skipped": "BUTTONDOWN_API_KEY not set — letter published to the site only"}
    json.dump(meta, open(os.path.join(outdir, f"{stem}.json"), "w"), indent=1)
    # index for the site
    idx = []
    for f in sorted(os.listdir(outdir)):
        if f.endswith(".json"): idx.append(json.load(open(os.path.join(outdir, f))))
    json.dump(idx, open(os.path.join(outdir, "index.json"), "w"), indent=1)
    print(json.dumps(meta, indent=1)); return 0

if __name__ == "__main__":
    sys.exit(main())
