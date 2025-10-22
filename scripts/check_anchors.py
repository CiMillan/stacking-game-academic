import re, unicodedata, sys, pathlib
p=pathlib.Path("README.md")
if not p.exists(): sys.exit("README.md not found")
txt=p.read_text(encoding="utf-8")

heads=[]
for line in txt.splitlines():
    m=re.match(r'^(#{1,6})\s*(.+?)\s*$', line)
    if m: heads.append((len(m.group(1)), m.group(2)))

def anchor(s):
    s=unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode("ascii").lower()
    s=re.sub(r'[^a-z0-9 -]','',s)
    s=re.sub(r'\s+','-',s)
    s=re.sub(r'-{2,}','-',s).strip('-')
    return s

seen={}
anchors=[]
for lvl,text in heads:
    base=anchor(text); suf=''
    if base in seen: seen[base]+=1; suf=f"-{seen[base]-1}"
    else: seen[base]=1
    anchors.append((lvl,text,f"{base}{suf}"))

print("=== Headings → Anchors ===")
for lvl,text,a in anchors:
    print(f"{'#'*lvl} {text}  ->  #{a}")

expected=[
 ("§4.1 Data Inputs","41-data-inputs"),
 ("§4.3 Reward Baseline","43-reward-baseline"),
 ("§5.1 Concentration (HHI)","51-concentration-hhi"),
 ("§5.2 Participation-adjusted Concentration","52-participation-adjusted-concentration"),
 ("§5.3 Size–Flow Elasticity of Delegations","53-sizeflow-elasticity-of-delegations"),
 ("§5.4 LST-Adjusted Stake Shares","54-lst-adjusted-stake-shares"),
 ("§5.5 Diversity — Client Mix & Geo/ASN Entropy","55-diversity-client-mix-geoasn-entropy"),
 ("§5.6 Diversity — DVT Cluster Effects","56-diversity-dvt-cluster-effects"),
]
have={a for _,_,a in anchors}
print("\n=== Quick-link verification ===")
for label,exp in expected:
    ok=exp in have
    status="✅ found" if ok else "❗missing"
    hint=""
    if not ok:
        prefix=exp.split('-')[0]+"-"
        cands=sorted(a for a in have if a.startswith(prefix))
        if cands: hint=f"  candidates: {', '.join(cands[:3])}"
    print(f"{status}: {label} -> #{exp}{hint}")
