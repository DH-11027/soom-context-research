"""Build the phase-02 research report from saved experiment outputs."""
from pathlib import Path
from html import escape
import hashlib
import json

ROOT = Path(__file__).resolve().parent
R = json.loads((ROOT / "results.json").read_text(encoding="utf-8"))
D = json.loads((ROOT / "link_diagnostic.json").read_text(encoding="utf-8"))
F = json.loads((ROOT / "fixtures.json").read_text(encoding="utf-8"))
assert hashlib.sha256((ROOT / "study.py").read_bytes()).hexdigest() == R["script_sha256"]
assert hashlib.sha256((ROOT / "diagnose_links.py").read_bytes()).hexdigest() == D["diagnostic_sha256"]
assert D["source_study_sha256"] == R["script_sha256"]


def table(headers, rows):
    return "<div class='scroll'><table><thead><tr>" + "".join(f"<th>{escape(str(h))}</th>" for h in headers) + "</tr></thead><tbody>" + "".join(
        "<tr>" + "".join(f"<td>{escape(str(v))}</td>" for v in row) + "</tr>" for row in rows
    ) + "</tbody></table></div>"


LABELS = {"all": "전체 유지", "recent_three": "최근 조각 3개", "lexical": "문자 유사도 선택",
          "lexical_with_given_edges": "유사도 + 참조 대상 보충", "calibrated": "통계 기준 통과 시만 압축"}
FAMILY_LABELS = {"duplicate": "중복", "correction_current": "현재 정정값", "correction_history": "변경 이력", "reference": "지시어와 목록",
                 "pending": "미완료 약속", "completion": "완료 근거", "exact_quote": "정확한 인용", "unrelated": "과거와 무관한 질문"}


def scores(split):
    return table(["방법", "압축한 사례", "필요 근거 누락", "기록 본문 바이트 절감"], [
        (LABELS[s["policy"]], f'{s["accepted"]}/{s["cases"]}', f'{s["failures"]}/{s["cases"]}', f'{100*s["byte_reduction"]:.2f}%')
        for s in R["summaries"][split]
    ])


def diagnostic(split):
    return table(["연결을 숨길 확률", "실제로 제공한 연결", "필요 근거 누락", "본문 바이트 절감"], [
        (f'{100*s["missing_edge_probability"]:.0f}%', f'{s["retained_true_edges"]}/{s["available_true_edges"]}',
         f'{s["failures"]}/{s["cases"]}', f'{100*s["byte_reduction"]:.2f}%') for s in D["reports"][split]
    ])


failure_row = next(r for r in R["rows"]["test_same_generator"] if r["family"] == "pending" and r["policies"]["lexical"]["failure"])
failure = next(c for c in F["splits"]["test_same_generator"] if c["id"] == failure_row["id"])
texts = {h["id"]: h["text"] for h in failure["history"]}
example = table(["역할", "문장"], [("질문", failure["query"]), ("선택한 요청", texts["t0"]),
                                      ("선택한 설명", texts["d1"]), ("빠뜨린 상태 변경", texts["t1"])])
fam = next(s for s in R["summaries"]["test_same_generator"] if s["policy"] == "lexical")["by_family"]
family_table = table(["유형", "필요 근거 누락", "누락률"], [
    (FAMILY_LABELS[k], f'{v["failures"]}/{v["n"]}', f'{100*v["failures"]/v["n"]:.1f}%') for k, v in fam.items()
])
calibration_table = table(["고정 임계값", "압축 후보 수", "관측 누락", "누락률 상한", "기준 통과"], [
    (c["threshold"], c["accepted"], c["errors"], f'{100*c["upper_risk_bound"]:.2f}%', "예" if c["certified_in_model"] else "아니오")
    for c in R["calibration"]["candidates"] if c["method"] == "lexical"
])
bound_table = table(["누락 0건인 압축 후보 수", "보정한 누락률 상한"], [
    (s["n"], f'{100*s["upper"]:.2f}%') for s in R["math_checks"]["zero_error_bounds"]
])
pair_items = "".join("<details><summary>" + escape(pair["name"]) + "</summary>" + table(
    ["항목", "왼쪽", "오른쪽"], [
        ("질문", pair["left"]["query"], pair["right"]["query"]),
        ("기록", " / ".join(h["text"] for h in pair["left"]["history"]), " / ".join(h["text"] for h in pair["right"]["history"])),
        ("정답", pair["left"]["answer"], pair["right"]["answer"]),
        ("충분 근거 표기", pair["left"]["required_any_of"], pair["right"]["required_any_of"]),
    ]) + "</details>" for pair in F["minimal_pairs"])

