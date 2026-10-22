# Phase08 동결 전 수학 검토

작성자: 주 구현자와 역할을 분리한 동일 모델의 수학 검토 에이전트.
이 문서는 외부 독립 검증이 아니다. 최초 작성 시각은
2026-10-22 20:05 KST / 11:05 UTC다. 새 Phase08 평가 자료·builder·라벨·결과를
읽지 않고 작성했다. 구현 후보 확정 후의 검토는 아래에 별도로 추가한다.

## 1. 검토 범위

직접 기준은 `6da051c0132811184ecf39975d7ff647a1f47842`다.
`research/phase07/HANDOFF_BACK.md`, `PROTOCOL.md`, `THEORY.md`,
`POSTFREEZE_REVIEW.md`, `BOUNDARY_ANALYSIS.md`를 이 순서로 읽었다.
그 뒤 Phase07 `cached.py`, `baseline.py`, Phase06 `scoped.py` 전체와
Phase05r2 `engine.py`의 파서·질문·snapshot·추상 전이 부분을 읽었다.
이번 검토자는 Phase07 주평가·사후 진단을 직접 재실행하지 않았으며,
그 일은 별도 감사 역할의 보고와 구분한다. 원시 결과를 이 문서에서 다시
집계했다는 주장도 하지 않는다. 기존 Phase01–07 파일은 수정하지 않았다.

검토한 코드에서 순수 단계는 원문, ordered entities, 고정된 규칙만 읽는다.
현재 `scope_from_text`는 full-string whitelist이며, 의미 선택기는 각 방문의
현재 demand로 상세 해석 요청 여부를 결정한다. 이 범위에서는 Phase07의
조건부 동등성 증명과 코드 구조 사이에 모순을 찾지 못했다. 이 진술은
자연어 의미의 정확성, 임의 입력에서의 정상 종료, 숨은 환경 변조의 부재를
독립적으로 증명했다는 뜻이 아니다.

## 2. 모든 유한 stream에서 fresh보다 손해 보지 않는 학습형 보장은 불가능

다음 단순 비용 모형을 먼저 고정한다.

- 기준은 매 요청을 fresh로 처리한다.
- 정책은 동일한 공통 의미 작업을 수행한다.
- 최초 재사용 준비에는 양의 추가비 `a > 0`가 든다.
- 이 추가비 이전에는 기준 대비 이미 실현한 절약이나 외부 선불 credit이 없다.
- 재사용으로 얻는 절약은 이후 요청에서만 발생한다.
- 미래 요청 존재 여부는 정책에 주어지지 않는다.

정책이 실제로 처음 투자하는 요청까지의 이력과 그 직후 종료하는 이력은,
투자 결정 시점까지 정책에 동일하게 보인다. 종료 이력에서는 후속 절약이
0이므로 기준 대비 비용 차이는 적어도 `a > 0`다. 따라서 이 모형에서
**비자명한 최초 투자를 허용하면서 모든 유한 입력의 누적 비용이 fresh
이하라는 보장을 동시에 줄 수 없다.**

재방문을 두 번 본 뒤 투자하더라도 마지막 투자 직후 종료하는 반례가 남는다.
재방문 관측 자체의 비용을 이미 지불했다면 그 비용도 더해진다. 이 정리는
새로운 과거 정보나 현재 요청 내부의 확정된 재사용, 처음부터 주어진 credit,
또는 공통 경로의 별도 비용 제거까지 금지하는 보편 명제가 아니다. 위의
명시한 투자 모형에 대한 유한 prefix 반례다. 실제 CPU의 정보이론적 하한도 아니다.

따라서 정직한 Phase08의 주장은 특정 사전 자료/비용 정의에서의 실증적
총비용 감소, 조건부 손익분기점, 또는 명시한 탐색 예산 아래의 regret 상한이어야
한다. 미래 반복을 예측하는 정책이 있다는 것만으로 무손실 비용 보장을
붙일 수는 없다.

## 3. cheap 해석을 먼저 지불하면 P7의 이득 창이 닫힐 수 있다

한 기록의 UTF-8 길이를 `L`, key context 길이를 `C`, 이번에 재사용하는
payload 길이 합을 `R`, 정책 추가비를 `G >= 0`라고 하자. Phase07과 동일하게
raw key 생성에 `L`, 전체 exact key probe에 `L+C`를 계상한다.

