"""Phase09 internal holdout author; no selector, runtime, or result imports.

The author shares the public finite grammar and study design. Gold is composed
as typed plans before evaluation. This is same-model role separation, not an
external blind natural-language test. Timing is deliberately absent here.
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
SEED = 2026102209
PARAMETERS, STEPS = 3, 12
FAMILIES = (
    "short_repeated", "short_churn", "long_cheap", "long_deep_repeat",
    "long_deep_churn", "fit_working_set", "pressure_working_set",
    "phase_shift", "same_length_misses", "revisions_copy_context",
    "scope_ambiguity", "integrity_unsupported_recovery",
)
NAMES = (("소담", "이솔", "가온"), ("다온", "윤슬", "해온"), ("도담", "수안", "시온"))
PLACES = ("도서관", "카페", "공원")
RAW_BYTE_BANDS = ((900, 1900), (9000, 18000), (57000, 74000))
NAMESPACE = "p9-semantics-1"


def event(kind, target=None, value=None, source=None, targets=None):
    return {"kind": kind, "target": target, "value": value,
            "source": source, "targets": [] if targets is None else targets}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(records):
    return hashlib.sha256(canonical(records).encode("utf-8")).hexdigest()


def snapshot(records):
    return {"head": len(records) - 1, "digest": digest(records)}


def question(entities, kind):
    a, b = entities
    pairs = {
        "a": (f"{a} 모임은 지금 몇 시야?", [(a, "time")]),
        "b": (f"{b} 모임은 지금 몇 시야?", [(b, "time")]),
        "ab": ("두 모임의 현재 시간을 알려줘.", [(a, "time"), (b, "time")]),
        "ap": (f"{a} 모임의 시간과 장소를 알려줘.", [(a, "time"), (a, "place")]),
        "bp": (f"{b} 모임의 시간과 장소를 알려줘.", [(b, "time"), (b, "place")]),
        "unsupported_history": (f"{a} 약속의 변경 이유를 시간순으로 설명해줘.", []),
        "unsupported_execution": (f"{b} 약속이 실제 달력에 저장됐는지 알려줘.", []),
        "unsupported_quote": ("이 대화에서 가장 오래된 요청을 그대로 인용해줘.", []),
    }
    text, fields = pairs[kind]
    return text, {"supported": bool(fields), "required_fields": [list(x) for x in fields]}


def payload(nbytes, salt):
    """Salted, same-composition Unicode; equal byte targets also equal lengths."""
    mark = hashlib.sha256(salt.encode("utf-8")).hexdigest()[:19]
    chunk = f"가상메모[{mark}]낱말연습;"
    count, tail = divmod(nbytes, len(chunk.encode("utf-8")))
    text = chunk * count + "한" * (tail // 3) + "z" * (tail % 3)
    assert len(text.encode("utf-8")) == nbytes
    return text


class Author:
    def __init__(self, family, p):
        self.family, self.p = family, p
        self.rng = random.Random(f"{SEED}/{family}/{p}")
        self.a, self.b, self.c = NAMES[p]
        self.entities = [self.a, self.b]
        self.at, self.bt = self.rng.randint(-5, 8), self.rng.randint(13, 29)

    def row(self, text, gold):
        return {"id": f"p9-{self.rng.getrandbits(104):026x}", "text": text, "gold": gold}

    def set(self, who, field, value, deep=False):
        if field == "time":
            text = (f"{who} 약속, 최종 시각은 {value}시로 적어둘게." if deep else
                    f"{who} 모임 시간은 {value}시로 확정해줘.")
        else:
            text = (f"{who} 약속 장소는 {value}로 적어둘게." if deep else
                    f"{who} 모임 장소는 {value}로 확정해줘.")
        return self.row(text, event("set", (who, field), value))

    def add(self, who, amount=1, deep=False):
        assert not deep or amount == 1
        text = (f"{who} 약속을 지금보다 한 시간 늦추자." if deep else
                f"{who} 모임 시간을 {abs(amount)}시간 {'뒤로' if amount >= 0 else '앞으로'} 옮겨줘.")
        return self.row(text, event("add", (who, "time"), amount))

    def copy(self, target, source):
        return self.row(f"{target} 모임 시간은 {source} 모임 시간과 같게 맞춰줘.",
                        event("copy", (target, "time"), source=(source, "time")))

    def maybe(self, value):
        return self.row(f"{self.a} 모임과 {self.b} 모임 중 하나의 시간은 {value}시로 확정해줘.",
                        event("maybe_set", value=value,
                              targets=[(self.a, "time"), (self.b, "time")]))

    def frame(self, who, field, value):
        text = (f"{who} 모임 시간은 {value}시로 재합의했어. 장소는 그대로야." if field == "time" else
                f"{who} 모임 장소는 {value}로 확정해줘. 시간은 건드리지 않아.")
        return self.row(text, event("set", (who, field), value))

    def quote(self, nbytes, salt, deep=True):
        left, right = (("표현 연습:「", "」라는 문장을 써봤어. 약속은 그대로야.") if deep else
                       ("예시일 뿐이야:「", "」 실제 변경은 없어."))
        available = nbytes - len((left + right).encode("utf-8"))
        assert available >= 100
        text = left + payload(available, f"{self.family}:{self.p}:{salt}") + right
        assert len(text.encode("utf-8")) == nbytes
        return self.row(text, event("noop"))

    def base(self, offset=0):
        return [self.set(self.a, "time", self.at + offset),
                self.set(self.b, "time", self.bt - 2 * offset),
                self.set(self.a, "place", PLACES[self.p]),
                self.set(self.b, "place", PLACES[(self.p + 1) % 3])]

    def length(self):
        return self.rng.randint(*RAW_BYTE_BANDS[self.p])

    def step(self, rows, i, kind="ab", *, entities=None, version=1):
        entities = list(self.entities if entities is None else entities)
        records = [{"seq": j, "id": r["id"], "text": r["text"]} for j, r in enumerate(rows)]
        text, contract = question(entities, kind)
        applicable = set(entities) == set(self.entities)
        return {"step_id": f"q{i:02d}", "parser_namespace": f"p9-semantics-{version}",
                "public": {"records": records, "entities": entities,
                           "snapshot": snapshot(records), "query": text},
                "gold": copy.deepcopy([r["gold"] for r in rows]),
                "question_contract": contract, "expected_integrity": "valid",
                "gold_applicable": applicable,
                "gold_exclusion_reason": None if applicable else "entity_membership_undefined"}


def build_stream(family, p):
    x = Author(family, p)
    a, b, c = x.a, x.b, x.c
    base = x.base()
    kinds = ("bp", "ab", "a", "ap", "b", "ab", "ap", "b", "bp", "a", "ab", "bp")
    steps = []

    if family == "short_repeated":
        rows = base + [x.add(b, -3), x.copy(a, b), x.add(a, deep=True),
                       x.set(b, "place", PLACES[(p + 2) % 3], deep=True),
                       x.quote(310 + 17 * p, "short-fixed", deep=True)]
        steps = [x.step(rows, i, kinds[i]) for i in range(STEPS)]

    elif family == "short_churn":
        for i in range(STEPS):
            rows = x.base(i - 3) + [x.add(a, 2 * i + 1), x.copy(b, a), x.add(a, -i - 1)]
            if i % 2 == 0:
                rows += [x.maybe(x.bt + i), x.set(b, "time", x.at + 2 * i, deep=True)]
            rows += [x.quote(260 + 23 * p + 7 * j, f"short:{i}:{j}", deep=j % 2 == 0)
                     for j in range(3 + (i % 4))]
            steps.append(x.step(rows, i, kinds[i]))

    elif family in ("long_cheap", "long_deep_repeat", "long_deep_churn"):
        length = x.length()
        fixed = x.quote(length, "persistent", deep=family != "long_cheap")
        prefix = base + [x.add(a, -2), x.copy(b, a), x.add(b, deep=True)]
        for i in range(STEPS):
            q = x.quote(length, f"one-use-{i}") if family == "long_deep_churn" else fixed
            # Two distinct placements of pure quotes exercise current demand without changing gold.
            rows = prefix[:5] + [q] + prefix[5:] if i % 3 == 0 else prefix + [q]
            steps.append(x.step(rows, i, kinds[i]))

    elif family in ("fit_working_set", "pressure_working_set"):
        count = (2, 3, 5)[p]
        bounds = ((14000, 22000), (28000, 38000), (48000, 58000)) if family == "fit_working_set" else (
            (77000, 89000), (87000, 102000), (102000, 116000))
        total = x.rng.randint(*bounds[p])
        lengths = [total // count + (j < total % count) for j in range(count)]
        assert (sum(lengths) < 60000) == (family == "fit_working_set")
        assert all(length < 60000 for length in lengths)
        pool = [x.quote(length, f"set:{j}") for j, length in enumerate(lengths)]
        for i in range(STEPS):
            # Reorder unchanged exact records, rather than copying the Phase08 fixed-history design.
            rotation = i % count
            ordered = pool[rotation:] + pool[:rotation]
            rows = base + [x.copy(a, b), x.add(b, -2)] + ordered
            steps.append(x.step(rows, i, kinds[i]))

    elif family == "phase_shift":
        length = x.length()
        old = x.quote(length, "old" )
        middle = x.quote(length, "middle")
        for i in range(STEPS):
            if i < 5:
                q = old
            elif i < 8:
                q = middle
            elif i == 8:
                q = old
            else:
                q = x.quote(length, f"terminal-one-use:{i}")
            rows = base + [x.copy(a, b), x.add(b, i % 2 + 1), q]
            steps.append(x.step(rows, i, kinds[i]))

    elif family == "same_length_misses":
        length = x.length()
        pool = [x.quote(length, f"collision:{j}") for j in range(5)]
        assert len({len(q["text"]) for q in pool}) == 1
        assert len({q["text"] for q in pool}) == len(pool)
        schedule = (0, 1, 0, 2, 3, 0, 4, 2, 4, 1, 0, 3)
        for i, index in enumerate(schedule):
            rows = base + [x.add(a, -1), x.copy(b, a), pool[index]]
            steps.append(x.step(rows, i, kinds[i], version=2 if i in (4, 7) else 1))

    elif family == "revisions_copy_context":
        fixed = x.quote(x.length(), "revision-context")
        source = x.set(a, "time", x.at + 2, deep=True)
        copy_ab, copy_ba = x.copy(a, b), x.copy(b, a)
        for i in range(STEPS):
            edited = copy.deepcopy(source)
            value = x.at + ((i * 7) % 19)
            edited["text"] = f"{a} 약속, 최종 시각은 {value}시로 적어둘게."
            edited["gold"] = event("set", (a, "time"), value)
            operations = [edited, copy_ba, x.add(a, deep=True), copy_ab]
            if i % 3 == 1:
                operations = [copy_ba, edited, copy_ab, x.add(b, -2)]
            elif i % 3 == 2:
                operations = [edited, x.add(a, -3), copy_ba]
            roster = [a, c] if i in (3, 9) else [b, a] if i in (2, 5, 10) else [a, b]
            rows = base + operations + [fixed]
            steps.append(x.step(rows, i, kinds[i], entities=roster, version=1 + (i % 3 == 0)))

    elif family == "scope_ambiguity":
        for i in range(STEPS):
            rows = base + [x.maybe(x.at + 6), x.add(a, deep=True)]
            if i < 4:
                rows += [x.frame(b, "place", PLACES[(p + 2) % 3])]
            elif i < 8:
                rows += [x.copy(b, a), x.frame(a, "time", x.bt + i)]
            else:
                rows += [x.set(a, "time", x.at + i, deep=True), x.copy(b, a),
                         x.frame(a, "place", PLACES[(p + i) % 3])]
            steps.append(x.step(rows, i, kinds[i]))

    elif family == "integrity_unsupported_recovery":
        fixed = x.quote((1300, 14000, 59000)[p], "recovery")
        rows = base + [x.add(b, -2), x.copy(a, b), fixed]
        kinds_here = ("ab", "a", "bp", "unsupported_history", "ap", "ab",
                      "unsupported_execution", "bp", "ab", "unsupported_quote", "a", "ab")
        for i in range(STEPS):
            current = rows + ([x.add(a, deep=True)] if i >= 8 else [])
            s = x.step(current, i, kinds_here[i])
            if i in (1, 4, 7, 10):
                s["expected_integrity"], s["gold_applicable"] = "invalid", False
                s["gold_exclusion_reason"] = "invalid_snapshot"
                pub = s["public"]
                if i == 1:
                    pub["snapshot"]["head"] += 2
                elif i == 4:
                    pub["records"][0]["text"] += " 덧붙인 기록"
                elif i == 7:
                    pub["records"][-1]["seq"] += 3
                    pub["snapshot"] = snapshot(pub["records"])
                else:
                    pub["snapshot"]["digest"] = "0" * 64
            steps.append(s)
    else:
        raise ValueError(family)

    return {"id": f"p9-holdout-{family}-{p:02d}", "family": family, "split": "holdout", "steps": steps}


def build_corpus():
    return [build_stream(family, p) for family in FAMILIES for p in range(PARAMETERS)]


def execute_gold(events, entities):
    """Typed-plan self-consistency, not raw interpretation or selector validation."""
    fields = [(e, f) for e in entities for f in ("time", "place")]
    ix = {f: j for j, f in enumerate(fields)}
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
                pos = ix[tuple(field)]
                after = list(state)
                if kind in ("set", "maybe_set"):
                    after[pos] = ev["value"]
                elif kind == "add":
                    assert type(after[pos]) is int
                    after[pos] += ev["value"]
                else:
                    after[pos] = state[ix[tuple(ev["source"])]]
                following.add(tuple(after))
        states = following
    assert states and all(all(v is not None for v in state) for state in states)
    return states


def validate_structure(corpus):
    assert len(corpus) == 36 and len({s["id"] for s in corpus}) == 36
    counts = Counter()
    lengths, chars, histories, typed, full_inputs = [], [], set(), set(), set()
    family_summary = {}
    for stream in corpus:
        assert stream["family"] in FAMILIES and stream["split"] == "holdout"
        assert len(stream["steps"]) == STEPS
        assert len({s["step_id"] for s in stream["steps"]}) == STEPS
        f = family_summary.setdefault(stream["family"], {"steps": 0, "record_occurrences": 0,
            "raw_bytes_sum_over_steps": 0, "max_record_bytes": 0, "min_record_bytes": 10**20,
            "unique_raw_histories": set(), "unique_typed_arrays_gold_applicable": set(),
            "max_history_bytes": 0, "max_quote_bytes_per_history": 0})
        for s in stream["steps"]:
            pub = s["public"]
            assert set(pub) == {"records", "entities", "snapshot", "query"}
            records, gold = pub["records"], s["gold"]
            assert len(records) == len(gold)
            assert len({r["id"] for r in records}) == len(records)
            assert all(set(r) == {"seq", "id", "text"} for r in records)
            assert len(pub["entities"]) == len(set(pub["entities"])) == 2
            expected = pub["snapshot"]
            valid = ([r["seq"] for r in records] == list(range(expected["head"] + 1)) and
                     digest(records) == expected["digest"])
            assert valid == (s["expected_integrity"] == "valid")
            fields = {(e, f) for e in pub["entities"] for f in ("time", "place")}
            required = {tuple(v) for v in s["question_contract"]["required_fields"]}
            assert required <= fields and bool(required) == s["question_contract"]["supported"]
            table = {"두 모임의 현재 시간을 알려줘.": {(e, "time") for e in pub["entities"]}}
            for e in pub["entities"]:
                table[f"{e} 모임은 지금 몇 시야?"] = {(e, "time")}
                table[f"{e} 모임의 시간과 장소를 알려줘."] = {(e, "time"), (e, "place")}
            assert table.get(pub["query"], set()) == required
            assert (pub["query"] in table) == s["question_contract"]["supported"]
            if s["gold_applicable"]:
                assert valid and s["gold_exclusion_reason"] is None
                assert all(ev["kind"] == "set" for ev in gold[:4])
                assert {tuple(ev["target"]) for ev in gold[:4]} == fields
                execute_gold(gold, pub["entities"])
                typed.add(canonical(gold))
                f["unique_typed_arrays_gold_applicable"].add(canonical(gold))
            else:
                assert s["gold_exclusion_reason"] in {"invalid_snapshot", "entity_membership_undefined"}
            if stream["family"] in {"short_repeated", "short_churn"}:
                assert all(len(r["text"]) < 256 for r in records)
            bl = [len(r["text"].encode("utf-8")) for r in records]
            cl = [len(r["text"]) for r in records]
            lengths.extend(bl)
            chars.extend(cl)
            raw_history = canonical([r["text"] for r in records])
            if valid:
                histories.add(raw_history)
                f["unique_raw_histories"].add(raw_history)
            full_inputs.add(canonical([pub, s["parser_namespace"]]))
            f["steps"] += 1
            f["record_occurrences"] += len(records)
            f["raw_bytes_sum_over_steps"] += sum(bl)
            f["max_history_bytes"] = max(f["max_history_bytes"], sum(bl))
            f["max_quote_bytes_per_history"] = max(f["max_quote_bytes_per_history"],
                sum(n for n, ev in zip(bl, gold) if ev["kind"] == "noop"))
            f["min_record_bytes"] = min(f["min_record_bytes"], *bl)
            f["max_record_bytes"] = max(f["max_record_bytes"], *bl)
            counts["steps"] += 1
            counts["valid_steps"] += valid
            counts["invalid_steps"] += not valid
            counts["gold_applicable_steps"] += s["gold_applicable"]
            counts["unsupported_questions"] += not s["question_contract"]["supported"]
            counts["gold_supported_steps"] += s["gold_applicable"] and s["question_contract"]["supported"]
            if s["gold_exclusion_reason"]:
                counts["excluded_" + s["gold_exclusion_reason"]] += 1
    for f in family_summary.values():
        f["unique_raw_histories"] = len(f["unique_raw_histories"])
        f["unique_typed_arrays_gold_applicable"] = len(f["unique_typed_arrays_gold_applicable"])
    return {"seed": SEED, "families": 12, "streams": len(corpus),
        "parameters_per_family": PARAMETERS, "steps_per_stream": STEPS, **dict(counts),
        "schema_and_typed_plan_checks": "passed", "selector_evaluated": False,
        "raw_length_bands_bytes": RAW_BYTE_BANDS,
        "record_occurrences": len(lengths), "record_bytes_min_max": [min(lengths), max(lengths)],
        "record_characters_min_max": [min(chars), max(chars)],
        "raw_bytes_sum_over_steps": sum(lengths),
        "valid_unique_raw_histories": len(histories),
        "exact_typed_arrays_gold_applicable": len(typed), "exact_public_and_namespace": len(full_inputs),
        "family_distribution": family_summary,
        "authorship": "separate same-model author; shared finite grammar and study design; not external blind evaluation",
        "semantic_boundary": "long payloads are grammar-defined noop quotes; no general natural-language or execution-evidence claim"}


def put_or_check(path, data, check):
    if check or path.exists():
        assert path.read_bytes() == data, f"Refusing to replace different bytes at {path}"
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def deterministic_gzip(data):
    """No original filename, zero mtime, stable GzipFile header (OS=255)."""
    target = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=target, compresslevel=9, mtime=0) as out:
        out.write(data)
    return target.getvalue()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=HERE / "data/holdout.json.gz")
    ap.add_argument("--manifest", type=Path, default=HERE / "data/holdout_manifest.json")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    corpus = build_corpus()
    summary = validate_structure(corpus)
    data = (json.dumps(corpus, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    compressed = deterministic_gzip(data)
    assert gzip.decompress(compressed) == data
    summary.update(data_file="data/holdout.json.gz", data_bytes=len(compressed),
                   data_sha256=hashlib.sha256(compressed).hexdigest(),
                   uncompressed_data_bytes=len(data), uncompressed_data_sha256=hashlib.sha256(data).hexdigest(),
                   compression="gzip level=9, filename='', mtime=0; serialization-only change before freeze",
                   builder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    manifest = (json.dumps(summary, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if args.check or args.output.exists():
        assert gzip.decompress(args.output.read_bytes()) == data, "Decompressed content differs"
    put_or_check(args.output, compressed, args.check)
    put_or_check(args.manifest, manifest, args.check)
    # Report metadata only; no raw records, typed labels, selector outcomes or timing.
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
