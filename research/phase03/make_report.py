"""Render phase-03 saved results and the separately preserved label audit."""
from pathlib import Path
from html import escape
import hashlib
import json

ROOT = Path(__file__).resolve().parent
R = json.loads((ROOT / "results.json").read_text(encoding="utf-8"))
A = json.loads((ROOT / "label_audit.json").read_text(encoding="utf-8"))
F = json.loads((ROOT / "evaluation_fixtures.json").read_text(encoding="utf-8"))
P = json.loads((ROOT / "frozen_protocol.json").read_text(encoding="utf-8"))
assert R["source_hashes"] == P["source_hashes"] == A["source_hashes"]
assert all(hashlib.sha256((ROOT / n).read_bytes()).hexdigest() == h for n, h in P["source_hashes"].items())


def table(headers, rows):
    return "<div class='scroll'><table><thead><tr>" + "".join(f"<th>{escape(str(h))}</th>" for h in headers) + "</tr></thead><tbody>" + "".join(
        "<tr>" + "".join(f"<td>{escape(str(v))}</td>" for v in row) + "</tr>" for row in rows
    ) + "</tbody></table></div>"


NAMES = {"all": "전체 유지", "lexical_only": "질문과 문자 유사도만 사용", "nearest": "가까운 요청에 연결",
         "similarity": "문자가 비슷한 요청에 연결", "selective": "후보가 하나일 때만 연결",
         "selective_with_candidates": "단일 후보 연결 + 애매한 후보 함께 보존"}


def extraction(split):
    return table(["연결 방식", "확정한 연결 중 타당", "찾을 수 있는 연결 회수", "애매한 대상 강제 확정"], [
        (NAMES[m], f'{x["justified_links"]}/{x["asserted_links"]}', f'{x["justified_links"]}/{x["resolvable_links"]}',
         f'{x["ambiguous_forced_links"]}/{x["ambiguous_events"]}')
        for m, x in R["results"][split]["summary"]["extraction"].items()
    ])


def selection(split):
    return table(["문맥 선택 방식", "최초 추적 기준 미충족", "검수 후 답변 근거 기준 미충족", "본문 바이트 절감"], [
        (NAMES[m], f'{x["original_trace_failures"]}/{x["cases"]}', f'{x["revised_evidence_failures"]}/{x["cases"]}',
         f'{100*x["byte_reduction"]:.2f}%') for m, x in A["reports"][split]["policies"].items()
    ])


def case_table(split, family):
    case = next(c for c in F[split] if c["family"] == family)
    ids = set(case["gold"]["roots"]) | {e["child"] for e in case["gold"]["events"]}
    if family == "quoted_example":
        ids |= {i for clause in case["gold"]["required_any_of"] for i in clause}
    return table(["구분", "본문"], [("현재 질문", case["public"]["query"])] + [
        ("기록", m["text"]) for m in case["public"]["history"] if m["id"] in ids
    ])


