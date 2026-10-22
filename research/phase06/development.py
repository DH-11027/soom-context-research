"""Development-only minimal cases. Never described as held-out evaluation."""
from __future__ import annotations

import scoped


ENTITIES = ["은하", "새벽"]


def event(kind, target=None, value=None, source=None, targets=None):
    return {"kind": kind, "target": target, "value": value, "source": source, "targets": targets or []}


def make_case(name, extra):
    a, b = ENTITIES
    stream = [(f"{a} 모임 시간은 8시로 확정해줘.", event("set", (a, "time"), 8)),
              (f"{b} 모임 시간은 11시로 확정해줘.", event("set", (b, "time"), 11)),
              (f"{a} 모임 장소는 도서관로 확정해줘.", event("set", (a, "place"), "도서관")),
              (f"{b} 모임 장소는 공원로 확정해줘.", event("set", (b, "place"), "공원"))] + extra
    records = [{"seq": i, "id": f"dev-{name}-{i}", "text": text} for i, (text, _) in enumerate(stream)]
    return {"id": name, "family": name, "split": "development",
            "public": {"records": records, "entities": ENTITIES, "snapshot": scoped.BASE.snapshot(records)},
            "queries": [f"{a} 모임은 지금 몇 시야?", f"{a} 모임의 시간과 장소를 알려줘.",
                        f"{b} 모임은 지금 몇 시야?", "두 모임의 현재 시간을 알려줘."],
            "gold": [ev for _, ev in stream]}


def build():
    a, b = ENTITIES
    place = (f"{a} 모임 장소는 카페로 바꿔줘.", event("set", (a, "place"), "카페"))
    time = (f"{a} 모임 시간은 16시로 재합의했어. 장소는 그대로야.", event("set", (a, "time"), 16))
    reset = (f"{a} 모임 시간은 12시로 확정해줘.", event("set", (a, "time"), 12))
    copy_time = (f"{b} 모임 시간은 {a} 모임 시간과 같게 맞춰줘.", event("copy", (b, "time"), source=(a, "time")))
    cases = [
        make_case("place_disjoint", [place]),
        make_case("place_explicit_frame", [(f"{a} 모임 장소는 카페로 확정해줘. 시간은 건드리지 않아.", place[1])]),
        make_case("time_scope", [time]),
        make_case("overwritten", [time, reset]),
        make_case("temporal_copy", [time, copy_time, reset]),
        make_case("copy_before_unknown", [copy_time, time]),
        make_case("place_copy", [(f"{a} 모임 장소는 {b} 모임 장소와 같게 맞춰줘.", event("copy", (a, "place"), source=(b, "place")))]),
        make_case("weak_update", [(f"{a} 모임과 {b} 모임 중 하나의 시간은 17시로 확정해줘.", event("maybe_set", value=17, targets=[(a, "time"), (b, "time")])), place]),
        make_case("quote", [(f"예시일 뿐이야:「{place[0]}」 실제 변경은 없어.", event("noop"))]),
        make_case("compound", [(place[0] + f" {a} 모임 시간은 18시로 확정해줘.", {"kind": "sequence", "events": [place[1], event("set", (a, "time"), 18)]})]),
        make_case("negation", [(f"{a} 모임 장소는 카페로 바꿔줘라는 말은 취소야. 시간은 19시로 해.", event("set", (a, "time"), 19))]),
        make_case("hidden_reference", [(f"{a} 모임 장소는 카페로 바꿔줘. 둘째 모임도 한 시간 늦춰줘.", {"kind": "sequence", "events": [place[1], event("add", (b, "time"), 1)]})]),
        make_case("late_correction", [reset, (f"정정할게. {a} 약속은 열네 시로 기억해줘.", event("set", (a, "time"), 14))]),
        make_case("independent_unknown", [(f"{b} 모임 시간은 16시로 재합의했어. 장소는 그대로야.", event("set", (b, "time"), 16))]),
        make_case("detail_noop", [("참고로 남기는 감상이야. 오늘 하늘빛이 참 맑았어.", event("noop"))]),
        make_case("scope_suffix", [place] * 12),
    ]
    unsupported = make_case("unsupported", [place])
    unsupported["queries"] = [f"{a} 모임 시간이 어떻게 바뀌었어?", f"{a} 모임 최초 요청을 인용해줘.",
                              f"{a} 모임 캘린더 반영은 실제 완료됐어?", f"{a} 모임은 지금 몇 시야?"]
    cases.append(unsupported)
    return cases
