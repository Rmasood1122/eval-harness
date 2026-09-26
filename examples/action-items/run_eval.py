import argparse, json, os, sys, re, time
from pathlib import Path
try:
    from anthropic import Anthropic
except ImportError:
    print("Run: pip install anthropic", file=sys.stderr); sys.exit(1)

MODEL = "claude-sonnet-4-6"

def load_golden(path):
    cases = []
    with open(path) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line: continue
            cases.append(json.loads(line))
    return cases

def extract_json(text):
    text = re.sub(r"```(json)?", "", text).strip()
    start = None
    for i, ch in enumerate(text):
        if ch in "[{": start = i; break
    if start is None: return None, "no JSON found"
    for end in range(len(text), start, -1):
        if text[end-1] in "]}":
            try: return json.loads(text[start:end]), None
            except json.JSONDecodeError: continue
    return None, "MALFORMED (unparseable JSON)"

def norm(s): return re.sub(r"[^a-z0-9]", "", str(s).lower())

def score_case(expected, got, err):
    r = {"malformed": False, "n_exp": len(expected) if isinstance(expected,list) else 0, "n_got": 0, "invented": 0, "score": 0.0}
    if err or not isinstance(got, list):
        r["malformed"] = True; return r
    r["n_got"] = len(got)
    exp_t = [norm(e.get("task","")) for e in expected]
    got_t = [norm(g.get("task","")) for g in got]
    matched = sum(1 for et in exp_t if any(et and (et in gt or gt in et) for gt in got_t))
    invented = sum(1 for gt in got_t if not any(gt and (gt in et or et in gt) for et in exp_t))
    r["invented"] = invented
    n = max(1, len(exp_t))
    r["score"] = max(0.0, min(1.0, matched/n - invented/n))
    return r

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True); ap.add_argument("--golden", required=True)
    ap.add_argument("--model", default=MODEL); ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Set ANTHROPIC_API_KEY first.", file=sys.stderr); sys.exit(1)
    tmpl = Path(a.prompt).read_text()
    cases = load_golden(a.golden)
    client = Anthropic()
    out = a.out or f"results/{Path(a.prompt).stem}.jsonl"
    rf = open(out, "w")
    scores, malformed = [], 0
    print(f"\nRunning {len(cases)} cases | prompt={a.prompt} | model={a.model}\n" + "-"*66)
    for c in cases:
        filled = tmpl.replace("{input}", c["input"])
        try:
            resp = client.messages.create(model=a.model, max_tokens=2000, messages=[{"role":"user","content":filled}])
            txt = "".join(b.text for b in resp.content if b.type=="text")
        except Exception as e:
            print(f"  {c['id']:<18} API ERROR: {e}"); txt = ""
        obj, err = extract_json(txt)
        sc = score_case(c.get("expected",[]), obj, err)
        scores.append(sc["score"]);  malformed += 1 if sc["malformed"] else 0
        rf.write(json.dumps({"id":c["id"],"raw":txt,"score":sc})+"\n")
        flag = "  <-- MALFORMED" if sc["malformed"] else (f"  <-- INVENTED {sc['invented']}" if sc["invented"] else "")
        print(f"  {c['id']:<18} score={sc['score']:.2f}  exp={sc['n_exp']} got={sc['n_got']}{flag}")
        time.sleep(0.3)
    rf.close()
    print("-"*66)
    print(f"AGGREGATE SCORE: {sum(scores)/len(scores):.3f}   (0=fail, 1=perfect)")
    print(f"MALFORMED OUTPUTS: {malformed}/{len(cases)}")
    print(f"Raw outputs saved to: {out}\n")

if __name__ == "__main__": main()