sections = [
    ("result", "이번 연구의 결론", """
<p><strong>정답 연결을 주지 않고 문장만으로 연결하는 작은 규칙 기반 실험을 수행했다.</strong>
확실한 단서로 후보가 하나일 때만 연결하고, 애매할 때 후보들을 함께 남기는 방법은 제한된 가상 사례에서 유효했다.
다만 새 표현을 만나면 요청이나 변경 보고 자체를 알아보지 못해 누락이 생겼다. 운영 적용의 근거는 아직 없다.</p>
<p>평가 과정에서 기준도 교정했다. 최초 기준은 원래 요청과 후속 보고를 모두 남기도록 요구했지만,
현재 상태만 묻는 질문에는 대상이 명시된 보고 하나로 충분한 사례가 있었다.
<strong>모든 연결을 복원하는 목표와 현재 질문에 충분히 답하는 목표는 다르다.</strong>
최초 결과와 사후 검수 결과를 모두 보존했다.</p>
<p>운영 코드·설정·데이터베이스·데몬은 변경하지 않았다. 실제 대화나 모델 API를 사용하지 않았고,
임베딩·LLM의 성능을 평가한 실험도 아니다.</p>
"""),
    ("design", "1. 무엇을 입력했고 무엇을 고정했나", """
<p>개발용 72건, 다른 문장틀·프로젝트 이름을 쓰는 평가 288건, 더 넓은 표현 변화를 주는 스트레스 288건을 만들었다.
9개 유형에 각각 8개 또는 32개의 변형을 배치했다. 동일 유형끼리 구조가 반복되는 템플릿 실험이며 독립·동일 분포의 실제 대화 표본이 아니다.</p>
<p>유형은 대상이 명시된 작업, 시간 정정, 후보가 하나인 지시 표현, 후보가 여러 개인 지시 표현,
보고를 흉내 낸 예시, 같은 프로젝트의 여러 문서, 새 상태 표현, 여러 단계의 상태 변경, 취소다.</p>
<p>추출기는 시간순 <code>id + text</code>만 입력받는다. 정답 연결·대상 유형·필수 근거 주석은 평가기만 사용했다.
문맥을 고를 때는 현재 질문도 입력한다. 무작위 메시지 ID를 바꾸어도 추출 결과가 대응 관계 그대로 유지되는지 확인했다.</p>
<p>개발 결과를 확인한 뒤 추출기·생성기·평가기의 해시를 고정하고 평가를 실행했다.
평가 결과를 본 뒤 이 세 파일을 변경하지 않았다. 다만 같은 연구자가 규칙과 모든 문장틀을 작성했으므로 독립적인 맹검이나 외부 사전등록은 아니다.</p>
<p>문맥 선택은 현재 질문과 마지막 기록을 유지하고, 질문과 문자 2-gram이 비슷한 과거 기록 두 개를 기본으로 둔다.
이후 추출된 연결을 양방향으로 따라 관련 기록을 보충한다. 비용은 본문 UTF-8 바이트이며 실제 입력 토큰·전체 프롬프트 비용과 다르다.</p>
"""),
    ("methods", "2. 비교한 연결 방법", """
<p>세 방법은 동일한 요청·변경 표현 감지 규칙을 공유한다. 요청으로 인식한 이전 기록 중 작업·일정 유형이 맞는 것을 후보로 삼는다.</p>
""" + table(["방법", "선택 기준", "한계"], [
    ("가까운 요청", "시간상 마지막 후보 하나", "다른 작업으로 대화가 전환됐어도 과거 작업을 보고할 수 있음"),
    ("문자 유사도", "보고와 문자 2-gram이 가장 비슷한 후보 하나", "단서가 부족해도 하나를 확정함"),
    ("보수적 연결", "명시된 프로젝트·문서 조건을 적용한 뒤 후보가 하나일 때만 확정", "표현 감지와 후보 목록이 틀리면 누락 또는 오연결 가능"),
]) + """
<p>보수적 연결에는 두 가지 보존 방식을 비교했다. 확정 연결만 보충하거나,
대상이 여러 개일 때 보고와 후보 기록들을 함께 보충한다. 후보를 함께 보존한다는 것은 모두 같은 대상을 가리킨다고 단정하는 것이 아니다.</p>
<p>이 연구 문제는 선행 연구의 대화 지시 대상 해석과 관련이 있다. CODI-CRAC은 개체 동일성, bridging, 담화 지시를 구분한다.
이번 간단한 요청–보고 연결은 그 모든 과제를 구현한 것이 아니다.
<a href='https://aclanthology.org/2021.codi-sharedtask.8/'>Li, Kobayashi &amp; Ng, CODI-CRAC 2021</a>.</p>
"""),
    ("links", "3. 연결 정확도와 회수율은 별개다", """
<p><strong>다른 문장틀로 만든 평가 288건.</strong> 사례 하나에 보고가 둘인 경우도 있고, 실제 보고가 아닌 사례도 있다.
그래서 문맥 사례 수와 연결 수의 분모가 다르다.</p>
""" + extraction("heldout") + """
<p>보수적 규칙이 확정한 192개 연결은 모두 맞았다. 대상이 불분명한 64개에서는 하나를 확정하지 않았다.
그러나 해석 가능한 연결 224개 가운데 32개를 놓쳤다. 주어진 표현 목록에 없는 ‘매듭지었어’ 등을 변경 보고로 인식하지 못했다.</p>
<pre>연결 정밀도 = 올바른 확정 연결 수 / 확정한 연결 수
연결 회수율 = 올바른 확정 연결 수 / 해석 가능한 정답 연결 수</pre>
<p>적게 연결하면 정밀도가 높게 나올 수 있다. 따라서 192/192라는 수치만으로 압축이 안전하다고 결론낼 수 없다.
이는 작성한 가상 문장틀에서 관측한 값이지 실제 한국어 대화의 정확도 추정이 아니다.</p>
<p><strong>스트레스 평가.</strong> 절반의 요청 문장을 ‘손 좀 봐줄래’, ‘약속 잡자’ 같은 다른 표현으로 바꾸고,
보고 예시를 나타내는 표현도 바꿨다.</p>
""" + extraction("stress") + """
<p>보수적 방법의 확정 연결은 96/96으로 맞았지만, 해석 가능한 연결 회수는 96/224로 줄었다.
요청 인식은 576개 중 288개, 실제 변경 보고 인식은 288개 중 256개였다.
보고가 아닌 예시 32개도 변경 보고로 잘못 감지했다.
애매한 사례에서 단정을 하지 않았더라도, 후보 둘을 모두 확보한 것은 64건 중 32건뿐이었다.</p>
"""),
    ("audit", "4. 평가 기준 검수: 요청 이력과 답변 근거", """
<p>최초 주석은 작업의 요청–보고 연결을 추적하려고 원래 요청과 보고를 함께 요구했다.
결과를 검수하면서 아래 사례에서는 그 요구가 현재 질문에 비해 강하다는 점을 확인했다.</p>
""" + case_table("heldout", "novel_expression") + """
<p>보고가 프로젝트와 문서를 직접 명시하고 있다. 현재 진행 상태를 답하는 데에는 보고가 충분할 수 있다.
원래 요청까지 없다는 이유로 곧바로 답변 근거 누락으로 처리하면 불필요한 문맥을 보존하도록 유도한다.</p>
<p>그래서 ‘대상이 명시된 작업 상태’, ‘새 표현의 상태 보고’, ‘대상이 명시된 취소’ 세 유형에서는
원래 요청을 필수로 보던 조건을 제거한 별도 지표를 만들었다. 각 평가 묶음 96건의 주석 기준을 검수했으며,
코드·문장·선택 결과·최초 점수는 변경하지 않았다.</p>
<p>이 검수 역시 동일 연구자가 사후에 한 것이며 독립적인 정답 판정은 아니다.
실제 모델이 답변을 생성했을 때의 정확도가 아니라, 작성자가 정한 충분 근거의 보존 여부를 평가한다.</p>
""" + selection("heldout") + """
<p>후보를 함께 남기는 방법은 최초 요청 추적 기준에서 32건, 검수 후 현재 질문의 근거 기준에서 0건을 놓쳤다.
본문 절감은 42.09%였다. 사후 기준의 0건을 사전 고정된 검증 통과나 실제 품질 보장으로 제시하지 않는다.</p>
""" + selection("stress") + """
<p>스트레스에서는 같은 방법이 검수 후에도 96/288건에서 근거 조건을 충족하지 못했다.
표현 감지 규칙의 한계가 남아 있으므로 실사용에 적용할 수 있다고 볼 수 없다.
또한 2차 연구와 문장·질문·평가 기준이 달라 절감률을 직접 비교해 성능 향상이나 하락으로 해석하지 않는다.</p>
"""),
    ("ambiguity", "5. 수학적으로 구별할 수 없는 경우", """
<p>다음 기록은 어느 쪽인지를 가르는 단서가 없다.</p>
<pre>A: 은하 프로젝트 안내문 작성해줘.
B: 산호 프로젝트 안내문도 작성해줘.
C: 둘 중 하나를 말하는 건데, 그 작업은 완료했어.</pre>
<p>화자가 A를 뜻한 세계와 B를 뜻한 세계에서 관측되는 입력 x가 똑같다고 가정하자.
두 세계의 사전 확률도 각각 1/2이라고 가정한다. 강제로 하나를 고르는 알고리즘이 A를 고를 확률을 r이라 하면:</p>
<pre>P(오류 | x) = (1/2)(1−r) + (1/2)r = 1/2.</pre>
<p>이 구성에서는 알고리즘을 복잡하게 하거나 무작위로 선택해도 정보가 새로 생기지 않는다.
이는 모든 모호한 대화의 실제 오류율이 50%라는 주장이 아니다. 동일 관측·동일 사전 확률을 가정한 식별 불가능성 반례다.</p>
<p>가능한 출력은 ‘A 또는 B 중 하나, 현재 기록만으로 확정할 수 없음’이다.
원문 후보를 함께 남기면 이 불확실성을 보존할 수 있지만, 그 자체가 숨겨진 정답을 알아내는 것은 아니다.
후속 문맥이나 확인이 필요할 수 있다.</p>
"""),
    ("blindspots", "6. 감지하지 못한 불확실성은 보류로도 해결되지 않는다", """
<p>후보가 둘이면 보류하는 로직은, 먼저 후보가 둘 있다는 사실을 알아야 작동한다.
아래 스트레스 사례에서는 요청 문장을 인식하지 못해 후보 집합이 비었다.</p>
""" + case_table("stress", "unique_reference") + """
<p>이는 ‘문맥 자체에 단서가 없음’과 다르다. 사람에게는 단서가 있지만 실험 규칙이 읽지 못한 것이다.
확정 연결, 여러 후보가 있는 상태, 후보를 찾지 못한 상태, 보고 자체를 감지하지 못한 상태를 구별해야 한다.</p>
""" + table(["상태", "의미", "연구상 처리"], [
    ("확정 연결", "현재 추출된 근거상 대상 하나", "연결 근거를 남기고 정확도 평가"),
    ("후보 여러 개", "복수의 가능한 대상이 실제로 발견됨", "단정하지 않고 후보와 원문 보존"),
    ("후보 없음", "추출 실패 또는 문맥 부족을 구별하지 못함", "관련 없음으로 해석하지 않음"),
    ("보고 감지 실패", "변경 문장이라는 사실을 놓침", "연결 단계만 고쳐서는 해결 불가"),
]) + """
<p>이번 실험은 이 구별의 필요성을 보여 주었을 뿐, 후보 없음이나 감지 실패를 자동으로 복구하는 방법을 구현하지 않았다.</p>
"""),
    ("next", "7. 다음 연구 방향", """
<p>다음에는 문장을 이해하는 추출기가 요청·정정·진행 보고·인용을 구별하고,
연결 후보와 근거가 되는 원문 구간을 함께 반환하는지 평가하는 것이 적절하다.
이번 실패 문구를 규칙 목록에 계속 추가하면 같은 문장틀에 맞춘 성적만 높일 수 있으므로, 새 표현의 독립 평가가 필요하다.</p>
<p>또한 현재 질문에 필요한 답변 근거와 장기 이력 추적 목표를 먼저 분리해야 한다.
‘모든 연결을 복원해서 최대한 남긴다’를 기본 목표로 삼으면 다시 문맥이 길어질 수 있다.
충분한 단독 보고는 짧게 유지하고, 참조가 풀려야 이해되는 기록은 연결을 회수하는 방향을 가설로 둔다.</p>
<p>실제 LLM·임베딩 기반 추출, 독립 주석 검수, 실제 답변 품질, 호출 비용·토큰·지연은 아직 검증하지 않았다.
연구 결과를 운영에 적용하지 않는다.</p>
"""),
    ("reproduce", "재현과 증거", f"""
<p>Python {escape(R['python'])} 표준 라이브러리만 사용했다. 정답이 추출기에 전달되지 않는 입력 구조,
ID 변경에 대한 결정 불변성, 과거 기록만 후보로 삼는 순서, 선택 집합의 포함 관계를 검사했다.
세 자료 묶음 간 동일한 전체 기록·질문은 없었지만 같은 유형의 문장틀은 공유한다.</p>
<pre># 개발 결과 재현
python -X utf8 evaluate.py --dev
# 고정된 해시와 일치하는 평가 재현
python -X utf8 evaluate.py --test
# 최초 결과를 보존한 별도 주석 검수
python -X utf8 audit_labels.py
python -X utf8 make_report.py</pre>
<p><code>--freeze</code>는 최초 평가 전에 한 번 실행했다. 이미 고정 파일이 있는 상태에서는 덮어쓰지 않는다.</p>
<p><a href='extractor.py'>문장 규칙 추출기</a> · <a href='fixtures.py'>가상 기록 생성기</a> ·
<a href='evaluate.py'>평가기</a> · <a href='frozen_protocol.json'>고정한 계획과 해시</a> ·
<a href='results.json'>최초 평가 결과</a> · <a href='label_audit.json'>별도 주석 검수</a> ·
<a href='evaluation_fixtures.json'>평가용 기록과 주석</a> · <a href='research.ipynb'>노트북</a> ·
<a href='../phase02/research.html'>이전 연구</a> · <a href='../index.html'>연구 목록</a></p>
<p class='small'>추출기 SHA-256: {escape(P['source_hashes']['extractor.py'])}<br>
고정 시각(UTC): {escape(P['created_at_utc'])}<br>
본문 표는 저장된 CLI 실행 결과다. 노트북의 재현 셀은 실행하지 않은 상태다.</p>
"""),
]

