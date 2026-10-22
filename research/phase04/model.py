"""A finite, explicitly defined semantics; no language model or production access.

This is a mathematical model check, not a natural-language benchmark. The index
is generated from exact symbolic events. Building that index from real language
is an unsolved prerequisite, deliberately outside this experiment.
"""

from itertools import product


QUESTIONS = {
    "current": "민들레 모임은 기록 범위 끝을 기준으로 현재 몇 시야?",
    "trajectory": "민들레 모임 시간이 처음부터 어떻게 바뀌었는지 순서대로 알려줘.",
    "verbatim": "민들레 모임을 처음 부탁한 문장을 원문 그대로 보여줘.",
}
PROTECTED = "직전 사용자: 필요한 근거로 확인해줘.\n직전 답변: 응, 이번 질문을 기준으로 확인할게.\n"
MODES = ("none", "last", "events")
SOURCE_COUNT = 5
HEAD = 4


def operation(index, kind):
    if kind == "none":
        return {
            "text": "민들레 모임 이야기는 잠시 쉬자. 오늘 산책에서는 가로수 잎이 노랗게 물들었고, 돌아오는 길에 따뜻한 차를 마셨어.",
            "kind": "none",
        }
    if kind == "quote":
        return {
            "text": "표현 예시로만 적어둘게. '민들레 모임은 18시로 바꿔줘'라고 쓸 수 있어. 실제 약속을 바꾸는 요청은 아니야.",
            "kind": "none",
        }
    if kind == "delta":
        return {
            "text": "민들레 모임은 바로 전에 정한 시간보다 한 시간 뒤로 변경해줘.",
            "kind": "delta", "value": 1,
        }
    hour = (12 if index == 2 else 14) + (kind == "set_b")
    return {
        "text": f"민들레 모임 시간을 정정할게. 이전 시각 대신 {hour}시로 확정해줘.",
        "kind": "set", "value": hour,
    }


def build_worlds():
    worlds = []
    kinds = ("none", "quote", "set_a", "set_b", "delta")
    # 2 initial values x 2 initial phrasings x 5 x 5 operations x 2 nuisances.
    for initial, wording, first, second, nuisance in product(
        (10, 11), (0, 1), kinds, kinds, (0, 1)
    ):
        original = (
            f"민들레 모임은 {initial}시에 잡아줘. 장소는 도서관으로 해줘."
            if wording == 0 else
            f"처음 계획을 적어둘게. 도서관에서 만나는 민들레 모임을 {initial}시에 잡아주면 좋겠어."
        )
        records = [
            {"seq": 0, "text": original},
            {"seq": 1, "text": "지난주에 읽은 책 이야기를 했었지. 책 속에서는 작은 정원을 가꾸는 과정이 자세히 나왔어. 지금 정하는 모임 시간과는 별개의 감상이야."},
            {"seq": 2, "text": operation(2, first)["text"]},
            {"seq": 3, "text": operation(3, second)["text"]},
            {"seq": 4, "text": (
                "다른 주제의 메모야. 하늘 프로젝트 안내문은 제목을 고르고 사진을 배치하는 중이었어. 그때 표지 후보와 문단 순서를 길게 비교했었지."
                if nuisance == 0 else
                "다른 주제의 메모야. 바다 프로젝트 예산표는 항목 이름을 정리하는 중이었어. 지난 대화에서는 표의 색상과 정렬 방식에 관해 이야기했어."
            )},
        ]
        state = initial
        trajectory = [[0, state]]
        for seq, kind in ((2, first), (3, second)):
            event = operation(seq, kind)
            if event["kind"] == "none":
                continue
            state = event["value"] if event["kind"] == "set" else state + event["value"]
            trajectory.append([seq, state])
        worlds.append({
            "id": f"world-{len(worlds):03d}",
            "parameters": {
                "initial": initial, "wording": wording, "first": first,
                "second": second, "nuisance": nuisance,
            },
            "records": records,
            "state_sequences": [p[0] for p in trajectory],
            "answers": {"current": state, "trajectory": trajectory, "verbatim": original},
        })
    return worlds


def certificate(world, mode):
    if mode == "none":
        return ""
    prefix = "[완전한 인덱스; 주제=민들레 모임 시간; 기록 범위=0..4; "
    if mode == "last":
        return prefix + f"마지막 실제 변경={world['state_sequences'][-1]}]\n"
    if mode == "events":
        return prefix + "실제 변경 목록=" + ",".join(map(str, world["state_sequences"])) + "]\n"
    raise ValueError(mode)


def source_text(world, mask):
    return "".join(f"[기록 {r['seq']}] {r['text']}\n" for r in world["records"] if mask & (1 << r["seq"]))


def rendering(world, mode, mask):
    return certificate(world, mode) + source_text(world, mask)


def byte_cost(world, mode, mask):
    return len(rendering(world, mode, mask).encode("utf-8"))
