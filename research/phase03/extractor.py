"""Text-only, deliberately small rule baselines for offline relation research.

No fixture/gold imports. Input is chronological opaque IDs plus text, and query
only for retrieval. This is not an LLM, embedding model, or production component.
"""
import math
import re

ROOT_CUES = ("해줘", "해 줘", "부탁해", "부탁할게", "기억해줘", "기록해줘", "잡아줘")
UPDATE_CUES = ("완료", "끝냈", "마무리", "정정", "변경", "취소", "아직", "시작하지", "남아")
META_CUES = ("예시", "인용", "가정", "표현", "문구", "설명용")
OBJECTS = ("안내문", "예산표", "보고서", "초대장", "참가자 명단", "지도", "발표문", "자료")
ENTITY = re.compile(r"([가-힣A-Za-z0-9_-]+)\s*(프로젝트|모임)")


def grams(text):
    text = re.sub(r"[^가-힣a-z0-9]", "", text.lower())
    return {text[i:i + 2] for i in range(len(text) - 1)}


def similarity(a, b):
    x, y = grams(a), grams(b)
    return len(x & y) / math.sqrt(max(1, len(x) * len(y)))


def attributes(text):
    entity = {name + suffix for name, suffix in ENTITY.findall(text)}
    objects = {obj for obj in OBJECTS if obj in text}
    if re.search(r"\d+\s*시", text) or any(s in text for s in ("시각", "시간", "일정", "모임")):
        kind = "schedule"
    elif objects or "작업" in text or "문서" in text or "프로젝트" in text:
        kind = "task"
    else:
        kind = None
    return {"entities": entity, "objects": objects, "kind": kind}


def extract(history, method="selective"):
    if method not in ("nearest", "similarity", "selective"):
        raise ValueError(method)
    roots, events = [], []
    for position, message in enumerate(history):
        text = message["text"]
        attrs = attributes(text)
        if any(cue in text for cue in META_CUES):
            continue
        if any(cue in text for cue in ROOT_CUES):
            roots.append({"id": message["id"], "text": text, "position": position, **attrs})
            continue
        if not any(cue in text for cue in UPDATE_CUES):
            continue
        eligible = [r for r in roots if attrs["kind"] is None or r["kind"] == attrs["kind"]]
        if method == "selective":
            if attrs["entities"]:
                eligible = [r for r in eligible if r["entities"] & attrs["entities"]]
            if attrs["objects"]:
                eligible = [r for r in eligible if r["objects"] & attrs["objects"]]
            parent = eligible[0]["id"] if len(eligible) == 1 else None
        elif not eligible:
            parent = None
        elif method == "nearest":
            parent = max(eligible, key=lambda r: r["position"])["id"]
        else:
            parent = max(eligible, key=lambda r: (similarity(text, r["text"]), r["position"]))["id"]
        events.append({"child": message["id"], "parent": parent,
                       "candidates": [r["id"] for r in eligible],
                       "decision": "linked" if parent else "ambiguous" if len(eligible) > 1 else "unresolved"})
    return {"roots": [r["id"] for r in roots], "events": events}


def retrieve(history, query):
    ranked = sorted(enumerate(history[:-1]), key=lambda item: (similarity(query, item[1]["text"]), item[0]), reverse=True)
    return {history[-1]["id"]} | {message["id"] for _, message in ranked[:2]}


def select(public, method, retain_candidates=False):
    history = public["history"]
    selected = retrieve(history, public["query"])
    if method == "lexical_only":
        return selected
    parsed = extract(history, method)
    bundles = []
    for event in parsed["events"]:
        if event["parent"]:
            bundles.append({event["child"], event["parent"]})
        elif retain_candidates and event["candidates"]:
            # Co-retention is NOT an assertion that every candidate is the referent.
            bundles.append({event["child"], *event["candidates"]})
    changed = True
    while changed:
        changed = False
        for bundle in bundles:
            if selected & bundle and not bundle <= selected:
                selected.update(bundle)
                changed = True
    return selected
