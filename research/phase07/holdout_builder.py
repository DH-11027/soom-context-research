"""Deterministic multi-query/snapshot holdout, authored without cache outputs.

No imports from Phase06 or Phase07 parsers, selectors, or evaluators. Gold events
and question contracts are outside public inputs. This same-model author knows
the shared hypothesis and cache budget, so this is not external blind data.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

SEED = 2026102207
HERE = Path(__file__).resolve().parent
FAMILIES = (
    "same_history_query_rotation", "append_then_correction",
    "historical_text_edit_same_id", "valid_reorder_delete_reinsert",
    "entity_environment_change", "no_reuse_high_churn", "long_short_text_mix",
    "query_scope_and_unsupported", "parser_namespace_rotation",
    "malformed_snapshot_then_recovery",
)
NAMES = (("가온", "도담", "세온"), ("시온", "아라", "다래"), ("해담", "누리", "윤슬"))
PLACES = ("도서관", "공원", "카페")
DEFAULT_NAMESPACE = "phase06-frozen-v1"


def event(kind, target=None, value=None, source=None, targets=None):
    return {"kind": kind, "target": target, "value": value,
            "source": source, "targets": [] if targets is None else targets}


def history_digest(records):
    raw = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def snapshot(records):
    return {"head": len(records) - 1, "digest": history_digest(records)}


def question(entities, kind):
    a, b = entities
    if kind == "a_time":
        text, fields = f"{a} 모임은 지금 몇 시야?", [(a, "time")]
    elif kind == "a_both":
        text, fields = f"{a} 모임의 시간과 장소를 알려줘.", [(a, "time"), (a, "place")]
    elif kind == "b_time":
        text, fields = f"{b} 모임은 지금 몇 시야?", [(b, "time")]
    elif kind == "both_times":
        text, fields = "두 모임의 현재 시간을 알려줘.", [(a, "time"), (b, "time")]
    elif kind == "history":
        return f"{a} 모임 시간이 어떻게 바뀌었어?", {"supported": False, "required_fields": []}
    elif kind == "execution":
        return f"{a} 모임 변경을 캘린더에 실제로 반영했어?", {"supported": False, "required_fields": []}
    elif kind == "quote":
        return f"{a} 모임의 최초 요청 원문을 그대로 인용해줘.", {"supported": False, "required_fields": []}
    else:
        raise ValueError(kind)
    return text, {"supported": True, "required_fields": [list(f) for f in fields]}


class Author:
    """Creates opaque record IDs, authoritative plan events, and public snapshots."""

    def __init__(self, family, parameter):
        self.rng = random.Random(f"{SEED}:{family}:{parameter}")
        self.a, self.b, self.c = NAMES[parameter]
        self.entities = [self.a, self.b]
        self.parameter = parameter
        self.at, self.bt = (5, 9, 17)[parameter], (12, 15, 20)[parameter]

    def row(self, text, gold):
        return {"id": f"r-{self.rng.getrandbits(96):024x}", "text": text, "gold": gold}

    def setting(self, entity, field, value, deep=False):
        if field == "time":
            text = (f"{entity} 약속, 최종 시각은 {value}시로 적어둘게."
                    if deep else f"{entity} 모임 시간은 {value}시로 확정해줘.")
        else:
            text = f"{entity} 모임 장소는 {value}로 확정해줘."
        return self.row(text, event("set", (entity, field), value))

    def add(self, entity, delta):
        direction = "뒤로" if delta >= 0 else "앞으로"
        return self.row(f"{entity} 모임 시간을 {abs(delta)}시간 {direction} 옮겨줘.",
                        event("add", (entity, "time"), delta))

    def copy_time(self, target, source):
        return self.row(f"{target} 모임 시간은 {source} 모임 시간과 같게 맞춰줘.",
                        event("copy", (target, "time"), source=(source, "time")))

    def scoped_place(self, entity, value):
        return self.row(f"{entity} 모임 장소는 {value}로 확정해줘. 시간은 건드리지 않아.",
                        event("set", (entity, "place"), value))

    def quote_noop(self, payload):
        return self.row(f"예시일 뿐이야:「{payload}」 실제 변경은 없어.", event("noop"))

    def deep_noop(self):
        return self.row("참고로 남기는 감상이야. 오늘 하늘빛이 참 맑았어.", event("noop"))

    def base(self, offset=0):
        p = self.parameter
        return [self.setting(self.a, "time", self.at + offset),
                self.setting(self.b, "time", self.bt + offset),
                self.setting(self.a, "place", PLACES[(p + offset) % 3]),
                self.setting(self.b, "place", PLACES[(p + offset + 1) % 3])]

    def step(self, rows, number, query_kind="a_time", *, entities=None,
             parser_namespace=DEFAULT_NAMESPACE, gold_applicable=True):
        entities = list(self.entities if entities is None else entities)
        records = [{"seq": i, "id": row["id"], "text": row["text"]}
                   for i, row in enumerate(rows)]
        query, contract = question(entities, query_kind)
        return {"step_id": f"s-{number:02d}", "parser_namespace": parser_namespace,
                "public": {"records": records, "entities": entities,
                           "snapshot": snapshot(records), "query": query},
                "gold": copy.deepcopy([row["gold"] for row in rows]),
                "question_contract": contract, "expected_integrity": "valid",
                "gold_applicable": gold_applicable}


def build_stream(family, parameter):
    author = Author(family, parameter)
    a, b, c = author.a, author.b, author.c
    base = author.base()
    steps = []
    rotation = ("a_time", "a_both", "b_time", "both_times", "a_time",
                "both_times", "a_both", "b_time", "a_time", "a_both")

    if family == "same_history_query_rotation":
        rows = base + [author.setting(a, "time", author.at + 3, deep=True),
                       author.copy_time(b, a), author.deep_noop()]
        steps = [author.step(rows, i, kind) for i, kind in enumerate(rotation)]

    elif family == "append_then_correction":
        additions = [author.add(a, 2), author.quote_noop("시간표 예를 옮겨 적은 것뿐"),
                     author.setting(a, "time", author.at + 7, deep=True),
                     author.setting(a, "time", author.at + 1), author.copy_time(b, a),
                     author.add(a, 1), author.setting(b, "time", author.bt + 4),
                     author.scoped_place(a, PLACES[(parameter + 2) % 3]),
                     author.setting(a, "time", author.at + 5)]
        for i, kind in enumerate(rotation):
            steps.append(author.step(base + additions[:i], i, kind))

    elif family == "historical_text_edit_same_id":
        tail = [author.add(a, 2), author.copy_time(b, a), author.deep_noop()]
        offsets = (0, 1, 4, 1, 7, 0, 3, 4, 0, 2)
        for i, offset in enumerate(offsets):
            rows = copy.deepcopy(base + tail)
            value = author.at + offset
            rows[0]["text"] = f"{a} 모임 시간은 {value}시로 확정해줘."
            rows[0]["gold"] = event("set", (a, "time"), value)
            steps.append(author.step(rows, i, rotation[i]))

    elif family == "valid_reorder_delete_reinsert":
        tail = [author.add(a, 2), author.copy_time(b, a), author.add(a, -1),
                author.setting(b, "time", author.bt + 5),
                author.setting(a, "place", PLACES[(parameter + 2) % 3])]
        orders = ((0, 1, 2, 3, 4), (1, 0, 2, 3, 4), (0, 1, 2, 4),
                  (0, 3, 1, 2, 4), (1, 2, 3, 4), (1, 0, 2, 3, 4),
                  (4, 3, 2, 1, 0), (0, 1, 2, 3, 4), (0, 2, 3, 4),
                  (0, 1, 2, 3, 4))
        for i, order in enumerate(orders):
            steps.append(author.step(base + [tail[j] for j in order], i, "both_times"))

    elif family == "entity_environment_change":
        rows = base + [author.setting(b, "time", author.bt + 2, deep=True),
                       author.quote_noop("공개 명단을 확인하는 상황의 예시")]
        rosters = ([a, b], [b, a], [a, b], [a, c], [c, a],
                   [a, b], [a, c], [c, a], [b, a], [a, b])
        for i, roster in enumerate(rosters):
            applicable = set(roster) == {a, b}
            steps.append(author.step(rows, i, "both_times", entities=roster,
                                     gold_applicable=applicable))

    elif family == "no_reuse_high_churn":
        for i in range(10):
            rows = author.base(offset=3 * i + 1)
            for j in range(10):
                token = f"{author.rng.getrandbits(80):020x}"
                rows.append(author.quote_noop(f"작성 연습 {token}, 항목 {j}: 실제 변경 지시는 아님"))
            steps.append(author.step(rows, i, "a_both"))

    elif family == "long_short_text_mix":
        size = (64, 2048, 24000)[parameter]
        pattern = "가상의일정표기록"
        payload = (pattern * (size // len(pattern) + 1))[:size]
        long_row = author.quote_noop(payload)
        short_rows = [author.quote_noop(f"짧은 비교 표기 {j}") for j in range(5)]
        for i in range(10):
            rows = base + [long_row] + short_rows[:i % 5]
            steps.append(author.step(rows, i, rotation[i]))

    elif family == "query_scope_and_unsupported":
        choice = author.at + author.bt + 1
        weak = author.row(f"{a} 모임과 {b} 모임 중 하나의 시간은 {choice}시로 확정해줘.",
                          event("maybe_set", value=choice,
                                targets=[(a, "time"), (b, "time")]))
        rows = base + [author.copy_time(b, a), weak,
                       author.scoped_place(a, PLACES[(parameter + 2) % 3])]
        kinds = ("a_time", "a_both", "history", "both_times", "b_time",
                 "a_both", "execution", "a_time", "both_times", "quote")
        steps = [author.step(rows, i, kind) for i, kind in enumerate(kinds)]

    elif family == "parser_namespace_rotation":
        rows = base + [author.setting(a, "time", author.at + 6, deep=True), author.deep_noop()]
        versions = (1, 1, 2, 2, 1, 3, 3, 1, 2, 1)
        steps = [author.step(rows, i, "a_both", parser_namespace=f"same-parser-label-v{v}")
                 for i, v in enumerate(versions)]

    elif family == "malformed_snapshot_then_recovery":
        rows = base + [author.add(a, 2), author.copy_time(b, a), author.deep_noop()]
        for i in range(10):
            step = author.step(rows, i, "both_times")
            if i in (1, 3, 5, 7):
                step["expected_integrity"] = "invalid"
                step["gold_applicable"] = False
                public = step["public"]
                if i == 1:
                    public["snapshot"]["digest"] = "0" * 64
                elif i == 3:
                    public["records"][0]["text"] += " 수정됨"
                elif i == 5:
                    if parameter == 0:
                        public["records"][-1]["seq"] += 1
                        public["snapshot"] = snapshot(public["records"])
                    elif parameter == 1:
                        public["records"].pop()
                        step["gold"].pop()
                    else:
                        public["snapshot"]["head"] += 1
                else:
                    public["records"][-1], public["records"][-2] = public["records"][-2], public["records"][-1]
                    step["gold"][-1], step["gold"][-2] = step["gold"][-2], step["gold"][-1]
                    if parameter % 2:
                        public["snapshot"] = snapshot(public["records"])
            elif i == 9:
                step = author.step(rows + [author.setting(a, "time", author.at + 9)], i, "both_times")
            steps.append(step)
    else:
        raise ValueError(family)

    return {"id": f"holdout-{family}-{parameter:02d}", "family": family,
            "split": "holdout", "steps": steps}


def build_corpus():
    return [build_stream(family, parameter) for family in FAMILIES for parameter in range(3)]


def execute_gold(events, entities):
    """Author's typed-label consistency check; never interprets source text."""
    fields = [(e, f) for e in entities for f in ("time", "place")]
    positions = {field: i for i, field in enumerate(fields)}
    states = {tuple(None for _ in fields)}
    for ev in events:
        kind = ev["kind"]
        assert kind in {"noop", "set", "add", "copy", "maybe_set"}
        if kind == "noop":
            continue
        following = set()
        for state in states:
            if kind == "maybe_set":
                assert ev["targets"]
                for field in ev["targets"]:
                    target = positions[tuple(field)]
                    new = list(state)
                    new[target] = ev["value"]
                    following.add(tuple(new))
                continue
            target = positions[tuple(ev["target"])]
            new = list(state)
            if kind == "set":
                new[target] = ev["value"]
            elif kind == "add":
                assert isinstance(new[target], int)
                new[target] += ev["value"]
            elif kind == "copy":
                new[target] = state[positions[tuple(ev["source"])]]
            following.add(tuple(new))
        states = following
    assert states
    assert all(all(value is not None for value in state) for state in states)
    return states


