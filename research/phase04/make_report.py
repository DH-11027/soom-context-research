"""Render the saved finite-model study as an HTML note and unexecuted notebook."""

import hashlib
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
AUDIT = json.loads((HERE / "audit.json").read_text(encoding="utf-8"))
PROTOCOL = json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))
LABELS = {"current": "현재 시각", "trajectory": "변경 과정", "verbatim": "최초 요청 원문"}


def esc(value):
    return html.escape(str(value))


def table(headers, rows):
    return "<div class='scroll'><table><thead><tr>" + "".join(f"<th>{esc(x)}</th>" for x in headers) + "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{esc(x)}</td>" for x in row) + "</tr>" for row in rows) + "</tbody></table></div>"


summary_rows = []
budget_rows = []
for q, label in LABELS.items():
    s = R["summary"][q]
    a = s["methods"]["adaptive"]
    fixed = next(r["fixed_exchange_query_bytes"] for r in R["rows"] if r["query"] == q)
    summary_rows.append([label, f"{s['methods']['joint']['mean_bytes']:.2f}", f"{s['methods']['no_index']['mean_bytes']:.2f}", f"{a['mean_bytes']:.2f}", f"{s['extra_reduction_vs_joint_percent']:.1f}%", f"{s['strictly_smaller_than_joint']}/200"])
    budget_rows.append([label, f"{a['min_bytes']}–{a['max_bytes']}", fixed, f"{a['min_bytes'] + fixed}–{a['max_bytes'] + fixed}", f"{s['min_budget_fails_worlds']}/200"])

summary_table = table(["질문", "세 질문 공통 최솟값", "질문별·인덱스 없음", "질문별·인덱스 선택", "공통 최솟값 대비 추가 절감", "더 작아진 세계"], summary_rows)
budget_table = table(["질문", "가변 근거 예산", "고정 직전 대화+질문", "둘을 합한 예산", "가장 작은 예산을 일률 적용하면 부족"], budget_rows)
matrix_table = table(["선택 기준 → 실제 질문", *LABELS.values()], [[LABELS[q], *[f"{n}/200" for n in row.values()]] for q, row in R["diagnostics"]["intent_mismatch_insufficient_worlds"].items()])
class_table = table(["답의 구분 기준", "서로 다른 답의 수", "고정 길이 답 코드의 하한(bit)"], [[LABELS.get(q, "세 답을 함께 구분"), n, R["fixed_length_answer_encoding_lower_bound_bits"][q]] for q, n in R["answer_class_counts"].items()])

example_sections = []
for i, example in enumerate(R["examples"]):
    title = ("10시 → 12시 → 14시", "10시 → 잡담 → 한 시간 뒤로", "10시 → 한 시간 뒤로 → 한 시간 뒤로", "10시 → 12시 → 18시라는 표현 예시")[i]
    original = "\n".join(f"[{r['seq']}] {r['text']}" for r in example["world"]["records"])
    plans = "".join(f"<h4>{esc(LABELS[q])} · {p['bytes']} bytes</h4><pre>{esc(p['rendered'])}</pre>" for q, p in example["plans"].items())
    example_sections.append(f"<details {'open' if i == 0 else ''}><summary>{esc(title)}</summary><p class='small'>고정된 기록 범위 0..4 안의 가상 사례. 모든 인덱스는 모델의 정확한 사건 정보로 만든다.</p><details><summary>전체 원문 5개</summary><pre>{esc(original)}</pre></details>{plans}</details>")

