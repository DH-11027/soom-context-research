# Phase09 이론 — 계측 삭제와 정책 보존은 다른 조건이다

동결 전 작성. 직접 기준은 Phase08 공개 완료 commit
`efba3224dd09d5c5e2bf9d9be11734fa10b32502`이다. 이 문서는 새 평가 자료의 내용과
성능 결과를 읽기 전에 작성했다. 코드와 선언된 입력 영역에 대한 조건부 증명이며,
Python 전체를 대상으로 하는 기계 검증이나 실제 자연어 의미 정확성의 증명이 아니다.

## 1. 하나의 질문과 두 종류의 결론

이번 연구는 Phase08의 선택·admission·replacement·용량을 고정하고, 결과와 정책에
영향을 주지 않는 계측 문장만 제거한다. 보존은 증명하고 실행시간은 실험으로 판정한다.

- 보존 명제: 같은 방법의 계측판과 비계측판은 매 입력 prefix에서 같은 의미 관찰과
  같은 정책 상태를 낸다.
- 성능 명제: **`fresh_uninstrumented`를 기준으로 `selective_uninstrumented`의
  cold 구축을 포함한 전체 workload 실행시간이 감소하는가?**

두 번째 명제는 첫 번째에서 따라오지 않는다. Phase08 자료와 시간 결과를 보고
이번 질문을 골랐으므로 그 자료는 이제 개발·회귀 자료다. 새로운 실험의 반복·순서·
주집계·판정 임계값은 [PROTOCOL.md](PROTOCOL.md)를 따른다.

## 2. 입력 영역과 관찰

질문 입력을 다음과 같이 둔다.

\[
x_t=(records_t,E_t,query_t,snapshot_t,namespace_t).
\]

`records`의 원문·순서·ID·seq, ordered entities, 현재 질문, expected snapshot과
namespace만 runtime에 전달한다. gold·family·미래 반복 수·종료 시점은 입력이 아니다.
입력은 유한한 native JSON 유사 값이며 원문·entity·namespace는 UTF-8로 인코딩 가능한
일반 `str`다. 객체의 사용자 정의 비교·속성 접근·인코더 부작용은 계약 밖이다.
각 호출 동안 입력과 동결 parser 코드는 외부에서 변경되지 않는다. 실행은 단일 스레드다.

`Obs`는 결과에서 `cost` 필드만 제외한 구조와 실제 근거 렌더 UTF-8 bytes의 쌍이다.

\[
Obs(x,r)=\bigl(r\setminus\{cost\},\;RenderUTF8(x,r)\bigr).
\]

따라서 `status`, `reason`의 존재·내용, `prediction`, `selected`,
`remaining_input_facts`의 존재·내용, `scope_trace`, `output_bytes`까지 보존한다.
무결성 실패의 렌더 관찰은 빈 bytes다. 길이나 digest만 같은 것으로 대체하지 않는다.
실제 실행 경로는 기존과 같이 render와 UTF-8 encode를 수행해 길이를 반환하며,
감사 실행에서 별도로 실제 bytes를 직접 비교한다. 주 timing 안에 검사용 재렌더를
추가하지 않는다.

관찰에는 실행시간, counter, event log, peak 통계, 객체 주소, allocator·GC·CPU 상태를
포함하지 않는다. 충분한 실행 자원과 정상적 Python 기본 연산을 가정한다.
`MemoryError`, 비동기 중단, 자원 고갈로 발생한 실패까지 계측 제거 전후 동일하다는
약속은 하지 않는다. 정상 입력의 snapshot 실패·지원하지 않는 질문과 음수 용량의
`ValueError` 같은 알고리즘의 명시적 오류 경로는 그대로 유지한다.

## 3. 보존할 정책 상태와 투영 π

Fresh는 질문 사이의 parser cache가 없으므로 정책 상태를 단위원소 `()`로 둔다.
Selective의 질문 경계 상태는 다음과 같다.

\[
S=(directory,max\_entries,max\_bytes,\mathcal E,D,B,n).
\]

- `𝓔`: **삽입 순서를 보존한** resident `(exact_key, item)` 열.
- exact key: `(encode(fingerprint, namespace, ordered_entities), UTF8(raw))`.
- item: `stages`, `size`, `characters`, `surplus`, `hits`, `order` 전부.
- `stages`: `cheap/contract/detail` 각각의 immutable 값과 실제 payload 길이.
- `D`: 문자 길이별 resident 수인 `lengths` directory.
- `B`: 현재 `retained_bytes`; `n`: 다음 삽입 순서인 `next_order`.
- `directory`, `max_entries`, `max_bytes`: 같은 알고리즘을 정의하는 설정.

