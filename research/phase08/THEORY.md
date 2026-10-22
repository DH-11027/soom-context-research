# Phase08 이론 계약 — 비용을 관측한 뒤 선택하는 순수 해석 재사용

동결 전 작성. 직접 기준은 Phase07 완료 커밋
`6da051c0132811184ecf39975d7ff647a1f47842`다. 의미 분석은 수정하지 않은
Phase06 `text_scoped`에 고정한다. 이 문서는 새 평가의 성능 결과를 전제하지
않으며, [`PROTOCOL.md`](PROTOCOL.md)의 주 가설과 별도로 **증명할 수 있는
보존·비용 경계와 증명할 수 없는 예측**을 구분한다.

## 1. 문제와 입력 경계

질문 q의 공개 입력은 다음과 같다.

\[
X_q=(records_q,E_q,query_q,snapshot_q,namespace_q).
\]

`E_q`는 순서를 유지한 엔터티 목록이다. `snapshot_q`의 검증과 현재 demand,
상태 실행, 선택 인덱스, trace, 출력 렌더는 질문마다 다시 계산한다.
원문은 정규화하지 않는다. 비교하는 관찰은 다음이다.

```text
status / integrity failure reason / prediction / selected
remaining_input_facts / rendered UTF-8 output / scope_trace
```

출력 길이가 같다는 것보다 강한 문자열 내용의 동등성을 요구한다.
비용 계측, hit 수, 시간, 캐시 상태는 같은 값일 필요가 없다.

순수 단계는 Phase07과 같이

\[
f_{s,v}(E,t)=y,\qquad s\in\{cheap,contract,detail\}
\]

다. 코드의 `contract`는 순수 scope 추출 단계다. `v`는 검증된 동결 코드의
fingerprint와 실행 namespace를 포함한다. 정확 key는

\[
k=(encode(v,E),UTF8(t))
\]

이고 tuple의 두 구성요소를 정확 비교한다. digest만 같다는 이유로 재사용하지
않는다. `f_s`는 원문·엔터티·고정 의미 규칙 이외의 시간, 난수, 과거 실행 상태,
외부 모델 응답을 읽지 않는다고 가정한다. 공개 입력은 한 `run` 동안 변하지 않고,
실행은 단일 스레드다. 입력이 다음 질문 사이에서 바뀌는 것은 허용한다.

`frozen.py`는 동결 소스의 기대 hash를 기록하며 실행 전 `verify_sources()`로
실제 소스를 확인한다. 매 질문마다 parser 파일을 다시 해시하는 계약은 아니다.
살아 있는 cache 안에서 코드·규칙을 몰래 바꾸면 이 전제가 성립하지 않는다.

### 허용하는 과거 정보와 금지하는 정보

정책은 현재 공개 원문 길이, 실제로 요청·실행한 stage 결과, 그 결과를 직접
encode한 길이, resident 항목의 크기, 이미 일어난 resident hit 수와 삽입 순서만
이용한다. 캐시 내부 상태는 과거·현재 공개 입력에서 유도된 정보다.

gold AST, 정답, family/split 이름, 미래 질문, 미래 반복 횟수, 종료 시점,
외부 semantic annotation은 정책 입력이 아니다. 캐시에 없는 항목의 반복 횟수를
알고 있다고 가정하지도 않는다. `h`는 해당 resident 항목의 실제 hit만 센다.
거절한 원문의 반복 인기를 기억하는 별도 sketch는 구현하지 않는다.

## 2. 선택 정책: 먼저 결과를 얻고 그다음 admission

고정 정책 상수는 다음과 같다.

| 식별자 | 값 | 의미 |
|---|---:|---|
| `MIN_CHARS` | 256 | Python `str` 문자 길이 gate |
| `MAX_ENTRIES` | 64 | resident 항목 수 한도 |
| `MAX_BYTES` | 65,536 | 정의한 논리 보관 크기의 합 한도 |
| `META_BYTES` | 80 | 항목당 control/directory용 논리 allowance |
| `HIT_CAP` | 255 | resident hit 계수의 포화값 |
| `ACTION_WEIGHT` | 8 | 선언한 control action 한 번의 작업점수 |
| `WARM_ACTIONS` | 8 | 완전 bundle hit의 선언한 action 수 |

80 bytes는 Python 객체의 물리 메모리를 측정하거나 상계한 값이 아니다.
원문·context·payload 크기와 별도로 열 개의 8-byte scalar에 해당하는 allowance를
정의한 것이다. metadata 초기화는 열 개의 control action으로도 계상한다.
metadata를 `cache_write_bytes`에 중복 가산하지 않는다.

