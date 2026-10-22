"""Generate a paired synthetic holdout without importing any selector/parser.

Authored by a separate same-model agent from the public task and language brief.
The author did not inspect the new selector or run selector evaluations. This is
an authored synthetic challenge set, not external or IID natural-language data.
Gold events belong exclusively to the evaluator, outside each public input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

SEED = 2026102206
HERE = Path(__file__).resolve().parent
SPLITS = ("heldout_controlled", "heldout_challenge")
FAMILIES = (
    "place_only_late", "other_entity_late", "time_only_late",
    "overwritten_unknown", "temporal_copy", "weak_choice", "quoted_update",
    "compound_change", "negation", "late_correction", "unsupported_query",
    "long_suffix",
)
NAMES = (("보름", "해솔"), ("솔빛", "물결"), ("다온", "새벽"), ("푸른", "다솜"))
PLACES = ("도서관", "공원", "카페")


def event(kind, target=None, value=None, source=None, targets=None, events=None):
    result = {"kind": kind, "target": target, "value": value,
              "source": source, "targets": [] if targets is None else targets}
    if events is not None:
        result["events"] = events
    return result


def digest(records):
    payload = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def setting(entity, field, value):
    if field == "time":
        text = f"{entity} 모임 시간은 {value}시로 확정해줘."
    else:
        text = f"{entity} 모임 장소는 {value}로 확정해줘."
    return text, event("set", (entity, field), value)


def place_update(entity, value, challenge, style=0):
    if challenge:
        destination = value + ("로" if value == "카페" else "으로")
        text = f"{entity} 모임은 장소만 {destination} 옮기고, 시간표는 유지하자."
    elif style % 2:
        text = f"{entity} 모임 장소는 {value}로 확정해줘. 시간은 건드리지 않아."
    else:
        text = f"{entity} 모임 장소는 {value}로 바꿔줘."
    return text, event("set", (entity, "place"), value)


def time_update(entity, value, challenge):
    if challenge:
        text = f"이번 정정은 {entity} 모임만 해당해. 시작 시각을 {value}시로 바꾸고 장소는 유지하자."
    else:
        text = f"{entity} 모임 시간은 {value}시로 재합의했어. 장소는 그대로야."
    return text, event("set", (entity, "time"), value)


def time_copy(target, source, challenge=False):
    text = (f"{target} 모임 시작은 지금 기록된 {source} 모임 시각을 그대로 따라가자."
            if challenge else f"{target} 모임 시간은 {source} 모임 시간과 같게 맞춰줘.")
    return text, event("copy", (target, "time"), source=(source, "time"))


def build_case(family, index, split):
    challenge = split == "heldout_challenge"
    a, b = NAMES[index]
    at, bt = (3, 7, 14, 21)[index], (11, 16, 5, 9)[index]
    ap, bp = PLACES[index % 3], PLACES[(index + 1) % 3]
    new_place, later_place = PLACES[(index + 2) % 3], PLACES[index % 3]
    changed_time = at + 4 + index
    stream = [setting(a, "time", at), setting(b, "time", bt),
              setting(a, "place", ap), setting(b, "place", bp)]

    if family == "place_only_late":
        stream += [place_update(a, new_place, challenge, index)]
    elif family == "other_entity_late":
        stream += [time_update(b, bt + 6, challenge)]
    elif family == "time_only_late":
        stream += [time_update(a, changed_time, challenge)]
        # The final relative change depends on the preceding value.
        delta = 1 + index % 2
        stream += [(f"{a} 모임 시간을 {delta}시간 앞으로 옮겨줘.",
                    event("add", (a, "time"), -delta))]
    elif family == "overwritten_unknown":
        stream += [time_update(a, changed_time, challenge),
                   setting(a, "time", at + 2)]
    elif family == "temporal_copy":
        if index % 2 == 0:
            # A must retain B's historical value, not B's final value.
            stream += [time_update(b, bt + 2, challenge),
                       time_copy(a, b), setting(b, "time", bt + 7)]
        else:
            stream += [place_update(b, new_place, challenge, index)]
            copy_text = (f"이번 {a} 모임 장소는 지금의 {b} 모임 장소를 따라가자."
                         if challenge else
                         f"{a} 모임 장소는 {b} 모임 장소와 같게 맞춰줘.")
            stream += [(copy_text, event("copy", (a, "place"), source=(b, "place"))),
                       setting(b, "place", later_place)]
    elif family == "weak_choice":
        choice = at + bt + 1
        choice_text = (f"{a} 또는 {b} 중 정확히 한 모임만 {choice}시로 바꾸자. 어느 쪽인지는 아직 정하지 않았어."
                       if challenge else
                       f"{a} 모임과 {b} 모임 중 하나의 시간은 {choice}시로 확정해줘.")
        stream += [(choice_text, event("maybe_set", value=choice,
                                      targets=[(a, "time"), (b, "time")])),
                   place_update(a, new_place, challenge, index)]
    elif family == "quoted_update":
        quoted = f"{a} 모임 장소는 {new_place}로 바꿔줘."
        text = (f"옛 메모에서 '{quoted}'라고 쓴 대목을 인용한 것뿐이야. 지금 계획을 바꾸지는 않아."
                if challenge else f"예시일 뿐이야:「{quoted}」 실제 변경은 없어.")
        stream += [(text, event("noop"))]
    elif family == "compound_change":
        text = (f"{a} 모임은 장소 {new_place}와 시작 시각 {changed_time}시를 함께 적용해줘."
                if challenge else
                f"{a} 모임 장소는 {new_place}로 바꿔줘. 그리고 {a} 모임 시간은 {changed_time}시로 확정해줘.")
        stream += [(text, event("sequence", events=[
            event("set", (a, "place"), new_place),
            event("set", (a, "time"), changed_time),
        ]))]
    elif family == "negation":
        text = (f"'{a} 모임 장소는 {new_place}로 바꿔줘.'라고 쓰려다 말았어. 변경 요청은 없고 장소와 시간 모두 지금 기록을 유지해."
                if challenge else
                f"{a} 모임 장소는 {new_place}로 바꾸지 마. 시간도 그대로야.")
        stream += [(text, event("noop"))]
    elif family == "late_correction":
        stream += [time_update(a, changed_time, challenge)]
        final_time = at + 1
        corrected = (f"아까 말한 {changed_time}시는 잘못 썼어. {a} 모임 시각은 {final_time}시가 최종이야. 장소는 유지해."
                     if challenge else f"{a} 모임 시간은 {final_time}시로 확정해줘.")
        stream += [(corrected, event("set", (a, "time"), final_time))]
    elif family == "unsupported_query":
        stream += [place_update(a, new_place, challenge, index)]
    elif family == "long_suffix":
        # Modest, explicitly varied lengths; avoid long unrelated padding.
        for offset in range(4 * (index + 1)):
            place = PLACES[(index + offset + 1) % 3]
            stream += [place_update(a, place, challenge, index + offset)]
    else:
        raise ValueError(family)

    rng = random.Random(f"{SEED}:{family}:{index}")
    records = [{"seq": i, "id": f"h-{rng.getrandbits(96):024x}", "text": text}
               for i, (text, _) in enumerate(stream)]
    queries = [f"{a} 모임은 지금 몇 시야?", f"{a} 모임의 시간과 장소를 알려줘.",
               f"{b} 모임은 지금 몇 시야?", "두 모임의 현재 시간을 알려줘."]
    if family == "unsupported_query":
        queries[1] = f"{a} 모임 장소가 어떻게 바뀌었어?"
        queries[3] = f"{a} 모임 변경을 캘린더에 실제로 반영했어?"
    return {"id": f"{split}-{family}-{index:02d}", "family": family, "split": split,
            "public": {"records": records, "entities": [a, b],
                       "snapshot": {"head": len(records) - 1, "digest": digest(records)}},
            "queries": queries, "gold": [ev for _, ev in stream]}


def build_corpus():
    return [build_case(family, index, split) for split in SPLITS
            for family in FAMILIES for index in range(4)]


def validate_structure(corpus):
    """Schema and paired-label checks only; no language parser or selector."""
    assert len(corpus) == 96
    assert sum(len(case["queries"]) for case in corpus) == 384
    assert Counter(case["split"] for case in corpus) == {split: 48 for split in SPLITS}
    assert len({case["id"] for case in corpus}) == len(corpus)
    by_pair = {}

    def check_event(ev, facts):
        assert ev["kind"] in {"noop", "set", "add", "copy", "maybe_set", "sequence"}
        if ev["kind"] == "sequence":
            assert ev["events"]
            for child in ev["events"]:
                check_event(child, facts)
        elif ev["kind"] == "maybe_set":
            assert len(ev["targets"]) == 2
            assert all(tuple(f) in facts for f in ev["targets"])
        elif ev["kind"] != "noop":
            assert tuple(ev["target"]) in facts
            if ev["kind"] == "copy":
                assert tuple(ev["source"]) in facts

    for case in corpus:
        public = case["public"]
        assert set(public) == {"records", "entities", "snapshot"}
        records = public["records"]
        assert len(records) == len(case["gold"])
        assert [record["seq"] for record in records] == list(range(len(records)))
        assert len({record["id"] for record in records}) == len(records)
        assert all(set(record) == {"seq", "id", "text"} for record in records)
        assert public["snapshot"] == {"head": len(records) - 1, "digest": digest(records)}
        facts = {(e, f) for e in public["entities"] for f in ("time", "place")}
        assert {tuple(ev["target"]) for ev in case["gold"][:4]} == facts
        assert all(ev["kind"] == "set" for ev in case["gold"][:4])
        for ev in case["gold"]:
            check_event(ev, facts)
        pair_key = (case["family"], case["id"].rsplit("-", 1)[1])
        if pair_key in by_pair:
            assert case["gold"] == by_pair[pair_key]["gold"]
            assert case["queries"] == by_pair[pair_key]["queries"]
        else:
            by_pair[pair_key] = case
    return {"histories": len(corpus), "queries": 384,
            "paired_latent_programs": len(by_pair), "families": len(FAMILIES),
            "split_histories": dict(Counter(case["split"] for case in corpus)),
            "schema_checks": "passed", "selector_evaluated": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "data" / "holdout.json")
    parser.add_argument("--check", action="store_true", help="Only compare existing bytes with regeneration")
    args = parser.parse_args()
    corpus = build_corpus()
    summary = validate_structure(corpus)
    payload = (json.dumps(corpus, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if args.check:
        assert args.output.read_bytes() == payload, "Heldout bytes differ from deterministic regeneration"
    elif args.output.exists():
        assert args.output.read_bytes() == payload, "Refusing to overwrite a different holdout"
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(payload)
    summary.update({"seed": SEED, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()})
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