css = """
:root{font-family:'Malgun Gothic',system-ui,sans-serif;color:#22343d;background:#f4f6f3;color-scheme:light}body{margin:0;line-height:1.85}main{max-width:1020px;margin:36px auto;padding:34px 40px;background:white;border:1px solid #dce4e0;border-radius:12px}h1{font-size:29px;line-height:1.4}h2{font-size:21px;margin-top:40px;line-height:1.5}p{margin:14px 0}a{color:#126474;text-underline-offset:3px}.meta,.small{color:#65757a}.small{font-size:12px;overflow-wrap:anywhere}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:10px 12px;border-bottom:1px solid #dce4e7;text-align:left;min-width:85px}th{background:#edf4f3}pre{overflow-x:auto;background:#f1f5f7;border-left:3px solid #638d98;padding:16px;font-size:13px;line-height:1.7}nav{display:flex;gap:8px 16px;flex-wrap:wrap;font-size:14px}@media(max-width:680px){main{padding:22px 16px;margin:0;border:0;border-radius:0}h1{font-size:24px}}@media print{main{border:0;margin:0;padding:0}nav{display:none}pre{white-space:pre-wrap}}
"""
html = "<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
html += "<title>문장만으로 후속 변경 연결하기 — SOOM 연구 03</title><style>" + css + "</style></head><body><main>"
html += "<p class='meta'>SOOM 연구 03 · 연구 전용 · 합성 자료 · 운영 변경 없음</p><h1>문장만으로 후속 변경을 연결할 수 있는가</h1>"
html += "<nav>" + "".join(f"<a href='#{ident}'>{escape(title)}</a>" for ident, title, _ in sections) + "</nav>"
html += "".join(f"<section id='{ident}'><h2>{escape(title)}</h2>{body}</section>" for ident, title, body in sections)
html += "</main></body></html>"
(ROOT / "research.html").write_text(html, encoding="utf-8")
cells = [{"cell_type": "markdown", "id": ident, "metadata": {}, "source": [f"## {title}\n\n", body]}
         for ident, title, body in sections]
