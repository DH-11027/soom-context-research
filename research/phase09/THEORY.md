# Phase09 이론 — 정책 상태를 보존하는 계측 제거

동결 전 작성. 기준은 Phase08 공개 완료 commit
`efba3224dd09d5c5e2bf9d9be11734fa10b32502`다. 이 문서는 새 평가 자료나
실행시간 결과를 전제하지 않는다. Phase08의 의미 선택기·보관 정책·상수·용량은
고정한다. 연구 질문은 계측을 제거한 두 경로의 실제 전체 시간 비교다.

## 1. 두 종류의 동등성

최종 답이 같다는 조건은 동일 정책이라는 조건보다 약하다. 예를 들어 cache의
hit 수를 지워도 현재 답은 같을 수 있지만 다음 admission의 victim이 달라진다.
그러므로 Phase09는 각 방법 내부의 계측판과 비계측판 사이에 **관찰과 정책 상태**를
함께 보존하도록 요구한다. Fresh와 selective 사이에는 관찰만 같아야 하며,
두 방법의 cache 상태까지 같다는 요구를 하지는 않는다.

현재 공개 입력은

\[
x_t=(records_t,E_t,query_t,snapshot_t,namespace_t)
\]

다. `E_t`의 순서는 보존하고, 원문을 정규화하지 않는다. 입력 prefix는
`x_1,...,x_t`다. Gold, family, 미래 반복, 미래 종료 시각은 실행 함수의 입력이 아니다.

### 관찰 `Obs`

한 질문의 관찰은 다음 값들의 정확한 내용이다.

```text
status
reason (존재 여부도 보존)
prediction
selected (순서 포함)
remaining_input_facts (존재 여부도 보존)
scope_trace
output_bytes
rendered evidence의 정확한 UTF-8 bytes
```

무결성 거절의 rendered evidence는 빈 bytes이며, 미지원 질문은 기존 전체 이력
렌더를 사용한다. Bytes 길이나 digest만 같다는 것을 본문 동일성의 정의로 삼지 않는다.
Prefix의 관찰은 각 질문 관찰의 순서 있는 열이다. 계측 `cost`, event log,
타이머, 메모리 주소, 객체 identity, 물리 메모리 사용량, 실제 시간은 제외한다.
이 중 실제 시간은 바로 별도 실험의 종속 변수다.

### 정책 상태 투영 `π`

Selective의 질문 사이 상태는 다음으로 정의한다.

\[
P=(cfg,M,D,B,o).
\]

- `cfg`: directory 활성 여부, max_entries, max_bytes 및 동결된 의미 fingerprint,
  `MIN_CHARS=256`, `HIT_CAP=255`, `META_BYTES=80`, `ACTION_WEIGHT=8`, `WARM_ACTIONS=8`.
- `M`: dict의 resident 삽입 순서를 보존한 exact key–entry 열. Key는 context bytes와
  raw UTF-8 bytes 전체다. Entry는 immutable cheap/contract/detail 값과 각 encoded
  길이, `size`, `characters`, `surplus`, `hits`, `order`를 포함한다.
- `D`: resident 문자 길이별 정확한 개수인 `lengths` directory.
- `B`: `retained_bytes`. 실제 entry size 합과 같아야 한다.
- `o`: 다음 삽입 순서를 정하는 `next_order`.

`π`는 계측판에서 위 상태를 남기고 per-query ledger, control events,
`peak_bytes`, `peak_entries`, 타이머 및 보고용 복사본만 지운다. Peak는 현재
보관량과 다르다. 삭제 가능한 것은 peak이며 `retained_bytes`는 삭제할 수 없다.
Directory의 내부 iteration 순서는 현재 정책에서 읽지 않지만 resident 순서는
보존한다. Entry의 `order`와 `next_order`도 다음 tie 처리의 입력이므로 남긴다.

Fresh에는 질문을 넘는 cache가 없어 persistent policy state는 빈 상태다.
질문 내부의 의미 event cache, demand와 abstract state는 계산 중 유지된다.
정리는 이 local state까지 대응시킨 뒤 질문 경계에서 위 `π`를 취한다.

요구하는 계약은 모든 유효한 실행 prefix에 대해

