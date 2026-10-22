"""Publish a self-contained research record, including negative results."""

import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
A = json.loads((HERE / "audit.json").read_text(encoding="utf-8"))
V2 = json.loads((HERE / "revision02/reduction_results.json").read_text(encoding="utf-8"))
P = json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))
LABELS = {"drop_unknown": "미인식 문장 무시", "cheap": "보수적 1차 해석", "eager": "전체 상세 해석", "lazy": "필요한 곳만 상세 해석"}


def esc(x):
    return html.escape(str(x))


def table(headers, rows):
    return "<div class='scroll'><table><thead><tr>" + "".join(f"<th>{esc(x)}</th>" for x in headers) + "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{esc(x)}</td>" for x in row) + "</tr>" for row in rows) + "</tbody></table></div>"


def outcomes(split):
    rows = []
    for mode, d in R["summary"][split].items():
        c = d["status_counts"]
        rows.append([LABELS[mode], f"{c.get('certified_model',0)}/{d['question_cases']}", d["false_certifications"], c.get("opaque_fallback", 0), c.get("ambiguous", 0), c.get("unsupported_query", 0), f"{d['output_byte_reduction_percent']:.2f}%", f"{d['mean_detail_calls']:.3f}"])
    return table(["방식", "단일 답 판정", "그중 틀린 판정", "미해석으로 전체 복원", "모호성 유지", "미지원 질문", "출력 bytes 절감", "평균 상세 해석 횟수"], rows)


cost_rows = []
for split, label in (("main", "기본 조합"), ("stress", "낯선 표현 추가")):
    for mode in ("eager", "lazy"):
        s = R["summary"][split][mode]
        cost_rows.append([label, LABELS[mode], s["total_detail_calls"], f"{s['output_plus_detail_proxy_reduction_percent']:.2f}%", f"{s['per_call_overhead_break_even_bytes']:.2f}"])

long_rows = [[r["pattern"], r["mode"], r["records"], r["cheap_reads"], r["detail_calls"]] for r in R["scaling"] if r["length"] == 4096]
operator_rows = [
    ["x ← c", "x를 요구 목록에서 제거", "이전 x 값에 의존하지 않음"],
    ["x ← x+d", "x를 계속 요구", "이전 x가 필요"],
    ["x ← y", "x 대신 당시의 y를 요구", "복사 이후 y의 변경은 x에 소급 적용되지 않음"],
    ["둘 중 하나를 c로", "각 후보의 이전 값도 유지", "단일 대상을 임의로 확정하지 않음"],
    ["해석하지 못한 문장", "영향 범위를 전체로 잡고 상세 해석", "계속 불명확하면 원문 전체로 복원"],
]

CSS = """
:root{font-family:'Malgun Gothic',system-ui,sans-serif;color:#233b43;background:#f2f6f3;color-scheme:light}body{margin:0;line-height:1.85}main{max-width:1120px;margin:30px auto;padding:38px 44px;border:1px solid #dbe4de;background:white;border-radius:14px}h1{font-size:30px;line-height:1.45;letter-spacing:-.025em}h2{font-size:22px;line-height:1.5;margin-top:42px}h3{font-size:18px;margin-top:25px}p{margin:15px 0}a{color:#086d7d;text-underline-offset:3px}.meta,.small{color:#65787c}.small{font-size:13px;overflow-wrap:anywhere}nav{display:flex;gap:9px 16px;flex-wrap:wrap;font-size:14px}.callout{background:#eaf3ef;border-left:4px solid #4d8876;padding:16px 22px;border-radius:5px}.limit{background:#fff5e7;border-left:4px solid #b89149;padding:16px 22px;border-radius:5px}.scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:13px;line-height:1.65}th,td{text-align:left;padding:10px 11px;border-bottom:1px solid #dbe4e2;min-width:90px}th{background:#edf4f2}pre{white-space:pre-wrap;padding:18px;border-left:3px solid #638c96;background:#f1f5f7;line-height:1.8;font-size:13px;overflow-x:auto}.formula{font-family:Consolas,monospace;font-size:14px}li{margin:8px 0}details{margin:15px 0;border:1px solid #dbe5df;border-radius:8px;padding:12px 16px}summary{cursor:pointer;font-weight:600}@media(max-width:700px){main{margin:0;border:0;border-radius:0;padding:23px 17px}h1{font-size:25px}}@media print{main{margin:0;padding:0;border:0}nav{display:none}}
"""

