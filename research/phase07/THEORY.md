# Phase 07 이론 계약: 질문 사이의 순수 해석 결과 재사용

기준: 공개 Phase 06 `13d166dc106fa3ab33128ad0626679fafdce5019`. [실행 전 계획](PROTOCOL.md)을 따른다. 기존 scope 언어, 선택 정책, 추상 의미, 최종 출력은 고정한다. 이 문서는 memoization의 동등성 조건과 사전 비용 모형을 설명하며, 실제 개선 여부는 동결 후 실험으로 판정한다. Memoization이나 LRU 자체를 새로 제안한다는 주장이 아니다.

## 1. 무엇을 재사용하는가

순수 해석 단계를 `cheap`, `scope`, `detail`로 나눈다. 각 단계의 함수는 다음과 같다.

\[
f_{s,v}(E,t)=y,
\qquad s\in\{cheap,scope,detail\}.
\]

- `v`: 함수 의미를 결정하는 실제 코드·규칙 fingerprint와 실행 namespace.
- `E`: 순서를 보존한 공개 엔터티 목록.
- `t`: 정규화하지 않은 정확한 원문.
- `y`: 해당 순수 단계의 반환값. `havoc`, scope의 `None` 등 계산된 unknown도 정상적인 값이다.

후보 구현은 한 원문에 대한 key를 각 단계마다 새로 만들지 않는다. 질의의 context를 canonical UTF-8로 표현하고, 방문한 기록마다 다음 구조의 정확 key를 한 번 준비한다.

```text
context = (frozen parser/scope fingerprint, execution namespace, ordered entities)
record_key = (canonical_context_bytes, exact_raw_text_utf8)
entry = {cheap: optional immutable value,
         scope: optional immutable value,
         detail: optional immutable value}
```

구조화된 pair 또는 동등한 길이 구분 인코딩을 사용한다. 구분 없는 문자열 이어붙이기는 서로 다른 입력을 같은 key로 만들 수 있다. 정상 입력 원문은 유효한 UTF-8로 표현 가능하다고 가정하며, Unicode normalization·공백 제거·대소문자 변환을 하지 않는다. Hash table 내부 hash가 충돌하더라도 최종 key 동등성은 context와 원문 전체의 정확 동등성으로 확인한다. 원문 digest 하나가 같다는 이유만으로 같은 원문으로 취급하지 않는다.

record ID, `seq`, 현재 질문, snapshot digest는 이 순수 함수의 입력이 아니므로 key에 필요하지 않다. 반대로 함수가 미래에 대명사 해석을 위해 앞선 문장이나 권한·역할을 읽는다면 이 계약은 더 이상 충분하지 않다. 그 의존성을 key에 포함하거나 재사용 범위를 다시 제한해야 한다.

## 2. 의미 버전과 신뢰 전제

`VERSION`이라는 표시 문자열만 같다고 의미가 같은 것은 아니다. 파서 코드뿐 아니라 `NOOPS`, `DEEP_NOOPS`, scope 규칙, 해석에 영향을 주는 설정까지 같은 namespace에서 고정돼 있어야 한다. 실제 동결 소스 fingerprint는 검증된 코드와 연결돼야 하며, cache가 살아 있는 동안 의미를 바꾸는 monkey patch나 mutable rule 변경을 숨기면 안 된다.

필요한 계약은 다음이다.

\[
v_1=v_2,\ E_1=E_2,\ t_1=t_2
\Longrightarrow
f_{s,v_1}(E_1,t_1)=f_{s,v_2}(E_2,t_2).
\]

내용 hash는 실용적인 동결 확인 수단이며, 위 명제는 의미 namespace가 올바르게 관리된다는 가정을 요구한다. 이번 실험의 namespace label 교체는 cache 분리 검사다. 실제 파서 배포 버전을 바꿨다는 실험으로 보고하지 않는다. 반환 의미까지 바뀌는 버전 반례는 별도 시험용 순수 함수로 검사할 수 있다.

각 stage는 허용 입력에서 결정적이고 순수해야 한다. 여기에는 상태, 시간, 난수, 외부 모델 응답 등에 따라 결과가 바뀌지 않는다는 조건이 포함된다. 원래 단계가 실패하는 입력에 대해 이번 정리가 새로운 정상 결과를 보장하지 않는다. 예외를 임의의 unknown으로 바꾸거나 오류를 숨기지 않는다. 비교는 같은 순수 함수의 정상 실행 영역 및 명시한 integrity 실패 경로에서 수행한다.