\[
\begin{aligned}
Obs(Run_{on}(x_{1:t}))&=Obs(Run_{off}(x_{1:t})),\\
\pi(S^{on}_t)&=S^{off}_t.
\end{aligned}
\]

이다. On/off가 final answer만 공유하고 resident 집합이나 hit 수가 다르면 실패다.

## 2. 입력·실행 가정과 예외의 경계

아래 정리는 다음 조건부 명제다.

1. Public 입력은 schema에 맞는 builtin JSON형의 유한 값이다. Entities, query,
   namespace와 text는 UTF-8로 표현 가능한 builtin 문자열이다. Record seq/head는
   코드가 기대하는 정수다. Snapshot이 틀린 경우와 미지원 질문은 허용한다.
2. 입력과 의미 함수·encoder·정책 상수는 한 실행 중 외부에서 변하지 않는다.
   순수 단계는 현재 text, ordered entities, 동결된 의미 코드에만 의존한다.
3. 실행은 단일 스레드이고 cache는 해당 실행이 빈 상태에서 만든 도달 가능한
   상태다. 외부 코드가 entry, hit, directory를 직접 변조하지 않는다.
4. 충분한 자원이 있어 두 경로가 정상 계산을 완료한다. MemoryError,
   프로세스 종료, signal 중단, 임의 tracing hook이나 finalizer의 관측 효과,
   사용자가 교체한 dict/int/str 연산은 모델에 넣지 않는다.
5. 지원 schema 밖의 임의 Python 객체, 임의 parser 예외의 동일 traceback,
   발생 시각, allocation/GC 행태는 계약하지 않는다.

무결성 실패는 자원 예외가 아니라 정상적인 반환 상태이므로 반드시 보존한다.
`record_gap_or_order`가 hash보다 앞서는 순서와, 정상 seq에서 전체 직렬화 후
digest를 비교하는 순서도 유지한다. 미지원 query의 early exit 전에는 snapshot
검증을 수행하고, early exit에서는 cache를 채우거나 hit를 갱신하지 않는다.

Fresh의 통계용 raw encode 삭제는 모든 임의 Python 문자열에서 예외가 같다는
주장이 아니다. 계약 안에서는 문자열이 UTF-8 encodable이며, 정상 seq의 record는
먼저 `json.dumps(..., ensure_ascii=False).encode('utf-8')`로 전체 검증된다.
새로운 의미 분기나 예외 처리에 그 통계용 길이가 쓰이지 않는다.

## 3. 데이터 의존성으로 분류한 계산

이 분류는 이름에 `count`나 `bytes`가 들어가는지로 정하지 않는다. 값에서
관찰 또는 다음 정책 결정으로 이어지는 데이터·제어 의존성이 있는지가 기준이다.

| 계산·상태 | 실제 사용처 | Phase09 처리 |
|---|---|---|
| `cost[...] += ...`, control event dict | 반환 cost 및 보고 합계 | 제거 가능 |
| `records_visited`, requests/calls/reused | 장부 | 제거 가능 |
| `perf_counter`, local_seconds | 시간 보고 | 내부 측정 제거; 외부 주 타이머 사용 |
| `phase07_work_proxy`, `phase08_work_score` | 보고 | 제거 가능 |
| `peak_bytes`, `peak_entries` | 최대값 보고 | 제거 가능 |
| Fresh 방문별 `len(text.encode('utf-8'))` | parser_source 장부 | encode와 size 모두 제거 가능 |
| 전체 snapshot JSON·UTF-8·SHA256 | 검증의 분기 | 유지 |
| 근거 렌더 및 그 UTF-8 표현 | 동일 결과물의 생성 | 유지 |
| Selective context encode | exact key, C, b, e | 유지 |
| Selective raw UTF-8와 길이 L | exact key, b, e | 필요한 실행 경로에서 유지 |
| 실제 payload encode와 길이 R | b, e, 보관 크기·축출 | 유지 |
| Immutable stage 변환 | 저장값 불변식 | 유지 |
| `hits=min(255,hits+1)` | victim weight `(hits+1)*surplus` | 유지 |
| `surplus`, size, retained_bytes | admission·용량·교체 | 유지 |
| `lengths`, 삽입/삭제·next_order | lookup 생략·동점 교체 | 유지 |
| victim 정렬·정수 교차곱·계획 | 축출 대상과 admission | 유지 |
| 현재 demand·copy·상태 실행·trace | 현재 관찰 | 유지 |

