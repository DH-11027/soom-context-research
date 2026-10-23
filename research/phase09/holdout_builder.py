"""Phase09 synthetic data: typed plans, no selector or timing imports.

Separate same-model author; shared public grammar and study objective, not an
external blind evaluation.  The implementation author must not open this file
or the raw/gold corpus until the local pre-evaluation freeze is recorded.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import io
import json
import random
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEED = 2026102309
PARAMETERS = 3
FAMILY_STEPS = {
    "cold_terminal": (1, 1, 1),
    "short_repeated": (24, 24, 24),
    "short_churn": (12, 12, 12),
    "long_cheap_repeated": (24, 24, 24),
    "deep_finite_horizons": (3, 8, 32),
    "same_length_churn": (12, 12, 12),
    "working_set_fit": (24, 24, 24),
    "working_set_pressure": (24, 24, 24),
    "phase_shift": (24, 24, 24),
    "revisions_copy_reorder": (16, 16, 16),
    "scope_context_rotation": (16, 16, 16),
    "integrity_unsupported_recovery": (16, 16, 16),
}
NAMES = (("해온", "다솜", "도담"), ("수림", "윤슬", "서하"), ("한결", "이룸", "온유"))
PLACES = ("도서관", "카페", "공원")
ROTATION = ("a_time", "both_times", "b_both", "b_time", "a_both", "both_times")


def event(kind, target=None, value=None, source=None, targets=None):
    return {"kind": kind, "target": target, "value": value,
            "source": source, "targets": [] if targets is None else targets}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def history_digest(records):
    return hashlib.sha256(canonical(records).encode("utf-8")).hexdigest()


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
        "history": (f"{a} 모임의 시간 변경 순서를 설명해줘.", []),
        "execution": (f"{b} 모임 일정을 실제 달력에 등록했어?", []),
        "quote": (f"{a} 모임의 최초 요청 문장을 그대로 인용해줘.", []),
    }
    raw, required = table[kind]
    return raw, {"supported": bool(required), "required_fields": [list(f) for f in required]}


def payload_bytes(length, salt, style):
    token = hashlib.sha256(salt.encode("utf-8")).hexdigest()[:19]
    glyphs = ("unapplied_example", "가상문장을따라적음", "🌿e\u0301가상")[style]
    chunk = f"{glyphs}:{token};"
    count, rest = divmod(length, len(chunk.encode("utf-8")))
    raw = chunk * count + "x" * rest
    assert len(raw.encode("utf-8")) == length
    assert count >= 1
    return raw


class Author:
    def __init__(self, family, parameter):
        self.family = family
        self.p = parameter
        self.rng = random.Random(f"{SEED}:{family}:{parameter}")
        self.a, self.b, self.c = NAMES[parameter]
        self.entities = [self.a, self.b]
        self.at = self.rng.randint(-4, 15)
        self.bt = self.rng.randint(18, 36)

    def row(self, raw, gold):
        return {"id": f"v-{self.rng.getrandbits(120):030x}", "text": raw, "gold": gold}

    def setting(self, entity, field, value, deep=False):
        if field == "time":
            raw = (f"{entity} 약속, 최종 시각은 {value}시로 적어둘게." if deep
                   else f"{entity} 모임 시간은 {value}시로 확정해줘.")
        else:
            raw = (f"{entity} 약속 장소는 {value}로 적어둘게." if deep
                   else f"{entity} 모임 장소는 {value}로 확정해줘.")
        return self.row(raw, event("set", (entity, field), value))

    def add(self, entity, delta, deep=False):
        assert not deep or delta == 1
        raw = (f"{entity} 약속을 지금보다 한 시간 늦추자." if deep else
               f"{entity} 모임 시간을 {abs(delta)}시간 {'뒤로' if delta >= 0 else '앞으로'} 옮겨줘.")
        return self.row(raw, event("add", (entity, "time"), delta))

    def copy_time(self, target, source):
        return self.row(f"{target} 모임 시간은 {source} 모임 시간과 같게 맞춰줘.",
                        event("copy", (target, "time"), source=(source, "time")))

    def maybe_time(self, value):
        return self.row(f"{self.a} 모임과 {self.b} 모임 중 하나의 시간은 {value}시로 확정해줘.",
                        event("maybe_set", value=value,
                              targets=[(self.a, "time"), (self.b, "time")]))

    def frame(self, entity, field, value):
        raw = (f"{entity} 모임 시간은 {value}시로 재합의했어. 장소는 그대로야." if field == "time"
               else f"{entity} 모임 장소는 {value}로 확정해줘. 시간은 건드리지 않아.")
        return self.row(raw, event("set", (entity, field), value))

    def quote(self, length, salt, deep=True):
        before, after = (("표현 연습:「", "」라는 문장을 써봤어. 약속은 그대로야.") if deep else
                         ("예시일 뿐이야:「", "」 실제 변경은 없어."))
        payload = payload_bytes(length - len((before + after).encode("utf-8")), salt, self.p)
        raw = before + payload + after
        assert len(raw.encode("utf-8")) == length
        return self.row(raw, event("noop"))

    def quote_chars(self, chars, salt, deep=True):
        before, after = (("표현 연습:「", "」라는 문장을 써봤어. 약속은 그대로야.") if deep else
                         ("예시일 뿐이야:「", "」 실제 변경은 없어."))
        token = hashlib.sha256(salt.encode("utf-8")).hexdigest()[:19]
        glyph = ("z", "나", "🌿")[self.p]
        raw = before + token + glyph * (chars - len(before + token + after)) + after
        assert len(raw) == chars
        return self.row(raw, event("noop"))

    def base(self, offset=0):
        return [self.setting(self.a, "time", self.at + offset),
                self.setting(self.b, "time", self.bt - offset),
                self.setting(self.a, "place", PLACES[(self.p + offset) % 3]),
                self.setting(self.b, "place", PLACES[(self.p + offset + 1) % 3])]

    def step(self, rows, index, kind="both_times", *, entities=None, namespace="p9-v1",
             gold_applicable=True, gold_exclusion_reason=None):
        entities = list(self.entities if entities is None else entities)
        records = [{"seq": i, "id": row["id"], "text": row["text"]} for i, row in enumerate(rows)]
        query, contract = question(entities, kind)
        return {"step_id": f"s{index:03d}", "parser_namespace": namespace,
                "public": {"records": records, "entities": entities,
                           "snapshot": snapshot(records), "query": query},
                "gold": copy.deepcopy([row["gold"] for row in rows]),
                "question_contract": contract, "expected_integrity": "valid",
                "gold_applicable": gold_applicable, "gold_exclusion_reason": gold_exclusion_reason}


def build_stream(family, parameter):
    w = Author(family, parameter)
    a, b, c, p = w.a, w.b, w.c, parameter
    base = w.base()
    n = FAMILY_STEPS[family][p]
    steps = []
    if family == "cold_terminal":
        length = (850, 18000, 68000)[p]
        rows = base + [w.add(a, 1, deep=True), w.copy_time(b, a),
                       w.quote(length, f"cold:{p}")]
        steps = [w.step(rows, 0)]
    elif family == "short_repeated":
        rows = base + [w.copy_time(b, a), w.add(a, 1, deep=True),
                       w.quote_chars(190 + 20 * p, f"short:{p}:one"),
                       w.quote_chars(255, f"short:{p}:edge", deep=False)]
        steps = [w.step(rows, i, ROTATION[i % len(ROTATION)]) for i in range(n)]
    elif family == "short_churn":
        for i in range(n):
            rows = w.base(2 * i + 1)
            rows += [w.add(a, i - 5), w.copy_time(b, a),
                     w.setting(a, "time", w.at + 3 * i, deep=True)]
            rows += [w.quote_chars(180 + (j % 4) * 17, f"churn:{p}:{i}:{j}", deep=(j % 2 == 0))
                     for j in range(6)]
            steps.append(w.step(rows, i, ROTATION[i % len(ROTATION)]))
    elif family == "long_cheap_repeated":
        length = (2400, 14500, 62500)[p]
        rows = base + [w.copy_time(b, a), w.add(a, -3),
                       w.quote(length, f"cheap:{p}", deep=False)]
        steps = [w.step(rows, i, ROTATION[i % len(ROTATION)]) for i in range(n)]
    elif family == "deep_finite_horizons":
        # Horizon and input length are deliberately joint design parameters.
        # This is not a factorial estimate of an isolated length/horizon effect.
        length = (2400, 14500, 62500)[p]
        rows = base + [w.copy_time(b, a), w.add(a, -3), w.quote(length, f"deep:{p}")]
        steps = [w.step(rows, i, ROTATION[i % len(ROTATION)]) for i in range(n)]
    elif family == "same_length_churn":
        length = (2600, 12600, 44000)[p]
        persistent = w.quote(length, f"collision:{p}:resident")
        for i in range(n):
            # All variable records have identical byte AND Unicode lengths.
            # Every third visit returns to one exact record; other visits churn.
            quote = persistent if i % 3 == 0 else w.quote(length, f"collision:{p}:{i}")
            assert len(quote["text"]) == len(persistent["text"])
            steps.append(w.step(base + [w.copy_time(b, a), quote], i, "both_times"))
    elif family == "working_set_fit":
        count, total = p + 2, (14000, 34000, 54000)[p]
        lengths = [total // count + (j < total % count) for j in range(count)]
        quotes = [w.quote(length, f"fit:{p}:{j}") for j, length in enumerate(lengths)]
        rows = base + [w.add(a, 2), w.copy_time(b, a)] + quotes
        steps = [w.step(rows, i, ROTATION[i % len(ROTATION)]) for i in range(n)]
    elif family == "working_set_pressure":
        lengths = ((36000, 37000), (24000, 25000, 26000), (19000, 20000, 21000, 22000))[p]
        quotes = [w.quote(length, f"pressure:{p}:{j}") for j, length in enumerate(lengths)]
        w.rng.shuffle(quotes)
        rows = base + [w.copy_time(b, a), w.add(a, 1, deep=True)] + quotes
        steps = [w.step(rows, i, ROTATION[i % len(ROTATION)]) for i in range(n)]
    elif family == "phase_shift":
        length = (9000, 20000, 30000)[p]
        old = [w.quote(length, f"shift:{p}:old:{j}") for j in range(2)]
        new = [w.quote(length, f"shift:{p}:new:{j}") for j in range(2)]
        for i in range(n):
            if i < 8:
                quotes = old
            elif i < 12:
                quotes = [w.quote(length, f"shift:{p}:single:{i}", deep=(i % 2 == 0))]
            else:
                quotes = new
            rows = base + [w.copy_time(b, a)]
            if i >= 8:
                rows += [w.setting(a, "time", w.at + 11, deep=True)]
            steps.append(w.step(rows + quotes, i, ROTATION[i % len(ROTATION)]))
    elif family == "revisions_copy_reorder":
        pool = [w.add(a, -2), w.copy_time(b, a), w.add(b, 1, deep=True),
                w.copy_time(a, b), w.setting(b, "time", w.bt + 8, deep=True)]
        for i in range(n):
            rows = copy.deepcopy(base)
            value = w.at + w.rng.randint(-8, 25)
            # Same ID, changed raw value: exact raw identity must govern reuse.
            rows[0]["text"] = f"{a} 모임 시간은 {value}시로 확정해줘."
            rows[0]["gold"] = event("set", (a, "time"), value)
            order = w.rng.sample(range(len(pool)), len(pool))
            if i % 4 == 2:
                order.pop(0)
            rows += [pool[j] for j in order]
            rows += [w.quote_chars((255, 256, 257)[p], f"revision-boundary:{p}:{i // 4}")]
            steps.append(w.step(rows, i))
    elif family == "scope_context_rotation":
        quote = w.quote(1600 + p * 300, f"context:{p}")
        for i in range(n):
            rows = base + [w.copy_time(b, a), w.maybe_time(w.bt + 5)]
            rows += [w.frame(a if i % 2 == 0 else b, "place", PLACES[(p + i) % 3])]
            if i in (6, 7, 12, 15):
                rows += [w.setting(a, "time", w.at + 7, deep=True), w.copy_time(b, a)]
            rows += [quote]
            roster = [a, c] if i in (3, 9, 14) else ([b, a] if i % 4 == 1 else [a, b])
            applicable = set(roster) == {a, b}
            steps.append(w.step(rows, i, ROTATION[i % len(ROTATION)], entities=roster,
                                namespace=f"p9-v{(i // 3) % 3 + 1}",
                                gold_applicable=applicable,
                                gold_exclusion_reason=None if applicable else "entity_membership_undefined"))
    elif family == "integrity_unsupported_recovery":
        rows = base + [w.add(a, 4), w.copy_time(b, a),
                       w.quote(2200 + p * 400, f"recovery:{p}")]
        for i in range(n):
            kind = {3: "history", 8: "execution", 14: "quote"}.get(i, ROTATION[i % len(ROTATION)])
            current = rows + ([w.setting(a, "time", w.at + 19, deep=True), w.copy_time(b, a)]
                              if i == n - 1 else [])
            step = w.step(current, i, kind)
            if i in (2, 5, 9, 13):
                step["expected_integrity"] = "invalid"
                step["gold_applicable"] = False
                step["gold_exclusion_reason"] = "invalid_snapshot"
                public = step["public"]
                if i == 2:
                    public["snapshot"]["digest"] = "9" * 64
                elif i == 5:
                    if p == 0:
                        public["records"][-1]["seq"] += 1
                        public["snapshot"] = snapshot(public["records"])
                    elif p == 1:
                        public["records"][0]["text"] += " 수정됨"
                    else:
                        public["records"][-1], public["records"][-2] = public["records"][-2], public["records"][-1]
                        step["gold"][-1], step["gold"][-2] = step["gold"][-2], step["gold"][-1]
                        public["snapshot"] = snapshot(public["records"])
                elif i == 9:
                    public["records"].pop(1)
                    step["gold"].pop(1)
                else:
                    public["snapshot"]["head"] += 1
            steps.append(step)
    else:
        raise ValueError(family)
    assert len(steps) == n
    return {"id": f"p9-holdout-{family}-{p:02d}", "family": family, "split": "holdout", "steps": steps}


def build_corpus():
    return [build_stream(family, p) for family in FAMILY_STEPS for p in range(PARAMETERS)]


def execute_gold(events, entities):
    """Independent author-side typed plan check; raw text is never parsed."""
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
    assert states and all(all(v is not None for v in state) for state in states)
    return states


def validate_structure(corpus):
    assert len(corpus) == 36 and len({s["id"] for s in corpus}) == 36
    counts, families = Counter(), {}
    all_raw, all_chars = [], []
    for stream in corpus:
        family = stream["family"]
        assert family in FAMILY_STEPS and stream["split"] == "holdout"
        p = int(stream["id"].rsplit("-", 1)[1])
        assert len(stream["steps"]) == FAMILY_STEPS[family][p]
        assert len({q["step_id"] for q in stream["steps"]}) == len(stream["steps"])
        step_raw_histories, raw_values, byte_lengths, char_lengths = [], [], [], []
        for q in stream["steps"]:
            public = q["public"]
            assert set(public) == {"records", "entities", "snapshot", "query"}
            records = public["records"]
            assert len(records) == len(q["gold"])
            assert all(set(r) == {"seq", "id", "text"} for r in records)
            assert len({r["id"] for r in records}) == len(records)
            assert len(public["entities"]) == len(set(public["entities"])) == 2
            expected = public["snapshot"]
            valid = ([r["seq"] for r in records] == list(range(expected["head"] + 1))
                     and history_digest(records) == expected["digest"])
            assert valid == (q["expected_integrity"] == "valid")
            if family in {"short_repeated", "short_churn"}:
                assert max(len(r["text"]) for r in records) < 256
            contract = q["question_contract"]
            assert set(contract) == {"supported", "required_fields"}
            fields = {(e, f) for e in public["entities"] for f in ("time", "place")}
            required = {tuple(f) for f in contract["required_fields"]}
            assert len(required) == len(contract["required_fields"])
            assert required <= fields and bool(required) == contract["supported"]
            supported = {"두 모임의 현재 시간을 알려줘.": {(e, "time") for e in public["entities"]}}
            for e in public["entities"]:
                supported[f"{e} 모임은 지금 몇 시야?"] = {(e, "time")}
                supported[f"{e} 모임의 시간과 장소를 알려줘."] = {(e, "time"), (e, "place")}
            assert supported.get(public["query"], set()) == required
            assert (public["query"] in supported) == contract["supported"]
            if q["gold_applicable"]:
                assert valid and q["gold_exclusion_reason"] is None
                assert all(ev["kind"] == "set" for ev in q["gold"][:4])
                assert {tuple(ev["target"]) for ev in q["gold"][:4]} == fields
                execute_gold(q["gold"], public["entities"])
            else:
                assert q["gold_exclusion_reason"] in {"invalid_snapshot", "entity_membership_undefined"}
            counts["steps"] += 1
            counts["valid_steps"] += valid
            counts["invalid_steps"] += not valid
            counts["gold_applicable_steps"] += q["gold_applicable"]
            counts["unsupported_questions"] += not contract["supported"]
            counts["gold_supported_steps"] += q["gold_applicable"] and contract["supported"]
            if q["gold_exclusion_reason"]:
                counts["excluded_" + q["gold_exclusion_reason"]] += 1
            texts = [r["text"] for r in records]
            step_raw_histories.append(canonical(texts))
            raw_values.extend(texts)
            byte_lengths.extend(len(x.encode("utf-8")) for x in texts)
            char_lengths.extend(len(x) for x in texts)
        families.setdefault(family, []).append({
            "stream_id": stream["id"], "steps": len(stream["steps"]),
            "raw_record_occurrences": len(raw_values), "distinct_raw_records": len(set(raw_values)),
            "distinct_ordered_raw_histories": len(set(step_raw_histories)),
            "record_utf8_bytes_min_max": [min(byte_lengths), max(byte_lengths)],
            "record_unicode_characters_min_max": [min(char_lengths), max(char_lengths)],
            "history_raw_utf8_total": sum(byte_lengths),
            "max_history_raw_utf8_bytes": max(sum(len(r["text"].encode("utf-8")) for r in q["public"]["records"]) for q in stream["steps"]),
        })
        all_raw.extend(byte_lengths)
        all_chars.extend(char_lengths)
    assert counts["steps"] == 622
    return {"seed": SEED, "families": len(FAMILY_STEPS), "streams": len(corpus),
            "parameters_per_family": PARAMETERS, "family_steps": FAMILY_STEPS,
            **dict(counts), "raw_record_occurrences": len(all_raw),
            "record_utf8_bytes_min_max": [min(all_raw), max(all_raw)],
            "record_unicode_characters_min_max": [min(all_chars), max(all_chars)],
            "raw_occurrences_at_or_above_256_characters": sum(x >= 256 for x in all_chars),
            "input_history_raw_utf8_total": sum(all_raw), "family_input_description": families,
            "design": {"raw_working_set_fit_totals": [14000, 34000, 54000],
                       "raw_working_set_pressure_totals": [73000, 75000, 82000],
                       "working_set_counts": [2, 3, 4],
                       "capacity_note": "raw-only sizes; exclude context/payload/metadata, not measured cache occupancy",
                       "repetition_note": "finite termination, fixed repeats, raw churn, same-length collisions and two phase changes",
                       "length_note": "Unicode/codepoint lengths and UTF-8 bytes both recorded; large raw is controlled noop quote"},
            "schema_and_gold_checks": "passed", "selector_evaluated": False,
            "authorship": "separate same-model agent, shared public grammar/design; not external blind evaluation"}


def write_or_check(path, payload, check):
    if check or path.exists():
        assert path.read_bytes() == payload, f"Refusing different bytes at {path}"
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=HERE / "data/holdout.json.gz")
    ap.add_argument("--manifest", type=Path, default=HERE / "data/holdout_manifest.json")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    corpus = build_corpus()
    manifest = validate_structure(corpus)
    payload = (json.dumps(corpus, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0) as zipped:
        zipped.write(payload)
    compressed = buffer.getvalue()
    assert gzip.decompress(compressed) == payload
    manifest.update({"data_bytes": len(compressed), "data_sha256": hashlib.sha256(compressed).hexdigest(),
                     "uncompressed_bytes": len(payload), "uncompressed_sha256": hashlib.sha256(payload).hexdigest(),
                     "compression": "gzip, mtime=0, empty filename, default level 9",
                     "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    encoded_manifest = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    write_or_check(args.output, compressed, args.check)
    write_or_check(args.manifest, encoded_manifest, args.check)
    print(json.dumps({k: manifest[k] for k in ("seed", "families", "streams", "steps", "data_bytes", "data_sha256", "builder_sha256", "schema_and_gold_checks")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