## 3. 질문마다 다시 계산하는 부분

cross-query cache가 저장하는 것은 순수 단계의 결과뿐이다. 다음은 매 질문 현재 입력에서 다시 계산한다.

- 기록 순서·범위·snapshot 검증.
- 질문의 요구 필드와 역방향 demand.
- scope가 현재 demand와 만나는지, detail 단계를 요청할지 여부.
- query-local `scoped_top`, 선택 인덱스, 남은 demand.
- 사건 당시의 상태와 copy source의 값.
- 현재 기록 index를 포함한 `scope_trace`.
- 최종 판정·prediction·원문 렌더링.

기존 query-local `cache[index]`는 한 질의 안에서 사용한다. 이 cache의 최종 event를 그대로 persistent cache로 승격하지 않는다. persistent cache는 그 아래 세 순수 함수의 결과를 단계별 슬롯에 저장한다.

이미 detail 결과가 존재해도 현재 알고리즘이 detail을 요청하지 않았다면 그것을 미리 꺼내 추론 경로를 바꾸지 않는다. 반대로 현재 알고리즘이 detail을 요청하면, 물리적 계산이 cache hit로 생략되더라도 논리적 detail 요청은 발생한 것이다.

따라서 `scope_trace.detail_avoided`는 기존처럼 scope와 demand의 비관련성 때문에 detail을 요청하지 않았는지를 나타낸다. `detail_avoided`를 cache hit 표시로 바꾸지 않는다. Cache의 hit·miss·stage 재사용은 별도 계측이다.

현재 phase06과 같은 검증 순서를 유지한다. 순서나 범위 오류가 먼저 발견되면 원래처럼 hash 이전에 `integrity_failure`를 반환할 수 있다. 순서 검사를 통과한 snapshot은 기존과 동일하게 전체 내용을 해시로 검증한다. Cache는 이 검증을 대신하거나 이전 검증 성공을 재사용하지 않는다. 미지원 질문과 invalid snapshot에서 기존에 없었던 파서 호출로 cache를 미리 채우지 않는다.

## 4. Immutable stage 값

원래 event의 dict와 `targets` list를 그대로 공유하면 caller의 mutation이 다음 질문에 영향을 줄 수 있다. 이번 계약은 저장값을 immutable 표현으로 만든다. 이 변환을 `freeze_s`, 의미상 복원을 `decode_s`라고 쓰면 다음을 요구한다.

\[
decode_s(freeze_s(y))=y.
\]

실제로 hit마다 JSON decode나 deep copy를 할 필요는 없다. 소비자가 immutable 값에 대해 같은 연산을 수행할 수 있으면 된다. 다만 target/source, 값, targets의 순서·중복, `None`과 빈 목록, scope의 전역 marker와 빈 scope 등 구분이 필요한 정보는 보존해야 한다. 실제 consumer가 관찰하는 동작도 원래 값과 같아야 한다.

단계별 슬롯에서 “아직 계산하지 않음”과 “계산 결과가 unknown”을 별도로 표현한다. 특히 cheap의 `havoc`가 detail의 계산 완료를 뜻하지 않으며, scope에서 `None`을 얻었다고 detail을 수행한 것도 아니다.

## 5. Cross-query 실행 동등성 정리

### 전제

1. 단계 함수와 의미 namespace는 §1–2의 조건을 만족한다.
2. 정확한 원문·ordered entities·context 동등성을 확인한다.
3. stage별 슬롯은 분리되며 immutable 저장·사용이 원래 반환 의미를 보존한다.
4. hit/miss는 현재 알고리즘의 논리적 stage 요청 조건을 바꾸지 않는다.
5. 현재 snapshot 검증, query-local 분석, 상태 실행, trace와 렌더링은 그대로다.
6. cache는 단일 스레드에서 결정적 순서로 사용한다. 동시 사용의 경합·중복 계산·LRU interleaving은 이번 계약 밖이다.

cache 상태의 불변식은 저장된 모든 슬롯에 대해

\[
decode_s(cache[v,E,t][s])=f_{s,v}(E,t)
\]

가 성립한다는 것이다. 첫 cache는 비어 있으므로 자명하다. miss에서 실제 순수 결과만 넣으면 유지되고, eviction은 올바른 항목을 삭제할 뿐이므로 유지된다.

