"""Exact byte-cost reduction of commuting integer-shift blocks.

Scope: already selected CURRENT-STATE evidence and exact recognized semantics.
No minimum-cost claim across copies, weak assignments, unknowns, or trajectories.
"""

import engine


def footprint(ev, universe):
    writes = engine.writes(ev, universe)
    reads = set()
    if ev["kind"] == "add":
        reads.add(ev["target"])
    elif ev["kind"] == "copy":
        reads.add(ev["source"])
    elif ev["kind"] == "maybe_set":
        reads.update(ev["targets"])
    return reads | writes


def minimum_subset(block):
    """block: (source index, integer delta, rendered source byte cost).

    Dynamic program stores the cheapest subset for each reachable sum.
    Exact signed integer recurrence; ties deterministic. No greedy selection.
    """
    dp = {0: (0, ())}
    for index, delta, cost in block:
        following = dict(dp)
        for total, (old_cost, selected) in dp.items():
            candidate = (old_cost + cost, selected + (index,))
            target = total + delta
            if target not in following or candidate < following[target]:
                following[target] = candidate
        dp = following
    total = sum(delta for _, delta, _ in block)
    cost, selected = dp[total]
    return {"sum": total, "cost": cost, "selected": list(selected), "reachable_sums": len(dp)}


def reduce_typed(records, indices, typed, universe):
    active = {}
    remove = set()
    proofs = []

    def flush(fact):
        block = active.pop(fact, [])
        if not block:
            return
        optimal = minimum_subset(block)
        eliminated = {i for i, _, _ in block} - set(optimal["selected"])
        remove.update(eliminated)
        proofs.append({"fact": list(fact), "source_indices": [i for i, _, _ in block],
                       "kept_indices": optimal["selected"], "net_delta": optimal["sum"],
                       "source_cost_before": sum(c for _, _, c in block),
                       "source_cost_after": optimal["cost"], "reachable_sums": optimal["reachable_sums"]})

    for i in indices:
        ev = typed[i]
        touched = footprint(ev, universe)
        # A read/copy/assignment/weak update touching the fact ends its block.
        for fact in list(active):
            if fact in touched and not (ev["kind"] == "add" and ev["target"] == fact):
                flush(fact)
        if ev["kind"] == "add":
            cost = len(f"[기록 {i}] {records[i]['text']}\n".encode("utf-8"))
            active.setdefault(ev["target"], []).append((i, ev["value"], cost))
    for fact in list(active):
        flush(fact)
    return [i for i in indices if i not in remove], proofs


def run(public, base=None):
    base = engine.run(public, "lazy") if base is None else base
    if base["status"] not in ("certified_model", "ambiguous"):
        return {"base": base, "selected": base["selected"], "output_bytes": base["output_bytes"],
                "blocks": [], "extra_detail_calls": 0, "extra_detail_source_bytes": 0}
    typed, extra_calls, extra_bytes = {}, 0, 0
    # Frozen engine has no exported AST cache. Count this prototype's repeated
    # detailed parsing honestly; a future integrated implementation could reuse it.
    for i in base["selected"]:
        text = public["records"][i]["text"]
        ev = engine.parse(text, public["entities"])
        if ev["kind"] == "havoc":
            ev = engine.parse(text, public["entities"], deep=True)
            extra_calls += 1
            extra_bytes += len(text.encode("utf-8"))
        assert ev["kind"] != "havoc"
        typed[i] = ev
    selected, proofs = reduce_typed(public["records"], base["selected"], typed, engine.facts(public["entities"]))
    output = engine.render(public["records"], selected, public["query"], public["snapshot"], base["status"])
    return {"base": base, "selected": selected, "output_bytes": len(output.encode("utf-8")),
            "blocks": proofs, "extra_detail_calls": extra_calls,
            "extra_detail_source_bytes": extra_bytes}