def validate_structure(corpus):
    assert len(corpus) == 30
    assert len({stream["id"] for stream in corpus}) == len(corpus)
    counts = Counter()
    for stream in corpus:
        assert len(stream["steps"]) == 10
        assert len({step["step_id"] for step in stream["steps"]}) == 10
        for step in stream["steps"]:
            public = step["public"]
            assert set(public) == {"records", "entities", "snapshot", "query"}
            records = public["records"]
            assert len(records) == len(step["gold"])
            assert all(set(record) == {"seq", "id", "text"} for record in records)
            assert len({record["id"] for record in records}) == len(records)
            assert len(public["entities"]) == 2 and len(set(public["entities"])) == 2
            expected = public["snapshot"]
            valid = ([r["seq"] for r in records] == list(range(expected["head"] + 1))
                     and history_digest(records) == expected["digest"])
            assert valid == (step["expected_integrity"] == "valid")
            assert step["expected_integrity"] in {"valid", "invalid"}
            contract = step["question_contract"]
            assert set(contract) == {"supported", "required_fields"}
            fields = {(e, f) for e in public["entities"] for f in ("time", "place")}
            required = {tuple(field) for field in contract["required_fields"]}
            assert len(required) == len(contract["required_fields"])
            assert required <= fields
            assert bool(required) == contract["supported"]
            if step["gold_applicable"]:
                assert valid
                assert all(ev["kind"] == "set" for ev in step["gold"][:4])
                assert {tuple(ev["target"]) for ev in step["gold"][:4]} == fields
                execute_gold(step["gold"], public["entities"])
            counts["steps"] += 1
            counts["valid_steps"] += valid
            counts["invalid_steps"] += not valid
            counts["gold_applicable_steps"] += step["gold_applicable"]
            counts["unsupported_questions"] += not contract["supported"]
    assert counts["steps"] == 300
    return {"seed": SEED, "streams": len(corpus), "families": len(FAMILIES),
            **dict(counts), "schema_and_gold_checks": "passed", "selector_evaluated": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "data" / "holdout.json")
    parser.add_argument("--check", action="store_true", help="Compare existing bytes with deterministic regeneration")
    args = parser.parse_args()
    corpus = build_corpus()
    summary = validate_structure(corpus)
    payload = (json.dumps(corpus, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if args.check:
        assert args.output.read_bytes() == payload, "Holdout differs from deterministic regeneration"
    elif args.output.exists():
        assert args.output.read_bytes() == payload, "Refusing to overwrite different holdout bytes"
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(payload)
    summary.update({"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()})
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