현재 방문에서 기준이 요청하는 단계 수가 `m`이고 모든 요청을 재사용하면

\[
\Delta_{warm}=(2-m)L+C+R+G.
\]

질의당 context 생성과 다른 기록의 비용은 아직 포함하지 않은 식이다.
`m <= 2`에서는 이 식부터 양수다. `m=3`이면 필요한 조건은

\[
L>C+R+G.
\]

여기서 `m`을 미리 안다고 가정하면 안 된다. 예컨대 cheap를 실제 실행해
해석 단계의 필요를 확인한 다음 cache를 찾는 전략은 최대 두 단계만
절약한다. 이때 cheap의 실행은 기준과 공통이고, 남은 최대 절약 `2L`에 대해

\[
\Delta_{after\ cheap}\ge (L+(L+C))+R+G-2L=C+R+G>0.
\]

따라서 같은 P7 비용 정의와 key 경로에서는 이 late lookup 전략이 완전히
warm이어도 기록 단위 이득을 낼 수 없다. 이것은 key 구축을 실제로 공유·제거한
다른 구현이나 CPU 상수가 큰 다른 파서에 대한 불가능 정리가 아니다.

가장 작은 정직한 대안은 해석 전에 유료 raw 관측으로 후보를 제한하고,
처음 실제 실행한 단계·payload를 근거로 admission을 결정하는 것이다.
낮은 비용의 prefilter가 모든 비유익 입력을 알아낼 것이라고 가정해서는 안 된다.
첫 miss에서는 원래 해석과 key/probe/관측 비용을 함께 지불한다.

## 4. 과거 stage 개수와 다음 방문의 stage 개수는 구분해야 한다

이전 질문에서 detail을 요청했다고 해서 다음 질문에서도 요청한다는 일반
보장은 없다. scope가 demand와 만나지 않으면 현재 선택기는 detail을 건너뛴다.
그러므로 과거 `m=3`만으로 다음 warm 이득을 단정하면 안 된다.

다만 현재 고정 코드에는 더 강한 충분조건이 있다. 실제 실행하여 얻은

```text
cheap.kind == "havoc"
scope == (None, "global")
```

를 정확한 원문·ordered entities·의미 namespace의 key 아래 보관했다고 하자.
기록의 `read`가 호출될 때 demand는 비어 있지 않고 field universe의 부분집합이다.
`None` scope는 바로 그 universe 전체이므로 현재 demand와 반드시 만난다.
따라서 이 key가 다시 방문되면 cheap, scope, detail 세 단계가 모두 요청된다.
이 조건은 gold·family·미래 질문을 읽지 않고도 이미 지불한 순수 결과에서
확인할 수 있다.

이 충분조건 없이도 stage별 재사용의 의미 보존은 가능하지만, 예상한 비용
절약은 줄어들 수 있다. 의미 안전성 조건과 비용 예측의 적중 조건을 분리한다.

## 5. 선택적 보관은 의미 증명을 어렵게 만들 필요가 없다

원문·ordered entities·실제 검증된 의미 fingerprint·namespace로 결정한 key를
`k`라 하고 단계 함수를 `f_s(k)`라 쓰자. 저장소의 불변식은 Phase07과 같다.

\[
\forall(k,s)\in\operatorname{dom}(M),\quad decode_s(M[k,s])=f_s(k).
\]

빈 저장소에서 시작하여, miss에서 실제 실행한 순수 값만 immutable로 보관하고,
hit에서는 해당 stage 슬롯만 읽으며, 삭제/축출은 값을 변형하지 않는다면 불변식이
유지된다. admission 정책이 길이·관측 재방문·과거 비용·현재 occupancy 중 무엇을
이용하든 이 명제는 변하지 않는다. 정책은 허용 입력의 정상 해석 요청을
건너뛰거나 다른 stage 값으로 대체할 수 없다.

현재 snapshot 검증, demand 전이, 상태 실행, trace, 원문 렌더가 같다는 전제
아래 단계별 귀납으로 status, integrity reason, prediction, selected,
remaining_input_facts, rendered UTF-8, scope_trace가 fresh와 같다.
정책이 비용 예측을 틀려도 이 불변식만 지키면 의미 결과는 같고 비용만 달라진다.