한 기록 방문의 순서는 다음과 같다.

1. 현재 원문의 문자 길이 `d(t)=len(text)`가 256 미만이면 cache 후보가 되지 않고
   원래 의미 경로를 실행한다. gate의 control action은 남는다.
2. 후보 길이에 해당하는 resident 항목이 하나라도 있는지 directory를 조회한다.
   없다면 exact key 생성/probe를 미리 하지 않는다.
3. 가능성이 있으면 질문당 lazy context를 만들고 exact key를 구성하여 조회한다.
   hit라면 현재 경로가 요청한 stage 슬롯만 읽는다.
4. miss 또는 directory 음성이면 원래 요청한 stage를 실제 실행한다. 후보의
   stage 관측·수집을 action으로 계상한다. speculative 상세 해석은 하지 않는다.
5. 실제로 세 stage를 모두 실행했고 cheap가 `havoc`, contract의 may-write가
   `None`인 경우만 admission을 검토한다. 그때 payload를 encode·immutable화하고
   준비 action과 encoding bytes를 센다.
6. 아래 수익성·용량·교체 조건을 통과할 때만 exact key와 complete bundle을 쓴다.
   미리 lookup하지 않았고 admission도 거절하면 원문 exact key 구축을 생략할 수
   있지만, 이미 실행한 해석·payload encoding·판단 비용은 남는다.

길이 `d`는 문자 수이고 `L=|UTF8(t)|`는 byte 수다. 서로 대체하지 않는다.
typed public 입력이 이미 Python 객체로 전달된 실행 환경에서 `len(str)`는 길이
관측이다. 입력 파일의 로딩·UTF-8 decode를 없앴다는 주장은 아니다.

### Admission과 교체 점수

현재 context 길이를 C, 세 stage payload의 canonical 길이 합을 R이라 하자.
항목의 논리 보관 크기 e와 ranking용 surplus b는

\[
e=C+L+R+80,
\qquad
b=L-C-R-8\cdot8.
\]

`b<=0`, 개별 용량 초과, 또는 entry 한도 0이면 보관을 거절한다.
resident i의 과거 hit 수 h_i를 이용한 weight는

\[
w_i=(h_i+1)b_i,\qquad 0\le h_i\le255.
\]

후보의 h는 0이다. 빈 공간이 충분하면 후보를 넣는다. 부족하면 resident 항목을
`w_i/e_i` 오름차순으로 정렬하고, 용량을 회복할 수 있는 prefix V를 계획한다.
비율은 정수 교차곱으로 비교하며 같은 비율이면 삽입 순서를 사용한다.

\[
b_{new}>\sum_{i\in V}w_i
\]

일 때만 V를 제거하고 새 항목을 넣는다. 제거 전에 전체 계획을 계산하므로
거절된 admission은 기존 항목을 일부만 지우지 않는다. 각 성공한 삽입 후
entry 수와 논리 크기 합을 동시에 검사한다.

**b는 다음 질문 전체의 이득 인증서가 아니다.** context 생성·다른 기록의 gate·
cold 구축을 제외한 한 resident 방문의 score다. w 역시 관측 과거로 만든
휴리스틱이며 실제 미래 수요, knapsack 최적해, 경쟁비율의 증명이 아니다.
보조 가중치 민감도는 같은 고정 정책의 결과를 다른 lambda로 다시 합산하는 것이며,
정책의 admission 자체를 그 lambda에 맞춰 재조정하는 실험이 아니다.

## 3. 길이 directory의 정확한 역할

directory D는 resident 원문 각각의 문자 길이와 그 개수를 유지한다.
정확히 같은 원문은 같은 문자 길이를 가지므로

\[
d(t)\notin D
\Longrightarrow
\nexists k\in cache:\operatorname{raw}(k)=UTF8(t).
\]

따라서 directory의 음성 응답은 exact hit가 없음을 보장한다. 그때 lookup을
생략해도 원래 hit를 잃지 않는다. 양성 응답은 같은 원문·context의 증거가 아니다.
같은 길이의 다른 원문, 다른 ordered entities, 다른 namespace 때문에 false-positive
probe가 생길 수 있으며, 그 key 비용과 miss를 그대로 계상한다.