**정리 M1.** 임의의 허용된 질의·이력 변경 stream에서 memoized 실행은 같은 입력으로 수정하지 않은 phase06 `text_scoped`를 다시 실행한 결과와 다음 관찰이 같다.

```text
status / integrity failure reason
prediction
selected
remaining_input_facts
rendered UTF-8 output
scope_trace
```

**증명.** 각 질의의 논리적 실행 단계에 대해 귀납한다. snapshot 검증과 초기 query 처리는 같으므로 같은 지점에서 시작한다. 순수 단계 요청에서 miss이면 같은 함수를 계산하고, hit이면 cache 불변식에 의해 같은 반환 의미를 얻는다. 그러므로 해당 지점의 분기, demand, 선택, 다음 요청과 trace가 같다. 이 불변식을 끝까지 적용하면 상태 실행과 최종 렌더도 같다. 질의가 끝나도 cache 불변식이 유지되므로 다음 질의에도 반복할 수 있다. □

한 기록의 여러 stage가 하나의 entry를 공유해도 슬롯 식별자가 분리되어 있으므로 같은 증명이 적용된다. 용량 0, 작은 용량, eviction, oversized entry의 비보관도 hit/miss만 바꾸므로 의미에는 영향을 주지 않는다.

렌더링은 기존 phase06 header와 출처 표기를 포함한다. Phase 07 표시를 prompt header에 새로 넣으면 문자열 정확동등이라는 계약이 달라진다. 최종 출력의 길이만 같은지보다 UTF-8 내용 또는 그 정확한 동등성을 검사해야 한다. 비용 계측과 local time은 의도적으로 달라질 수 있으므로 이 의미 동등성 목록에 포함하지 않는다.

## 6. 작은 반례와 검사 범위

### 6.1 실제 동결 문법: stage 혼동

```text
가람 약속, 최종 시각은 11시로 적어둘게.
```

이 원문에 대해 cheap는 `havoc`, detail은 `set(가람.time,11)`이다. stage 구분 없는 저장소에서 cheap 결과를 detail 결과로 반환하면 원래의 단일 값 판정이 fallback으로 바뀐다. record key를 공유하되 stage 슬롯을 분리해야 하는 이유다.

### 6.2 실제 동결 문법: 동일 ID의 원문 수정

```text
id=r, text=가람 모임 시간은 10시로 확정해줘.
→ 같은 id=r, text=가람 모임 시간은 11시로 확정해줘.
```

snapshot까지 새로 갱신한 정상 입력에서 ID만으로 재사용하면 틀린 10을 남길 수 있다. 정확 원문 key에서는 11의 해석이 새 요청이다. 과거 기록을 수정해도 원문에 대한 순수 결과가 잘못 재사용되지 않는다.

### 6.3 엔터티 환경과 버전

어떤 이름이 roster에 없을 때의 `havoc`는 그 이름을 추가한 roster에서의 결과와 다를 수 있다. 반대 방향의 변경도 가능하다. 엔터티 목록을 key에서 빼면 답변 범위나 결과를 바꿀 수 있다.

version을 key에서 빼면 새 parser가 고친 해석 또는 새로 지원한 해석에 오래된 결과를 적용할 수 있다. namespace만 교체하는 현재 검사는 실제 의미 변경과 구분한다. 의미 변경 자체의 반례는 이전 순수 함수와 수정 순수 함수를 나란히 둔 별도 검사다.

### 6.4 순서와 copy 값

`A=10; A=11`과 `A=11; A=10`은 마지막 값이 다르다. 각 문장의 순수 AST를 재사용하는 것은 안전하지만 답까지 재사용하면 안 된다. 또한 같은 `B=A` 문장도 앞선 A 변경에 따라 다른 역사적 값을 복사한다. Cache에는 `copy(B,A)`만 저장하고 source 값은 현재 실행에서 읽어야 한다.

### 6.5 query-local TOP의 범용 반례와 현재 문법의 경계

시험용 순수 함수에서 어떤 원문 r이 다음 계약을 가진다고 하자.

```text
cheap(r) = unknown
scope(r) = {A.time}
detail(r) = set(A.time,11)
```

첫 질문이 B이면 r의 detail을 건너뛰어 query-local TOP을 만들 수 있다. 다음 질문이 A이면 detail을 요청하여 11을 알아야 한다. 첫 질의의 TOP을 persistent 결과로 저장하면 다음 질의의 답변 범위를 잃는다. 순수 stage 결과만 보관하면 이런 문제가 없다.