이 정리는 기존 파서의 참된 자연어 의미, 공동 답집합의 완전성,
reader의 독립적 근거 검증, 실제 실행 성공을 추가로 보장하지 않는다.

## 6. 공간 제약과 이득 조건은 서로 다른 제약이다

한 항목의 논리적 보관 크기는 key와 저장 stage payload의 합이다.
각 항목이 개별 한도 이하라는 사실은 함께 보관 가능함을 뜻하지 않는다.
후보 `i`를 넣을 때는 최소한

\[
\operatorname{used}+\operatorname{size}(i)\le B,
\qquad \operatorname{entries}+1\le N
\]

를 확인하거나, 이를 만족할 만큼 축출해야 한다. 현재 occupancy 점검은 온라인으로
가능하지만 미래 working set을 공짜로 아는 것은 아니다. admission을 거부하고
기존 항목을 유지하면 상호 축출의 특정 반례를 막을 수 있으나, 오래된 무용 항목이
공간을 독점하는 새로운 반례가 생긴다. 가치 기준으로 교체해도 가치가 관측 과거에
기초하면 미래 인기 역전의 반례가 남는다. 현재 단계에서 모든 workload의 최적
replacement를 보장하려 할 필요는 없다.

한 반복 조건에서 cold 추가비를 `A>0`, 매 후속 hit의 순절약을 `s>0`라 하면
T회 요청의 누적 차이는

\[
\Delta_T=A-(T-1)s
\]

이며 strict 이득은 `T>1+A/s`에서 가능하다. 이 단순식은 중간 miss·축출·namespace
변경·정책 학습비 증가가 없다는 조건을 요구한다. warm 이득 `s>0`은 전체
stream 이득의 충분조건이 아니다.

## 7. 비용 장부와 복잡도에 남겨야 할 항

- 공통 snapshot 직렬화·hash는 질문마다 그대로 남는다.
- 후보 gate가 원문을 읽거나 encode하면 그 작업을 계상한다.
- 반복 횟수/최근 방문 정보의 lookup·갱신·저장도 무료가 아니다.
- 상세 결과를 알아내는 최초 실행, immutable 변환, payload 길이 encoding,
  exact key 생성/probe, 삽입/축출을 포함한다.
- 파서 요청·실제 실행·entry hit·실제 stage reuse를 각각 구분한다.
- 정책 비교·산술·bookkeeping CPU를 논리 byte 항 하나로 실제 CPU처럼
  환산하지 않는다. 명시한 proxy, operation counters, wall time의 범위를 구분한다.

질문 q의 snapshot 길이가 `B_q`이면 기존 검증을 유지하는 유효 입력에서
`sum_q Theta(B_q)` 직렬화·hash 작업이 남는다. 방문 원문의 exact key를 새로
만드는 경로는 원문 길이에 의존한다. 자료구조 lookup 자체가 평균 상수 시간이더라도
전체 key 생성·검증이 상수 시간인 것은 아니다. bounded entry 수는 CPython RSS
상한도 아니다.

Phase06 fresh는 계측을 위해 `len(text.encode("utf-8"))`를 구한다. 이 encoding을
새 경로가 재사용할 수는 있지만, Phase07과 동일한 논리 비용 정의를 유지하면서
필요한 raw exact key의 `L`을 갑자기 무료로 처리해서는 안 된다. 실제 중복 작업
공유와 proxy 정의 변경은 별도로 명시해야 한다.

## 8. 현재 권고

검증/key 공유는 유용할 가능성이 있으나 snapshot 직렬화의 어떤 바이트가
key에 실제로 공유되는지까지 새 계약이 필요하다. 이번 한 단계에서는 순수
선택기의 의미 계약을 유지하고, 관측된 stage 비용과 payload·occupancy를 이용하는
선택적 보관 하나를 구현하여 **cold부터의 전체 비용**을 fresh와 비교하는 것이
가장 명료하다. 결과가 부정이어도 위 경계·반례와 동결 실험을 남기면 연구 질문을
한 단계 좁힌다. Phase07 자료와 사후 경계를 설계에 쓰면 모두 개발 자료다.

## 9. 구현 후보 검토

### 9.1 20:08 KST / 11:08 UTC: 설계 설명 검토