계측 상태는 이 상태에 `cost`, event, timer, `peak_bytes`, `peak_entries`를 붙인
확장 상태로 볼 수 있다. `π`는 그 보고 전용 성분만 제거한다. `hits`는 제거하지 않는다.
`next_order`는 현재 답변에 드러나지 않아도 미래 tie-breaking에 영향을 주므로 남긴다.
정책 상태 비교는 serialize된 길이나 hash 비교가 아닌 구조와 exact bytes 비교다.

각 질문 안에서는 추가로 `demand`, `selected`, `query_events`, `trace`, 현재
`context/raw/key`, 관측 stage 값, victim 계획 등의 알고리즘 지역변수를 보존한다.
특히 `query_events`와 fresh의 질문 내부 `cache`는 통계 장부가 아니다.

목표 계약은 모든 유한 입력열의 모든 prefix에 대해

\[
\begin{aligned}
Obs(Run_I(x_{1:t}))&=Obs(Run_U(x_{1:t})),\\
\pi(S^I_t)&=S^U_t
\end{aligned}
\]

가 성립하는 것이다. 첫 식은 prefix가 낸 관찰의 순서 있는 열의 동일성이다.
최종 답 하나가 같다는 조건보다 두 식의 결합이 강하다.

## 4. 실제 데이터 의존성: 무엇을 지우고 무엇을 남기는가

검토한 원천은 Phase06 `scoped.py`, Phase07 `cached.py`의 fresh wrapper,
Phase08 `runtime.py`와 `evaluation.py`의 fresh wrapper다. 계측판은 원래 Phase08
경로를 직접 호출한다. 비계측판은 [derive_off.py](derive_off.py)가 그 특정 소스에서
명시된 계측 문장을 제거해 만든 [runtime_off.py](runtime_off.py)다.
[ERASURE_MAP.json](ERASURE_MAP.json)은 삭제 문장과 source hash를 기록한다.
이 변환기는 임의 프로그램의 안전한 dead-code 제거기라는 주장이 아니다.

| 값·계산 | 실제 소비자 | 결정 |
|---|---|---|
| `cost`의 호출·bytes·request·reuse counter | 보고·검증·점수 합 | 제거 |
| `action(cost, ...)`, `control_events` | control 통계·P8 보고 | 제거 |
| 내부 timer와 `finish`의 비용 합계 | `local_seconds`, 보고 필드 | 제거 |
| `peak_bytes`, `peak_entries` | peak 보고만 | 제거 |
| fresh의 `size=len(text.encode('utf-8'))` | source-byte counter만 | 제거 |
| selective의 `raw`, `size` | exact key와 L, admission size/surplus | 유지 |
| context encoding과 길이 C | exact key, size/surplus | 유지 |
| stage payload encoding과 길이 R | size/surplus, 저장 stage metadata | 유지 |
| `ACTION_WEIGHT * WARM_ACTIONS = 64` | 실제 surplus 계산 | **유지** |
| `hits`, saturation 255 | resident weight와 victim 비교 | 유지 |
| `surplus/size/order/next_order` | replacement·tie-breaking | 유지 |
| directory·retained bytes·용량 검사 | lookup 및 동시 보관·victim 결정 | 유지 |
| immutable 변환·정확 key 비교 | 값·context 보존 | 유지 |
| 전체 snapshot 직렬화·hash·검증 | 실제 실패/진행 분기 | 유지 |
| 현재 demand·상태 전이·copy·렌더 | 의미 관찰 | 유지 |

Fresh의 source-size encode 결과는 parser 입력에 들어가지 않는다. parser는 원래 `text`
자체를 받으며, 해당 정수는 오직 `*_source_bytes`에 더해진다. 반면 selective의 같은
형태의 encode는 정확 key와 L의 공급자다. **양쪽에 같은 이름의 encode가 있어도
데이터 의존성이 다르므로 제거 범위가 다르다.** Snapshot을 만드는 별도의 encode와
근거를 렌더하는 encode는 fresh에서도 남는다.

이번 변환은 보수적인 문장 수준 제거다. Selective의 short bypass처럼 실제로
key/admission에 도달하지 않는 특정 실행에서는 `raw`가 불필요할 수 있다. 그러나
공유된 `raw` 변수는 다른 경로에서 실제 정책에 필요하므로 모든 방문의 원래 encode
순서를 유지한다. lazy encoding·경로별 이동·자료구조 변경은 하지 않는다.
따라서 **최대로 최적화한 runtime 또는 모든 동적 dead 계산을 없앤 runtime이 아니다.**
측정 결과는 이 공개된 제거 방식에 대한 것이다.

## 5. 보조정리와 보존 증명

### 보조정리 E1 — 보고 장부의 비간섭