원문 길이만 같은 두 기록을 같은 의미로 취급하면 이 정리는 성립하지 않는다.
directory는 부정 필터이고 semantic key가 아니다. 모든 삽입·삭제가 directory
계수를 맞게 갱신한다는 불변식이 필요하다.

`no_directory` ablation은 이 길이 필터를 resident 존재 여부 검사로 교체한다.
gate·admission·exact key·용량·교체 점수는 같게 둔다. 존재 확인도 action에 포함한다.
그 비교는 길이 필터의 역할을 분리하는 것이며, 주 비교는 항상 fresh다.

### 제한된 ablation 지배 정리

다음 명제는 새 holdout을 열기 전, 개발 검사와 코드 검토 단계에서 추가했다.
두 방법이 같은 빈 상태에서 같은 공개 입력 stream을 처리하고,
`no_directory` 역시 길이 metadata를 유지하지만 `possible()`에서만 그것을
사용하지 않는 현재 구현을 전제한다.

**정리 D8.** 매 질문 후 두 방법의 resident key·stage·hit 수·삽입 순서·길이
directory·occupancy는 같다. 실제 파서 stage 실행 수도 같다. 또한 정의한 장부에서

\[
\forall q,\lambda\ge0:\quad
P_8^{selective}(q;\lambda)\le P_8^{no\_directory}(q;\lambda).
\]

증명은 처리 순서에 대한 귀납이다. 길이 필터가 생략하는 조회는 앞의 보조정리에
따라 반드시 exact miss다. 실패한 `get`은 resident 상태나 hit 수를 바꾸지 않는다.
진짜 hit는 두 경로에서 함께 발생한다. admission은 실제 발생한 비용 합계가
아니라 동일한 순수값·C·L·R·resident h에서 구한 b를 사용하므로 같은 결정을
내린다. 따라서 다음 상태와 실제 파서 호출이 같다.

비용은 추가 miss의 key/probe/context/action에서만 달라질 수 있다. 두
`possible()` 검사는 같은 1 action이고, false-positive exact miss의 추가비는
비음수다. normal 경로에서 뒤늦게 admission용 key/context를 만들 필요가 있으면
그 비용은 이미 만든 no_directory와 같아지고, 거절하거나 다른 경로로 끝나면
normal 경로가 그 비용을 피한다. 나머지 장부는 같으므로 부등식이 성립한다. □

이 정리는 **해당 ablation에 대한 정의된 proxy의 관계**다. fresh보다 싸다는
정리도, 서로 다른 자료구조 연산의 실제 CPU 시간이 같다는 정리도 아니다.
directory lookup과 `bool(entries)`의 물리 비용 차이는 별도 timing에서 드러날 수 있다.

## 4. Complete global bundle은 다음 방문에도 세 stage를 요청한다

이미 실제 실행한 결과가

```text
cheap.kind == "havoc"
contract == (None, "global")
detail has actually been evaluated
```

인 key를 다시 방문한다고 하자. 현재 루프는 비어 있지 않은 demand일 때만
기록을 읽는다. demand는 현재 field universe의 부분집합이다. contract의 `None`은
universe 전체를 뜻하므로 demand와 반드시 만난다. 따라서 cheap, contract,
detail이 모두 요청된다. 세 stage의 동결 순수성 때문에 저장값이 이 분기 조건을
바꿀 수 없다.

이 조건은 단순히 “과거에 세 번 실행했다”보다 강하다. 일반 scoped 항목은
다음 demand에 따라 detail 요청을 생략할 수 있다. 그런 항목의 과거 stage 수를
미래 stage 수라고 가정하지 않기 위해 현재 후보를 제한했다.

detail 결과가 `havoc`이어도 complete bundle일 수 있다. 이는 현재 선택기가
다시 보류하거나 전체 이력을 출력하게 할 뿐이며, unknown 자체를 정확하게
재사용한다. detail `havoc`에서 만드는 query-local `scoped_top`은 저장하지 않는다.

## 5. 관찰적 동등성 정리

저장된 모든 stage에 대해 다음 불변식을 둔다.

\[
decode_s(cache[k][s])=f_s(k).
\]

빈 저장소에서는 자명하다. 실제 miss의 순수 결과만 보관하고 immutable 변환이
필요한 반환 의미를 보존하므로 admission은 불변식을 유지한다. hit는 정확 key와
동일 stage의 값만 읽는다. 삭제·축출은 올바른 값을 제거할 뿐이다. directory의
조회 생략은 hit가 없을 때만 적용하므로 miss 경로로의 이동도 안전하다.