주 구현자로부터 다음 후보 설계를 전달받았다. 아직 최종 코드를 읽어 확인한
내용은 아니다.

- `len(text)`를 이용한 길이 gate. 짧은 원문은 순수 해석만 수행한다.
- resident 항목의 문자 길이 directory. 같은 길이가 없으면 exact key probe를
  생략하고 fresh 해석한다.
- 실제 실행으로 cheap havoc·global scope·detail을 모두 얻은 bundle만
  수익성·용량 판단의 후보로 삼는다.
- exact key, immutable stage, snapshot·선택기의 공통 실행 경로를 유지한다.
- 예상 1회 절약 score `b>0`, 과거 resident 재사용 횟수 `h`를 이용한
  `w=(h+1)b`와 논리 보관 크기로 교체를 판단한다.
- 주 비용은 `P8=P7+lambda*A`이며 `A`는 명시한 cache-policy 추상 연산 횟수,
  `lambda=8`을 사전에 고정하고 다른 가중치를 보조 민감도로 보고한다.

**길이 directory 보조정리.** 문자 길이 `d(t)`는 UTF-8 byte 길이 `L(t)`와
다르다. 그러나 원문이 정확히 같으면 문자 길이도 같다. directory가 모든 resident
항목의 문자 길이와 그 개수를 정확히 유지한다면,

\[
d(t)\notin D\Longrightarrow
\nexists k\in M:\operatorname{raw}(k)=t.
\]

따라서 음성 응답일 때 exact lookup을 생략하는 것은 안전하다. 양성 응답은
동일 원문 또는 동일 context의 증거가 아니므로 기존 exact key 검사가 필요하다.
같은 길이의 다른 원문·namespace는 유료 false-positive probe를 만들 수 있다.
길이가 같다는 이유로 stage를 재사용해서는 안 된다.

**후보의 조건부 비용식.** 한 질문에서 cache 후보 기록이 하나이고 다른 기록의
추가 정책비는 별도라고 하자. `C`는 질문당 한 번 생성하는 context 길이,
`R`은 세 stage payload 합이다. 빈 cache에서 첫 길이가 directory에 없어
probe를 생략한다면 첫 방문 추가비는

\[
A_{cold}=2L+2C+2R+\lambda a_{cold}.
\]

항목별로 raw key `L`, context `C`, value encode `R`, cache write `C+L+R`,
정책 연산 `lambda*a_cold`를 더한 것이다. 이후 완전 warm인 같은 방문에서는

\[
\Delta_{warm}=-L+2C+R+\lambda a_{warm}.
\]

질문당 context 생성을 제외한 ranking용 score `L-C-R-lambda*g_hit`와 위 식은
동일하지 않다. query 전체에서 strict 이득이 나려면
`L>2C+R+lambda*a_warm`이어야 한다. `g_hit`를 실제 연산 수의 상계라고 부르려면
gate·directory·probe·touch·hit update를 모두 포함하는지 코드로 확인해야 한다.
이 확인 전에는 추정 score일 뿐이다.

**교체 휴리스틱의 반례.** 큰 `b`의 A를 먼저 저장한 뒤 A는 다시 요청하지 않고,
조금 작은 `b`의 B만 반복한다. A와 B가 함께 들어가지 않고 B의 후보 weight가
A의 weight를 넘지 못한다면 B는 매번 거절된다. resident hit만 `h`에 반영하는
정책은 거절된 B의 반복 인기를 배우지 못한다. 이는 의미 오류가 아니라 과거
정보와 admission 경로 때문에 발생하는 비용 실패다. 미래 인기를 안다고
가정하거나 최적 knapsack 정책이라고 해석하지 않는다.

**연산 계수와 복잡도.** `P8`은 순수 byte량이 아니라 사전에 선택한 단위당
가중치를 가진 논리 작업점수다. `lambda=8`을 실제 CPU의 비용비로 부르지 않는다.
밀도 순 정렬은 N개 항목에 대해 `O(N log N)` 비교가 필요하므로 최대 64개 항목을
본다고 모든 관리 작업이 64번인 것은 아니다. 구현의 비교/정렬 event 또는
wall-time 범위에서 이를 빠뜨리지 않아야 한다. 밀도 비교는 정수 교차곱을 쓰면
실수 tie 처리 문제를 줄일 수 있다.