**현재 동결 phase06 raw-only 문법에서는 6개 scope whitelist와 detail 문법이 서로 겹치지 않는다.** 따라서 위 상황을 현재 `text_scoped`의 실제 관측 결함으로 보고하지 않는다. 그것은 scope와 detail이 겹치는 시험용 순수 함수의 conformance 반례 또는 oracle scope 조건의 반례다. Oracle를 사용한 검사를 raw-only 품질 개선·실패로 합치지 않는다.

### 6.6 값 mutation과 실패한 snapshot

반환된 event의 `targets`를 바꿀 수 있고 그 객체가 cache와 공유된다면 다음 해석을 오염시킬 수 있다. Immutable 값 검사는 이런 alias를 차단하는지를 확인한다. 현재 소비자가 실제로 mutation을 수행한다는 관측과는 구분한다.

과거 cache가 충분히 채워졌더라도 수정·삭제·재정렬 후 snapshot이 맞지 않으면 원래와 같은 integrity 실패를 반환해야 한다. Cached AST가 있다고 현재 archive 검증을 생략할 수 없다.

## 7. Bounded LRU와 amortization

사전 용량은 64 entries와 65,536 logical serialized bytes다. 한도 밖 항목은 보관하지 않는다. stage 슬롯 추가로 항목 크기가 늘어날 때도 같은 한도를 적용한다. 두 제한을 만족하도록 결정적인 LRU 순서로 제거한다. 이는 retained key·stage payload의 논리적 크기를 제한하며 CPython allocator, 객체 header, 임시 문자열, 전체 기록 등의 RSS 상한은 아니다.

전체 stream의 논리적 stage 요청을 j=1,…,L, 원래 stage 계산 비용을 c_j, miss 집합을 M이라고 쓰면

\[
C_{fresh}=C_{common}+\sum_{j=1}^{L}c_j,
\]

\[
C_{memo}=C_{common}+\sum_{j\in M}c_j
+C_{key/lookup}+C_{immutable}+C_{LRU}.
\]

`C_common`에는 매 질문의 snapshot 검증, 순회, demand·상태 실행과 출력이 남는다. 실제 backend 실행 감소만으로 전체 비용 감소를 결론낼 수 없다.

용량이 모든 필요한 record key와 stage 슬롯을 보관할 만큼 충분하고 의미 context가 고정되면 각 고유 stage key는 최초 한 번만 계산하면 된다. 유한 LRU에서는 이 보장이 없다. working set이 용량을 넘고 순환하면 반복 stream이어도 hit가 거의 없고 bookkeeping만 늘 수 있다. `reset`은 질의 안의 중복 원문 재사용, `lru`는 그 효과에 질문 사이의 재사용을 더한다. `disabled`는 용량 0의 같은 새 경로여서 key·관리 비용 자체를 분리한다.

entry hit와 stage 재사용도 다르다. 이미 존재하는 entry라도 요청한 stage 슬롯이 없으면 그 순수 함수는 실행해야 한다. 성공 판정에는 실제 cheap/scope/detail 실행 감소를 사용하며 hit 숫자만 쓰지 않는다.

## 8. 사전 byte-work proxy의 구조적 제약

프로토콜은 다음의 동일 가중 logical traffic을 정의한다.

\[
P7=output+hash+parser\_source+key\_build+key\_probe
+value\_encode+cache\_read\_payload+cache\_write.
\]

이것은 실제 메모리 버스 바이트나 LLM 비용이 아니다. immutable 객체를 반환하더라도 재사용한 payload의 canonical 길이를 계산한다. Miss에서 payload 크기를 계산하는 encoding은 비활성/oversized cache에서도 value_encode로 계상한다. 완전 warm hit에서는 이 항이 0이므로 아래 식은 그대로다. LRU·hash table·immutable 변환 등의 CPU 비용은 별도 local wall time에 포함한다.

한 방문 기록의 raw UTF-8 길이를 L_t, context의 canonical 길이를 C, 원래 요청하는 stage 수를 m∈{1,2,3}, 완전 warm hit에서 읽는 payload 길이 합을 R이라 하자. 한 기록에서 key 준비와 entry probe를 각각 한 번 공유하고 그 모든 stage가 hit이면, 이 기록의 fresh 대비 proxy 차이는 질의당 context 생성비를 제외하고

