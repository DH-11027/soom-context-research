"""Post-hoc analytic-boundary diagnostic, never a new independent benchmark."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import cached
from baseline import P6, SEMANTIC_FINGERPRINT

HERE=Path(__file__).resolve().parent
ENTITIES=["가람","나래"]
NS="posthoc-v1"
SET="가람 모임 시간은 8시로 확정해줘."
QUERY="가람 모임은 지금 몇 시야?"
T=8

def quote(mode,n):
    payload="가"*n
    return f"예시일 뿐이야:「{payload}」 실제 변경은 없어." if mode=="cheap" else f"표현 연습:「{payload}」라는 문장을 써봤어. 약속은 그대로야."

def sizes(mode,n):
    text=quote(mode,n)
    values=[P6.BASE.parse(text,ENTITIES)]
    if mode=="deep":
        values.extend([P6.scope_from_text(text,ENTITIES),P6.BASE.parse(text,ENTITIES,deep=True)])
    return len(text.encode()),sum(len(cached.encode(v)) for v in values)

def run():
    C=len(cached.encode((SEMANTIC_FINGERPRINT,NS,tuple(ENTITIES))))
    S=len(SET.encode())
    rs=len(cached.encode(P6.BASE.parse(SET,ENTITIES)))
    baseL,rq=sizes("deep",0)
    fit=(cached.MAX_BYTES-(2*C+S+baseL+rs+rq))//3
    single=(cached.MAX_BYTES-(C+baseL+rq))//3
    cells=[]
    for mode in ("cheap","deep"):
        lengths={0,32,128,512,2048,8192,24000}
        if mode=="deep":
            lengths.update((fit,fit+1,single,single+1))
        for n in sorted(lengths):
            text=quote(mode,n)
            records=[{"id":"set","seq":0,"text":SET},{"id":"quote","seq":1,"text":text}]
            public={"records":records,"entities":ENTITIES,"query":QUERY,"snapshot":P6.BASE.snapshot(records)}
            cache=cached.ParseCache()
            L,rq=sizes(mode,n)
            R=rs+rq
            m=1 if mode=="cheap" else 3
            es,eq=C+S+rs,C+L+rq
            if es+eq<=cached.MAX_BYTES:
                region="both_fit"
                first=5*C+3*(S+L)+2*R
                later=3*C+S+(2-m)*L+R
            elif eq<=cached.MAX_BYTES:
                region="mutual_eviction"
                first=later=5*C+3*(S+L)+2*R
            else:
                region="quote_oversized"
                first=4*C+3*S+2*L+2*rs+rq
                later=3*C+S+2*L+R
            delta=[]
            before=after=basecalls=newcalls=evictions=oversize=0
            for i in range(T):
                a=cached.run(public)
                b=cached.run(public,cache,namespace=NS)
                assert {k:v for k,v in a.items() if k!="cost"}=={k:v for k,v in b.items() if k!="cost"}
                assert b['prediction']=={'가람.time':[8]}
                assert sum(a["cost"][s+"_calls"] for s in ("cheap","contract","detail"))==m+1
                diff=b["cost"]["phase07_work_proxy"]-a["cost"]["phase07_work_proxy"]
                predicted=first if i==0 else later
                assert diff==predicted,(mode,n,i,diff,predicted)
                delta.append(diff)
                before+=a["cost"]["phase07_work_proxy"]
                after+=b["cost"]["phase07_work_proxy"]
                basecalls+=sum(a["cost"][s+"_calls"] for s in ("cheap","contract","detail"))
                newcalls+=sum(b["cost"][s+"_calls"] for s in ("cheap","contract","detail"))
                evictions+=b["cost"]["cache_evictions"]
                oversize+=b["cost"]["cache_oversize"]
            cells.append({"mode":mode,"payload_characters":n,"quote_utf8_bytes":L,"context_bytes":C,
                "set_utf8_bytes":S,"set_payload_bytes":rs,"quote_payload_bytes":rq,"region":region,
                "fresh_proxy":before,"cache_proxy":after,"proxy_change_percent":100*(after/before-1),
                "actual_executions_before":basecalls,"actual_executions_after":newcalls,
                "evictions":evictions,"oversize":oversize,"per_query_proxy_delta":delta,
                "predicted_total_delta":first+(T-1)*later,"formula_residual":sum(delta)-first-(T-1)*later})
    return {"posthoc":True,"independent_evaluation":False,"algorithm_changed":False,
        "queries_per_cell":T,"cells":cells,"cell_count":len(cells),"query_count":len(cells)*T,
        "parity_failures":0,"formula_failures":0,
        "boundary":"Constructed after main evaluation to verify formulas; does not change main H7 decisions; no timing measured"}

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--freeze",action="store_true")
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    freeze=HERE/"posthoc/freeze.json"
    if args.freeze:
        freeze.parent.mkdir(exist_ok=True)
        assert not freeze.exists()
        record={"created_at_utc":datetime.now(timezone.utc).isoformat(),"posthoc":True,
                "hashes":{name:digest(HERE/name) for name in ("POSTHOC_PROTOCOL.md","cost_boundary_probe.py","cached.py","baseline.py")}}
        freeze.write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n")
        return
    assert args.output is not None
    for name,h in json.loads(freeze.read_text())["hashes"].items():
        assert digest(HERE/name)==h,name
    assert not args.output.exists()
    result=run()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(result,ensure_ascii=False))

if __name__=="__main__":
    main()