P8의 `ACTION_WEIGHT*WARM_ACTIONS=64`는 이름이 계측을 연상시키지만 실제
surplus 식의 고정 상수다. `control_actions`를 지워도 이 64를 지우지 않는다.

이번 구현은 selective에서 매 방문의 eager raw encode를 그대로 남긴다.
해당 raw가 향후 key/admission에 쓰이지 않는 분기에서도 옮기지 않았다.
이는 source AST에서 명시적 계측 문장을 삭제하는 보수적인 정책 보존 구현이다.
Fresh가 raw encode를 완전히 지우고 selective는 필요한 encode를 남기는
비대칭을 숨기지 않는다. 동일 관찰·정책은 동일한 CPU 작업량을 뜻하지 않는다.

## 4. 보조정리와 보존 증명

### 보조정리 E1: 장부의 비간섭

Phase08 `runtime.py` 및 fresh의 고정 Phase06/07 wrapper에서, selective의
`cost` 값은 정책 또는 의미 분기의 피연산자로 읽히지 않는다. 쓰인 장부를
다시 읽는 곳은 장부 합산·event 갱신·보고 구성이다. `peak_*`도 보고 경로에서만
읽힌다. 이 경로들은 보존할 상태나 의미 값에 다시 값을 쓰지 않는다.

따라서 해당 문장들만 지우면 나머지 값의 평가 순서와 값은 같다. 장부의
`setdefault`, 덧셈, timer 호출은 가정 4 아래 관찰되지 않는 stuttering step이다.
자원 실패를 포함하면 지워진 할당이 MemoryError를 피할 수 있어 이 정리의
전제가 없어지므로 전체 Python의 예외 동등성으로 확대하지 않는다. □

### 보조정리 E2: fresh의 통계용 encode 제거

Phase06 `run(...,'text_scoped')`의 `read()`에서 `size`의 모든 사용은
cheap/contract/detail source-byte 장부 갱신이다. 파서에는 원래 `text`가,
scope에는 `text,entities`가 전달되며 demand·상태·렌더는 `size`를 읽지 않는다.
E1에 따라 장부를 지우면 `size`는 죽은 값이다. 가정 1과 4 아래 encode와
len을 함께 지워도 관찰 및 local 의미 상태가 같다. 전체 snapshot encode와
렌더 encode에는 별도의 살아 있는 사용처가 있으므로 이 결론이 적용되지 않는다. □

### 보조정리 E3: selective 정책 전이의 결정성

같은 `π(S)`와 같은 현재 입력에서 길이 gate와 directory의 값은 같다.
Directory 양성에서 context/raw exact key는 같으므로 get의 hit/miss와 포화 hit
갱신도 같다. Miss에서 같은 자연 단계만 요청하고 같은 순수 결과를 얻는다.
후보이면 같은 encode에 의해 C,L,R가 같고

\[
b=L-C-R-64,\qquad e=C+L+R+80
\]

도 같다. 각 resident의 weight `w=(h+1)b`와 integer density 비교,
insertion-order tie도 같아 같은 victim prefix를 계획한다. 따라서
`b_new > sum(w_victim)`의 진위와 삽입·삭제·directory·retained·next_order
갱신도 같다. E1의 장부는 어느 피연산자에도 들어가지 않는다. □

### 정리 E9: 계측 제거의 prefix 보존

위 가정 아래, E1/E2의 삭제만 수행하고 E3의 실제 계산을 유지한 비계측판은
fresh와 selective 각각에서 §1의 두 동등식을 모든 유한 prefix에 만족한다.

