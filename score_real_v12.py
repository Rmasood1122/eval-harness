import json, re
def norm(s): return re.sub(r"[^a-z0-9]", "", str(s).lower())
def extract_json(text):
    text = re.sub(r"```json", "", text); text = re.sub(r"```", "", text).strip()
    s = None
    for i,ch in enumerate(text):
        if ch in "[{": s=i; break
    if s is None: return None
    for e in range(len(text), s, -1):
        if text[e-1] in "]}":
            try: return json.loads(text[s:e])
            except: continue
    return None

golden = {json.loads(l)["id"]: json.loads(l)["expected"] for l in open("golden/real_cases.jsonl")}
total = 0
for line in open("results/extract_v1_2.jsonl"):
    row = json.loads(line); cid = row["id"]
    got = extract_json(row["raw"]) or []
    exp = golden[cid]
    exp_t = [norm(e["task"]) for e in exp]
    got_t = [norm(g.get("task","")) for g in got]
    # recall: expected tasks found in output (token-overlap, not substring)
    def overlap(a,b):
        wa,wb=set(re.findall(r"[a-z]+",a.lower())),set(re.findall(r"[a-z]+",b.lower()))
        return len(wa&wb)/max(1,len(wa)) > 0.4
    matched = sum(1 for e in [x["task"] for x in exp] if any(overlap(e,g.get("task","")) for g in got))
    invented = max(0, len(got) - matched)
    n = max(1, len(exp))
    score = max(0.0, min(1.0, matched/n - invented/n)) if exp else (1.0 if len(got)==0 else 0.0)
    total += score
    print(f"  {cid:<18} score={score:.2f}  exp={len(exp)} got={len(got)} matched={matched}")
print("-"*50)
print(f"CORRECTED AGGREGATE: {total/len(golden):.3f}")