각 질문의 실행 단계에 대해 귀납한다. snapshot 검증과 query 처리가 같아서
같은 상태에서 시작한다. 순수 stage 요청의 반환값이 같으므로 현재 demand,
선택, scope trace, 다음 요청이 같다. 현재 상태 실행과 원문 렌더도 같다.
질문이 끝난 뒤 저장소 불변식이 남으므로 다음 질문에 대해 반복한다.

**정리 S8.** 위의 순수성·완전 key·immutable 변환·동결 의미 규칙·동일 실행
경로·단일 스레드 전제 아래, 선택적 실행은 같은 공개 입력의 fresh 실행과
§1의 모든 관찰이 같다. 용량 거절·과거 인기 예측 실패·false-positive probe는
이 정리의 결론을 바꾸지 않는다.

원문을 바꾸고 snapshot을 갱신하면 새 원문 key를 사용한다. snapshot이 틀리면
cache 접근 전에 기존과 같은 integrity 실패를 반환한다. 미지원 질문도 기존처럼
전체 이력을 돌려주고 순수 파서 cache를 미리 채우지 않는다.

이 정리는 기존 파서가 자연어의 실제 의미를 맞혔다는 증명이 아니다.
product abstraction에서의 답과 실제 공동 답집합을 같게 만들지 않으며,
원문·digest만 받은 reader의 독립 의미 검증이나 실제 작업 실행 성공을
추가로 보장하지 않는다. 기존 오류나 보류도 그대로 재현할 수 있다.

## 6. 비용: byte ledger와 control 점수, 실제 시간을 분리한다

Phase07 byte ledger는 그대로 둔다.

\[
P_7=output+hash+parser\_source+key\_build+key\_probe
+value\_encode+cache\_read\_payload+cache\_write.
\]

새 주 지표는 선언한 cache-policy action 합 A를 더한

\[
\boxed{P_8(\lambda)=P_7+\lambda A,\qquad\lambda=8.}
\]

다. 이것은 **논리 작업점수**다. 두 항을 더했다고 실제 byte 전송량·CPU 명령 수·
메모리 비용으로 해석하지 않는다. action은 길이 gate, directory/presence 조회,
context access, exact lookup, hit update, stage 관측/준비/읽기, eligibility,
candidate 산술, 용량·victim 검사, density 비교, 삽입·삭제 등의 사전 정의한
추상 event다. 각 event는 여러 Python 명령을 포함할 수 있다. 실제 관리·해석·
검증·렌더의 시간은 별도 wall time에서 측정한다.

Phase07 LRU에도 해당 container/slot/준비 작업의 같은 종류 action을 계측하되,
기존 P7 byte 합이 변하지 않는지 검사한다. fresh는 새 cache-policy action이 없다.
P8의 결론은 선택한 가중치에 의존할 수 있으므로 lambda=0,32,128도 보조로 보고한다.
가장 좋은 가중치를 사후 주 지표로 바꾸지 않는다.

Phase06 fresh도 source 크기 계측을 위해 UTF-8 encoding을 수행한다. 새 경로가
그 raw bytes 객체를 key 구성에 이용해도 P7의 논리 key-build `L`을 계속 계상한다.
공통 계측용 encoding이 있다는 이유로 exact key 생성이 무료라고 하지 않는다.
전체 snapshot 검증은 줄이지 않는다.

### 6.1 완전히 warm인 한 후보 기록

기록이 방문되고 세 stage를 모두 hit하면 기존 파서 입력 `3L`을 절약한다.
key 생성 `L`, exact probe `C+L`, payload read `R`, 기록 단위 action 8회를 지불한다.
질문당 context encoding을 제외한 차이는

\[
\Delta_{record}=-L+C+R+8\lambda.
\]

primary lambda=8에서 b는 정확히 이 값의 음수다. 실제 코드의 8회는
gate 1, directory 1, context access 1, exact get 1, hit update 1, stage read 3이다.
context의 **access action**과 실제 한 번의 **encoding bytes C**는 다른 항이다.

한 질문에 이 후보 하나만 있어 context 전체를 이 방문에 귀속하면

\[
\Delta_{warm}=-L+2C+R+8\lambda.
\]

다른 방문의 gate, miss, admission 비용은 여기에 추가된다. 따라서 b가
양수여도 질문 또는 stream 전체의 비용이 감소한다는 충분조건은 아니다.

### 6.2 빈 cache에서 새로운 길이의 최초 admission

