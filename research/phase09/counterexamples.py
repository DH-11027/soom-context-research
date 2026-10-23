"""Small pre-freeze erasure mutants; policy divergence, not performance data.

Only existing frozen P8 runtime is exercised. No corpus is loaded and no timing
is collected/reported. Each mutant is intentionally wrong and isolated in this
process; source files and the final policy are never changed.
"""
import json

from bindings import P6, R8


def public(body_length):
    text = "표현 연습:「" + "x" * body_length + "」라는 문장을 써봤어. 약속은 그대로야."
    records = [
        {"seq": 0, "id": "set", "text": "가람 모임 시간은 3시로 확정해줘."},
        {"seq": 1, "id": "quote", "text": text},
    ]
    return {"records": records, "entities": ["가람", "누리"],
            "query": "가람 모임은 지금 몇 시야?", "snapshot": P6.BASE.snapshot(records)}


def observe(p, result):
    rendered = b"" if result["status"] == "integrity_failure" else P6.render(
        p, result["selected"], result["status"]).encode("utf-8")
    return {k: v for k, v in result.items() if k != "cost"}, rendered


def policy(cache):
    return (cache.directory, cache.max_entries, cache.max_bytes,
            tuple((key, dict(value)) for key, value in cache.entries.items()),
            dict(cache.lengths), cache.retained_bytes, cache.next_order)


def item_summary(cache):
    return [{"L": len(k[1]), "C": len(k[0]),
             "R": sum(n for _, n in item["stages"].values()),
             "size": item["size"], "surplus": item["surplus"],
             "hits": item["hits"], "order": item["order"]}
            for k, item in cache.entries.items()]


class ErasedHitMutant(R8.SelectiveCache):
    """The erroneous interpretation that resident hit count is only telemetry."""
    def get(self, key, cost):
        item = self.entries.get(key)
        old_hits = None if item is None else item["hits"]
        result = super().get(key, cost)
        if item is not None:
            item["hits"] = old_hits
        return result


def run():
    namespace = "math-erasure"
    normal, mutant = R8.SelectiveCache(), ErasedHitMutant()
    hit_rows = []
    for index, p in enumerate((public(33000), public(33000), public(34000)), 1):
        left = R8.run(p, normal, namespace=namespace)
        right = R8.run(p, mutant, namespace=namespace)
        equal_obs = observe(p, left) == observe(p, right)
        equal_policy = policy(normal) == policy(mutant)
        assert equal_obs
        assert equal_policy == (index == 1)
        hit_rows.append({"prefix": index, "observation_equal": equal_obs,
                         "policy_equal": equal_policy, "normal": item_summary(normal),
                         "mutant": item_summary(mutant),
                         "normal_capacity_rejections": left["cost"]["admission_reject_capacity"],
                         "mutant_capacity_rejections": right["cost"]["admission_reject_capacity"]})
    assert hit_rows[-1]["normal_capacity_rejections"] == 1
    assert hit_rows[-1]["mutant_capacity_rejections"] == 0
    assert next(iter(normal.entries))[1] != next(iter(mutant.entries))[1]

    # ACTION_WEIGHT is also a real policy operand: deleting its score report
    # cannot justify changing it to zero in the surplus expression.
    p = public(249)
    normal, mutant = R8.SelectiveCache(), R8.SelectiveCache()
    left = R8.run(p, normal, namespace=namespace)
    old_weight = R8.ACTION_WEIGHT
    assert old_weight == 8
    try:
        R8.ACTION_WEIGHT = 0
        right = R8.run(p, mutant, namespace=namespace)
    finally:
        R8.ACTION_WEIGHT = old_weight
    assert observe(p, left) == observe(p, right)
    assert not normal.entries and len(mutant.entries) == 1
    assert left["cost"]["admission_reject_gain"] == 1
    entry = item_summary(mutant)[0]
    assert (entry["L"], entry["C"], entry["R"], entry["surplus"]) == (320, 103, 154, 63)
    weight_row = {"prefix": 1, "characters": len(p["records"][1]["text"]),
                  "L": entry["L"], "C": entry["C"], "R": entry["R"],
                  "normal_surplus": entry["surplus"] - 64,
                  "mutant_surplus": entry["surplus"],
                  "observation_equal": True, "policy_equal": False,
                  "normal_entries": 0, "mutant_entries": 1}
    return {"scope": "constructed development counterexamples, not timing or held-out evidence",
            "erased_resident_hit": hit_rows, "erased_policy_weight": weight_row,
            "mutants_detected": 2}


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