CSS = """
:root{font-family:'Malgun Gothic',system-ui,sans-serif;color:#203b43;background:#f3f6f3;color-scheme:light}body{margin:0;line-height:1.85}main{max-width:1080px;margin:32px auto;padding:38px 44px;background:#fff;border:1px solid #dbe5df;border-radius:14px}h1{font-size:30px;line-height:1.4;letter-spacing:-.03em}h2{font-size:22px;margin-top:42px;line-height:1.5}h3{font-size:18px;margin-top:25px}h4{margin-bottom:8px}p{margin:15px 0}a{color:#0c697b;text-underline-offset:3px}nav{display:flex;gap:10px 18px;flex-wrap:wrap;font-size:14px}.meta,.small{color:#64777b}.small{font-size:13px;overflow-wrap:anywhere}.callout{padding:18px 22px;background:#eaf3ef;border-left:4px solid #4b8873;border-radius:5px}.limit{padding:16px 20px;background:#fff6e7;border-left:4px solid #bc934f;border-radius:5px}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px;line-height:1.65}th,td{padding:10px;border-bottom:1px solid #d9e5e2;text-align:left;min-width:95px}th{background:#edf4f2}pre{padding:18px;background:#f1f5f7;overflow-x:auto;white-space:pre-wrap;font-size:13px;border-left:3px solid #5b8490;line-height:1.8}.formula{font-family:Consolas,monospace;font-size:14px}details{margin:16px 0;padding:12px 16px;border:1px solid #dbe6e1;border-radius:8px}summary{cursor:pointer;font-weight:600}li{margin:8px 0}code{font-family:Consolas,monospace;font-size:.92em}@media(max-width:700px){main{padding:24px 17px;margin:0;border:0;border-radius:0}h1{font-size:25px}}@media print{main{margin:0;padding:0;border:0}nav{display:none}details{break-inside:avoid}a{color:inherit}}
"""