sections = [
    ("result", "이번 결론", """
<p><strong>운영에 적용할 단계는 아니다.</strong> 가상 기록에서 단어가 비슷한 조각만 고르면 분량을 많이 줄일 수 있었지만,
정정·미완료 약속·완료 근거를 놓쳤다. 고정한 22개 압축 후보 정책 중 통계 기준을 통과한 정책은 없었다.</p>
<p>실패를 살펴본 후 별도로 수행한 진단에서는, 원래 요청에서 그 요청을 가리키는 후속 기록까지 양방향으로 찾게 하니
모든 필요한 근거를 남길 수 있었다. 단, <strong>정확한 연결 관계를 미리 제공한 조건</strong>이다.
실제 문장에서 관계를 알아내는 능력은 평가하지 않았다.</p>
<p>현재까지의 유망한 가설은 ‘비슷한 문장을 지우기’보다 <strong>질문에 관련된 기록을 찾고, 그 기록의 정정·진행 상태·참조 연결을 함께 회수하기</strong>다.
이번 작업은 이 가설을 좁힌 연구다. 운영 코드·설정·데이터베이스·데몬은 변경하지 않았다.</p>
"""),
    ("design", "1. 데이터와 측정 대상", """
<p>교정용 512건, 같은 생성기로 만든 별도 평가 512건, 표현과 유형 비중을 바꾼 스트레스 평가 512건을 만들었다.
모두 사람이 읽을 수 있는 한국어 가상 기록이다. 실제 SOOM 대화를 사용하지 않았으며 모델 API를 호출하지 않았다.</p>
<p>각 사례에는 과거 기록 조각 8개와 현재 질문이 있다. 현재 질문과 마지막 조각은 항상 남긴다.
나머지 두 조각은 최근순 또는 문자 2-gram 유사도로 고른다. 완전한 Q/A 쌍이 아닌 조각 단위의 단순화다.
현재 운영의 작업 메모리·권한·전체 프롬프트 구성을 재현한 실험도 아니다.</p>
<p>정답 주석은 ‘이 조각들 중 하나면 충분하다’는 OR 조건과, 함께 필요한 근거들의 AND 조건으로 구성했다.
모든 조건이 충족되는지를 검사한다. 이 주석은 작성자가 정했으며 독립 검수자가 검증한 데이터셋은 아니다.</p>
<p>측정치는 <strong>필요 근거가 선택 결과에 남았는지</strong>다. 근거가 있어도 모델이 오독할 수 있으므로 답변 정확도와 다르다.
또한 분량은 기록 본문의 UTF-8 바이트 합이다. 입력 토큰·전체 프롬프트·요약 또는 검색 비용 절감률이 아니다.</p>
<p>선택기의 점수·임계값·후보 정책을 첫 결과를 보기 전에 고정했다. 교정 자료로만 통과 여부를 결정했다.
평가 자료는 동일한 템플릿 계열에서 생성했으므로, 새로운 언어 표현이나 실제 대화에 대한 일반화 검증으로 볼 수 없다.</p>
"""),
    ("frozen", "2. 고정한 선택기의 결과", """
<p><strong>생성 분포가 같은 별도 512건.</strong> 참조 보충은 ‘선택된 문장 → 그 문장이 가리키는 기록’ 방향으로만 수행한다.
이 방향 관계도 생성기가 제공한 정답 연결이며, 자동 추출 결과가 아니다.</p>
""" + scores("test_same_generator") + """
<p>통계 기준을 통과한 정책이 없어 보수적 선택은 전체 유지로 돌아갔다. 그 결과 누락 0건·절감 0%다.
이를 압축 성공이나 개선된 모델 정확도로 해석하지 않는다.</p>
<p><strong>스트레스 512건.</strong> 짧은 지시 표현의 비중을 20%에서 80%로 높이고, 정정·상태·참조 유형을 더 자주 생성했다.
서로 다른 두 요소를 함께 바꿨으므로 어느 변화의 영향인지 분리해서 추정할 수는 없다.</p>
""" + scores("stress_shifted_generator") + """
<p>이 분포 이동에서는 같은 통계 보장을 주장하지 않는다. 문제를 더 자주 노출시키기 위한 스트레스 검사다.</p>
"""),
    ("failure", "3. 참조 관계만 덧붙여도 해결되지 않은 이유", """
<p>가장 직접적인 반례는 ‘요청은 찾았지만 나중의 진행 보고는 놓친 경우’였다.</p>
""" + example + """
<p>주제 이름이 들어간 원래 요청과 긴 설명은 질문과 단어가 많이 겹친다.
‘그 작업’으로 시작하는 상태 보고에는 이름이 빠져 있어 선택에서 밀린다.
선택된 문장에서만 참조 대상을 보충하면, 애초에 선택되지 않은 상태 보고는 돌아오지 않는다.</p>
""" + family_table + """
<p>따라서 전체 평균만 보지 말고 정정과 약속의 누락을 별도로 확인해야 한다.
이 표의 유형은 평가용 정답 주석이며, 선택기는 유형 이름이나 정답을 입력받지 않았다.</p>
"""),
    ("diagnostic", "4. 실패 이후의 별도 진단: 양방향 연결 회수", """
<p>여기부터는 앞의 실패를 본 뒤 설계한 <strong>사후 진단</strong>이다. 같은 평가 사례를 재사용했으며 새로운 검증 성적으로 취급하지 않는다.
기존 교정 후보 22개에도 추가하지 않았다.</p>
<p>생성기가 알려 준 연결 A → B를 양방향으로 탐색했다. 상태 보고에서 원래 요청을 찾을 수도 있고,
원래 요청에서 그것을 가리키는 상태 보고를 찾을 수도 있게 했다. 문장을 대체하거나 진위를 판정하지 않고 함께 남긴다.</p>
<p>연결의 일부를 고정된 난수로 숨겨, 관계를 알아내지 못했을 때의 영향을 확인했다.</p>
""" + diagnostic("test_same_generator") + """
<p>정확한 연결을 모두 제공하면 동일 생성기 사례의 누락은 46건에서 0건, 바이트 절감은 68.57%에서 67.49%가 됐다.
연결을 50% 확률로 숨긴 조건에서는 누락이 28건으로 돌아왔다. 같은 무작위 추첨의 한 실현 결과이며 평균 효과 추정은 아니다.</p>
""" + diagnostic("stress_shifted_generator") + """
<p>이 결과는 <strong>관계 정보를 정확히 알면 가능한 수준</strong>을 보여 준다. 정답 연결 제공에 의존하므로 실사용 해결책으로 입증된 것이 아니다.
실제 관계 추출 오차, 잘못된 연결, 여러 단계 참조, 연결이 많아져 분량이 늘어나는 경우, 실제 답변 품질은 아직 평가하지 않았다.</p>
"""),
    ("statistics", "5. ‘확신할 때만 압축’의 통계적 의미", """
<p>선택기의 점수를 정답 확률로 취급하지 않는다. 별도 교정 자료에서 점수 임계값별 실제 근거 누락을 센다.
이 접근은 여러 후보를 검정해 위험을 제어하는 Learn then Test의 선택적 예측 구성에서 착안했다.
<a href='https://arxiv.org/pdf/2110.01052'>Angelopoulos et al., Learn then Test, §3.2</a>.</p>
<pre>A_j(X) = 1이면 후보 정책 j가 해당 사례를 압축함
L_j(X,Y) = 필요한 근거를 하나라도 잃으면 1
R_j = P(L_j = 1 | A_j = 1)
n_j = 교정 자료 중 A_j = 1인 사례 수
k_j = 그중 근거를 누락한 사례 수</pre>
<p>정책과 점수 함수를 미리 고정하고, 교정 사례가 목표 분포에서 독립·동일 분포로 추출됐다고 가정한다.
선택된 표본 수 n_j에 조건부로 오류 횟수를 이항분포로 다룬다. 각각의 상한 U_j는 다음 방정식의 해다.</p>
<pre>Σ_{i=0}^{k_j} C(n_j,i) U_j^i (1−U_j)^(n_j−i) = δ/M
M = 22, δ = 0.05
n_j = 0인 후보는 인증하지 않음; k_j = n_j이면 U_j = 1</pre>
<p>각 상한을 δ/M 수준으로 구성하면 합집합 부등식에 의해, 교정 자료의 무작위성에 대해 최소 1−δ 확률로
모든 고정 후보의 모집단 누락률이 동시에 해당 상한 이하에 놓인다.
그중 U_j ≤ α인 정책을 선택할 수 있다. 여기서는 연구용 예시로 α = 5%를 썼으며 운영의 허용 오류율로 제안한 값이 아니다.</p>
<p>통과 후보 중 교정 자료에서 바이트를 가장 많이 절감하는 것을 택하고, 없으면 전체를 유지하도록 했다.
임계값이 높다고 실제 오류율이 반드시 내려가는 것은 아니므로 단조성을 가정하지 않았다.</p>
""" + calibration_table + """
<p>표는 문자 유사도 방법의 11개 후보다. 참조 보충 방법 11개의 결과도 같았으며 보정에는 모두 22개를 포함했다.
점수 0.5 이상인 56건에서는 누락이 없었지만 상한은 약 10.3%로, 연구용 5% 기준을 통과하지 못했다.</p>
<pre>누락 0건일 때: U = 1 − (δ/M)^(1/n)</pre>
""" + bound_table + """
<p>같은 가정과 22개 후보 보정 아래에서, 누락 0건인 압축 후보가 최소 119건 있어야 5% 상한,
606건 있어야 1% 상한을 충족한다. 이는 전체 교정 사례 수가 아닌 <strong>실제로 압축을 선택한 표본 수</strong>다.
실제 대화의 의존성·분포 이동·주석 오류가 있으면 이 숫자를 그대로 적용할 수 없다.</p>
<p>이는 미래의 모든 개별 질문이 안전하다는 보장이 아니다. 한 평가 묶음의 실현 누락률이 상한 이내라는 보장도 아니다.
또한 유한 표본에서 오류를 한 번도 보지 않았다고 오류 확률이 정확히 0임을 인증할 수 없다.</p>
"""),
    ("groups", "6. 평균이 좋아도 중요한 유형은 실패할 수 있다", """
<pre>드문 유형의 비중 = 1%, 그 유형의 오류율 = 100%
나머지 유형의 오류율 = 0%
전체 평균 오류율 = 1%</pre>
<p>전체 5% 기준을 만족해도 드문 유형에서는 매번 실패할 수 있다.
정정·미완료 약속·완료 증거 같은 항목은 평균 점수만으로 보호할 수 없다는 간단한 반례다.</p>
<p>향후에는 알려진 핵심 의무를 별도 보존 조건으로 두고, 그런 의무를 식별하는 과정도 평가해야 한다.
유형별 통계 보장을 추가한다면 유형을 사전에 정의하고 다중 검정과 표본 부족을 다시 처리해야 한다.
이번 실험에서는 유형별 결과를 보여 주었을 뿐 유형별 통계 인증까지 수행하지 않았다.</p>
"""),
    ("pairs", "7. 작은 표현 변화로 정답이 달라지는 기준 사례", """
<p>아래 6쌍은 독립적인 판독용 기준 사례다. 모델에 답변시키지 않았으므로 성적표는 없다.
중첩 목록은 바깥쪽이 AND, 안쪽이 OR인 충분 근거 조건을 나타낸다.</p>
""" + pair_items),
    ("next", "8. 다음 연구에서 남은 질문", """
<p>다음으로 검증할 것은 <strong>요청과 나중의 정정·완료·취소 사이 연결을 실제 문장에서 정확히 추출할 수 있는가</strong>다.
유사도만 높이는 것보다 필요한 후속 기록을 놓치지 않는지에 초점을 둔다.
자동 추출을 시험할 때는 정답 연결을 입력하지 않고, 새로운 표현과 주제를 가진 별도 평가 자료를 먼저 고정해야 한다.</p>
<p>관계를 놓치는 비율뿐 아니라 잘못 연결하는 비율, 남겨지는 분량, 추출·검색 비용, 지연, 최종 답변을 함께 본다.
현재는 연결 추출기, 임베딩 모델, 실제 LLM 답변 비교를 구현하거나 실행하지 않았다.
운영에 적용할 변경은 만들지 않았고, 본 연구 폴더만 추가했다.</p>
"""),
    ("reproduce", "재현과 파일", f"""
<p>Python {escape(R['python'])} 표준 라이브러리만 사용했다. 이항 누적확률 계산은 작은 n에서 직접 합과 {R['math_checks']['binomial_cross_checks']}회 교차 확인했다.
이 검사는 통계 계산 구현 검사이며 모델 품질 검사가 아니다.</p>
<pre>python -X utf8 study.py
python -X utf8 diagnose_links.py
python -X utf8 make_report.py</pre>
<p><a href='study.py'>고정 실험 코드</a> · <a href='results.json'>전체 실험 결과</a> · <a href='fixtures.json'>가상 기록과 정답 주석</a> ·
<a href='diagnose_links.py'>사후 연결 진단</a> · <a href='link_diagnostic.json'>진단 결과</a> ·
<a href='research.ipynb'>노트북</a> · <a href='../research.html'>이전 연구 노트</a></p>
<p class='small'>고정 실험 SHA-256: {escape(R['script_sha256'])}<br>
사후 진단 SHA-256: {escape(D['diagnostic_sha256'])}<br>
기록일: 2026-10-22. 본문은 저장된 CLI 실행 결과다. 노트북 재현 셀은 실행하지 않은 상태다.</p>
"""),
]