\[
\Delta P7=(2-m)L_t+C+R.
\]

원래 parser source는 mL_t이고, warm reuse에서는 parser 실행을 하지 않지만 text key 생성 L_t, 전체 context+text probe C+L_t, payload read R을 지불하기 때문이다. 이 식은 프로토콜의 비용 정의와 동일한 방문·stage 요청 조건 아래의 계산이다.

- m=1인 cheap-only 기록은 완전 warm 상태에서도 이 proxy에서 손해다.
- m=2인 cheap+scope 기록도 context와 payload 비용 때문에 이 proxy에서 이득이 나지 않는다.
- m=3인 기록에서는 L_t>C+R일 때만 개선 여지가 있다. 질의당 context 생성비와 cold 구축·eviction 비용까지 회수해야 stream 전체에서도 이득이다.

매 stage마다 key를 새로 만들고 전체 probe까지 다시 계상하면 warm key traffic만 최소 2mL_t가 되어, 저장한 parser source mL_t를 넘는다. 이 비용 정의에서는 그런 구현의 proxy 개선이 구조적으로 불가능하다. 그래서 record당 공유를 선택했다. 실제 코드에서도 entry lookup을 한 번 공유하지 않고 여러 번 전체 key를 probe한다면 그 실제 논리 요청을 비용에 반영해야 한다.

이 결론은 **사전 proxy의 대수적 제약**이며 실제 CPU 시간의 정보이론적 하한이 아니다. 파서의 CPU 상수가 크면 proxy가 나빠져도 실행 시간은 좋아질 수 있고, 키 인코딩·LRU 관리가 비싸면 실제 시간도 나빠질 수 있다. 두 결과를 따로 보고한다. Cache miss에서는 원래 parser source에 key·write 비용이 더해지므로 초기 구축 비용을 warm 결과에서 숨기면 안 된다.

## 9. 반복 질문에서도 전체 archive 비용은 남는다

질의 q의 전체 snapshot 바이트를 B_q라고 하면 현재처럼 매번 전체 hash를 검증하는 유효 입력 stream에서는 적어도 \(\sum_q\Theta(B_q)\)의 직렬화·hash 작업이 남는다. 원문 접근을 완전히 없앤다는 주장은 불가능하다. 같은 snapshot의 사전 검증 또는 인증된 incremental index를 재사용하는 연구는 별도 계약이며 이번에는 구현하지 않는다.

반복 질의에서 순수 해석 miss가 충분히 줄어도 출력은 정확동등하다. 따라서 이번 연구는 출력 바이트 감소, 실제 LLM 입력 토큰 감소, 자연어 답변 품질 개선, 운영 배포 성능 개선을 주장하지 않는다. 가능한 성과는 고정 분석기의 반복 순수 계산을 줄이고, 그 이득이 사전 전체 비용 모형과 로컬 시간에서 어디까지 남는지 확인하는 것이다.

## 10. 검증의 역할과 남는 한계

H7-S는 위 전제 아래의 일반 동등성 명제이며 실험은 그 구현을 검사한다. H7-P는 실제 stage 실행이 줄었는지, H7-C는 사전 proxy가 줄었는지, H7-T는 cold 시작과 cache 관리를 포함한 실행 시간이 줄었는지 각각 따로 판정한다.

회귀 자료와 같은 모델의 별도 작성 stream은 외부 독립 의미 평가가 아니다. roster 규약이 달라 gold 의미를 정의하지 않은 조건과 invalid snapshot은 실제 답 정확성 분모에 섞지 않는다. 그 경우에도 기존 실행과의 동등성·무결성 동작을 검사한다.

이 정리는 원래 phase06의 해석 정확도를 높이지 않는다. 기존의 불확실성, 지원하지 않는 질문, snapshot 최신성 경계, standalone prompt 의미 검증의 부재도 그대로다. 틀린 원래 해석을 정확히 재사용하는 것은 같은 오류를 재현할 뿐이다. 캐시가 올바른가와 원래 의미 분석기가 올바른가는 분리된 연구 질문이다.

이 문서를 준비하며 `PROTOCOL.md`, phase06 `scoped.py`의 순수 scope 함수·실행 경로, phase05r2 `engine.py`의 parser·query 문법을 읽었다. Phase 07 holdout의 파일·개별 사례·라벨·실행 결과는 읽지 않았다.
