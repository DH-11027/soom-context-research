"""Phase08 synthetic streams, authored without executing any selector.

Only the public grammar, schema, research question and prespecified family/range
contract are shared with implementation. Labels are generated from typed plans,
never from parser outputs. This is same-model role separation, not external
blind data. No Phase08 policy/development/result imports are permitted here.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

SEED = 2026102208
HERE = Path(__file__).resolve().parent
FAMILIES = (
    "short_repeated", "short_churn", "long_cheap_repeated",
    "long_deep_repeated", "long_deep_single_use", "working_set_fit",
    "working_set_pressure", "phase_shift", "revisions_copy_reorder",
    "scope_and_ambiguity", "entity_namespace_rotation",
    "integrity_unsupported_recovery",
)
NAMES = (("새봄", "마루", "이든"), ("노을", "라온", "하늬"), ("나래", "여울", "아온"))
PLACES = ("공원", "도서관", "카페")
RAW_BYTE_BANDS = ((1000, 4000), (12000, 24000), (60000, 75000))
DEFAULT_NAMESPACE = "p8-v1"
STEPS = 12
PARAMETERS = 3


def event(kind, target=None, value=None, source=None, targets=None):
    return {"kind": kind, "target": target, "value": value,
            "source": source, "targets": [] if targets is None else targets}


def history_digest(records):
    wire = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(wire.encode("utf-8")).hexdigest()


def snapshot(records):
    return {"head": len(records) - 1, "digest": history_digest(records)}


def question(entities, kind):
    a, b = entities
    table = {
        "a_time": (f"{a} 모임은 지금 몇 시야?", [(a, "time")]),
        "b_time": (f"{b} 모임은 지금 몇 시야?", [(b, "time")]),
        "a_both": (f"{a} 모임의 시간과 장소를 알려줘.", [(a, "time"), (a, "place")]),
        "b_both": (f"{b} 모임의 시간과 장소를 알려줘.", [(b, "time"), (b, "place")]),
        "both_times": ("두 모임의 현재 시간을 알려줘.", [(a, "time"), (b, "time")]),
        "history": (f"{a} 모임 시간이 바뀐 순서를 설명해줘.", []),
        "execution": (f"{b} 모임 약속을 캘린더에 실제로 등록했어?", []),
        "quote": (f"{a} 모임의 가장 오래된 요청을 원문으로 인용해줘.", []),
    }
    text, fields = table[kind]
    return text, {"supported": bool(fields), "required_fields": [list(f) for f in fields]}


def exact_payload(byte_length, salt):
    """Deterministic valid Unicode payload with exact UTF-8 length, no newline."""
    token = hashlib.sha256(salt.encode("utf-8")).hexdigest()[:17]
    chunk = f"연습기록{token}가상의약속을옮겨적음;"
    chunk_bytes = len(chunk.encode("utf-8"))
    repeats, remaining = divmod(byte_length, chunk_bytes)
    payload = chunk * repeats + "가" * (remaining // 3) + "x" * (remaining % 3)
    assert len(payload.encode("utf-8")) == byte_length
    return payload


class Author:
    def __init__(self, family, parameter):
        self.family = family
        self.parameter = parameter
        self.rng = random.Random(f"{SEED}:{family}:{parameter}")
        self.a, self.b, self.c = NAMES[parameter]
        self.entities = [self.a, self.b]
        self.at = self.rng.randint(5, 13)
        self.bt = self.rng.randint(17, 25)

    def row(self, text, gold):
        return {"id": f"u-{self.rng.getrandbits(112):028x}", "text": text, "gold": gold}

    def setting(self, entity, field, value, deep=False):
        if field == "time":
            text = (f"{entity} 약속, 최종 시각은 {value}시로 적어둘게."
                    if deep else f"{entity} 모임 시간은 {value}시로 확정해줘.")
        else:
            text = (f"{entity} 약속 장소는 {value}로 적어둘게."
                    if deep else f"{entity} 모임 장소는 {value}로 확정해줘.")
        return self.row(text, event("set", (entity, field), value))

    def add(self, entity, delta, deep=False):
        assert not deep or delta == 1
        text = (f"{entity} 약속을 지금보다 한 시간 늦추자." if deep else
                f"{entity} 모임 시간을 {abs(delta)}시간 {'뒤로' if delta >= 0 else '앞으로'} 옮겨줘.")
        return self.row(text, event("add", (entity, "time"), delta))

    def copy_time(self, target, source):
        return self.row(f"{target} 모임 시간은 {source} 모임 시간과 같게 맞춰줘.",
                        event("copy", (target, "time"), source=(source, "time")))

    def maybe_time(self, value):
        return self.row(f"{self.a} 모임과 {self.b} 모임 중 하나의 시간은 {value}시로 확정해줘.",
                        event("maybe_set", value=value,
                              targets=[(self.a, "time"), (self.b, "time")]))

    def scope_place(self, entity, value):
        return self.row(f"{entity} 모임 장소는 {value}로 확정해줘. 시간은 건드리지 않아.",
                        event("set", (entity, "place"), value))

    def scope_time(self, entity, value):
        return self.row(f"{entity} 모임 시간은 {value}시로 재합의했어. 장소는 그대로야.",
                        event("set", (entity, "time"), value))

    def quote(self, raw_bytes, salt, deep=True):
        before, after = (("표현 연습:「", "」라는 문장을 써봤어. 약속은 그대로야.") if deep else
                         ("예시일 뿐이야:「", "」 실제 변경은 없어."))
        available = raw_bytes - len((before + after).encode("utf-8"))
        assert available >= 128, "Salt must be represented in at least one full chunk"
        text = before + exact_payload(available, salt) + after
        assert len(text.encode("utf-8")) == raw_bytes
        return self.row(text, event("noop"))

    def small_quote(self, salt, deep=False):
        return self.quote(self.rng.randint(220, 380), salt, deep)

    def base(self, offset=0):
        p = self.parameter
        return [self.setting(self.a, "time", self.at + offset),
                self.setting(self.b, "time", self.bt - offset),
                self.setting(self.a, "place", PLACES[(p + offset) % 3]),
                self.setting(self.b, "place", PLACES[(p + offset + 2) % 3])]

    def band_length(self):
        # Matched size across cheap/deep/repeated/single-use family conditions.
        rng = random.Random(f"{SEED}:matched-raw-band:{self.parameter}")
        return rng.randint(*RAW_BYTE_BANDS[self.parameter])

    def step(self, rows, index, query_kind="a_time", *, entities=None,
             namespace=DEFAULT_NAMESPACE, gold_applicable=True,
             gold_exclusion_reason=None):
        entities = list(self.entities if entities is None else entities)
        records = [{"seq": i, "id": row["id"], "text": row["text"]}
                   for i, row in enumerate(rows)]
        query, contract = question(entities, query_kind)
        return {"step_id": f"t{index:02d}", "parser_namespace": namespace,
                "public": {"records": records, "entities": entities,
                           "snapshot": snapshot(records), "query": query},
                "gold": copy.deepcopy([row["gold"] for row in rows]),
                "question_contract": contract, "expected_integrity": "valid",
                "gold_applicable": gold_applicable,
                "gold_exclusion_reason": gold_exclusion_reason}


def build_stream(family, parameter):
    author = Author(family, parameter)
    a, b, c = author.a, author.b, author.c
    base = author.base()
    rotation = ("a_both", "b_time", "both_times", "a_time", "b_both", "a_time",
                "both_times", "b_time", "a_both", "b_both", "a_time", "both_times")
    steps = []

    if family == "short_repeated":
        rows = base + [author.setting(a, "time", author.at + 4, deep=True),
                       author.copy_time(b, a), author.add(a, 1, deep=True),
                       author.small_quote("fixed-note-1", deep=True),
                       author.small_quote("fixed-note-2")]
        steps = [author.step(rows, i, rotation[i]) for i in range(STEPS)]

    elif family == "short_churn":
        for i in range(STEPS):
            rows = author.base(offset=2 * i + 1)
            rows += [author.setting(b, "time", author.bt + 3 * i, deep=True),
                     author.copy_time(a, b), author.add(b, i + 1)]
            rows += [author.small_quote(f"{family}:{parameter}:{i}:{j}", deep=(j % 2 == 0))
                     for j in range(8)]
            steps.append(author.step(rows, i, rotation[i]))

    elif family in ("long_cheap_repeated", "long_deep_repeated", "long_deep_single_use"):
        length = author.band_length()
        persistent = author.quote(length, f"{family}:{parameter}:fixed",
                                  deep=(family != "long_cheap_repeated"))
        tail = [author.copy_time(b, a), author.add(a, 1, deep=True)]
        for i in range(STEPS):
            large = (author.quote(length, f"{family}:{parameter}:unique:{i}")
                     if family == "long_deep_single_use" else persistent)
            steps.append(author.step(base + tail + [large], i, rotation[i]))

    elif family == "working_set_fit":
        count = parameter + 2
        total = author.rng.randint(22000, 46000)
        lengths = [total // count + (j < total % count) for j in range(count)]
        assert 20000 <= sum(lengths) <= 50000
        quotes = [author.quote(length, f"fit:{parameter}:{j}") for j, length in enumerate(lengths)]
        rows = base + [author.copy_time(b, a), author.add(a, -2)] + quotes
        steps = [author.step(rows, i, rotation[i]) for i in range(STEPS)]

    elif family == "working_set_pressure":
        count = parameter + 2
        band = ((34000, 47000), (23000, 32000), (18000, 23000))[parameter]
        lengths = [author.rng.randint(*band) for _ in range(count)]
        assert sum(lengths) > 65536 and all(16000 <= value <= 48000 for value in lengths)
        quotes = [author.quote(length, f"pressure:{parameter}:{j}")
                  for j, length in enumerate(lengths)]
        author.rng.shuffle(quotes)
        rows = base + [author.add(a, 3), author.copy_time(b, a)] + quotes
        steps = [author.step(rows, i, rotation[i]) for i in range(STEPS)]

    elif family == "phase_shift":
        length = author.band_length()
        early = author.quote(length, f"phase:{parameter}:early")
        late = author.quote(length, f"phase:{parameter}:late")
        for i in range(STEPS):
            if i < 4:
                large = early
            elif i < 8:
                large = author.quote(length, f"phase:{parameter}:one-shot:{i}", deep=(i % 2 == 0))
            else:
                large = late
            rows = base + [author.copy_time(b, a)]
            if i >= 6:
                rows.append(author.setting(a, "time", author.at + 7, deep=True))
            steps.append(author.step(rows + [large], i, rotation[i]))

    elif family == "revisions_copy_reorder":
        pool = [author.setting(a, "time", author.at + 3, deep=True),
                author.copy_time(b, a), author.add(a, -2), author.copy_time(a, b),
                author.add(b, 1, deep=True)]
        offsets = author.rng.sample(range(0, 24), STEPS)
        for i, offset in enumerate(offsets):
            current_base = copy.deepcopy(base)
            value = author.at + offset
            current_base[0]["text"] = (f"{a} 약속, 최종 시각은 {value}시로 적어둘게."
                                       if i % 3 == 0 else f"{a} 모임 시간은 {value}시로 확정해줘.")
            current_base[0]["gold"] = event("set", (a, "time"), value)
            order = list(range(len(pool)))
            author.rng.shuffle(order)
            if i in (2, 5, 9):
                order.pop(i % len(order))
            rows = current_base + [pool[j] for j in order]
            if i in (4, 8, 11):
                rows.append(author.setting(b, "time", author.bt + i, deep=(i % 2 == 0)))
            rows.append(author.small_quote(f"revision:{parameter}:{i // 3}"))
            steps.append(author.step(rows, i, "both_times"))

    elif family == "scope_and_ambiguity":
        for i in range(STEPS):
            rows = base + [author.copy_time(b, a), author.maybe_time(author.bt + 6)]
            if i % 3 == 0:
                rows.append(author.scope_place(a, PLACES[(parameter + 1) % 3]))
            elif i % 3 == 1:
                rows.append(author.scope_time(b, author.bt + 2))
            else:
                rows.append(author.scope_place(b, PLACES[parameter]))
            if i >= 8:
                rows += [author.setting(a, "time", author.at + 1, deep=True), author.copy_time(b, a)]
            kind = ("a_time", "both_times", "b_both", "a_both")[i % 4]
            steps.append(author.step(rows, i, kind))

    elif family == "entity_namespace_rotation":
        rows = base + [author.setting(b, "time", author.bt + 4, deep=True),
                       author.copy_time(a, b), author.small_quote("environment-repeat", deep=True)]
        rosters = ([a, b], [b, a], [a, b], [a, c], [c, a], [a, b],
                   [b, a], [a, b], [a, c], [a, b], [a, b], [b, a])
        versions = (1, 1, 2, 2, 1, 3, 1, 3, 2, 1, 2, 1)
        for i, (roster, version) in enumerate(zip(rosters, versions)):
            applicable = set(roster) == {a, b}
            steps.append(author.step(rows, i, rotation[i], entities=roster,
                                     namespace=f"p8-v{version}", gold_applicable=applicable,
                                     gold_exclusion_reason=None if applicable else "entity_membership_undefined"))

    elif family == "integrity_unsupported_recovery":
        rows = base + [author.add(a, 3), author.copy_time(b, a),
                       author.small_quote("integrity-repeated", deep=True)]
        kinds = ("both_times", "a_time", "a_both", "history", "b_time", "both_times",
                 "execution", "both_times", "b_both", "quote", "a_time", "both_times")
        for i in range(STEPS):
            current = rows + ([author.setting(a, "time", author.at + 12, deep=True)] if i == 11 else [])
            step = author.step(current, i, kinds[i])
            if i in (1, 4, 7, 10):
                step["expected_integrity"] = "invalid"
                step["gold_applicable"] = False
                step["gold_exclusion_reason"] = "invalid_snapshot"
                public = step["public"]
                if i == 1:
                    public["snapshot"]["digest"] = "f" * 64
                elif i == 4:
                    if parameter == 0:
                        public["records"][-1]["seq"] += 2
                        public["snapshot"] = snapshot(public["records"])
                    elif parameter == 1:
                        public["records"][0]["text"] += " 뒤늦게 편집됨"
                    else:
                        public["records"][-1], public["records"][-2] = public["records"][-2], public["records"][-1]
                        step["gold"][-1], step["gold"][-2] = step["gold"][-2], step["gold"][-1]
                        public["snapshot"] = snapshot(public["records"])
                elif i == 7:
                    public["records"].pop(2)
                    step["gold"].pop(2)
                else:
                    public["snapshot"]["head"] += 1
            steps.append(step)
    else:
        raise ValueError(family)

    return {"id": f"p8-holdout-{family}-{parameter:02d}", "family": family,
            "split": "holdout", "steps": steps}


def build_corpus():
    return [build_stream(family, p) for family in FAMILIES for p in range(PARAMETERS)]


def execute_gold(events, entities):
    """Author-side typed-plan consistency only; does not interpret raw text."""
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
            targets = ev["targets"] if kind == "maybe_set" else [ev["target"]]
            assert targets
            for field in targets:
                target = positions[tuple(field)]
                new = list(state)
                if kind in ("set", "maybe_set"):
                    new[target] = ev["value"]
                elif kind == "add":
                    assert type(new[target]) is int
                    new[target] += ev["value"]
                elif kind == "copy":
                    new[target] = state[positions[tuple(ev["source"])]]
                following.add(tuple(new))
        states = following
    assert states and all(all(value is not None for value in state) for state in states)
    return states


def validate_structure(corpus):
    assert len(corpus) == len(FAMILIES) * PARAMETERS
    assert len({stream["id"] for stream in corpus}) == len(corpus)
    counts = Counter()
    for stream in corpus:
        assert stream["family"] in FAMILIES and stream["split"] == "holdout"
        assert len(stream["steps"]) == STEPS
        assert len({step["step_id"] for step in stream["steps"]}) == STEPS
        for step in stream["steps"]:
            public = step["public"]
            assert set(public) == {"records", "entities", "snapshot", "query"}
            records = public["records"]
            assert len(records) == len(step["gold"])
            assert all(set(record) == {"seq", "id", "text"} for record in records)
            assert len({record["id"] for record in records}) == len(records)
            assert len(public["entities"]) == 2 and len(set(public["entities"])) == 2
            if stream["family"] in ("short_repeated", "short_churn"):
                assert all(len(record["text"]) < 256 for record in records)
            expected = public["snapshot"]
            valid = ([r["seq"] for r in records] == list(range(expected["head"] + 1))
                     and history_digest(records) == expected["digest"])
            assert valid == (step["expected_integrity"] == "valid")
            contract = step["question_contract"]
            assert set(contract) == {"supported", "required_fields"}
            fields = {(e, f) for e in public["entities"] for f in ("time", "place")}
            required = {tuple(field) for field in contract["required_fields"]}
            assert len(required) == len(contract["required_fields"])
            assert required <= fields and bool(required) == contract["supported"]
            # Independently enumerate the finite query contract; no parser import.
            supported_table = {"두 모임의 현재 시간을 알려줘.": {(e, "time") for e in public["entities"]}}
            for e in public["entities"]:
                supported_table[f"{e} 모임은 지금 몇 시야?"] = {(e, "time")}
                supported_table[f"{e} 모임의 시간과 장소를 알려줘."] = {(e, "time"), (e, "place")}
            assert supported_table.get(public["query"], set()) == required
            assert (public["query"] in supported_table) == contract["supported"]
            if step["gold_applicable"]:
                assert valid and step["gold_exclusion_reason"] is None
                assert all(ev["kind"] == "set" for ev in step["gold"][:4])
                assert {tuple(ev["target"]) for ev in step["gold"][:4]} == fields
                execute_gold(step["gold"], public["entities"])
            else:
                assert step["gold_exclusion_reason"] in {"invalid_snapshot", "entity_membership_undefined"}
            counts["steps"] += 1
            counts["valid_steps"] += valid
            counts["invalid_steps"] += not valid
            counts["gold_applicable_steps"] += step["gold_applicable"]
            counts["unsupported_questions"] += not contract["supported"]
            counts["gold_supported_steps"] += step["gold_applicable"] and contract["supported"]
            if step["gold_exclusion_reason"]:
                counts["excluded_" + step["gold_exclusion_reason"]] += 1
    assert counts["steps"] == 432
    return {"seed": SEED, "families": len(FAMILIES), "streams": len(corpus),
            "parameters_per_family": PARAMETERS, "steps_per_stream": STEPS,
            **dict(counts), "schema_and_gold_checks": "passed",
            "selector_evaluated": False,
            "authorship": "separate same-model agent, shared public design; not external blind evaluation"}


def write_or_check(path, payload, check):
    if check or path.exists():
        assert path.read_bytes() == payload, f"Refusing different bytes at {path}"
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "data/holdout.json")
    parser.add_argument("--manifest", type=Path, default=HERE / "data/holdout_manifest.json")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    corpus = build_corpus()
    summary = validate_structure(corpus)
    payload = (json.dumps(corpus, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    summary.update({"data_bytes": len(payload), "data_sha256": hashlib.sha256(payload).hexdigest(),
                    "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    manifest = (json.dumps(summary, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    write_or_check(args.output, payload, args.check)
    write_or_check(args.manifest, manifest, args.check)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