BODY = f"""
<p class='meta'>SOOM 맥락 압축 연구 · 05 · 2026-10-22 · 운영 변경 없음</p>
<h1>필요한 기록을 거꾸로 찾고, 필요한 의미만 더 해석하기</h1>
<p>질문별 의존 관계 추적, 보수적인 해석 확장, 정수 변경 구간의 정확한 최소 비용 계산.</p>
<nav><a href='../index.html'>전체 연구</a><a href='#results'>비교 결과</a><a href='#algorithm'>알고리즘</a><a href='#proof'>성립 조건</a><a href='#algebra'>상쇄 최적화</a><a href='#limits'>한계</a><a href='research.ipynb'>노트북</a></nav>

<div class='callout'><strong>이번 단계의 성과</strong><p>정답 세계 전체를 알아야 했던 Phase 04에서 벗어나, 문장과 질문만 입력받는 연구용 선택기를 만들었다. 같은 제한된 해석기를 사용하면서 전체를 상세 해석한 방식과 동일한 판정·근거를 672개 질문에서 얻었고, 상세 해석 횟수는 기본 조합 92.87%, 낯선 표현 조합 90.63% 감소했다. 상대 변경이 서로 상쇄되는 일부 구간에는 별도의 정확한 최소 비용 알고리즘을 추가했다.</p></div>
<div class='limit'><strong>숫자의 경계</strong><p>이는 실제 LLM 호출이나 자연어 이해 능력 개선의 측정이 아니다. 두 단계 해석기는 작은 한국어 패턴 인식 함수다. 가상 계획 기록의 의미를 정확히 정의한 조건에서 비교했다. 낯선 표현을 추가하면 단일 답을 판정하는 사례가 75%에서 12.5%로 줄어든다. 운영 코드·DB·데몬·설정은 변경하지 않았다.</p></div>

<h2 id='results'>1. 개선된 부분과 여전히 막힌 부분</h2>
<p>가상 기록 336개에 질문을 두 개씩 붙여 672개 질문 사례를 만들었다. 기본 조합은 12개 구조 × 16개 파라미터 = 192개 기록·384개 질문, 낯선 표현 조합은 12개 구조 × 12개 변형 = 144개 기록·288개 질문이다. 각 묶음은 같은 작성자가 만든 통제된 문법 조합이며 독립적인 실제 대화 표본이 아니다. 질문 둘이 같은 기록을 공유한다. 매 질문은 새 실행으로 비교하며 질문 사이 캐시 재사용은 하지 않았다.</p>
<p>선택기에는 원문·순서·불투명 ID·대상 명단·질문·스냅샷만 전달했다. 구조 이름과 정답 전이는 전달하지 않았다. 평가기는 별도의 정답 전이를 실행해 가능한 결과를 구한다. 질문 해석도 지원 문법 안에서만 이루어지며, 지원하지 않는 질문에는 전체 원문을 돌려준다.</p>
<h3>기본 조합 · 384개 질문</h3>
{outcomes('main')}
<p>새로운 표현을 무시하면 가장 짧아 보이지만, 336개 단일 답 판정 중 112개가 틀렸다. 보수적으로 미해석 문장을 유지한 뒤 필요한 부분만 더 해석하면, 단일 답을 판정할 수 있는 사례가 128개에서 288개로 늘었다. 나머지는 미해석 원문 48개, 실제 대상 모호성 32개, 지원하지 않는 질문 16개였다. 잘못된 판정 0은 이 조건과 보류 비율을 함께 읽어야 한다.</p>
<h3>낯선 표현·인용·정정 변형 · 288개 질문</h3>
{outcomes('stress')}
<p>상세 해석기도 모르는 표현을 추가하면 240개에서 전체 원문으로 복원했다. 여기에서는 상세 해석이 보수적 1차 해석보다 단일 답 판정 수를 늘리지 못했다. 이것이 현재의 병목이다. 새 알고리즘이 문장 이해 능력을 만들어낸 것은 아니다. 미인식 문장 무시는 잘못된 단일 답 126개 외에도, 모호한 후보를 잘못 좁힌 사례가 있어 전체 가능한 답을 누락한 경우는 129개였다.</p>

<h2 id='algorithm'>2. 무엇을 구현했는가</h2>
<p>대화를 두 모임의 계획 값 <code>시간·장소</code>를 바꾸는 순서 있는 기록으로 모델링했다. 질문에서 요구하는 필드만 표시하고, 최신 기록부터 거꾸로 본다. 이때 원래 문장을 삭제하거나 DB를 바꾸지 않고, 현재 질문에 전달할 원문 목록만 만든다.</p>
{table(['기록의 의미', '역방향 요구 정보', '이유'], operator_rows)}
<pre>요구 = 이번 질문이 묻는 필드
최신 기록부터:
    요구가 비었으면 이전 기록의 상세 해석 중단
    문장을 1차 해석
    알 수 없으면 그 문장만 상세 해석
    요구 필드에 영향을 줄 수 있으면 원문을 선택
    그 결과를 계산하는 데 필요한 이전 필드로 요구를 갱신
선택한 기록의 가능한 결과 계산
    한 값이면: 정의된 모형 안에서 단일 답 판정
    복수 후보면: 모호성 유지
    미해석 영향이 남으면: 전체 원문으로 복원</pre>
<p>‘가람의 시간을 노을과 같게’ 한 뒤 노을 시간이 다시 바뀌는 경우도 구분한다. 가람에게 필요한 것은 복사 당시의 노을 값이다. 단순히 같은 주제를 전부 연결하거나 가장 최신 노을 값을 가져오면 이 관계를 잘못 처리할 수 있다. 시간 확정은 시간 의존성만 끝내며, 장소를 물었을 때 필요한 과거 장소 기록까지 없애지 않는다.</p>
<p>처음 보는 문장은 모든 필드에 영향을 줄 수 있다고 처리한다. 상세 해석으로 실제 의미를 좁힐 수 있을 때만 그 범위를 줄인다. 뒤에 명시적인 값 확정이 있으면 해당 필드의 이전 불확실성은 현재 결과에 영향을 주지 않을 수 있다. 반면 미해석 문장이 최신 확정 이후에 있으면 임의로 무시하지 않는다.</p>

<h2 id='proof'>3. 언제 이 선택이 맞는가</h2>
<h3>보수적인 결과 집합과 단일 답 판정</h3>
<p>각 필드의 가능한 값들을 집합으로 표현하고, 알 수 없으면 모든 값이 가능하다는 ⊤를 사용한다. ‘두 모임 중 하나’는 각 필드가 이전 값 또는 새 값일 수 있다고 둔다. 이 곱집합 표현은 필드 사이 상관관계를 잃어 불필요한 후보를 늘릴 수 있지만, 전이 의미가 맞으면 실제 가능한 값을 제외하지 않는다.</p>
<pre class='formula'>각 실제 전이 F_i와 추상 전이 F_i#가 다음을 만족한다고 가정:
F_i(γ(a)) ⊆ γ(F_i#(a))

그러면 합성된 전체 추상 결과에도 실제 결과가 포함된다.
질문 필드의 추상 결과가 {{v}}이면 실제 가능한 값도 v이다.</pre>
<p>증명은 기록 순서에 대한 귀납이다. 단, 문장을 잘못 해석해서 실제 전이가 이 포함 관계 밖에 있으면 보장은 사라진다. 이는 범용 한국어를 정확하게 해석했다는 증명이 아니다. 이 실험에서 ‘확정’은 <strong>대화에 서술된 계획 값</strong>을 뜻하며 실제 캘린더 변경이나 작업 실행 완료를 뜻하지 않는다.</p>
<h3>역방향 요구 정보가 추상 결과를 보존하는 이유</h3>
<p>각 전이에 대해 출력에서 필요한 필드 D를 계산하려면 입력에서 어떤 필드가 필요한지 <code>pre_i(D)</code>로 정의한다. 그 입력 필드가 같으면 요구한 출력도 같아야 한다. 쓰기 대상이 D와 만나지 않는 기록은 현재 단계에서 제외할 수 있다. 값 확정은 이전 값 의존성을 제거하고, 상대 변경은 유지하며, 복사는 다른 필드의 당시 값을 요구한다. 이 성질을 역순으로 이어가면 선택한 기록과 전체 기록의 질문별 추상 결과가 일치한다.</p>
<p>전체 상세 해석과 필요한 곳만 해석한 방식의 판정·예측·선택 ID가 672개 질문에서 일치했다. 별도의 구체 실행기로 길이 4의 연산 흐름 6,561개를 전수 비교한 19,683개 질문에서도 선택 전후 실제 가능한 답 집합이 같았다. 독립 구현으로 확인했지만 작성자는 동일하며, 한정된 연산 공간 검증이다.</p>
<h3>실행량과 생략을 멈출 조건</h3>
<p>새 방식은 전체 선택을 반복 계산하는 대신 한 번의 역방향 순회에서 필요한 미해석 문장을 즉시 해석한다. 각 방문 기록은 1차 해석 한 번, 필요하면 상세 해석 한 번만 받는다. 필드 수를 k, 기록 수를 n이라 하면 필드 집합 처리량은 O(nk)이며, 문자 검사와 해시 비용은 별도다. 무관하다고 확정할 수 없는 최신 기록이 길게 이어지면 상세 해석을 많이 해야 하는 최악의 경우는 남는다.</p>
{table(['배치', '방식', '전체 기록 수', '1차 해석 기록 수', '상세 해석 횟수'], long_rows)}
<p>4,096개 미해석 문장이 마지막 확정보다 앞에 있으면 상세 해석 4,096회를 생략했다. 같은 문장들이 확정 뒤에 있으면 두 방식 모두 4,096회를 수행했다. <strong>원문 로드·스냅샷 해시는 여전히 전체 bytes를 읽는다.</strong> 상세 의미 해석과 최종 문맥을 줄인 결과이지 저장소 전체 읽기를 피한 결과가 아니다. 단 한 번의 로컬 실행 시간은 원본에 남겼지만 실제 LLM 지연이나 안정적인 성능 벤치마크로 사용하지 않았다.</p>

<h2>4. 완결성 확인이 증명하는 것</h2>
<p>누락·순서 변경·내용 변경은 기대한 기록 범위와 SHA-256을 대조해 검출했다. 하지만 해시가 맞는다는 사실은 문장 의미를 올바르게 해석했다는 뜻도, 더 최신 기록이 없다는 뜻도 아니다.</p>
<p>실험에서 이전 스냅샷은 13시, 새 기록이 붙은 스냅샷은 22시를 가리켰고 둘 다 각각의 스냅샷 안에서는 일관됐다. 새 head를 별도로 확인하지 않으면 옛 스냅샷만으로 최신성을 판정할 수 없다. 운영에 적용하려면 권위 있는 저장소에서 확인한 같은 시점의 기록 범위·원문·실행 근거가 맞아야 한다. 이 연구는 운영 저장소의 그 계약을 구현하거나 검증하지 않았다.</p>
<p>또한 확인하지 않은 최신 문장이 임의의 정정을 담을 수 있다면, 그 문장만 다른 두 기록 세계는 읽은 내용이 같아도 답이 다르다. 따라서 아무런 추가 가정 없이 일부만 읽어 ‘변경이 빠짐없다’를 보장할 수는 없다. 확인 범위·영향 범위가 정확하다는 계약, 그 뒤의 확정으로 이전 값이 무관해지는 구조, 또는 불확실성 유지 중 하나가 필요하다.</p>

<h2>5. 해석 비용까지 더하면 이득이 달라진다</h2>
<p>상세 단계는 실제 모델 호출이 아니라 로컬 패턴 함수다. 아래는 상세 단계에 전달한 원문 bytes를 출력 bytes와 더한 <strong>비용 대리 지표</strong>다. 토크나이저·모델 가격·고정 시스템 지침·출력 토큰·질문 사이 캐시는 계산하지 않았다. bytes를 같은 비용 단위로 보았을 때의 한정된 비교다.</p>
{table(['자료', '방식', '상세 해석 총횟수', '출력+상세 원문 bytes 절감', '추가 호출당 고정 bytes 손익분기점'], cost_rows)}
<pre class='formula'>비용 대리값 = 출력 bytes + 상세 해석 원문 bytes + h × 상세 해석 횟수
h* = (전체 원문 출력 bytes − 출력 bytes − 상세 원문 bytes) / 상세 횟수</pre>
<p>낯선 표현 조합에서 전체 상세 해석은 최종 출력만 보면 9.21% 절감이지만, 상세 단계의 원문까지 더하면 37.21% 증가했다. 필요한 곳만 상세 해석하면 같은 계산에서 4.31% 절감이며, 호출당 추가 비용 여유도 68.56 bytes에 불과하다. 실제 모델 호출로 바꾸면 고정 지침과 답변 비용이 이 여유를 쉽게 넘을 수 있으므로, 호출 횟수 감소를 그대로 비용 절감률로 부르면 안 된다.</p>

<h2 id='algebra'>6. 관측된 비최소 사례에서 추가한 정확 최적화</h2>
<p>의존성 추적은 근거를 보존하지만 가장 짧은 선택을 보장하지 않는다. ‘0시 → 1시간 뒤로 → 1시간 앞으로’는 현재 시각만 물을 때 최초 0시만으로도 같은 결과를 낼 수 있다. 두 상대 변경 중 하나만 지우면 답이 달라지므로, 한 문장씩 지워 보는 방법은 이 상쇄를 발견하지 못할 수 있다.</p>
<h3>중간 참조가 없는 정수 변경 구간</h3>
<p>한 필드 x에 대한 상대 변경 d₁,…,dₘ이 있고, 그 사이 x를 다른 곳에서 읽거나 다른 종류로 쓰는 기록이 없다고 하자. 다른 필드의 독립된 기록은 사이에 있어도 된다. 최종 효과는 x ← x+Σdᵢ다. 원문 i의 비용을 cᵢ라 하면 같은 총변경을 만드는 원문 부분집합의 최저 비용을 구할 수 있다.</p>
<pre class='formula'>D₀(0)=0, 나머지는 ∞
Dᵢ(s)=min(Dᵢ₋₁(s), Dᵢ₋₁(s−dᵢ)+cᵢ)

목표: Dₘ(Σdᵢ)
정수 합의 범위 R=Σ|dᵢ|이면 O(mR) 상태 갱신의 의사다항 알고리즘.</pre>
<p>각 단계는 i번째 원문을 제외하거나 포함하는 두 경우로 모든 부분집합을 나누므로, 귀납적으로 그 구간의 최소 비용을 구한다. 실제 구현은 도달 가능한 정수 합만 사전에 저장하고 선택 원문도 복원한다. 선택 경로를 복사해 저장하는 현재 Python 구현에는 경로 길이에 따른 추가 메모리·복사 비용이 있다. 임의로 큰 정수 변경까지 빠르다는 주장은 하지 않는다.</p>
<p>복사나 다른 읽기가 중간 값을 관측하면 반드시 구간을 끊는다. 예를 들어 A를 한 시간 늦춘 뒤 B가 A의 시간을 복사하고, 이후 A를 다시 당기면 B는 중간 값을 기억한다. 이때 두 변경을 함께 없애면 B가 틀리므로 상쇄할 수 없다. 약한 대상 변경이나 미해석 기록도 구간 경계다. 변경 과정·원문 인용 질문에는 이 최적화를 적용하지 않는다.</p>
{table(['검증 항목', '결과'], [
    ['11개 연산으로 만든 길이 4 흐름', f"{V2['operator_programs']:,}개"],
    ['3개 질문의 구체 답 집합 보존', f"{V2['concrete_projection_comparisons']:,}/{V2['concrete_projection_comparisons']:,}"],
    ['실제로 근거가 더 짧아진 질문', f"{V2['strictly_smaller_queries']:,}개"],
    ['연산 조합 전체의 추가 출력 bytes 절감', f"{V2['additional_output_byte_reduction_percent']:.2f}%"],
    ['부호 있는 변경 구간과 모든 부분집합의 최솟값 대조', f"{V2['exact_subset_dp_checks']:,}개 일치"],
    ['0시, +1, −1 사례', '366 → 241 bytes; 단일 답 판정 유지'],
    ['앞선 672개 대화 질문의 추가 절감', '0개'],
])}
<p>2.42%는 이 연산 조합에서의 전체 추가 절감이다. 전반적인 대화 압축률이나 기존 방식보다 늘 안전하게 더 낫다는 뜻이 아니다. 이전 대화 조합에는 상쇄 가능한 음수 변경이 없어서 추가 이득이 없었다. 동결된 기본 엔진에서 AST 캐시를 넘겨받지 못해 이 부가 단계가 상세 해석 80회·원문 4,112 bytes를 다시 처리하기도 했다. 따라서 현재 연구 코드를 모든 질문에 무조건 붙일 이유는 없다. 통합한다면 이미 해석한 결과를 재사용하고 해당 변경 구간에만 적용할 필요가 있다.</p>

<h3>검증 중 발견한 오류와 수정 기록</h3>
<p>첫 상쇄 실험은 답 보존 검사를 모두 통과했지만 절감 사례가 0이었다. 확인해 보니 기본 패턴 <code>(뒤|앞)로</code>가 자연스러운 ‘앞으로’를 인식하지 못했다. 원문 전체로 복원하는 경로가 실행되어, 최적화가 작동하지 않아도 답 보존 검사만 통과했던 것이다. 앞선 비최소 사례는 최초 실행에서 이 복원 경로였으므로, 그 결과만으로 의존성 선택기의 비최소성을 실증했다고 해석하면 안 된다.</p>
<p>첫 버전과 그 결과를 보존하고 <code>revision02</code>에서 ‘뒤로/앞으로’를 명시적으로 구분했다. 이후 단일 답 판정 상태에서 상쇄가 실제로 실행되는지, 모든 알려진 연산이 의도한 의미로 파싱되는지, 최소 한 건 이상의 절감이 발생하는지를 필수 검사로 추가했다. 수정 후 위 수치를 얻었고, 기존 672개 질문 × 4개 방식의 결과 2,688개는 그대로였다. 이 수정도 연구 폴더 안에서만 이루어졌다.</p>

<h2 id='limits'>7. 운영 적용 전에 남은 가장 큰 문제</h2>
<p><strong>해석기의 의미 보장이 가장 큰 미해결 부분이다.</strong> 이 연구는 제한된 문법의 계획 기록을 다룬다. 실제 대화의 요청·실행 결과·과거 인용·추측·철회·조건부 부탁은 같은 문구라도 의미가 달라질 수 있다. 정확한 쓰기 대상과 확정 여부를 인식하지 못하면 ‘앞선 정보를 덮었다’는 판단 자체가 틀릴 수 있다.</p>
<p>모든 미해석 문장을 전체 영향으로 두면 위험한 누락을 줄이지만, 낯선 표현에서는 압축을 거의 포기한다. 이 타협을 개선하려면 문장마다 ‘확실히 바꾸는 필드’와 ‘바꿀 수도 있는 필드’를 구분하는 해석기를 별도로 평가해야 한다. 높은 자신감이나 높은 유사도만으로 확실한 변경으로 승격시키는 것은 위 증명의 전제를 만족시키지 않는다.</p>
<p>실제 적용에서는 호칭·관계 맥락·현재 메시지·미완료 부탁·최신 실행 증거·권한 규칙처럼 보호할 정보를 별도로 고정해야 한다. 현재 연구의 시간·장소 값만으로 그 보호 정책을 구현했다고 볼 수 없다. 실제 모델이 압축된 근거를 올바르게 읽고 답하는지, 원문 복원이 사용자 응답 품질을 유지하는지, 전체 토큰과 지연이 감소하는지도 아직 측정하지 않았다.</p>

<h2>8. 관련 연구와 재현</h2>
<p><a href='https://cs.nyu.edu/~pcousot/COUSOTpapers/POPL77.shtml'>Cousot &amp; Cousot, Abstract Interpretation (1977)</a>의 핵심은 실제 동작을 포함하는 근사 의미를 구성해 성질을 분석하는 것이다. 여기서는 문장 해석이 맞다는 조건 아래 가능한 계획 값의 상한 집합을 유지하는 데 사용했다. 프로그램 분석의 개념을 대화 기록에 적용한 연구 모형이며 새로운 추상 해석 이론을 주장하지 않는다.</p>
<p><a href='https://www.cs.cmu.edu/~emc/papers/Conference%20Papers/Counterexample-guided%20Abstraction%20Refinement.pdf'>Clarke et al., Counterexample-guided Abstraction Refinement (2000)</a>는 거친 모형에서 생긴 불필요한 가능성을 단계적으로 줄이는 접근을 연구한다. 이번 구현은 그 관점과 역방향 의존성 분석에서 착안했지만, 해당 논문의 모델 검사기나 반례 검증 절차를 그대로 구현한 CEGAR 시스템은 아니다. 여기서 상세 해석은 고정된 패턴 함수다.</p>
<p><a href='engine.py'>기본 선택기</a> · <a href='fixtures.py'>가상 기록 생성</a> · <a href='study.py'>비교 실험</a> · <a href='protocol.json'>첫 실험 고정 기록</a> · <a href='results.json'>전체 결과</a> · <a href='audit.py'>별도 구체 실행 검증</a> · <a href='audit.json'>검증 결과</a></p>
<p><a href='reduction_results.json'>수정 전 상쇄 실험</a> · <a href='reduction_diagnosis.json'>실패 원인 기록</a> · <a href='revision02/engine.py'>수정된 해석기</a> · <a href='revision02/reducer.py'>정수 합 최소 비용 선택</a> · <a href='revision02/reduction_protocol.json'>수정 실험 고정 기록</a> · <a href='revision02/reduction_results.json'>수정 후 결과</a> · <a href='revision02/corpus_regression.json'>기존 사례 회귀 결과</a> · <a href='research.ipynb'>연구 노트북</a></p>
<pre># phase05 폴더에서, 기존 동결 입력을 사용
python study.py --run
python audit.py
python revision02/reduction_study.py --run
python make_report.py</pre>
<p>표준 라이브러리만 사용한다. <code>revision02/audit.py</code>는 수정 실험에서 별도 구체 실행 함수를 불러오는 보조 파일이며, 위에 표시한 명령으로 재현한다. 초기 --freeze는 이미 완료했으므로 다시 호출할 필요가 없다. 노트북은 미실행 재현 문서이며 실제 수치는 명령줄 실행 결과다.</p>
<p class='small'>기본 실험 동결 시각 UTC: {esc(P['created_at_utc'])}<br>기본 protocol SHA-256: {esc(R['protocol_sha256'])}<br>이전 Phase 03·04의 동결 파일과 결과를 유지했다. 새 연구 파일과 전체 연구 색인만 추가·수정했다.</p>
"""