### 9.2 코드 검토

동결 전 `runtime.py`, `frozen.py`, `PROTOCOL.md`를 읽고 설계와 대조했다.
처음 코드에는 admission eligibility를 두 번 평가하는 중복이 있었고, eligible
miss의 stage 결과 수집이 control event로 드러나지 않았다. 주 구현자에게
전달하여 중복을 제거하고 `stage_observation`, `stage_payload_prepare`를
각 단계당 계상하도록 수정한 뒤 다시 확인했다. 짧은 bypass는 admission용
값을 수집하지 않는다. 이 수정은 새 holdout을 열기 전이다.

최종 검토한 소스 hash는 다음과 같다. 이 문서가 저장소 실행의 동결 파일을
대신하지는 않으며, 최종 동결 manifest가 일치 여부의 기준이다.

| 파일 | SHA-256 |
|---|---|
| `runtime.py` | `d923f5f1a0012b5f70348ed4cfdd376791ac6e12b1af3ed7b663e4aab674de13` |
| `frozen.py` | `cff396a3c06e8065434d57edbbfb86a888b84d5eb094f2b97e369c1c3026e9bf` |

확인한 핵심은 다음과 같다.

- exact key를 만들 때 context와 raw bytes가 분리되고, 길이 directory는 조회
  생략에만 사용한다.
- 현재 자연 경로의 실제 세 stage가 모두 관측된 뒤에만 global bundle을 보관한다.
- cache에 있는 값은 stage별 immutable이고 현재 demand에 맞춘 trace와 TOP은
  다시 만든다. 입력 검증은 cache 경로보다 먼저다.
- 완전 hit의 action은 정확히 8이며 query context bytes와 다른 short gate는
  별도다. 단독 새 후보의 성공한 cold admission은 24 action이다.
- occupancy와 entry 수를 모두 고려하여 victim 전체 계획 후 한꺼번에 반영한다.
  ranking은 정수 교차곱과 삽입 순서 tie를 사용한다.
- 정책의 `h`는 resident hit만 기억하므로 §9.1의 인기 고착 반례가 남는다.
- `frozen.py`에는 evaluator/gold/data import가 없으며 의미 source fingerprint는
  사전 소스 검증과 결합해 사용해야 한다.

코드 구조와 위 조건부 보존/비용식의 불일치는 최종 검토 범위에서 찾지 못했다.
이것은 모든 허용 입력의 프로그램 정형 검증이나 자연어 의미 검증이 아니다.
평가기 전체와 새 자료의 gold 의미는 이 역할의 검토 대상이 아니며 별도 감사와
구분한다.

### 9.3 직접 실행한 작은 개발용 식 검사

새 holdout과 무관하게 짧은 set과 `가` 1,000자를 본문으로 하는 deep quote의
두 기록을 만들고 같은 질문을 8회 실행했다. `namespace="v1"`,
`entities=["가람","누리"]`에서 실제 길이는 `L=3071`, `C=93`, `R=154`였다.

| 검사 | 관측 |
|---|---:|
| cold query의 control actions | 25 |
| warm query의 control actions | 9 |
| cold P8 차이 | +6,836 |
| 이후 매 warm P8 차이 | −2,659 |
| 8회 누적 P8 차이 | −11,777 |
| `(3−8)L+16C+9R+8(9×8+16)` | −11,777 |
| 식 잔차 | 0 / 1개 구성 stream |

이는 동결 전 구성한 1 stream/8질문의 산술·계측 검사다. 새로운 독립 성능
평가로 세지 않는다. wall time은 이 검사에서 측정하지 않았다. 전체 평가의
성과를 이 유리한 예로 대체할 수 없다.

정리와 구체적 cold/warm 식, 허용 정보, 공간·시간 복잡도, 작은 반례,
확인한 선행 연구는 [`THEORY.md`](THEORY.md)에 정리했다.
개발 단계의 코드 검토로 `selective`와 `no_directory`의 resident 상태·실행 수
동일성 및 nonnegative lambda에서 P8의 제한적 지배 관계도 도출하여 동결 전
THEORY에 추가했다. 이 명제는 fresh 또는 실제 CPU 시간에 대한 지배가 아니다.
Phase08 새 holdout/builder/개별 라벨/결과는 이 문서 완료 시점까지 읽지 않았다.