BODY = f"""
<p class='meta'>SOOM 맥락 압축 연구 · 04 · 2026-10-22 · 운영 변경 없음</p>
<h1>답이 달라지는 가능성을 모두 배제할 때까지</h1>
<p>질문별 최소 근거와 적응형 예산을, 작은 유한 세계에서 정확히 계산한다.</p>
<nav><a href='../index.html'>전체 연구</a><a href='#result'>결과</a><a href='#math'>수학적 조건</a><a href='#examples'>같은 기록·다른 질문</a><a href='#limits'>한계</a><a href='research.ipynb'>노트북</a><a href='results.json'>수치 원본</a></nav>

<div class='callout'><strong>이번에 얻은 결론</strong><p>생략해도 되는 정보는 질문에 따라 달라진다. 주어진 근거와 양립하는 대화들이 모두 같은 답을 주면, 그 근거는 해당 질문에 충분하다. 이 조건을 사용하면 예산을 미리 정하는 대신, 답을 바꿀 가능성을 제거하는 데 필요한 최소 분량을 계산할 수 있다.</p></div>
<div class='limit'><strong>적용 범위</strong><p>200개 가상 세계를 빠짐없이 열거한 수학 모형 실험이다. 최적화기는 모든 가능한 세계와 정확한 사건 의미를 아는 <strong>정답 정보를 사용하는 최적화기(oracle)</strong>다. 실제 한국어 이해, 자동 인덱스 생성, LLM 답변 품질은 평가하지 않았다. 코드·평가 규칙·세계 목록을 계산 전에 고정했으나, 같은 작성자가 만든 실험이며 외부 사전등록이나 독립 평가가 아니다.</p></div>

<h2>1. 지난 실험의 평가 문제를 이렇게 바꿨다</h2>
<p>Phase 03에서는 현재 상태에 답할 수 있는 문장이 있어도 최초 부탁이 빠지면 실패로 세는 문제가 있었다. 이후 별도 라벨 감사를 남겼다. 이번에는 필요한 원문 ID를 사람이 지정하지 않고, 대화의 상태 전이에서 답을 계산한다. 남긴 문장과 모순되지 않는 다른 세계가 다른 답을 내는지 전부 확인한다. 이 역시 정의한 모형의 의미론에 의존하지만, 결과를 본 뒤 근거 목록을 완화하는 과정은 없다.</p>
<p>가상 세계에는 모임의 최초 시각, 절대 시각 변경, 상대 변경(+1시간), 실제 변경이 아닌 인용문, 무관한 대화가 있다. 최초 시각 2개 × 최초 표현 2개 × 첫 변경 5개 × 둘째 변경 5개 × 무관한 대화 2개 = 200개다. 각 세계에 <strong>현재 시각·변경 과정·최초 요청 원문</strong>을 모두 질문해 600개 질문 사례를 만들었다. 독립 표본 600개라는 뜻은 아니며 신뢰구간이나 일반화 성공률을 계산하지 않는다.</p>

<h2 id='result'>2. 같은 기록에 필요한 분량이 달랐다</h2>
<p>아래 단위는 UTF-8 bytes다. 원문 표시, 줄바꿈, 선택한 인덱스 문구를 포함한다. 토큰 수·전체 시스템 프롬프트·도구 설명·인덱스 생성 비용·검색 지연은 측정하지 않았다. 각 열은 해당 조건에서 전수 탐색한 최소 비용의 세계별 평균이다.</p>
{summary_table}
<p>세 질문에 모두 답할 수 있는 최적의 공통 근거를 기준으로도, 현재 시각에는 <strong>37.2%</strong>, 최초 요청 원문에는 <strong>63.5%</strong>의 추가 생략 여지가 있었다. 변경 과정에는 추가 이득이 0이었다. 이 모형에서 변경 과정을 밝히는 원문을 모으면 다른 두 질문에도 답할 수 있기 때문이다. 이 숫자는 자연어 대화나 실제 프롬프트의 예상 절감률이 아니다.</p>
<p>전체 원문 평균은 738.70 bytes다. 무관한 원문 길이는 임의로 설계했기 때문에 전체 대비 절감률을 주된 결과로 삼지 않았다. 공통 최적해와 질문별 최적해의 비교도 이 세계·문구·직렬화 방식에 한정된다.</p>

<h3>예산도 필요한 근거에 따라 달라진다</h3>
{budget_table}
<p>현재 시각만 물어도 가변 근거는 96–318 bytes였다. 절대 시각을 명시한 최종 변경은 짧게 끝나지만, “직전 시간보다 한 시간 뒤”에는 이전 값이 필요하다. 가장 짧은 사례의 예산을 모두에게 적용하면 현재 시각 120/200개 세계에서 충분한 근거를 담을 수 없다. 반대로 항상 최대 예산만 채워야 할 이유도 없다. 위 합계에도 시스템 규칙이나 도구 설명은 포함되지 않는다.</p>

<h2 id='math'>3. 충분함의 기준과 최적화</h2>
<p>Ω는 허용한 가능한 대화 세계, h는 실제 세계, q는 현재 질문, f<sub>q</sub>(h)는 그 세계의 답이다. S는 남긴 원문, M은 선택적으로 제공한 정확한 인덱스다. 현재 질문과 보호할 직전 대화는 모든 후보에서 고정한다.</p>
<pre class='formula'>Ω(S,M) = {{h′ ∈ Ω : h′는 S의 문장·기록 위치 및 M과 모순되지 않음}}

충분함 ⇔ Ω(S,M) ≠ ∅ 이고 {{f_q(h′) : h′ ∈ Ω(S,M)}} = {{f_q(h)}}

B*(h,q) = min [ C(M) + Σ(i∈S) c_i ]
          subject to 위 충분함 조건</pre>
<p>즉, 남긴 근거가 모두 맞는데도 답이 달라질 세계가 하나라도 있으면 충분하다고 부르지 않는다. 어떤 기록을 선택했다는 사실 자체에서 숨은 답을 추론하는 통로는 허용하지 않는다. 선택기의 행동을 암호처럼 읽는 대신, 실제 표시된 문장과 인덱스만 근거로 인정한다.</p>

<h3>고정된 가능한 세계에서는 가중 집합 덮개 문제가 된다</h3>
<p>하나의 인덱스 방식 M을 고정하자. M과 양립하지만 실제 답과 다른 세계들의 집합을 W라 하고, 기록 i가 내용 불일치로 배제하는 세계들의 집합을 D<sub>i</sub>라 하자.</p>
<pre class='formula'>W = {{h′ : h′는 M과 양립하고 f_q(h′) ≠ f_q(h)}}
D_i = {{h′ ∈ W : h′의 기록 i가 실제 기록 i와 다름}}

충분함 ⇔ ∪(i∈S) D_i = W
G(S) = |∪(i∈S) D_i|</pre>
<p>G는 단조 부분모듈러다. A⊆B이면 기록 i의 추가 이득은 아직 배제하지 않은 D<sub>i</sub>의 원소 수이고, B에서 그 수가 더 커질 수 없다. 각 인덱스 선택지에 대해 비용을 더한 가중 집합 덮개를 풀고 최솟값을 택한다. 이번에는 원문 5개이므로 2⁵ × 인덱스 3종 = 96개 후보를 정확히 탐색했다.</p>
<p><strong>Phase 01의 XOR 반례와 충돌하지 않는다.</strong> 여기서 부분모듈러인 것은 명시한 대안 세계를 배제하는 집합의 크기다. 실제 LLM 답변 효용이나 상호정보량이 항상 부분모듈러라는 주장이 아니다. 실세계에서는 가능한 대화 세계와 정확한 의미를 구성하는 문제가 여전히 남는다.</p>

<h3>적응형 예산을 뒷받침하는 두 가지 순서 관계</h3>
<pre class='formula'>같은 후보·비용에서 가능한 세계가 늘면:
Ω₁ ⊆ Ω₂  ⇒  B*(Ω₁,q) ≤ B*(Ω₂,q)

같은 후보·비용에서 보장해야 할 질문이 늘면:
Q₁ ⊆ Q₂  ⇒  B*(Q₁) ≤ B*(Q₂)</pre>
<p>증명은 제약식의 포함 관계다. 배제해야 할 답의 대안이나 동시에 보존해야 할 질문이 늘면 가능한 선택 집합이 줄어든다. 단, 후보 근거·비용·정답 함수가 같은 조건이다. 새로 더 효율적인 근거가 추가되는 상황까지 이 부등식으로 설명할 수는 없다.</p>
<p>따라서 적응형 예산의 기준은 단순히 대화가 길거나 애매한 정도가 아니라, <strong>이번 답을 바꾸는 아직 배제되지 않은 가능성</strong>이어야 한다. 실제 모형에서도 답과 독립적인 다른 프로젝트 문구를 바꿔도 최적 근거가 바뀌지 않았다.</p>
<p><strong>예산을 늘려도 해결되지 않는 경우도 있다.</strong> 두 세계가 제공 가능한 모든 원문·인덱스에서 똑같이 보이는데 요구한 단일 답이 다르면, 어떤 부분집합도 둘을 구분할 수 없다. 이때 단일 답을 확정하는 문제의 실행 가능한 해가 없으므로 B*=∞로 정의한다. 추가 원문이 아니라 새 정보나 의도 확인이 필요하다. 후보 집합과 불확실성을 정확히 설명하는 응답을 허용하면 답의 목표 자체가 달라진다. 이 명제는 별도의 논리적 반례이며, 위 200개 세계의 실측 건수에 섞지 않았다.</p>

<h3>얼마나 다른 답을 구분해야 하는가</h3>
{class_table}
<p>같은 보호 맥락에서 N개 답을 오류 없이 구분하는 고정 길이 이진 코드는 적어도 ⌈log₂N⌉ bits가 필요하다. N개 답에 서로 다른 코드를 주어야 한다는 단순한 개수 논증이다. 위 수치는 답 자체의 정보 하한이며, 인용 가능한 원문을 담는 비용이나 토큰 예산이 아니다. 이번 질문을 이미 알면 미래의 다른 질문까지 모두 구분하는 코드를 만들 필요가 줄어든다는 설명에 사용한다. 원문 보관과 이후 재검색은 별도로 유지해야 한다.</p>

<h2 id='examples'>4. 원문은 같은데 필요한 근거는 달라진다</h2>
{''.join(example_sections)}
<p class='small'>첫 사례에서 기록 3만으로 현재 시각을 알 수 있는 이유에는, 이 유한 모형에서 기록 4는 언제나 무관하고 범위가 4에서 끝난다는 가정도 들어 있다. 실제 서비스가 이런 완결성을 확인하지 못했다면 같은 생략을 정당화할 수 없다.</p>

<h2>5. 무엇을 알면 생략할 수 있고, 무엇이 빠지면 위험한가</h2>
<h3>최신 문장도 이전 값을 필요로 한다</h3>
<p>정답 사건 정보를 이용해 가장 최근 실제 변경 문장 하나를 고르더라도, 별도 인덱스가 없으면 현재 시각 근거가 부족한 세계는 120/200개였다. 정확한 마지막 변경 위치를 함께 주면 56/200개로 줄었다. 남은 사례들은 상대 변경의 기준 값이 필요한 경우다. 이 진단조차 최신 사건을 완벽하게 찾았다는 가정으로 계산했으며 실제 검색기의 실패율이 아니다.</p>
<h3>‘이후 변경 없음’이라는 확인도 정보를 전달한다</h3>
<p>인덱스는 이 모형에서 정확한 사건 목록으로 만든다. 주제, 확인 범위, 마지막 변경 위치 또는 전체 변경 위치 목록을 명시하고, 그 문구의 bytes도 계산한다. 현재 시각 96/200개, 변경 과정 128/200개 세계에서 인덱스가 최소 비용을 낮췄다. 최초 원문에는 이득이 없었다. 비용이 더 크면 인덱스를 선택하지 않는다. 이번 문구에서는 최적해에 전체 변경 목록 또는 인덱스 없음만 선택되었고, 마지막 위치만 담은 방식은 최적 비용 이점이 없었다.</p>
<p>실제 기록이 10시 → 12시 → 14시인데 인덱스가 마지막 변경을 12시로 잘못 표시하면, 12시 기록과 그 인덱스에 맞는 모든 모형 세계의 답은 12시가 된다. 실제 세계가 거짓 인덱스 때문에 후보에서 빠진 것이다. <strong>모형 안에서 답이 하나뿐이라는 사실도, 모형이 틀렸으면 정답을 보장하지 않는다.</strong> Phase 03에서 확인한 변경 탐지 누락이 이 인덱스에 이어지면 같은 문제가 생길 수 있다.</p>
<p>또한 기록 4까지 정확히 확인했더라도, 기록 5에서 16시로 다시 바뀌면 이전 확인서가 증명하는 것은 기록 4 시점의 상태뿐이다. ‘현재’ 질문에 답하려면 원문 조회와 확인 범위가 같은 최신 스냅샷을 가리키는지도 확인해야 한다.</p>
<h3>질문 해석을 틀리면 충분한 근거가 달라진다</h3>
<p>각 질문에 최적인 근거를 다른 질문에 재사용했을 때, 충분하지 않은 세계 수다. 대각선 0은 정답 의미를 아는 최적화의 결과이며, 실제 질문 분류 정확도 측정이 아니다.</p>
{matrix_table}
<p>현재 시각용 최소 근거를 변경 과정 질문에 사용하면 128/200개 세계에서 정보가 부족했다. 질문이 두 뜻으로 해석될 수 있다면, 두 뜻을 함께 보존하는 제약을 사용하거나 의도를 확인해야 한다. 가장 짧게 압축되는 뜻을 임의로 고르는 방법은 정당화되지 않는다.</p>

<h2 id='limits'>6. 이번에 확인한 것과 아직 확인하지 않은 것</h2>
<p>주어진 유한 세계에서는 모든 최적해의 충분함과 최소 비용을 검증했다. 원래의 비트셋 계산 외에 별도 리스트·집합 구현으로 1,800개 최적해 비교가 모두 일치했다. 집합 덮개와 직접 비교의 동치, 모든 부분집합의 단조성·한계 이득 감소, 원문 ID 변경과 무관한 주제 변경에 대한 불변성도 확인했다. 두 검증 구현은 같은 작성자와 같은 세계 모형을 사용한다.</p>
<p>현실의 임의 대화에는 가능한 세계의 전수 목록이 없다. 질문 해석, 요청과 보고의 구분, 상대 참조, 뒤늦은 정정, 인용과 실제 요청 구분을 자동으로 얼마나 정확히 처리하는지 이번 실험은 알려주지 않는다. 불확실성을 모두 표현하는 모형을 만드는 비용도 측정하지 않았다. 충분한 근거를 제공한 뒤 실제 LLM이 그 근거대로 답하는지도 별개다.</p>
<p>다음 연구를 진행한다면 수치상 절감률을 더 높이는 것보다, <strong>“관련 변경을 모두 찾았다”는 판단이 틀리는 조건</strong>을 먼저 평가할 이유가 생겼다. 이를 위해 정정·상대 참조·인용의 의미를 바꾼 대조 사례와 고정된 판정 규칙을 사용할 수 있다. 이번 결과만으로 운영 선택기나 예산 정책을 바꿀 근거는 부족하다. 운영 코드, 기존 DB, 데몬, 설정은 이 연구에서 변경하지 않았다.</p>

<h2>7. 관련 연구와 재현</h2>
<p><a href='https://arxiv.org/abs/2411.06037'>Joren et al., Sufficient Context (ICLR 2025)</a>는 질문에 관련된 자료가 있다는 것과 충분한 정보가 있다는 것을 구분하고, 근거의 충분함에 따라 모델 오류를 분석한다. 여기의 유한 세계 전수 비교는 해당 논문의 자동 평가기를 구현한 것이 아니며, 그 실험 성과를 가져오지 않았다.</p>
<p><a href='https://aclanthology.org/2024.emnlp-main.1194/'>Yoon et al., CompAct (EMNLP 2024)</a>는 다단계 질의응답에서 필요한 정보를 적극적으로 압축하는 접근을 연구한다. 질문 중심 압축이라는 관련성을 참고했다. 이 보고서의 직접적인 기여 범위는 SOOM 문제를 작은 정확한 의미론에 옮겨 조건과 반례를 계산한 것이다. 집합 덮개·부분모듈러성·정보 하한 자체의 새 이론을 주장하지 않는다.</p>
<p><a href='model.py'>세계·비용 모형</a> · <a href='study.py'>정확 탐색</a> · <a href='protocol.json'>계산 전 고정 기록</a> · <a href='worlds.json'>200개 세계</a> · <a href='audit.py'>별도 검증</a> · <a href='audit.json'>검증 결과</a> · <a href='results.json'>전체 결과</a> · <a href='research.ipynb'>노트북</a></p>
<pre>python study.py --run
python audit.py
python make_report.py</pre>
<p>이미 고정한 protocol.json을 재사용한다. --freeze는 초기 생성용이며 기존 고정 기록을 덮어쓰지 않는다. Python 표준 라이브러리만 사용한다. 노트북은 설명과 재현 셀을 포함한 미실행 문서이며, 이 보고서의 수치는 명령줄에서 실제 실행한 결과다.</p>
<p class='small'>고정 시각(UTC): {esc(PROTOCOL['created_at_utc'])}<br>protocol SHA-256: {esc(R['protocol_sha256'])}<br>results SHA-256: {esc(AUDIT['results_sha256'])}</p>
"""


