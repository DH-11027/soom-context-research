"""Synthetic planned-state programs and Korean surface forms.

Gold transitions are exported separately and NEVER passed to engine.run.
The semantics are controlled; these are not independent natural conversations.
"""

import random
from engine import event, snapshot

FAMILIES = (
    "absolute_reset", "relative_chain", "cross_entity_copy", "partial_fields",
    "novel_late", "novel_overwritten", "opaque_late", "opaque_overwritten",
    "quoted_change", "ambiguous_target", "unsupported_query", "irrelevant_refinement",
)


def item(text, ev):
    return {"text": text, "gold": ev}


def setting(e, field, value, style="cheap"):
    if style == "opaque":
        text = f"{e} 쪽 약속은 새 흐름으로 갈게. 시각 칸에는 {value}를 남겨뒀어."
    elif field == "place":
        text = f"{e} 모임 장소는 {value}로 확정해줘." if style == "cheap" else f"{e} 약속 장소는 {value}로 적어둘게."
    elif style == "cheap":
        text = f"{e} 모임 시간은 {value}시로 확정해줘."
    else:
        text = f"{e} 약속, 최종 시각은 {value}시로 적어둘게."
    return item(text, event("set", (e, field), value))


def noise(deep=False):
    return item("참고로 남기는 감상이야. 오늘 하늘빛이 참 맑았어." if deep else "다른 이야기: 오늘은 구름 사진을 찍었어.", event("noop"))


def build_case(family, index, split="main", prefix_length=None):
    a, b = (("가람", "노을") if split == "main" else ("하늬", "여울"))
    rng = random.Random(f"{family}:{index}:{split}")
    value = 8 + index % 4
    # Long old unrelated material makes work saved by demand refinement visible.
    prefix_length = (4 + 2 * (index % 5)) if prefix_length is None else prefix_length
    seq = [noise(deep=True) for _ in range(prefix_length)]
    seq += [setting(a, "time", value), setting(b, "time", value + 3), setting(a, "place", "도서관"), setting(b, "place", "공원")]
    if family == "absolute_reset":
        seq += [setting(a, "time", value + 1), noise(), setting(a, "time", value + 5)]
    elif family == "relative_chain":
        seq += [item(f"{a} 모임 시간을 2시간 뒤로 옮겨줘.", event("add", (a, "time"), 2)), item(f"{a} 약속을 지금보다 한 시간 늦추자.", event("add", (a, "time"), 1))]
    elif family == "cross_entity_copy":
        seq += [setting(b, "time", value + 4), item(f"{a} 모임 시간은 {b} 모임 시간과 같게 맞춰줘.", event("copy", (a, "time"), source=(b, "time"))), setting(b, "time", value + 8)]
    elif family == "partial_fields":
        seq += [setting(a, "place", "카페", "deep"), setting(a, "time", value + 5)]
    elif family == "novel_late":
        seq += [setting(a, "time", value + 6, "deep")]
    elif family == "novel_overwritten":
        seq += [setting(a, "time", value + 2, "deep"), setting(a, "time", value + 6)]
    elif family == "opaque_late":
        seq += [setting(a, "time", value + 7, "opaque")]
    elif family == "opaque_overwritten":
        seq += [setting(a, "time", value + 7, "opaque"), setting(a, "time", value + 6)]
    elif family == "quoted_change":
        seq += [item(f"표현 연습:「{a} 모임 시간은 19시로 확정해줘.」라는 문장을 써봤어. 약속은 그대로야.", event("noop"))]
    elif family == "ambiguous_target":
        seq += [item(f"{a} 모임과 {b} 모임 중 하나의 시간은 17시로 확정해줘.", event("maybe_set", value=17, targets=[(a, "time"), (b, "time")]))]
    elif family == "irrelevant_refinement":
        seq += [noise(deep=True), setting(a, "time", value + 3), noise(deep=True)]
    elif family != "unsupported_query":
        raise ValueError(family)
    seq += [noise() for _ in range(index % 3)]
    if split == "stress":
        # These variants are deliberately outside BOTH parsers, fixed before evaluation.
        if index % 4 == 0:
            seq += [item(f"{a} 약속 시각은 {value + 9}시로 재합의했어. 그렇게 기억해 둬.", event("set", (a, "time"), value + 9))]
        elif index % 4 == 1:
            seq += [item(f"{a} 모임 시간은 23시로 확정해줘. 아니, 방금 문장은 예시야.", event("noop"))]
        elif index % 4 == 2:
            seq += [item(f"이전 기록을 인용할게: {a} 모임 시간은 23시로 확정해줘.", event("noop")), setting(a, "time", value + 4)]
        else:
            seq += [item(f"{a} 모임 장소는 카페로 확정해줘. 시간은 건드리지 않아.", event("set", (a, "place"), "카페"))]
    records = [{"seq": i, "id": f"m-{rng.getrandbits(64):016x}", "text": e["text"]} for i, e in enumerate(seq)]
    queries = [f"{a} 모임은 지금 몇 시야?", f"{a} 모임의 시간과 장소를 알려줘."]
    if family == "unsupported_query":
        queries[1] = f"{a} 모임 시간이 어떻게 바뀌었어?"
    return {"id": f"{split}-{family}-{index:02d}", "family": family, "split": split,
            "public": {"records": records, "entities": [a, b], "snapshot": snapshot(records)},
            "queries": queries, "gold": [e["gold"] for e in seq]}


def build_corpus():
    return [build_case(family, i, split) for split, size in (("main", 16), ("stress", 12)) for family in FAMILIES for i in range(size)]