위 소스에서 `cost`의 숫자·event 목록, 내부 시각과 peak 값은 실제 parser 입력,
snapshot 판정, 현재 demand, 반환 관찰 또는 selective의 policy branch 조건에
사용되지 않는다. 해당 값끼리 합산하거나 보고하는 소비자만 있다.
`cost` 갱신을 제거해도 유지된 변수와 branch 조건값은 바뀌지 않는다.

이는 변수 이름으로 판정한 명제가 아니다. `hits`라는 counter와
`ACTION_WEIGHT`라는 점수 상수는 정책 branch에 도달하므로 E1의 삭제 집합에 속하지
않는다. `finish`를 제거할 때도 인수로 먼저 계산되던 result·render는 그대로 남긴다.

### 보조정리 E2 — 한 cache 연산의 정책 보존

같은 투영 상태와 같은 인수를 가진 두 cache를 가정한다.

1. `possible`: 같은 문자 길이와 같은 directory에서 같은 bool을 반환한다.
2. `get`: 같은 exact key와 같은 entries에서 같은 miss/hit가 나고, hit일 때 양쪽 모두
   `min(255,h+1)`을 수행하며 같은 immutable stage를 반환한다.
3. `admit`: 같은 실제 stage 값의 같은 encoding으로 R을 얻는다. 같은 C·L·R로
   `b=L−C−R−64`, `e=C+L+R+80`을 계산한다. 따라서 gate·개별 크기·용량 분기가 같다.
   부족하면 같은 순서의 resident를 읽고 같은 정수 교차곱과 삽입 순서로 정렬한다.
   같은 최소 prefix victim 집합 V와 `lost=Σ(h_i+1)b_i`를 얻는다. 비교 `b>lost`와
   성공 시 삭제·삽입·directory·retained·next_order 갱신이 모두 같다.

그 사이의 계측 문장은 E1에 의해 결과를 바꾸지 않는다. 따라서 각 cache 연산의
반환값과 이후 투영 상태가 같다. 거절한 victim 계획의 부분 삭제도 두 판 모두 없다. □

### 보조정리 E3 — 한 질문의 보존

같은 입력과 같은 초기 투영 상태에서 시작한다. Snapshot의 순서 검사와 canonical
직렬화·SHA-256 비교는 같으므로 같은 early exit 또는 같은 질문 파싱으로 진행한다.
지원 질문이면 역순 루프의 같은 demand에서 같은 기록을 방문한다. 단계 요청은 현재
순수 해석값과 demand로 결정되며, cache 연산은 E2에 의해 같다. 실제 miss parser는
같은 고정 함수와 입력을 받는다. 따라서 stage 요청·실제 호출·hit/miss 결정이 같다.

같은 event를 `query_events`에 기록하므로 writes·preimage·현재 copy 실행·최종 선택과
추상 상태가 같다. `scope_trace`도 같은 분기에서 같은 원소를 추가한다. 같은 status·
선택·snapshot·query로 render하므로 전체 Obs가 같다. 모든 cache 연산이 E2를 지키므로
질문 종료 상태의 π도 같다. Fresh는 cache 정책 부분이 없는 동일 논증이다. □

### 정리 E9 — 모든 prefix의 관찰·정책 상태 보존

빈 selective cache와 fresh 단위원소 상태에서 위 가정을 만족하는 입력열을 처리하면
§3의 두 등식이 모든 prefix에 대해 성립한다.

**증명.** 빈 상태의 π는 같다. t번째 질문 전까지 상태·관찰이 같다고 가정하면 E3가
t번째 관찰과 다음 상태의 동일성을 준다. 유한 t에 대한 귀납으로 끝난다. 코드의
세부 실행으로 보면 제거 문장은 관찰 없는 stuttering step이며, 남은 알고리즘 단계는
동일한 변수값으로 대응한다. □

이 정리는 `run_fresh(public)`의 고정 기본 경로 `text_scoped`와
`run_selective(public,cache,namespace=...)`에 대한 것이다. 생성 소스에 남은 다른
legacy method, 특히 `frozen_lazy`를 호출했을 때까지 비계측이라고 주장하지 않는다.
API는 그 경로를 주 실험에 사용하지 않는다. `derive_off.py --check`와 별도 실행
감사는 증명 가정과 실제 artifact의 결합을 검사하며 보편 정형 검증을 대신하지 않는다.

## 6. 작은 실행 반례: 최종 답만 검사하면 실패를 놓친다

[counterexamples.py](counterexamples.py)는 새 자료를 읽지 않고 만든 두 mutant를
실행한다. 시간 측정 결과는 수집·보고하지 않는다. 기준 상수·용량은 모두 Phase08과 같다.