def cell(kind, source, index):
    item = {"cell_type": kind, "id": f"phase04-{index:02d}", "metadata": {}, "source": source.splitlines(keepends=True)}
    if kind == "code":
        item.update(execution_count=None, outputs=[])
    return item


def run():
    document = "<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>04 · 질문별 충분한 근거와 적응형 예산</title><style>" + CSS + "</style></head><body><main>" + BODY + "</main></body></html>\n"
    (HERE / "research.html").write_text(document, encoding="utf-8")
    cells = [
        ("markdown", "# 질문별 충분한 근거와 적응형 예산\n\n200개 유한 세계를 전수 비교하는 연구용 모형. 운영 변경 없음. 실제 LLM 평가가 아니며, 모든 의미와 대안 세계를 아는 oracle 최적화다. `research.html`에 전체 해설과 실패 조건을 기록했다. 이 노트북은 미실행 재현 문서다. 같은 폴더에서 열어 실행한다.\n"),
        ("markdown", r"""## 충분함

$\Omega(S,M)$은 남긴 원문과 정확한 인덱스에 양립하는 세계다.

$$\{f_q(h'):h'\in\Omega(S,M)\}=\{f_q(h)\}$$

일 때에만 충분하다고 정의한다. 선택한 문장들에서 답이 달라질 가능성이 없어야 한다.

$$B^*(h,q)=\min_{S,M}\left[C(M)+\sum_{i\in S}c_i\right]$$

위 충분함을 제약식으로 둔다. 비용은 UTF-8 bytes이며 토큰 수나 전체 프롬프트 비용이 아니다.
"""),
        ("code", "import json\nfrom pathlib import Path\nbase = Path.cwd()\nassert (base / 'protocol.json').exists(), 'phase04 폴더에서 실행하세요.'\nresult = json.loads((base / 'results.json').read_text(encoding='utf-8'))\nresult['summary']\n"),
        ("markdown", "## 관측 결과\n\n같은 세계의 세 질문에 모두 대비한 최소 근거와 비교하면, 현재 시각은 37.2%, 최초 원문은 63.5%의 추가 생략 여지가 있었다. 변경 과정에는 추가 이득이 없었다. 문구 길이·정의한 세계·완벽한 의미 해석에 의존하는 수치이며 실서비스 절감률이 아니다.\n\n현재 시각의 최소 가변 근거는 96–318 bytes. 고정 직전 대화와 질문 204 bytes를 더하면 300–522 bytes다. 시스템 규칙과 도구 설명 등은 포함되지 않는다.\n"),
        ("markdown", r"""## 집합 덮개로의 변환

인덱스 방식을 고정한 뒤, 실제 답과 다른 가능한 세계들을 $W$라 하자. 원문 $i$가 내용 불일치로 제거하는 세계들을 $D_i$라 하면 충분함은

$$\bigcup_{i\in S}D_i=W$$

와 같다. $G(S)=|\bigcup_{i\in S}D_i|$는 단조 부분모듈러다. 이 주장은 집합 제거 함수에 한정되며 LLM 효용이나 정보 이득의 일반 부분모듈러성을 뜻하지 않는다.

같은 후보와 비용 아래 가능한 세계 또는 동시에 보장할 질문이 늘면 제약이 강해져 $B^*$는 감소하지 않는다. 무관한 불확실성은 답을 바꾸지 않으면 추가 근거를 요구하지 않을 수 있다.

제공 가능한 모든 관측이 같은 두 세계에서 요구한 단일 답이 다르면, 어떤 선택도 구분할 수 없어 $B^*=\infty$다. 추가 정보·의도 확인 또는 불확실성을 포함한 응답 목표가 필요하다. 이 명제는 200개 세계 실험과 별도의 논리적 반례다.
"""),
        ("code", "result['diagnostics']\n"),
        ("markdown", "## 실패 조건\n\n최근 실제 변경 문장 + 정확한 마지막 위치만으로도 상대 변경 때문에 56/200개 세계에서 현재 답의 근거가 부족했다. 틀린 인덱스는 실제 세계를 후보에서 배제해 틀린 답을 유일한 답으로 만들 수 있다. 기록 4 시점의 확인으로 이후 기록 5의 변경까지 증명하지 못한다. 현재 시각용 최소 근거를 변경 과정에 쓰면 128/200개 세계에서 부족하다. 이 수치는 실제 모델 실패율이 아니다.\n"),
        ("code", "# 기존 고정 입력으로 재현. 네트워크/운영 데이터 접근 없음.\nimport subprocess, sys\nsubprocess.run([sys.executable, str(base / 'study.py'), '--run'], cwd=base, check=True)\nsubprocess.run([sys.executable, str(base / 'audit.py')], cwd=base, check=True)\n"),
        ("markdown", "## 관련 문헌과 한계\n\n- [Sufficient Context, ICLR 2025](https://arxiv.org/abs/2411.06037): 근거 충분함과 답변 정확도 구분.\n- [CompAct, EMNLP 2024](https://aclanthology.org/2024.emnlp-main.1194/): 질문에 필요한 정보를 적극적으로 압축.\n\n본 연구는 두 논문의 자동 평가기/압축기를 재현하지 않는다. 고정한 200개 세계는 독립 자연어 표본이 아니다. 정확한 사건 인덱스는 상징적 정답으로 생성했으며 그 생성 비용·언어 이해 품질·모델 출력 품질·운영 토큰/지연을 측정하지 않았다.\n"),
    ]
    notebook = {"nbformat": 4, "nbformat_minor": 5, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python", "version": "3.12"}}, "cells": [cell(kind, source, i) for i, (kind, source) in enumerate(cells)]}
    (HERE / "research.ipynb").write_text(json.dumps(notebook, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    index = HERE.parent / "index.html"
    content = index.read_text(encoding="utf-8")
    if "phase04/research.html" not in content:
        marker = "<p><a href='phase03/research.html'>"
        assert marker in content
        content = content.replace(marker, "<p><a href='phase04/research.html'>04 · 질문에 충분한 근거와 적응형 예산</a><br>가능한 답을 바꾸는 세계를 배제하는 조건, 정확한 최소 비용, 인덱스의 완결성과 한계.</p>" + marker, 1)
        index.write_text(content, encoding="utf-8")
    print(json.dumps({"html": str(HERE / "research.html"), "notebook_cells": len(cells), "results_sha256": hashlib.sha256((HERE / "results.json").read_bytes()).hexdigest()}, ensure_ascii=False))


if __name__ == "__main__":
    run()
