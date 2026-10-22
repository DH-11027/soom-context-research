"""Small pre-freeze counterexamples to unsound instrumentation deletion.

No holdout, gold, timing or LLM input. The two mutants deliberately violate
the contract; the real off implementation must remain equal to frozen on.
"""
import argparse
import hashlib
import json
from pathlib import Path

from bindings import P6, P8R
import off_selective


def quote_bytes(length, letter):
    prefix = "표현 연습:「"
    suffix = "」라는 문장을 써봤어. 약속은 그대로야."
    text = prefix + letter * (length - len((prefix + suffix).encode())) + suffix
    assert len(text.encode()) == length
    return text


def public(text):
    texts = ["가람 모임 시간은 8시로 확정해줘.", "가람 모임 장소는 카페로 확정해줘.",
             "누리 모임 시간은 9시로 확정해줘.", "누리 모임 장소는 카페로 확정해줘.", text]
    records = [{"seq": i, "id": f"counterexample-{i}", "text": t} for i, t in enumerate(texts)]
    serialized = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return {"records": records, "entities": ["가람", "누리"],
            "query": "가람 모임은 지금 몇 시야?",
            "snapshot": {"head": len(records)-1, "digest": hashlib.sha256(serialized).hexdigest()}}


def obs(p, result):
    fields = {k: v for k, v in result.items() if k != "cost"}
    rendered = b"" if result["status"] == "integrity_failure" else P6.render(p, result["selected"], result["status"]).encode()
    return fields, rendered


def project(cache):
    return (cache.directory, cache.max_entries, cache.max_bytes,
            [(key, item["stages"], item["size"], item["characters"], item["surplus"],
              item["hits"], item["order"]) for key, item in cache.entries.items()],
            dict(cache.lengths), cache.retained_bytes, cache.next_order)


def brief(cache):
    return [{"raw_bytes": len(key[1]), "C": len(key[0]),
             "R": sum(v[1] for v in item["stages"].values()),
             "size": item["size"], "surplus": item["surplus"],
             "hits": item["hits"], "order": item["order"]}
            for key, item in cache.entries.items()]


class LostHitCounter(off_selective.SelectiveCache):
    """Incorrectly treats the policy hit count as a removable statistic."""
    def get(self, key):
        item = self.entries.get(key)
        return None if item is None else item["stages"]


class LengthAsIdentity(off_selective.SelectiveCache):
    """Incorrectly substitutes a positive length filter for exact equality."""
    def get(self, key):
        characters = len(key[1].decode("utf-8"))
        for item in self.entries.values():
            if item["characters"] == characters:
                item["hits"] = min(P8R.HIT_CAP, item["hits"] + 1)
                return item["stages"]
        return None


def audit():
    original, erased, mutant = P8R.SelectiveCache(), off_selective.SelectiveCache(), LostHitCounter()
    rows = []
    for i, (length, letter) in enumerate([(20000, "a"), (30000, "b"), (20000, "a"), (21000, "c")]):
        p = public(quote_bytes(length, letter))
        a, b, c = P8R.run(p, original), off_selective.run(p, erased), off_selective.run(p, mutant)
        assert obs(p, a) == obs(p, b) == obs(p, c)
        assert project(original) == project(erased)
        rows.append({"step": i+1, "observation_equal_all_three": True,
                     "real_on_off_policy_equal": True,
                     "mutant_policy_equal": project(original) == project(mutant),
                     "original_state": brief(original), "mutant_state": brief(mutant)})
    assert [len(k[1]) for k in original.entries] == [20000, 30000]
    assert [len(k[1]) for k in mutant.entries] == [30000, 21000]
    assert original.next_order == 2 and mutant.next_order == 3
    # Current output equality misses even the first policy error (the lost hit
    # at step 3), and the next admission exposes a different resident set.
    assert [r["mutant_policy_equal"] for r in rows] == [True, True, False, False]

    exact, wrong = off_selective.SelectiveCache(), LengthAsIdentity()
    first = quote_bytes(1600, "x")
    second = "알 수 없는 사건:" + "x" * (len(first)-len("알 수 없는 사건:"))
    assert len(first) == len(second) and first != second
    p = public(first)
    assert obs(p, off_selective.run(p, exact)) == obs(p, off_selective.run(p, wrong))
    p = public(second)
    good, bad = off_selective.run(p, exact), off_selective.run(p, wrong)
    assert good["status"] == "opaque_fallback"
    assert bad["status"] == "certified_model"
    assert obs(p, good) != obs(p, bad)

    return {"scope": "pre-freeze development counterexamples, not holdout or timing",
            "lost_hit_counter": {"steps": rows, "observation_failures": 0,
                                  "policy_failure_steps": [3, 4],
                                  "resident_set_diverges_at_step": 4},
            "same_length_identity": {"characters": len(first),
                                     "exact_status": good["status"],
                                     "mutant_status": bad["status"],
                                     "detected": True},
            "real_erasure_failures": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit()
    data = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as out:
            out.write(data)
        print(f"Counterexamples verified: {args.output}")
    else:
        print(data, end="")


if __name__ == "__main__":
    main()
