"""Synthetic evidence-retention study; no SOOM imports, models, APIs, or DB access.

Policies and the threshold grid below are fixed before viewing calibration/test
results. Dependency edges in one diagnostic arm are supplied by the generator;
they are NOT extracted from Korean by a model. Byte counts are not token counts.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from itertools import combinations
from pathlib import Path
import hashlib
import json
import math
import platform
import random
import re
import time

ROOT = Path(__file__).resolve().parent
SEED = 2026102202
N_CAL = 512
N_TEST = 512
ALPHA = 0.05  # illustrative evidence-omission target, NOT a production tolerance
DELTA = 0.05
THRESHOLDS = tuple(i / 10 for i in range(11))
METHODS = ("lexical", "lexical_with_given_edges")
M = len(THRESHOLDS) * len(METHODS)
FAMILIES = ("duplicate", "correction_current", "correction_history", "reference",
            "pending", "completion", "exact_quote", "unrelated")
TOPICS = ("도서관", "박물관", "전시관", "연구실", "체육관", "공연장", "회의실", "공방")


def grams(text):
    compact = re.sub(r"[^가-힣a-zA-Z0-9]", "", text.lower())
    return {compact[i:i + 2] for i in range(len(compact) - 1)}


def evidence_bytes(case, selected):
    # Content-only UTF-8 bytes. Full prompt/schema/tokenizer overhead is unmeasured.
    return sum(len(item["text"].encode("utf-8")) for item in case["history"] if item["id"] in selected)


def missing(case, selected):
    # AND over requirements, OR over sufficient alternatives for each requirement.
    return [choices for choices in case["required_any_of"] if not set(choices) & selected]


def closure(selected, edges):
    selected = set(selected)
    changed = True
    while changed:
        changed = False
        for child, parent in edges:
            if child in selected and parent not in selected:
                selected.add(parent)
                changed = True
    return selected


def propose(public_case, method):
    # Only this public view is passed in: no family, answer, or gold requirement.
    history, query = public_case["history"], public_case["query"]
    protected = {history[-1]["id"]}
    q = grams(query)
    ranked = []
    for position, item in enumerate(history[:-1]):
        d = grams(item["text"])
        score = len(q & d) / math.sqrt(max(1, len(q) * len(d)))
        ranked.append((score, position, item["id"], len(q & d) / max(1, len(q))))
    ranked.sort(reverse=True)
    selected = protected | {entry[2] for entry in ranked[:2]}
    # A transparent, untrained ranking heuristic; this is NOT a probability.
    strength = (ranked[0][3] + ranked[1][3]) / 2
    margin = (ranked[1][0] - ranked[2][0]) / max(ranked[1][0], 1e-12)
    confidence = min(1.0, max(0.0, 0.75 * strength + 0.25 * margin))
    if method == "lexical_with_given_edges":
        selected = closure(selected, public_case["dependencies"])
    return selected, confidence


def make_case(seed, split, shifted=False):
    rng = random.Random(seed)
    if shifted:
        family = rng.choices(FAMILIES, weights=(1, 3, 2, 3, 3, 3, 1, 1))[0]
    else:
        family = rng.choice(FAMILIES)
    topic = rng.choice(TOPICS)
    old, new = rng.sample(range(10, 20), 2)
    serial = rng.randrange(100000, 999999)
    brief_reference = rng.random() < (0.8 if shifted else 0.2)
    edges = []
    if family == "duplicate":
        t0 = f"{topic} 모임 시간은 {old}시야. 일정 번호 {serial}."
        t1 = f"다시 확인하면 {topic} 모임 시간은 {old}시야."
        query = f"{topic} 모임 시간은 몇 시야?"
        required = [["t0", "t1"]]
        expected = f"{old}시"
    elif family in ("correction_current", "correction_history"):
        t0 = f"{topic} 모임 시간은 {old}시로 기록해줘. 일정 번호 {serial}."
        t1 = (f"정정할게. 그건 {new}시야. 이전 기록은 더 이상 유효하지 않아." if brief_reference else
              f"{topic} 모임 시간을 {new}시로 정정해. 이전 기록은 더 이상 유효하지 않아.")
        edges = [["t1", "t0"]] if brief_reference else []
        if family == "correction_current":
            query, required, expected = f"{topic} 모임은 최종적으로 몇 시야?", [["t1"]], f"{new}시"
            if brief_reference:
                required = [["t0"], ["t1"]]
        else:
            query = f"{topic} 모임 시간을 처음에 어떻게 정했고 나중에 어떻게 바꿨어?"
            required, expected = [["t0"], ["t1"]], f"{old}시에서 {new}시로 변경"
    elif family == "reference":
        t0 = f"{topic} 준비 후보: 1. 안내문 2. 지도 3. 참가자 명단. 기록 번호 {serial}."
        t1 = ("내일 준비는 아까 세 번째 걸로 정했어." if brief_reference else
              f"{topic} 내일 준비는 위 목록의 세 번째 걸로 정했어.")
        query = f"{topic} 내일 준비는 무엇으로 정했지?"
        required, expected, edges = [["t0"], ["t1"]], "참가자 명단", [["t1", "t0"]]
    elif family in ("pending", "completion"):
        t0 = f"{topic} 자료 정리 부탁할게. 작업 번호 {serial}."
        subject = "그 작업은" if brief_reference else f"{topic} 자료 정리는"
        if family == "pending":
            t1 = f"{subject} 아직 시작하지 않았어. 내일까지 하기로 약속했어."
            expected = "미완료; 내일까지 하기로 한 약속이 남음"
        else:
            t1 = f"{subject} 완료했어. 결과 파일을 확인했어."
            expected = "완료; 결과 파일 확인 근거 있음"
        query = f"{topic} 자료 정리 끝났어, 아니면 아직 할 일이야?"
        required = [["t1"]] if not brief_reference else [["t0"], ["t1"]]
        edges = [["t1", "t0"]] if brief_reference else []
    elif family == "exact_quote":
        t0 = f"{topic} 안내 원문: 우천 시에도 행사는 예정대로 진행합니다. 문서 번호 {serial}."
        t1 = f"{topic} 안내 요약: 비가 와도 행사 일정은 그대로야."
        query = f"{topic} 안내에서 비가 올 때에 관한 문장을 원문 그대로 알려줘."
        required, expected = [["t0"]], "우천 시에도 행사는 예정대로 진행합니다."
    else:
        t0 = f"{topic} 모임의 준비물을 정리했어. 번호 {serial}."
        t1 = f"{topic} 모임에서는 자료를 화면에 띄울 수 있어."
        query, required, expected = "지금 내가 보낸 문장은 어떤 언어로 쓰여 있어?", [], "한국어"
    background = [
        ("d0", f"{topic} 관련 메타 대화에서는 도구 설명과 프롬프트 길이를 줄이는 방법을 논의했어."),
        ("d1", f"{topic} 모임 시간 확인 방법과 자료 정리 방법을 예시로 설명했어. 실제 일정 변경이나 작업 완료 보고는 아니야."),
        ("d2", "오늘 점심에는 국수를 먹었고 산책을 했어."),
        ("d3", "휴대폰 화면의 글자 크기를 키웠어."),
        ("d4", f"다른 장소의 일정 번호는 {serial + 1}이야. 여기는 별개의 이야기야."),
    ]
    items = [("t0", t0), ("t1", t1), *background]
    rng.shuffle(items)
    p0 = next(i for i, v in enumerate(items) if v[0] == "t0")
    p1 = next(i for i, v in enumerate(items) if v[0] == "t1")
    if p0 > p1:
        items[p0], items[p1] = items[p1], items[p0]
    items.append(("latest", "응, 지금 질문을 이어서 들을게."))
    return {"id": f"{split}-{seed}", "family": family, "query": query,
            "history": [{"id": ident, "text": text} for ident, text in items],
            "dependencies": edges, "required_any_of": required,
            "expected_answer": expected, "brief_reference": brief_reference}


def minimal_pairs():
    base = {"history": [{"id": "a", "text": "회의는 15시로 잡았어."},
                        {"id": "b", "text": "정정: 회의는 16시야."}],
            "query": "회의는 최종적으로 몇 시야?", "required_any_of": [["b"]], "answer": "16시"}
    correction = deepcopy(base); correction["history"][1]["text"] = "정정: 회의는 17시야."; correction["answer"] = "17시"
    history_query = deepcopy(base); history_query.update(query="회의 시간이 어떻게 바뀌었지?", required_any_of=[["a"], ["b"]], answer="15시에서 16시")
    planned = {"history": [{"id": "a", "text": "보고서 정리를 부탁해."},
                           {"id": "b", "text": "보고서 정리는 아직 완료하지 않았어."}],
               "query": "보고서 정리는 끝났니?", "required_any_of": [["b"]], "answer": "미완료"}
    done = deepcopy(planned); done["history"][1]["text"] = "보고서 정리는 이미 완료했어."; done["answer"] = "완료"
    promised = {"history": [{"id": "a", "text": "내일까지 지도 제작을 해줘."},
                            {"id": "b", "text": "지도 제작 약속은 유효하고 아직 미완료야."}],
                "query": "남은 약속이 뭐야?", "required_any_of": [["a"], ["b"]], "answer": "내일까지 지도 제작"}
    cancelled = deepcopy(promised); cancelled["history"][1]["text"] = "지도 제작 약속은 취소했어."; cancelled["answer"] = "지도 제작 약속 없음"; cancelled["required_any_of"] = [["b"]]
    referenced = {"history": [{"id": "a", "text": "후보: 1. 안내문 2. 지도 3. 명단"},
                              {"id": "b", "text": "준비물은 세 번째 걸로 정했어."}],
                  "query": "준비물로 뭘 골랐지?", "required_any_of": [["a"], ["b"]], "answer": "명단"}
    other_ref = deepcopy(referenced); other_ref["history"][1]["text"] = "준비물은 두 번째 걸로 정했어."; other_ref["answer"] = "지도"
    quote = {"history": [{"id": "a", "text": "원문: 우천 시에도 행사는 예정대로 진행합니다."},
                         {"id": "b", "text": "요약: 비가 와도 행사 일정은 그대로야."}],
             "query": "행사 안내를 원문 그대로 알려줘.", "required_any_of": [["a"]],
             "answer": "우천 시에도 행사는 예정대로 진행합니다."}
    gist = deepcopy(quote); gist.update(query="비가 오면 행사 일정이 바뀌어?", required_any_of=[["a", "b"]], answer="아니오")
    return [{"name": name, "left": left, "right": right} for name, left, right in (
        ("정정값 하나 변경", base, correction), ("현재 상태와 변경 이력", base, history_query),
        ("미완료와 완료", planned, done), ("유효한 약속과 취소", promised, cancelled),
        ("지시 대상 변경", referenced, other_ref), ("원문 인용과 뜻 요약", quote, gist))]


def evaluate_case(case):
    public = {k: case[k] for k in ("history", "query", "dependencies")}
    all_ids = {h["id"] for h in case["history"]}
    full_bytes = evidence_bytes(case, all_ids)
    policies = {"all": (all_ids, None),
                "recent_three": ({h["id"] for h in case["history"][-3:]}, None)}
    for method in METHODS:
        policies[method] = propose(public, method)
    return {"id": case["id"], "family": case["family"], "full_bytes": full_bytes,
            "policies": {name: {"selected": sorted(selected), "score": score,
                                 "missing": missing(case, selected), "failure": bool(missing(case, selected)),
                                 "bytes": evidence_bytes(case, selected)}
                         for name, (selected, score) in policies.items()}}


def binomial_cdf(k, n, p):
    if k >= n or p <= 0:
        return 1.0
    if p >= 1:
        return 0.0
    logs = [math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1)
            + i * math.log(p) + (n - i) * math.log1p(-p) for i in range(k + 1)]
    top = max(logs)
    return min(1.0, math.exp(top) * math.fsum(math.exp(v - top) for v in logs))


def upper_bound(errors, n, delta):
    # Exact one-sided binomial upper bound; its inputs must be iid Bernoulli trials.
    if n == 0 or errors == n:
        return 1.0
    if errors == 0:
        return -math.expm1(math.log(delta) / n)
    lo, hi = errors / n, 1.0
    for _ in range(65):
        mid = (lo + hi) / 2
        if binomial_cdf(errors, n, mid) > delta:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def calibrate(rows):
    candidates = []
    for method in METHODS:
        for threshold in THRESHOLDS:
            accepted = [r for r in rows if r["policies"][method]["score"] >= threshold]
            n = len(accepted)
            errors = sum(r["policies"][method]["failure"] for r in accepted)
            upper = upper_bound(errors, n, DELTA / M)
            saved = sum(r["full_bytes"] - r["policies"][method]["bytes"] for r in accepted)
            candidates.append({"method": method, "threshold": threshold, "accepted": n,
                               "errors": errors, "upper_risk_bound": upper,
                               "saved_bytes": saved, "certified_in_model": n > 0 and upper <= ALPHA})
    eligible = [c for c in candidates if c["certified_in_model"]]
    chosen = max(eligible, key=lambda c: (c["saved_bytes"], -c["upper_risk_bound"])) if eligible else None
    return {"candidates": candidates, "chosen": chosen}


def summarize(rows, policy, chosen=None):
    failures = accepted = saved = total = 0
    by_family = {f: {"n": 0, "accepted": 0, "failures": 0, "saved_bytes": 0, "full_bytes": 0} for f in FAMILIES}
    for row in rows:
        compress = policy != "all"
        actual = policy
        if policy == "calibrated":
            compress = chosen is not None and row["policies"][chosen["method"]]["score"] >= chosen["threshold"]
            actual = chosen["method"] if compress else "all"
        result = row["policies"][actual]
        failure = int(result["failure"])
        saving = row["full_bytes"] - result["bytes"]
        failures += failure; accepted += int(compress); saved += saving; total += row["full_bytes"]
        group = by_family[row["family"]]
        group["n"] += 1; group["accepted"] += int(compress); group["failures"] += failure
        group["saved_bytes"] += saving; group["full_bytes"] += row["full_bytes"]
    return {"policy": policy, "cases": len(rows), "accepted": accepted, "failures": failures,
            "failure_rate_all": failures / len(rows),
            "failure_rate_accepted": failures / accepted if accepted else None,
            "byte_reduction": saved / total, "by_family": by_family}


def verify_math():
    checks = 0
    for n in range(1, 21):
        for k in range(n + 1):
            for p in (0.01, 0.1, 0.5, 0.9, 0.99):
                direct = sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))
                assert abs(direct - binomial_cdf(k, n, p)) < 1e-11
                checks += 1
    for n in (10, 100, 512):
        previous = -1
        for k in sorted({0, 1, n // 5, n // 2, n - 1, n}):
            bound = upper_bound(k, n, DELTA / M)
            assert bound >= previous
            previous = bound
            if 0 < k < n:
                assert abs(binomial_cdf(k, n, bound) - DELTA / M) < 1e-10
    # A counterexample to converting average risk into a guarantee for every type.
    # A rare type can have 100% loss while population-average loss is 1%.
    assert 0.01 * 1.0 + 0.99 * 0.0 < ALPHA
    return {"binomial_cross_checks": checks,
            "zero_error_minimum_n": {str(alpha): math.ceil(math.log(DELTA / M) / math.log1p(-alpha))
                                     for alpha in (0.05, 0.01)},
            "zero_error_bounds": [{"n": n, "upper": upper_bound(0, n, DELTA / M)} for n in (20, 100, 500, 1000)],
            "rare_type_counterexample": {"rare_type_mass": 0.01, "rare_type_risk": 1.0, "population_risk": 0.01}}


def main():
    started = time.perf_counter()
    splits = {
        "calibration": [make_case(SEED + i, "cal") for i in range(N_CAL)],
        "test_same_generator": [make_case(SEED + 10000 + i, "test") for i in range(N_TEST)],
        "stress_shifted_generator": [make_case(SEED + 20000 + i, "shift", True) for i in range(N_TEST)],
    }
    ids = [{c["id"] for c in cases} for cases in splits.values()]
    assert all(not a & b for a, b in combinations(ids, 2))
    rows = {split: [evaluate_case(c) for c in cases] for split, cases in splits.items()}
    calibration = calibrate(rows["calibration"])
    chosen = calibration["chosen"]
    scores = {split: [summarize(rs, policy, chosen) for policy in ("all", "recent_three", *METHODS, "calibrated")]
              for split, rs in rows.items()}
    for rs in rows.values():
        for row in rs:
            assert not row["policies"]["all"]["failure"]
            assert set(row["policies"]["lexical"]["selected"]) <= set(row["policies"]["lexical_with_given_edges"]["selected"])
            assert int(row["policies"]["lexical_with_given_edges"]["failure"]) <= int(row["policies"]["lexical"]["failure"])
    # Preserve the diagnostic instances, including failures, without selecting only successes.
    fixtures = {"scope": "entirely synthetic, with author-provided evidence labels and dependency edges",
                "minimal_pairs": minimal_pairs(), "splits": splits}
    (ROOT / "fixtures.json").write_text(json.dumps(fixtures, ensure_ascii=False, indent=2), encoding="utf-8")
    result = {"scope": "offline synthetic evidence retention; no LLM answer evaluation or production change",
              "python": platform.python_version(), "seed": SEED, "alpha": ALPHA, "delta": DELTA,
              "candidate_count": M, "calibration": calibration, "summaries": scores,
              "math_checks": verify_math(), "rows": rows,
              "elapsed_seconds": time.perf_counter() - started,
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (ROOT / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    brief = {"calibrated_policy": chosen, "math_checks": result["math_checks"],
             "evaluations": {split: [{k: v for k, v in s.items() if k != "by_family"} for s in summaries]
                             for split, summaries in scores.items() if split != "calibration"},
             "elapsed_seconds": result["elapsed_seconds"]}
    print(json.dumps(brief, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
