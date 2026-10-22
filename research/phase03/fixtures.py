"""Synthetic public text and separate author-written gold annotations.

No gold antecedents or source-role IDs are supplied to extractor.py. Test wording
banks differ from development; the same researcher authored both, so this is not
a blind external benchmark. Counts are balanced template variants, not IID data.
"""
import random

FAMILIES = ("explicit_task", "explicit_schedule", "unique_reference", "ambiguous_reference", "quoted_example",
            "same_entity", "novel_expression", "chain", "cancelled")
ENTITIES = {
    "dev": ("가람", "나래", "다온", "라온", "마루", "바다"),
    "heldout": ("은하", "산호", "무지개", "새벽", "호수", "단풍"),
    "stress": ("노을", "솔빛", "들꽃", "달무리", "초록", "하늬"),
}
OBJECTS = ("안내문", "예산표", "보고서", "초대장", "지도", "발표문")


def make_case(family, variant, split):
    rng = random.Random(2026102203 + FAMILIES.index(family) * 1000 + variant + {"dev": 0, "heldout": 100000, "stress": 200000}[split])
    a, b = rng.sample(ENTITIES[split], 2)
    obj, other = rng.sample(OBJECTS, 2)
    old, new = rng.sample(range(10, 20), 2)
    serial = rng.randrange(100000, 999999)
    brief = split != "dev"

    def task(name, item):
        if split == "dev":
            return f"{name} 프로젝트의 {item} 작성해줘. 접수 번호 {serial}."
        if split == "heldout":
            return f"{name} 프로젝트에서 쓸 {item}, 작성 부탁할게. 기록 번호 {serial}."
        if variant % 2 == 0:
            return f"{name} 프로젝트의 {item}, 손 좀 봐줄래? 식별 번호 {serial}."
        return f"{name} 프로젝트의 {item}, 정리해줘. 식별 번호 {serial}."

    def schedule(name):
        if split == "dev":
            return f"{name} 모임 시간을 {old}시로 기록해줘."
        if split == "heldout":
            return f"{name} 모임 시각을 {old}시로 기억해줘."
        return f"{name} 모임, {old}시로 약속 잡자." if variant % 2 == 0 else f"{name} 모임, {old}시로 잡아줘."

    root_a, root_b = task(a, obj), task(b, other)
    update = f"{a} 프로젝트의 {obj}는 완료했어." if not brief else f"{a} 프로젝트에서 부탁한 {obj} 건은 마무리했어."
    query = f"{a} 프로젝트 {obj}의 진행 상태를 알려줘."
    events = [("update", "root_a")]
    requirements = [["root_a"], ["update"]]
    alternatives = {}
    update2 = None
    if family == "explicit_schedule":
        root_a, root_b = schedule(a), schedule(b)
        update = f"{a} 모임은 {new}시로 정정해." if not brief else f"{a} 모임은 이제 {new}시로 변경됐어."
        query = f"{a} 모임 시간은 어떻게 변경됐어?"
    elif family == "unique_reference":
        root_b = schedule(b)
        update = "그 작업은 아직 완료하지 않았어." if not brief else "아까 맡긴 문서 작업은 마무리했어."
    elif family == "ambiguous_reference":
        root_b = task(b, obj)
        update = "둘 중 하나를 말하는 건데, 그 작업은 완료했어." if not brief else "어느 쪽인지는 말하지 않을게. 그 작업은 마무리했어."
        events = [("update", None)]
        alternatives = {"update": ["root_a", "root_b"]}
        requirements = [["root_a"], ["root_b"], ["update"]]
        query = "완료 보고의 대상 후보를 모두 알려주고, 어느 프로젝트 작업인지 확정할 수 있는지도 설명해줘."
    elif family == "quoted_example":
        if split == "dev":
            update = "설명 예시: '그 작업은 완료했어'라는 문구를 연습한 거야. 실제 보고가 아니야."
        elif split == "heldout":
            update = "문장 표현을 설명할 때 '그 작업은 마무리했어'라고 쓸 수 있어. 실제 보고가 아니야."
        else:
            update = "가령 누군가 '그 작업은 완료했어'라고 한다고 치자. 그런 일이 실제로 있었다는 뜻은 아니야."
        events = []
        requirements = [["update"]]
        query = "위 완료 문장은 실제 작업 보고야, 아니면 설명을 위한 문장이야?"
    elif family == "same_entity":
        root_b = task(a, other)
        update = f"{a} 프로젝트 건은 완료했어. 어느 문서인지는 말하지 않았어." if not brief else f"{a} 프로젝트에서 한 건을 마무리했어. 문서명은 밝히지 않았어."
        events = [("update", None)]
        alternatives = {"update": ["root_a", "root_b"]}
        requirements = [["root_a"], ["root_b"], ["update"]]
        query = f"{a} 프로젝트 완료 보고의 대상 문서 후보와 아직 확정할 수 없는 부분을 설명해줘."
    elif family == "novel_expression":
        update = f"{a} 프로젝트의 {obj}를 끝냈어." if not brief else f"{a} 프로젝트의 {obj}, 드디어 매듭지었어. 결과물을 넘겨뒀어."
    elif family == "chain":
        root_b = schedule(b)
        update = "그 작업은 아직 시작하지 않았어." if not brief else "아까 말한 문서 작업은 아직 손대지 않았어."
        update2 = f"{a} 프로젝트의 {obj}는 완료했어." if not brief else f"{a} 프로젝트에서 부탁한 {obj}는 마무리했어."
        events.append(("update2", "root_a"))
        requirements = [["root_a"], ["update"], ["update2"]]
        query = f"{a} 프로젝트 {obj}의 요청 이후 진행 상태가 어떻게 바뀌었어?"
    elif family == "cancelled":
        update = f"{a} 프로젝트의 {obj} 요청은 취소했어." if not brief else f"{a} 프로젝트에서 부탁했던 {obj} 건은 취소했어."
    named = [
        ("intro", "오늘 산책한 길에 꽃이 많이 피어 있었어."),
        ("root_a", root_a),
        ("aside", "휴대폰 화면 글자를 조금 키웠어."),
        ("root_b", root_b),
        ("meta", f"{a} 프로젝트 {obj} 진행 상태를 확인하는 방법을 설명한 적 있어. 실제 상태 보고는 아니야."),
        ("update", update),
    ]
    if update2:
        named.append(("update2", update2))
    named += [("tail", "내일 날씨는 나중에 확인해보자."), ("latest", "응, 지금 질문을 이어서 들을게.")]
    opaque = {name: f"m{rng.getrandbits(64):016x}" for name, _ in named}
    history = [{"id": opaque[name], "text": text} for name, text in named]
    return {
        "id": f"{split}-{family}-{variant}", "family": family,
        "public": {"history": history, "query": query},
        "gold": {"roots": [opaque["root_a"], opaque["root_b"]],
                 "events": [{"child": opaque[child], "parent": opaque[parent] if parent else None,
                             "possible_parents": [opaque[p] for p in alternatives.get(child, [])]}
                            for child, parent in events],
                 "required_any_of": [[opaque[p] for p in clause] for clause in requirements]},
    }


def cases(split):
    count = 8 if split == "dev" else 32
    return [make_case(family, i, split) for family in FAMILIES for i in range(count)]


def indistinguishable_worlds():
    public = {"history": [
        {"id": "a", "text": "은하 프로젝트 안내문 작성해줘."},
        {"id": "b", "text": "산호 프로젝트 안내문도 작성해줘."},
        {"id": "c", "text": "둘 중 하나를 말하는 건데, 그 작업은 완료했어."},
    ], "query": "어느 작업을 완료했어?"}
    return {"public": public, "world_a_parent": "a", "world_b_parent": "b",
            "assumed_world_probabilities": [0.5, 0.5],
            "minimum_forced_single_answer_error_under_this_prior": 0.5}
