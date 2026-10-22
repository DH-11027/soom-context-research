"""Root-authored development only. No holdout imports."""
from copy import deepcopy
from baseline import P6

def event(kind, entity=None, value=None, source=None):
    return P6.BASE.event(kind, (entity, "time") if entity else None, value,
        source=(source, "time") if source else None)

def step(texts, query="가람 모임은 지금 몇 시야?", entities=("가람", "나래"), namespace="v1"):
    records = [{"id": f"r{i}", "seq": i, "text": text} for i, text in enumerate(texts)]
    public = {"records": records, "entities": list(entities), "query": query, "snapshot": P6.BASE.snapshot(records)}
    return {"step_id": "development", "parser_namespace": namespace, "public": public,
            "gold_applicable": False, "expected_integrity": "valid", "gold": [],
            "question_contract": {"supported": P6.BASE.parse_query(query, list(entities)) is not None,
                                  "required_fields": sorted(P6.BASE.parse_query(query, list(entities)) or [])}}

def build():
    initial = ["가람 모임 시간은 8시로 확정해줘.", "나래 모임 시간은 9시로 확정해줘."]
    deep = initial + ["가람 약속, 최종 시각은 11시로 적어둘게.", "참고로 남기는 감상이야. 오늘 하늘빛이 참 맑았어."]
    repeated = [step(deep, q) for _ in range(3) for q in ("가람 모임은 지금 몇 시야?", "두 모임의 현재 시간을 알려줘.")]
    changes = [step(initial), step([initial[0].replace("8시", "18시"), initial[1]]),
               step(initial + ["가람 모임 시간을 2시간 뒤로 옮겨줘."]),
               step(list(reversed(initial)))]
    scope = [step(initial + ["가람 모임 장소만 다시 정해줘."], q) for q in
             ("가람 모임은 지금 몇 시야?", "가람 모임의 시간과 장소를 알려줘.")]
    unique = [step([f"가람 모임 시간은 {n}시로 확정해줘."]) for n in range(9)]
    invalid = step(deep)
    invalid["public"]["snapshot"]["digest"] = "0" * 64
    invalid["expected_integrity"] = "invalid"
    guards = [step(deep), invalid, step(deep), step(deep, "캘린더에 실제 반영됐어?"), step(deep, namespace="v2")]
    return [{"id": f"dev-{name}", "family": name, "split": "development", "steps": rows}
            for name, rows in (("repeated", repeated), ("edited", changes), ("scoped", scope), ("unique", unique), ("guards", guards))]