directory가 음성이면 최초 exact probe는 생략된다. 자연 경로의 해석 비용은
fresh와 같다. 성공적으로 보관하는 최초 추가비는

\[
\Delta_{cold}=2L+2C+2R+\lambda a_c.
\]

이는 raw key `L`, context `C`, value encode `R`, cache write `C+L+R`,
실제 선언 action `a_c`의 합이다. 현재 코드의 단독 후보에서는 `a_c=24`다:
gate·directory·eligibility·context 각 1, stage 관측 3, payload 준비 3,
candidate 산술 2, positive·capacity 각 1, metadata/entry 초기화 10.
축출·같은 길이 충돌·이미 생성된 context가 있는 경우에는 이 특수 계수를
그대로 쓰지 않고 실제 ledger를 적용한다.

### 6.3 두 기록·반복 질문의 closed form

짧은 set 기록 하나와 긴 deep global noop 기록 하나가 있고, 같은 지원 질문을
T회 반복한다고 하자. 매번 뒤의 noop부터 읽은 뒤 set을 읽고 종료한다.
두 원문·entities·namespace는 고정한다. set은 gate 미만이라 보관하지 않고,
noop은 최초 admission 후 계속 보관된다. 첫 directory는 비어 있고,
다른 resident·축출·입력 변경은 없다고 가정한다.

짧은 set의 gate 1회를 각 질문에 더하면 cold action은 25, warm은 9다.
따라서

\[
\begin{aligned}
\Delta_1&=2L+2C+2R+25\lambda,\\
\Delta_{q>1}&=-L+2C+R+9\lambda,\\
\boxed{\Delta_T}&=\boxed{(3-T)L+2TC+(T+1)R+(9T+16)\lambda}.
\end{aligned}
\]

보관 조건은 `C+L+R+80 <= 65536`, 문자 gate와 b 조건도 함께 만족해야 한다.
이 모형에서는 **T<=3이면 길이만 늘려 전체 이득을 만들 수 없다.** T>3에서는

\[
L>\frac{2TC+(T+1)R+(9T+16)\lambda}{T-3}
\]

가 strict 총이득 조건이다. 이것은 가정된 반복 구조와 선택한 P8 장부에 대한
식이다. 원문 길이의 실제 CPU 하한이나 임의 workload의 이득을 뜻하지 않는다.
주평가의 결과를 이 구성된 예제로 대체하지 않는다.

## 7. 작은 반례와 불가능한 약속

### 7.1 첫 투자를 한 직후 끝나는 stream

동일 공통 경로를 유지하고, 이전에 실현한 절약이나 외부 credit 없이,
양의 추가비 a를 처음 지불하며 그 회수는 미래 재사용에 의존한다고 하자.
정책의 최초 투자까지 같은 이력을 보여 준 뒤 stream을 종료하면 미래 절약은 0이고
누적 차이는 적어도 a다. 그러므로 이 모형에서 비자명한 투자를 허용하면서
모든 유한 stream의 비용이 fresh 이하라고 보장할 수 없다. 몇 번의 반복을
관측한 뒤 투자하더라도 첫 투자 직후 종료하는 prefix가 남는다.

이는 현재 요청 안의 이미 확정된 중복, 별도 공통 비용 최적화, 외부 credit,
다른 비용 모형까지 금지하는 보편 명제가 아니다. Phase08처럼 cold 투자 뒤
미래에 회수하는 계약의 반례다.

### 7.2 cheap를 먼저 실행해 stage 수를 공짜로 알아낼 수 없다

cheap를 먼저 지불한 후 두 남은 stage만 재사용하면 최대 `2L`을 절약한다.
하지만 기존 exact key 비용만 `L+(L+C)`이므로

\[
\Delta\ge C+R+\lambda a>0.
\]

동일 key 비용 정의에서는 이 late lookup 전략의 warm 이득이 막힌다.
새 구현은 이 문제를 피하기 위해 해석 이전에는 유료 raw 길이만 보고,
해석 뒤에 이미 관측한 결과로 admission한다. 어떤 원문이 세 stage인지를
공짜로 알아내는 oracle는 없다.

### 7.3 같은 길이는 같은 의미가 아니다

서로 다른 원문이 같은 `len(text)`를 갖거나, 같은 원문이 다른 entity universe에
들어갈 수 있다. directory의 양성 응답만으로 재사용하면 이전 해석을 잘못
적용할 수 있다. 현재 정책은 exact context와 raw bytes 검사를 추가로 한다.
이 검사는 의미에 필요하며 충돌 workload에서 비용을 늘릴 수 있다.