def run():
    document = "<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>05 · 필요한 의미만 해석하는 맥락 선택</title><style>" + CSS + "</style></head><body><main>" + BODY + "</main></body></html>\n"
    (HERE / "research.html").write_text(document, encoding="utf-8")
    sections = [
        ("markdown", "# 필요한 의미만 해석하는 맥락 선택\n\n연구용 프로토타입. 운영 변경 없음. 한국어 패턴 함수와 가상 계획 기록이며 실제 LLM 평가가 아니다. 전체 해설은 research.html. 노트북은 미실행 재현 문서다. phase05 폴더에서 실행한다.\n"),
        ("code", "import json\nfrom pathlib import Path\nbase = Path.cwd()\nassert (base / 'protocol.json').exists()\nr = json.loads((base / 'results.json').read_text(encoding='utf-8'))\nr['summary']\n"),
        ("markdown", "## 역방향 의존성\n\n현재 질문 필드에서 시작한다. 상수 대입은 해당 필드의 이전 값 의존성을 끝내고, 상대 변경은 유지하며, 복사는 그 시점의 다른 필드로 요구를 옮긴다. 미해석 문장은 전체 영향으로 간주해 상세 해석하며, 해결하지 못하면 전체 원문으로 복원한다.\n\n전체 상세 해석과 동일한 결과를 672개 질문에서 얻었다. 상세 단계 호출은 기본 3,140→224, 낯선 표현 조합 2,562→240이었다. 로컬 함수 호출 수이며 LLM 호출 측정이 아니다.\n"),
        ("markdown", r"""## 조건부 정확성

각 문장 전이에 대해 $F_i(\gamma(a))\subseteq\gamma(F_i^\#(a))$가 성립하면, 추상 결과에는 실제 결과가 포함된다. 질문 필드의 결과가 한 값이면 정의된 의미론 안에서는 그 값으로 확정할 수 있다.

이 전제는 자연어 해석의 정확성을 보장해 주지 않는다. 실제 실행 완료가 아니라 계획 값을 다룬다. 스냅샷 해시도 기록의 byte 동일성만 확인하며 최신 head나 의미를 보장하지 않는다.
"""),
        ("code", "r['fault_checks'], [x for x in r['scaling'] if x['length']==4096]\n"),
        ("markdown", r"""## 상대 변경 구간의 최소 비용

중간 읽기·다른 쓰기가 없는 같은 필드의 정수 이동에서, 원문 부분집합의 합이 원래 합과 같으면 최종 값이 보존된다.

$$D_i(s)=\min(D_{i-1}(s),D_{i-1}(s-d_i)+c_i)$$

목표는 $D_m(\sum_i d_i)$. 구간 내부의 정확한 최적해이며 전체 문맥 최소 비용은 아니다. 중간 값을 다른 필드가 읽으면 그 지점에서 반드시 구간을 끊는다.
"""),
        ("code", "v2 = json.loads((base / 'revision02/reduction_results.json').read_text(encoding='utf-8'))\n{k:v for k,v in v2.items() if k!='examples'}\n"),
        ("markdown", "## 부정 결과도 보존\n\n낯선 표현 조합은 288개 질문 중 36개에서만 단일 답 판정, 240개 전체 원문 복원, 12개 미지원 질문이었다. 상세 해석 원문 bytes까지 더한 절감은 필요한 곳만 해석해도 4.31%였다.\n\n첫 상쇄 실험은 '앞으로'를 인식하지 못해 전체 원문 복원으로 빠졌으며 실제 절감 0이었다. 수정 전 결과와 원인을 보존했다. 수정 버전에서 단일 답 판정 상태의 실제 상쇄와 11개 연산 의미를 추가 확인했다. 43,923개 질문 비교에서 답을 보존했고 2,936개가 짧아졌지만, 추가 절감은 그 연산 조합에서 2.42%였다. 기존 672개 대화 질문에는 이득이 없고 중복 상세 해석 비용이 있었다.\n"),
        ("code", "# 공개된 재현 명령; 네트워크·운영 데이터·LLM 호출 없음\nimport subprocess, sys\nsubprocess.run([sys.executable, str(base/'study.py'), '--run'], cwd=base, check=True)\nsubprocess.run([sys.executable, str(base/'audit.py')], cwd=base, check=True)\nsubprocess.run([sys.executable, str(base/'revision02/reduction_study.py'), '--run'], cwd=base, check=True)\n"),
        ("markdown", "## 관련 문헌\n\n- [Cousot & Cousot 1977](https://cs.nyu.edu/~pcousot/COUSOTpapers/POPL77.shtml): 보수적인 추상 의미.\n- [Clarke et al. 2000](https://www.cs.cmu.edu/~emc/papers/Conference%20Papers/Counterexample-guided%20Abstraction%20Refinement.pdf): 추상화의 단계적 정밀화.\n\n문헌의 이론을 참고한 제한된 연구 모형이다. 실제 자연어 이해, 실제 모델 답변, 전체 토큰·지연, 보호 메모리 정책은 검증하지 않았다.\n"),
    ]
    cells = []
    for i, (kind, source) in enumerate(sections):
        cell = {"cell_type": kind, "id": f"phase05-{i:02d}", "metadata": {}, "source": source.splitlines(keepends=True)}
        if kind == "code":
            cell.update(execution_count=None, outputs=[])
        cells.append(cell)
    notebook = {"nbformat": 4, "nbformat_minor": 5, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python", "version": "3.12"}}, "cells": cells}
    (HERE / "research.ipynb").write_text(json.dumps(notebook, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    index = HERE.parent / "index.html"
    content = index.read_text(encoding="utf-8")
    if "phase05/research.html" not in content:
        marker = "<p><a href='phase04/research.html'>"
        assert marker in content
        content = content.replace(marker, "<p><a href='phase05/research.html'>05 · 필요한 의미만 해석하는 맥락 선택</a><br>역방향 의존성, 미해석 문장의 보수적 처리, 정수 변경 구간의 최소 비용, 부정 결과와 수정 검증.</p>" + marker, 1)
        index.write_text(content, encoding="utf-8")
    print(json.dumps({"html": str(HERE/'research.html'), "notebook_cells": len(cells)}, ensure_ascii=False))


if __name__ == "__main__":
    run()