cells.append({"cell_type": "code", "id": "inspect_saved", "execution_count": None, "outputs": [], "metadata": {},
              "source": ["# 저장된 결과 읽기. 실행 재현 명령은 본문 참고.\n", "import json\n", "from pathlib import Path\n",
                         "results = json.loads(Path('results.json').read_text(encoding='utf-8'))\n",
                         "results['results']['heldout']['summary']['extraction']\n"]})
nb = {"nbformat": 4, "nbformat_minor": 5, "metadata": {
    "kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
    "language_info": {"name": "python", "version": R["python"]},
    "scope": "text-only rule baselines, frozen evaluation, separately preserved post-hoc label audit",
}, "cells": cells}
(ROOT / "research.ipynb").write_text(json.dumps(nb, ensure_ascii=False, indent=2), encoding="utf-8")
index = "<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>SOOM 맥락 압축 연구</title><style>" + css + "</style></head><body><main>"
index += "<p class='meta'>운영 방식 유지 · 별도 연구 기록</p><h1>SOOM 맥락 압축 연구</h1><p>수식과 가상 실험의 조건을 기록한다. 실제 운영 품질 검증이나 적용 결과와 구분한다.</p>"
index += "<p><a href='phase03/research.html'>03 · 문장만으로 후속 변경 연결하기</a><br>자동 규칙, 모호성, 누락, 질문에 필요한 근거와 이력 추적의 차이.</p>"
index += "<p><a href='phase02/research.html'>02 · 생략 판단과 후속 변경 연결</a><br>통계적 보류와 정확한 연결을 제공한 조건에서의 진단.</p>"
index += "<p><a href='research.html'>01 · 질문별 대화 맥락 압축</a><br>가중 coverage, 연결 관계의 반례, 점수 오차 민감도.</p></main></body></html>"
(ROOT.parent / "index.html").write_text(index, encoding="utf-8")
print("Created phase03/research.html, phase03/research.ipynb and the research index.")