### 7.4 과거 인기 때문에 새로운 반복 항목이 계속 거절되는 반례

같은 payload 크기를 가진 긴 deep noop A와 B를 잡되

\[
e_A\le B_{cap},\quad e_B\le B_{cap},\quad
e_A+e_B>B_{cap},\quad b_A>b_B>0
\]

라고 하자. A를 한 번 요청하여 보관한 뒤 A는 더 이상 쓰지 않고 B만 반복한다.
A의 hit 수는 0이고 `w_A=b_A`다. B를 넣으려면 A를 축출해야 하지만
`b_B>w_A`가 거짓이므로 B는 거절된다. 거절한 B의 반복 횟수를 저장하지 않기
때문에 이후도 같은 판단이 반복된다. 정확성은 유지되지만 새 인기 항목의
세 stage는 매번 실행된다. 길이가 달라 exact probe를 생략해도 context,
payload encoding, 정책 판단의 양의 추가비가 남는다.

이는 admission 휴리스틱의 실패 사례이며 실제 미래를 알지 못하는 조건의
중요한 경계다. 이를 숨기기 위해 holdout의 해당 조건을 빼거나 정책을 사후
수정하지 않는다. decay·거절 항목 이력·탐색 allowance 등은 별도 다음 연구다.

## 8. 계산 복잡도와 공간 범위

질문 q의 전체 snapshot 직렬화 길이를 `B_q`, 방문 기록 집합을 V_q,
실제로 실행한 stage들의 실제 계산비를 `p_s(E,t)`라 쓰자. 문자열 regex 파서의
CPU 비용을 source 길이 하나와 같다고 가정하지 않는다.

고정 폭 scalar를 사용하는 word-RAM 설명에서는 공통 경로 외 추가 작업은 대략

\[
O\!\left(\sum_q\sum_{t\in V_q}1
+\sum_{\text{key 준비/probe}}(L+C)
+\sum_{\text{payload 준비}}R
+\sum_{\text{용량 충돌}}N\log N\right)
\]

이다. 실제 miss의 `sum p_s`와 현재 추상 실행·출력 비용은 별도로 남는다.
N<=64지만 이는 sorting이 64번 이하의 연산이라는 뜻이 아니다. density 비교는
각각 ledger에 기록한다. Python 정수 `next_order`는 admission 수에 따라 성장하므로
무한 stream의 bit complexity까지 고정 폭 O(1)이라고 주장하지 않는다.

유효 snapshot의 공통 검증은 여전히

\[
\sum_q\Theta(B_q)
\]

의 직렬화·hash 작업을 요구한다. 방문 원문의 정확 key 접근은 길이에 의존한다.
hash table의 평균 lookup 비용과 key 생성/검증을 합쳐 상수 시간이라고 부르지 않는다.
dict hash 충돌의 최악 경우나 동시 실행은 추가 경계다.

정의한 retained 크기 합은 65,536 이하이고 항목 수는 64 이하다. 이 상한은
public 이력, query-local events, regex 임시 객체, JSON/UTF-8 임시값, Python
객체 header/allocator, 전체 RSS를 포함하지 않는다. physical memory 절감 주장은 없다.

## 9. 기존 연구와 이번 기여의 범위

비용·크기·과거 접근을 이용하는 cache 정책은 새로운 발명이 아니다.
Cao와 Irani의 [GreedyDual-Size 원 논문 알고리즘 설명](https://www.usenix.org/legacy/publications/library/proceedings/usits97/full_papers/cao/cao_html/node8.html)은
비용/크기와 접근 locality를 결합한다. Einziger, Friedman, Manes의
[TinyLFU 저자 원고](https://arxiv.org/abs/1512.00727)는 최근 접근 빈도로
admission을 판단한다. 이 두 자료를 관련 선행 연구의 확인에 사용했다.

현재 코드는 GreedyDual-Size나 TinyLFU의 정확 구현이 아니며, 그들의 성능·
경쟁비율을 승계하지 않는다. 이번 기여의 범위는 고정된 순수 해석 경로에서
관측 가능 정보만으로 후보를 선택하고, 길이 음성 필터와 stage 계약의 보존을
분리해 증명하며, 정보 획득·관리까지 명시한 비용 장부로 fresh와 비교하는
제한된 연구 단계다. 임의 자연어 대화의 압축 품질이나 LLM 비용 개선은
이 정리와 실험 범위에 포함하지 않는다.