css = """
:root{font-family:'Malgun Gothic',system-ui,sans-serif;color:#24343c;background:#f5f6f2;color-scheme:light}body{margin:0;line-height:1.85}main{max-width:1000px;margin:36px auto;padding:34px 40px;background:white;border:1px solid #dce4e0;border-radius:12px}h1{font-size:29px;line-height:1.4}h2{font-size:21px;margin-top:40px;line-height:1.5}p{margin:14px 0}a{color:#126474;text-underline-offset:3px}.meta,.small{color:#66747b}.small{font-size:12px;overflow-wrap:anywhere}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:10px 12px;border-bottom:1px solid #dce4e7;text-align:left;min-width:80px}th{background:#eff5f4}pre{overflow-x:auto;background:#f1f5f7;border-left:3px solid #638d98;padding:16px;font-size:13px;line-height:1.7}details{padding:12px 0;border-bottom:1px solid #dde3e5}summary{cursor:pointer;font-weight:bold}nav{display:flex;gap:8px 16px;flex-wrap:wrap;font-size:14px}@media(max-width:680px){main{padding:22px 16px;margin:0;border:0;border-radius:0}h1{font-size:24px}}@media print{main{border:0;margin:0;padding:0}nav{display:none}pre{white-space:pre-wrap}}
"""
html = "<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
html += "<title>생략 판단과 후속 변경 연결 — SOOM 연구 02</title><style>" + css + "</style></head><body><main>"
html += "<p class='meta'>SOOM 연구 02 · 2026-10-22 · 운영 변경 없음 · 합성 자료</p><h1>생략해도 된다는 근거는 무엇인가</h1>"
html += "<nav>" + "".join(f"<a href='#{ident}'>{escape(title)}</a>" for ident, title, _ in sections) + "</nav>"
html += "".join(f"<section id='{ident}'><h2>{escape(title)}</h2>{body}</section>" for ident, title, body in sections)
html += "</main></body></html>"
(ROOT / "research.html").write_text(html, encoding="utf-8")
cells = [{"cell_type": "markdown", "id": ident, "metadata": {}, "source": [f"## {title}\n\n", body]}
         for ident, title, body in sections]
cells.append({"cell_type": "code", "id": "rerun", "metadata": {}, "execution_count": None, "outputs": [],
              "source": ["# 이 노트북 폴더에서 실행. 가상 결과 파일을 다시 생성한다.\n", "import runpy\n",
                         "runpy.run_path('study.py', run_name='__main__')\n",
                         "runpy.run_path('diagnose_links.py', run_name='__main__')\n"]})
nb = {"nbformat": 4, "nbformat_minor": 5, "metadata": {
    "kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
    "language_info": {"name": "python", "version": R["python"]},
    "research_scope": "synthetic evidence retention, with separate post-hoc oracle-edge diagnostic",
}, "cells": cells}
(ROOT / "research.ipynb").write_text(json.dumps(nb, ensure_ascii=False, indent=2), encoding="utf-8")
print("Created phase02/research.html and phase02/research.ipynb")