**증명.** 빈 cache 또는 fresh의 빈 persistent state에서 성립한다.
prefix t−1까지 성립한다고 하자. 다음 질문의 snapshot과 query 처리는 같은
데이터·순서로 실행되므로 같은 early exit 또는 같은 requested facts를 만든다.
정상 선택 루프는 같은 demand에서 시작한다. 각 방문은 fresh의 경우 E2에
따라, selective의 경우 E3에 따라 같은 단계값과 같은 정책 전이를 얻는다.
그러므로 writes/preimage, 다음 방문 여부, selected, abstract 실행, 현재 copy,
status, prediction, trace, evidence render가 같다. 질문 종료 후 E3가 같은
정책 상태를 남긴다. E1의 추가 장부 step은 상태 투영을 바꾸지 않는다.
따라서 t에서 성립하고 귀납법으로 모든 유한 prefix에서 성립한다. □

이는 소스별 수학적 검토이며 Python 인터프리터 전체를 proof assistant로
정형 검증했다는 뜻이 아니다. 실행 감사는 각 prefix에서 실제 구현이 이
삭제 규칙을 따랐는지 보완 확인한다. 새 평가의 오류 0만으로 정리가 증명되는
것도 아니며, 정리만으로 잘못 구현된 비계측 코드가 자동으로 옳아지는 것도 아니다.

`erase.py`는 검토한 두 source의 특정 함수/class AST만 골라 장부·내부 타이머·
peak를 삭제하고 fresh의 죽은 size 계산을 지운다. 생성은 timing 이전에 끝나며,
`off_fresh.py`와 `off_selective.py`는 정적 소스다. `--check`는 생성 결과와
`erasure_manifest.json`의 정확한 bytes를 확인한다. Manifest는 원본 문장과
source/output SHA-256을 남긴다. 이 transformer는 임의 프로그램의 계측을
안전하게 지우는 범용 정리가 아니다. `off_fresh.run`의 보존 범위는 호출자가
고정한 `method='text_scoped'`이며, 남아 있는 다른 method branch는 Phase09의
주 실행·증명·성능 계약에 포함되지 않는다.

### 따름정리: frozen fresh와의 의미 관찰 연결

Phase08의 S8 조건부 순수 재사용 보존 전제가 추가로 성립하면

\[
Obs(F_{off})=Obs(F_{on})=Obs(S_{on})=Obs(S_{off}).
\]

단, `π(S_on)=S_off`는 selective 안의 정책 상태 등식이다. Fresh와 selective의
cache 상태가 같다는 결론은 아니다. 기존 파서의 실제 자연어 의미 정확성,
미완료 요청·실행 증거의 일반 보존, LLM 품질까지는 이 따름정리의 범위가 아니다.

## 5. 작은 반례: 답이 같아도 지우면 안 되는 계수

고정 Phase08 runtime에 서로 다른 deep noop A,B,C를 각각 UTF-8
20,000 / 30,000 / 21,000 bytes로 만들어 `A → B → A → C`로 요청했다.
Entities는 `['가람','누리']`, namespace는 `v1`이고 매 질문 같은 초기 set
기록과 query를 사용했다. 실제 context 길이 C=93, payload R=154였다.

| 항목 | b=L−311 | e=L+327 | 네 번째 요청 직전 정상 h |
|---|---:|---:|---:|
| A | 19,689 | 20,327 | 1 |
| B | 29,689 | 30,327 | 0 |
| 새 C | 20,689 | 21,327 | 후보 0 |

A와 B는 함께 들어가지만 C까지는 못 들어간다. 정상은 A의 weight가 39,378로
증가해 B를 victim 후보로 고른다. 새 C의 20,689는 B의 29,689보다 작아 거절한다.
`hits`를 잘못 지운 mutant는 A의 weight를 19,689로 취급해 A를 먼저 고르고,
20,689>19,689이므로 A를 축출하고 C를 넣는다.

네 질문의 의미 결과는 모두 같았다. 그러나 마지막 resident는 정상 `[A,B]`,
mutant `[B,C]`다. 현재 final answer 감사만으로는 이 실패를 놓친다. 이 수치는
개발 반례의 직접 실행이며 새 holdout 성능 표본도 CPU 측정도 아니다.
최초 직접 실험은 네 번째 요청 직전에 hit를 0으로 되돌렸다.
보존한 [counterexamples.py](counterexamples.py)는 hit 갱신 자체를 생략하는
동일 결함 mutant를 사용하므로 정책 상태 차이를 이미 세 번째 질문에서 찾고,
네 번째 질문에서 resident 집합 차이를 찾는다. 실제 비계측판은 매 prefix에서
원본 계측판과 관찰·정책 상태가 같다. 코드와 결과는 함께 보존했다.

