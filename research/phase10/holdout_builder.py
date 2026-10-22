"""Phase10 internal holdout author; no selector, runtime, or result imports.

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
SEED = 2026102210
PARAMETERS = 4
HORIZONS = (2, 8, 24, 64)
FAMILIES = (
    "short_repeated", "short_churn", "long_cheap", "long_deep_repeat",
    "long_deep_churn", "fit_working_set", "pressure_working_set",
    "phase_shift", "same_length_misses", "revisions_copy_context",
    "scope_ambiguity", "integrity_unsupported_recovery",
)
NAMES = (("해나", "루리", "보미"), ("하람", "세아", "온유"), ("단비", "예담", "로운"), ("새론", "미루", "나림"))
PLACES = ("도서관", "카페", "공원")
RAW_BYTE_BANDS = ((850, 2100), (7000, 19000), (48000, 63000), (68000, 83000))
UNICODE_STYLES = ("ascii", "hangul", "emoji", "mixed")


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


def payload(nbytes, salt, style):
    """Exact bytes, valid Unicode, no newline; equal style/bytes yields equal chars."""
    mark = hashlib.sha256(salt.encode("utf-8")).hexdigest()[:23]
    chunks = {"ascii": f"scratch_{mark}_imaginary;",
              "hangul": f"비망록{mark}아무변경없는낱말연습;",
              "emoji": f"🪶🧭🌱{mark}🔷🫧;",
              "mixed": f"draft|가상낙서|🪶🧭|{mark}|;"}
    chunk = chunks[style]
    count, tail = divmod(nbytes, len(chunk.encode("utf-8")))
    # Tail respects exact byte length without partial UTF-8 code points.
    fillers = {"ascii": "a", "hangul": "나", "emoji": "🌿", "mixed": "한"}
    filler = fillers[style]
    size = len(filler.encode("utf-8"))
    text = chunk * count + filler * (tail // size) + "x" * (tail % size)
    assert len(text.encode("utf-8")) == nbytes
    return text


class Author:
    def __init__(self, family, p):
        self.family, self.p = family, p
        self.horizon = HORIZONS[p]
        self.band = (p + FAMILIES.index(family)) % 4
        self.style = UNICODE_STYLES[(2 * p + FAMILIES.index(family)) % 4]
        self.rng = random.Random(f"{SEED}/{family}/{p}")
        self.a, self.b, self.c = NAMES[p]
        self.entities = [self.a, self.b]
        self.at, self.bt = self.rng.randint(-17, 7), self.rng.randint(16, 41)

    def row(self, text, gold):
        return {"id": f"p10-{self.rng.getrandbits(104):026x}", "text": text, "gold": gold}

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

    def quote(self, nbytes, salt, deep=True, style=None):
        left, right = (("표현 연습:「", "」라는 문장을 써봤어. 약속은 그대로야.") if deep else
                       ("예시일 뿐이야:「", "」 실제 변경은 없어."))
        available = nbytes - len((left + right).encode("utf-8"))
        assert available >= 80
        text = left + payload(available, f"{self.family}:{self.p}:{salt}", self.style if style is None else style) + right
        assert len(text.encode("utf-8")) == nbytes
        return self.row(text, event("noop"))

    def base(self, offset=0):
        return [self.set(self.a, "time", self.at + offset),
                self.set(self.b, "time", self.bt - 2 * offset),
                self.set(self.a, "place", PLACES[self.p % 3]),
                self.set(self.b, "place", PLACES[(self.p + 1) % 3])]

    def length(self):
        return self.rng.randint(*RAW_BYTE_BANDS[self.band])

    def step(self, rows, i, kind="ab", *, entities=None, version=1):
        entities = list(self.entities if entities is None else entities)
        records = [{"seq": j, "id": r["id"], "text": r["text"]} for j, r in enumerate(rows)]
        text, contract = question(entities, kind)
        applicable = set(entities) == set(self.entities)
        return {"step_id": f"q{i:02d}", "parser_namespace": f"p10-semantics-{version}",
                "public": {"records": records, "entities": entities,
                           "snapshot": snapshot(records), "query": text},
                "gold": copy.deepcopy([r["gold"] for r in rows]),
                "question_contract": contract, "expected_integrity": "valid",
                "gold_applicable": applicable,
                "gold_exclusion_reason": None if applicable else "entity_membership_undefined"}


def build_stream(family, p):
    x = Author(family, p)
    a, b, c = x.a, x.b, x.c
    base, horizon = x.base(), x.horizon
    kinds = ("ab", "ap", "b", "bp", "a", "ab", "bp", "ap", "a", "b")
    steps, working_set = [], None

    if family == "short_repeated":
        rows = base + [x.copy(b, a), x.add(a, -4), x.copy(a, b), x.add(b, deep=True),
                       x.set(a, "place", PLACES[(p + 2) % 3], deep=True),
                       x.quote(230, "persistent-short", style="ascii")]
        steps = [x.step(rows, i, kinds[(i + p) % len(kinds)]) for i in range(horizon)]

    elif family == "short_churn":
        for i in range(horizon):
            rows = x.base((i * 5 + 2 * p) % 23 - 11)
            rows += [x.copy(a, b), x.add(a, -1 - i % 5), x.copy(b, a)]
            if i % 3 == 0:
                rows += [x.maybe(x.at + i), x.add(b, deep=True)]
            rows += [x.quote(210 + 5 * j, f"churn:{i}:{j}", deep=(i + j) % 2 == 0,
                             style=UNICODE_STYLES[(i + j + p) % 4]) for j in range(2 + i % 5)]
            steps.append(x.step(rows, i, kinds[(2 * i + p) % len(kinds)]))

    elif family in {"long_cheap", "long_deep_repeat", "long_deep_churn"}:
        length = x.length()
        fixed = x.quote(length, "persistent", deep=family != "long_cheap")
        prefix = base + [x.copy(a, b), x.add(b, -3), x.copy(b, a), x.add(a, deep=True)]
        for i in range(horizon):
            note = x.quote(length, f"single-use:{i}") if family == "long_deep_churn" else fixed
            # No-op placement is current history, not an annotation to the selector.
            pos = 4 + (i % 5)
            rows = prefix[:pos] + [note] + prefix[pos:]
            steps.append(x.step(rows, i, kinds[(i + 3 * p) % len(kinds)]))
        working_set = {"quote_pool_count": horizon if family == "long_deep_churn" else 1,
                       "simultaneous_quote_raw_bytes": length, "quote_lengths": [length]}

    elif family in {"fit_working_set", "pressure_working_set"}:
        count = (2, 3, 4, 6)[x.band]
        bounds = (((20000, 28000), (30000, 38000), (40000, 48000), (50000, 58000))
                  if family == "fit_working_set" else
                  ((75000, 89000), (90000, 103000), (104000, 117000), (118000, 130000)))
        total = x.rng.randint(*bounds[x.band])
        # Slightly unequal, content-only lengths; no payload/runtime size oracle.
        lengths = [total // count + (j < total % count) for j in range(count)]
        transfer = min(613 + 29 * p, lengths[-1] // 5)
        lengths[0] += transfer
        lengths[-1] -= transfer
        pool = [x.quote(n, f"working-set:{j}", style=UNICODE_STYLES[(j + p) % 4])
                for j, n in enumerate(lengths)]
        for i in range(horizon):
            order = list(range(count))
            shift = (2 * i + p) % count
            order = order[shift:] + order[:shift]
            if i % 3 == 2:
                order.reverse()
            rows = base + [x.add(a, -2), x.copy(b, a)] + [pool[j] for j in order]
            steps.append(x.step(rows, i, kinds[(i + p) % len(kinds)]))
        working_set = {"quote_pool_count": count, "simultaneous_quote_raw_bytes": total,
                       "quote_lengths": lengths}

    elif family == "phase_shift":
        length = x.length()
        old, new = x.quote(length, "first-era"), x.quote(length, "second-era")
        cut1, cut2 = max(1, horizon // 3), max(1, (2 * horizon) // 3)
        for i in range(horizon):
            if i == horizon - 1:
                note = x.quote(length, f"terminal-no-future:{i}")
            elif i < cut1:
                note = old
            elif i < cut2:
                note = new
            elif i == cut2:
                note = old
            else:
                note = x.quote(length, f"late-single-use:{i}")
            rows = base + [x.copy(b, a), x.add(a, -1 - i % 3), note]
            steps.append(x.step(rows, i, kinds[(i + p) % len(kinds)]))
        working_set = {"quote_pool_count": len({s["public"]["records"][-1]["text"] for s in steps}),
                       "simultaneous_quote_raw_bytes": length, "quote_lengths": [length]}

    elif family == "same_length_misses":
        length = x.length()
        pool = [x.quote(length, f"same-length-{j}") for j in range(7)]
        assert len({len(r["text"]) for r in pool}) == 1
        assert len({r["text"] for r in pool}) == 7
        sequence = (0, 2, 1, 0, 3, 4, 0, 5, 6, 2, 4, 1)
        for i in range(horizon):
            note = pool[sequence[(i + p) % len(sequence)]]
            rows = base + [x.add(b, -1), x.copy(a, b), note]
            steps.append(x.step(rows, i, kinds[(i + p) % len(kinds)], version=1 + (i % 5 == 4)))
        working_set = {"quote_pool_count": 7, "simultaneous_quote_raw_bytes": length,
                       "potential_quote_pool_raw_bytes": 7 * length, "quote_lengths": [length] * 7}

    elif family == "revisions_copy_context":
        length = x.length()
        note = x.quote(length, "context-shared")
        mutable = x.set(b, "time", x.bt + 3, deep=True)
        a_from_b, b_from_a = x.copy(a, b), x.copy(b, a)
        for i in range(horizon):
            revised = copy.deepcopy(mutable)
            value = x.bt - (11 * i + p) % 31
            revised["text"] = f"{b} 약속, 최종 시각은 {value}시로 적어둘게."
            revised["gold"] = event("set", (b, "time"), value)
            tail = ([revised, a_from_b, x.add(b, deep=True), b_from_a] if i % 3 == 0 else
                    [a_from_b, revised, x.add(a, -2), b_from_a] if i % 3 == 1 else
                    [revised, x.add(b, -4), a_from_b])
            membership_change = i % 9 in (3, 7) and i != horizon - 1
            roster = [a, c] if membership_change else [b, a] if i % 4 in (1, 2) else [a, b]
            steps.append(x.step(base + tail + [note], i, kinds[(i + p) % len(kinds)],
                                entities=roster, version=1 + (i // 4) % 3))
        working_set = {"quote_pool_count": 1, "simultaneous_quote_raw_bytes": length,
                       "quote_lengths": [length]}

    elif family == "scope_ambiguity":
        for i in range(horizon):
            rows = base + [x.add(b, -2), x.maybe(x.bt - i % 5), x.copy(a, b)]
            segment = i % 8
            if segment < 3:
                rows += [x.frame(a, "place", PLACES[(i + p) % 3])]
            elif segment < 6:
                rows += [x.frame(b, "time", x.at + i), x.add(a, deep=True)]
            else:
                rows += [x.set(b, "time", x.bt + i, deep=True), x.copy(a, b),
                         x.frame(b, "place", PLACES[(i + p + 1) % 3])]
            steps.append(x.step(rows, i, kinds[(i + p) % len(kinds)]))

    elif family == "integrity_unsupported_recovery":
        length = x.length()
        note = x.quote(length, "integrity-quote")
        rows = base + [x.copy(b, a), x.add(a, -3), note]
        for i in range(horizon):
            slot = i % 10
            kind = kinds[(i + p) % len(kinds)]
            if i != horizon - 1 and slot in (3, 7):
                kind = "unsupported_history" if slot == 3 else "unsupported_execution"
            current = rows + ([x.add(b, deep=True)] if i >= horizon // 2 else [])
            s = x.step(current, i, kind)
            if i != horizon - 1 and slot in (1, 5, 9):
                s["expected_integrity"], s["gold_applicable"] = "invalid", False
                s["gold_exclusion_reason"] = "invalid_snapshot"
                pub = s["public"]
                if slot == 1:
                    pub["snapshot"]["head"] += 1 + p
                elif slot == 5:
                    pub["records"][1]["text"] += " 사후 메모"
                else:
                    pub["records"][-1]["seq"] += 2
                    pub["snapshot"] = snapshot(pub["records"])
            steps.append(s)
        working_set = {"quote_pool_count": 1, "simultaneous_quote_raw_bytes": length,
                       "quote_lengths": [length]}
    else:
        raise ValueError(family)

    return {"id": f"p10-holdout-{family}-{p:02d}", "family": family, "split": "holdout",
            "author_design": {"parameter": p, "horizon": horizon, "raw_length_band_index": x.band,
                "raw_length_band": RAW_BYTE_BANDS[x.band], "primary_unicode_style": x.style,
                "working_set": working_set}, "steps": steps}


def build_corpus():
    return [build_stream(family, p) for family in FAMILIES for p in range(PARAMETERS)]


def execute_gold(events, entities):
    """Typed-plan checks only. Never read raw text or invoke the frozen parser."""
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
    assert len(corpus) == 48 and len({s["id"] for s in corpus}) == 48
    counts = Counter()
    all_raw_bytes, all_raw_chars = [], []
    valid_histories, typed, public_keys = set(), set(), set()
    family_summary, stream_summary = {}, []
    horizon_band = Counter()
    for stream in corpus:
        f, design = stream["family"], stream["author_design"]
        horizon = design["horizon"]
        assert f in FAMILIES and stream["split"] == "holdout"
        assert len(stream["steps"]) == horizon == HORIZONS[design["parameter"]]
        assert len({s["step_id"] for s in stream["steps"]}) == horizon
        horizon_band[(horizon, design["raw_length_band_index"])] += 1
        family = family_summary.setdefault(f, {"streams": 0, "horizons": [], "steps": 0,
            "raw_bytes_sum_over_steps": 0, "raw_bytes_max": 0, "raw_characters_max": 0,
            "valid_raw_histories": set(), "gold_typed_arrays": set()})
        family["streams"] += 1
        family["horizons"].append(horizon)
        lengths, chars, quote_sums = [], [], []
        for s in stream["steps"]:
            pub, gold = s["public"], s["gold"]
            assert set(pub) == {"records", "entities", "snapshot", "query"}
            records = pub["records"]
            assert len(records) == len(gold) and len({r["id"] for r in records}) == len(records)
            assert all(set(r) == {"seq", "id", "text"} for r in records)
            assert len(pub["entities"]) == len(set(pub["entities"])) == 2
            expected = pub["snapshot"]
            valid = ([r["seq"] for r in records] == list(range(expected["head"] + 1)) and
                     digest(records) == expected["digest"])
            assert valid == (s["expected_integrity"] == "valid")
            fields = {(e, z) for e in pub["entities"] for z in ("time", "place")}
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
                family["gold_typed_arrays"].add(canonical(gold))
            else:
                assert s["gold_exclusion_reason"] in {"invalid_snapshot", "entity_membership_undefined"}
            if f in {"short_repeated", "short_churn"}:
                assert all(len(r["text"]) < 256 for r in records)
            bl, cl = [len(r["text"].encode()) for r in records], [len(r["text"]) for r in records]
            lengths.extend(bl)
            chars.extend(cl)
            quote_sums.append(sum(n for n, ev in zip(bl, gold) if ev["kind"] == "noop"))
            if valid:
                raw_history = canonical([r["text"] for r in records])
                valid_histories.add(raw_history)
                family["valid_raw_histories"].add(raw_history)
            public_keys.add(canonical([pub, s["parser_namespace"]]))
            family["steps"] += 1
            counts["steps"] += 1
            counts["valid_steps"] += valid
            counts["invalid_steps"] += not valid
            counts["gold_applicable_steps"] += s["gold_applicable"]
            counts["unsupported_questions"] += not s["question_contract"]["supported"]
            counts["valid_supported_steps"] += valid and s["question_contract"]["supported"]
            counts["gold_supported_steps"] += s["gold_applicable"] and s["question_contract"]["supported"]
            if s["gold_exclusion_reason"]:
                counts["excluded_" + s["gold_exclusion_reason"]] += 1
        all_raw_bytes.extend(lengths)
        all_raw_chars.extend(chars)
        family["raw_bytes_sum_over_steps"] += sum(lengths)
        family["raw_bytes_max"] = max(family["raw_bytes_max"], *lengths)
        family["raw_characters_max"] = max(family["raw_characters_max"], *chars)
        stream_summary.append({"id": stream["id"], "family": f, **design,
            "record_occurrences": len(lengths), "record_bytes_min_max": [min(lengths), max(lengths)],
            "record_characters_min_max": [min(chars), max(chars)],
            "raw_bytes_sum_over_steps": sum(lengths), "max_noop_raw_bytes_per_history": max(quote_sums)})
    assert counts["steps"] == 1176
    for family in family_summary.values():
        assert sorted(family["horizons"]) == list(HORIZONS)
        assert family["streams"] == 4 and family["steps"] == 98
        family["valid_raw_histories"] = len(family["valid_raw_histories"])
        family["gold_typed_arrays"] = len(family["gold_typed_arrays"])
    assert all(horizon_band[(h, b)] == 3 for h in HORIZONS for b in range(4))
    return {"seed": SEED, "families": 12, "streams": len(corpus), "parameters_per_family": PARAMETERS,
        "horizons_per_family": HORIZONS, **dict(counts),
        "schema_and_typed_plan_checks": "passed", "selector_evaluated": False,
        "trace_model_or_calibration_read": False, "raw_length_bands_bytes": RAW_BYTE_BANDS,
        "unicode_styles": UNICODE_STYLES,
        "horizon_band_design_stream_counts": [{"horizon": h, "band": b, "streams": horizon_band[h, b]}
                                              for h in HORIZONS for b in range(4)],
        "record_occurrences": len(all_raw_bytes),
        "record_bytes_min_max": [min(all_raw_bytes), max(all_raw_bytes)],
        "record_characters_min_max": [min(all_raw_chars), max(all_raw_chars)],
        "raw_bytes_sum_over_steps": sum(all_raw_bytes),
        "valid_unique_raw_histories": len(valid_histories), "exact_typed_arrays_gold_applicable": len(typed),
        "exact_public_and_namespace": len(public_keys),
        "family_distribution": family_summary, "stream_distribution": stream_summary,
        "authorship": "same-model separate data author; shared public grammar/design and Phase09 history; not external blind data",
        "semantic_boundary": "long payloads are controlled-grammar noop; no new natural-language or execution-evidence ability",
        "identity_boundary": "exact canonical JSON identities, not independent programs or semantic equivalence classes"}


def put_or_check(path, data, check):
    if check or path.exists():
        assert path.read_bytes() == data, f"Refusing to replace different bytes at {path}"
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def deterministic_gzip(data):
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
                   data_sha256=hashlib.sha256(compressed).hexdigest(), uncompressed_data_bytes=len(data),
                   uncompressed_data_sha256=hashlib.sha256(data).hexdigest(),
                   compression="gzip level=9 filename='' mtime=0", builder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    manifest = (json.dumps(summary, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if args.check or args.output.exists():
        assert gzip.decompress(args.output.read_bytes()) == data
    put_or_check(args.output, compressed, args.check)
    put_or_check(args.manifest, manifest, args.check)
    brief = {k: v for k, v in summary.items() if k not in {"family_distribution", "stream_distribution"}}
    print(json.dumps(brief, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