### 6.1 Resident hit 수를 통계라고 지우면

`namespace='math-erasure'`, entities `['가람','누리']`, short set 하나 뒤에 deep noop
quote 하나를 놓는다. Quote A는 `x` 33,000개, B는 34,000개를 본문에 넣는다.

| 항목 | L | C | R | e | b |
|---|---:|---:|---:|---:|---:|
| A | 33,071 | 103 | 154 | 33,408 | 32,750 |
| B | 34,071 | 103 | 154 | 34,408 | 33,750 |

각각은 65,536에 들어가지만 둘은 동시에 들어가지 않는다. Stream `A,A,B`에서
정상판 A의 hit는 1이 되어 `w_A=65,500`이다. 따라서 B를 거절한다. hit 갱신을
삭제한 mutant는 `w_A=32,750`이므로 B를 받아 A를 축출한다.

**세 질문의 Obs는 모두 같지만 π는 두 번째 prefix부터 다르고, 세 번째에는
resident key 자체가 달라진다.** 이는 출력 동등성만으로 같은 정책의 비계측판이라고
인정할 수 없는 구체적 반례다.

### 6.2 계측을 없앴으니 λ도 0으로 바꾸면

같은 context에서 quote 본문을 `x` 249개로 만들면 문자 수 278, L=320, C=103,
R=154다. 정상 surplus는 `320−103−154−64=−1`이라 거절한다. 점수 계측을
삭제한다는 이유로 `ACTION_WEIGHT=0`으로 바꾸면 surplus가 63이 되어 보관한다.
최초 질문의 Obs는 같아도 cache 상태는 즉시 달라진다.

**측정을 위해 만든 상수라도 정책의 판단식에 들어간 순간 삭제 가능한 장부가 아니다.**
Phase09은 그 64를 그대로 남기며, 계측을 제거한 환경에 맞춰 admission을 다시
최적화하지 않는다. 두 mutant는 기존 정상 Phase08에 오류가 있었다는 증거가 아니다.

## 7. 시간에 관한 비정리와 상호작용

E9로 같은 방법의 실제 parser 요청·호출·cache 결정을 보존할 수 있다. 그러므로
비계측 주 timing 밖의 별도 호출 감사로 그 동일성을 확인할 수 있다. 그러나 장부를
지운 Python 프로그램의 실행시간 부등식은 E9의 귀결이 아니다.

방법 m의 네 시간 관측을 `T_{m,on}`, `T_{m,off}`라 하면

\[
I=(T_{sel,on}-T_{sel,off})-(T_{fresh,on}-T_{fresh,off})
\]

는 계측 제거 전후 격차 변화의 기술 통계로 계산할 수 있다. 이를 특정 counter 또는
event 함수의 정확한 CPU 비용이라고 부를 수는 없다. 할당·GC·코드 배치·branch·
regex/CPU cache·스케줄링이 상호작용한다. 주 timing에 monkey patch, call log,
gold 평가나 profiler를 다시 넣으면 다른 실험이 된다.

계측 제거로 fresh의 source-size encode가 사라지고 selective에서는 남는 비대칭은
데이터 의존성의 결과다. 이를 제외해 selective에 유리한 비교를 만들지 않는다.
양쪽의 전체 snapshot 검증·현재 상태 실행·같은 렌더·cold cache 생성은 시간 구간에
남는다. parser cache가 빈 것과 CPU/OS cache 전체가 차가운 것은 다른 조건이다.

## 8. Phase08의 경계를 유지한다

- 양의 최초 투자 뒤 stream을 종료할 수 있다면 모든 유한 stream에서의 무손해 보장은
  그 투자 모형에서 불가능하다. 계측 삭제가 미래 재방문을 보장하지 않는다.
- Cheap를 먼저 지불한 뒤 최대 두 stage를 재사용하면 기존 P7 key charge 아래
  `Δ≥C+R+λa`다. 이 논리 점수 경계를 실제 시간 하한으로 옮기지 않는다.
- 과거 인기의 고착, 같은 길이의 다른 원문, 함께 들어가야 하는 working-set 용량
  경계는 고정 정책에 남는다. 이번에 replacement와 자료구조를 바꾸지 않았다.
- D8은 selective와 no_directory의 같은 상태·호출 및 P8 점수 관계다. Fresh 대비
  또는 CPU 시간에 대한 정리가 아니다.
- E9는 기존 제한 parser의 의미 오류도 보존할 수 있다. 실제 자연어 이해, 일반적인
  정정·미완료 요청·실행 증거 보존, 외부 reader 검증, LLM token·요금·답변 품질은
  검증하지 않는다. **SOOM 운영 변경 없음.**