그 밖의 직접적인 반례도 남는다.

- `retained_bytes`를 peak처럼 지우면 개별 적합한 두 항목을 함께 넣어 총 용량을
  넘길 수 있다. 개별 size 한도는 동시 보관 한도가 아니다.
- Payload encode를 없애 R=0으로 대체하면 b와 e가 모두 바뀐다. 예를 들어
  L=400,C=100,R=250이면 실제 b=−14로 거절하지만 대체값에서는 b=236으로
  통과한다. 이는 상태 산술 반례이며 현재 문법에서 이 정확 tuple을 생성했다는
  주장은 하지 않는다.
- `ACTION_WEIGHT*WARM_ACTIONS`를 장부와 함께 지우면 b가 64 증가해 admission
  임계점이 달라진다. 계측 명칭이 붙은 상수도 정책 의존성이 있으면 살아 있다.
- 같은 문자 길이의 서로 다른 원문 또는 같은 원문의 다른 ordered entities나
  namespace는 exact hit가 아니다. 길이 양성을 equality로 대체할 수 없다.

## 6. 시간에 대해 증명할 수 없는 것과 할 수 있는 산술

E9는 시간을 관찰에서 제외하므로 어떤 시간 대소도 따라오지 않는다.
계측 삭제는 할당·GC·분기·CPU cache locality와 상호작용한다. On/off 차이는
변경 전체의 관측된 효과이지 event 기록 한 부품의 정확한 CPU 비용이 아니다.

같은 정의의 네 시간 집계값을 `F_on,F_off,S_on,S_off`라 하고

\[
d_F=F_{on}-F_{off},\qquad d_S=S_{on}-S_{off}
\]

라 정의하면 단순 항등식

\[
S_{off}-F_{off}=(S_{on}-F_{on})-(d_S-d_F)
\]

을 얻는다. 따라서 selective의 계측 제거 후 시간이 줄었다는 사실만으로
fresh_off보다 빠르다고 할 수 없다. 기존 격차를 뒤집으려면 `d_S-d_F`가
기존 격차보다 커야 한다. 여기서 d는 동일한 집계 규약의 관측값 차이이지
독립적인 코드 부품의 시간으로 해석하지 않는다.

상대 제거 비율을 `r_F=1−F_off/F_on`, `r_S=1−S_off/S_on`이라 놓으면

\[
\frac{S_{off}}{F_{off}}=
\frac{S_{on}}{F_{on}}\frac{1-r_S}{1-r_F}.
\]

주 가설의 직접 비교는 언제나 왼쪽이다. `S_off/F_on`을 주 성과로 쓰면
fresh에서 제거 가능한 작업을 남겨 둔 비대칭 비교가 된다.

## 7. Phase08 경계의 유지

Phase09는 다음을 정책 변경으로 해결하지 않는다.

1. 양의 최초 cache 투자 직후 종료하는 stream은 미래 절약이 없다. 모든 유한
   stream에서 fresh 이하라는 보장은 기존 투자 모형에서 여전히 불가능하다.
2. Cheap를 먼저 지불한 뒤 남은 두 stage만 재사용하는 전략의
   `ΔP7≥C+R>0` 경계는 기존 P7 장부의 명제다. 비계측 CPU 시간의 하한이 아니다.
3. 이미 큰 surplus/hit를 가진 resident가 작은 새 인기 후보를 계속 거절하는
   과거 인기 고착은 동일 정책에서 그대로 남는다.
4. 같은 길이는 같은 exact key가 아니다.
5. 각 entry가 단독으로 맞아도 동시 working set은 65,536을 넘을 수 있다.
6. D8은 selective와 no_directory의 논리 작업점수 관계다. Fresh 대비 또는
   wall-clock CPU 시간 관계가 아니다.

새 이득이 관측되어도 이 경계가 사라졌다고 말하지 않는다. 실제 시간의 방향은
동결한 새 합성 자료·고정 환경의 실험 명제로 남긴다. SOOM 운영 변경은 없다.
