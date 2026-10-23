# Phase09 실행 전 계획 — 정책을 보존하는 계측 제거와 실제 시간

작성일: 2026-10-23 KST. 직접 기준은 Phase08 공개 완료 commit
`efba3224dd09d5c5e2bf9d9be11734fa10b32502`이다. 모든 새 작업은
`research/phase09/`에 있으며 SOOM 운영 변경은 없다. 새 자료의 원문·gold·builder를
주 구현자가 열기 전에 이 문서·실행 코드·자료 hash를 로컬 commit으로 동결한다.
로컬 동결은 외부 사전 등록이 아니며, GitHub 공개는 평가 이후다.

## 1. 선택한 한 질문과 반박 가능한 판정

Phase08은 P8 점수를 줄였지만 두 시간 관측에서 느렸다. 시작 재현에서도 선택 경로가
느렸고, directory 유무의 시간 순서는 다시 바뀌었다. 장부를 실제 CPU로 환산할 근거가
없으므로 정책을 다시 조정하기보다 동일 정책의 계측 의존성을 먼저 확인한다.
자연어 의미 일반화도 중요한 미해결 문제지만 이 단계에서는 동시에 추진하지 않는다.

**H9:** 동일 의미 관찰·전체 snapshot 검증·정책 상태를 보존하는 보수적 계측 제거 후,
고정한 새 합성 workload에서 `selective_uninstrumented`가
`fresh_uninstrumented`보다 cold 비용을 포함한 전체 실행시간을 실질적으로 줄인다.

실질적 차이는 사전에 **5%**로 정한다. 주 추정량은 동일 block의 전체 workload 시간 비율
`T(selective_off)/T(fresh_off)` 24개의 중앙값이다. 10,000회 block bootstrap의 조건부
95% 구간 상단이 0.95 미만이고 전반 12/후반 12 block 중앙값도 각각 0.95 미만이어야
실질적 개선을 지지한다. 구간 하단이 0.95 초과이면 이 환경·자료의 5% 개선 가설을
기각한다. 나머지는 미확인이다. 1.00 경계와의 관계도 원자료 그대로 보고한다.
5%는 운영 요구사항이나 보편적인 중요성 기준이 아니라 사전 선언한 연구 판정선이다.

보존·상태·실제 파서/검증 호출 trace 또는 적용 가능한 gold 검사에 실패하면
성능보다 먼저 **계측 제거 계약 실패**로 판정하고 주 timing을 수행하지 않는다.
정확성이 실패했는데 더 빠른 실행을 성과로 발표하지 않는다.

## 2. 입력·관찰·상태 계약

런타임에 전달하는 입력은 `records`, ordered `entities`, `query`, `snapshot`과
`parser_namespace`뿐이다. family/정답/typed gold/미래 step/종료 시점은 전달하지 않는다.

`Obs`는 `status`, `reason`, `prediction`, `selected`, `output_bytes`,
`remaining_input_facts`, `scope_trace` 및 같은 renderer의 **정확한 UTF-8 결과**다.
비용 장부와 내부 시간은 제외한다. 렌더와 원래 출력 UTF-8 encoding은 양쪽에서 그대로
실행한다. 문자열 내용 비교를 위한 추가 렌더는 정확성 감사에만 있고 timing에 넣지 않는다.

각 prefix t에서 같은 방법의 on/off 사이에 다음을 요구한다.

\[
Obs(Run_{on}(x_{1:t}))=Obs(Run_{off}(x_{1:t})),\qquad
\pi(S_{t,on})=S_{t,off}.
\]

`pi`는 보고용 peak/cost/event/time만 지운다. selective에는 exact context/raw keys,
dict iteration order, immutable stage 값과 payload 길이, size, 문자 수, surplus, hits,
entry order, next_order, directory 값과 순서, retained_bytes, directory mode와 용량이
남는다. fresh에는 질문 사이 persistent policy state가 없다. 질문 내부 query-event
memo, demand, 추상 상태, copy 시점 값, 선택·근거 trace는 계측으로 취급하지 않는다.

증명 가정은 고정된 순수 semantic code, UTF-8로 표현 가능한 정상 JSON형 유한 입력,
단일 실행·중간 외부 변조 없음, 충분한 자원이다. MemoryError, 비동기 중단, 객체 identity,
GC callback·timer 등의 외부 관측 동등성을 주장하지 않는다. 원래 negative-capacity
ValueError와 snapshot 거절·unsupported early exit는 보존한다.

## 3. 지우는 것과 남기는 것

`derive_off.py`가 원본 AST에서 확인한 reporting assignment/counter, action event,
내부 timer, cost 보고 합산, 보고용 peak를 제거해 `runtime_off.py`를 만든다.
원본 파일은 수정하지 않는다. 이 특정 소스를 위한 검토 가능한 변환이며 범용 compiler
정확성 정리는 아니다. 생성 파일 재생성 hash 검사와 삭제 목록 `ERASURE_MAP.json`을 남긴다.

Fresh의 `len(text.encode('utf-8'))`는 source-byte 장부에만 연결되므로 제거한다.
Selective의 `raw`는 exact key와 실제 L에 연결되므로 원래 방문 위치의 encoding을
보수적으로 유지한다. 짧은 bypass나 일부 miss 경로에서 동적으로 불필요해질 수 있으나
새 lazy encoding·분기 재배치 최적화는 하지 않는다. 따라서 완전히 최소인 CPU 구현을
검증하는 연구가 아니라 **명시한 보수적 source erasure**를 검증한다. 이 비대칭을 숨기지 않는다.

Exact context/raw encoding·비교, 실제 payload encoding과 immutable 변환, L/C/R,
surplus/victim 산술·정렬·용량 검사, hit 갱신, directory 관리, 삽입·삭제, 전체 snapshot
직렬화/hash, 현재 query-demand·추상 실행·copy·선택·렌더는 유지한다.

특히 action을 세지 않아도 `ACTION_WEIGHT=8`, `WARM_ACTIONS=8`과
`b=L-C-R-64`는 유지한다. 장부에서 유래한 상수도 정책 결정에 쓰이는 순간 정책 의미다.
`MIN_CHARS=256`, `HIT_CAP=255`, `META_BYTES=80`, `MAX_BYTES=65536`,
`MAX_ENTRIES=64`와 기존 자료구조·admission·replacement를 고정한다.

## 4. 네 경로와 출발 구현 동등성

| 방법 | 실제 실행 |
|---|---|
| fresh_instrumented | 수정하지 않은 Phase08 `evaluation.run('fresh',...)` |
| fresh_uninstrumented | Phase06 `run`의 default text_scoped 경로에서 장부만 제거 |
| selective_instrumented | 수정하지 않은 Phase08 `evaluation.run('selective',...)` |
| selective_uninstrumented | Phase08 selective에서 위 계측을 제거 |

기존 계측판을 새로 구현하지 않는다. Fresh의 기존 P7/P8 wrapper 비용도 on에는 그대로
남고 off에서는 reporting wrapper와 장부가 사라진다. Fresh off를 selective용 stage
helper로 다시 구현하지 않는다. instrumented 원본과 개발 입력의 비시간 장부도 대조한다.
Fresh off의 default 이외 legacy method는 이번 계약·평가 범위 밖이다.

## 5. 개발 자료와 새 자료

Phase08 원문·주평가·사후 분석·시간 결과는 방향 선택에 사용했으므로 모두 개발/회귀다.
Phase08 432 step과 development 89 step, 더 이전 1,356질문은 정확성 회귀에만 쓴다.
그 수를 새 평가의 독립 분모에 더하지 않는다. 개발 중 새 timing 수치로 정책을 조정하지 않는다.

새 자료는 같은 모델의 별도 작성자가 seed **2026102309**로 만든
**12 family ×3 parameterization =36 stream /622 step**이다. 짧음/긴 원문,
cheap/deep noop, 반복/단일 사용/동일 길이 miss, fit/pressure, phase shift,
정정·copy·질문 변화, namespace/entities, invalid/unsupported/recovery를 포함한다.
최초 투자 직후 종료하는 1-step과 짧은/중간/긴 horizon을 포함한다.
정확한 horizon·길이·반복·working-set 분포는 별도 작성자의 동결 manifest에 있다.
자료·builder·작성 기록은 root가 동결 전 읽지 않고 byte hash만 계산한다.
압축은 mtime=0의 deterministic gzip이며 해제 JSON도 hash를 기록한다.

공개 문법·정책 설계를 공유한 같은 모델 역할 분리다. 외부 독립 검증이나 운영 대화의
대표 표본이 아니다. 큰 원문은 제한 문법의 noop quote다. 적용 gold 분모, 유효/지원
분모, exact raw history와 typed-event 배열 중복을 별도로 보고한다.
이전 자료의 유리한 family를 선택해 새 평가로 부르지 않는다.

## 6. 주 timing: 실행 전에 고정한 규칙

- CPython, 표준 라이브러리. `PYTHONHASHSEED=0`, GC는 켠 채 기본 threshold 유지.
- 허용 CPU affinity의 가장 작은 CPU에 timing process를 고정한다. CPU 독점·주파수
  고정·OS cache flush는 하지 않는다. 환경과 affinity를 저장한다.
- 4방법의 24개 순열을 각각 한 번 사용하는 완전 block design. seed로 순열 순서만 섞는다.
  각 위치에 각 방법은 6번이며 pairwise 순서도 균형이다. 실제 실행 순서를 모두 저장한다.
- 방법당 전체 workload 1회의 사전 warm-up을 명시적으로 폐기한다. 이후 **24 block**을
  반드시 모두 수행한다. 각 방법 구간에서 전체 workload를 **3회** 실행하고 시간을 3으로
  나눈다. 내부 각 stream·각 cycle마다 새로운 parser cache를 만든다.
- 타이머는 전체 `workload` 호출 밖의 `perf_counter_ns` 두 호출뿐이다. Cache 생성·파괴,
  cold 구축, 전체 검증, 파싱, key/payload, 정책, 현재 실행, 동일 렌더를 모두 포함한다.
- import/파일·자료 로딩/공개 입력 준비/정답 평가/상태 검사/보고/LLM 호출은 제외한다.
  네 방법 모두 같은 범위다. Off에는 monkeypatch·event·호출 counter를 추가하지 않는다.
- 결과 object 해제와 정책 때문에 발생하는 할당·GC는 자연 실행에 포함한다.
  타이머 안의 동작을 부분 CPU 비용들의 단순 합으로 가정하지 않는다.
- 원시 ns, 모든 표본, 중앙값·IQR·최소·최대, paired ratio, 전반/후반을 저장한다.
  이상치 삭제·유리한 재실행 선택·결과에 따른 반복 추가는 하지 않는다.
- correctness 실패, hash 불일치, 실행 exception이면 중단하고 실패 receipt를 남긴다.
  환경 중단은 완료된 원자료와 사유를 보존하고 이 세션의 판정은 미확인으로 남긴다.
  단순히 잡음이 크거나 수치가 불리하다는 이유로 중단·재시작하지 않는다.

Parser cache cold와 CPU/OS cold는 다르다. 24개 timing 반복이나 stream 내부 질문은
24개 독립 대화 표본이 아니다. Bootstrap 단위는 네 방법을 함께 잰 **complete block**이며
추정 대상은 고정 corpus·고정 환경의 timing-session 중앙 비율이다. Block 교환가능성은
가정이고 serial dependence를 배제하지 못하므로 구간은 조건부·근사적이다. 대화 분포에
대한 일반화나 하드웨어 모집단 유의성 검정으로 표현하지 않는다.

## 7. 보조 실행과 재현·중단 경계

정확성 실행은 네 경로의 Obs·prefix state를 직접 비교하고 parser/scope 순서와 full
snapshot hash 입력을 별도 monkeypatch로 기록한다. Direct 값/bytes equality가 판정이며
hash는 압축 receipt다. 원시 행은 deterministic gzip으로 남긴다. Gold 평가기는 Phase07/
Phase06의 고정 평가기를 재사용하므로 새로운 외부 정답 검증을 했다고 주장하지 않는다.
Stage/키/상태의 고의 mutant와 hit·정책상수 제거 반례로 검사기가 잡는지도 확인한다.

보조 timing은 off 두 방법만, stream별 **8회**, AB/BA 교대, 각 구간 **5 cycle**이며
group 순서는 고정 seed로 섞는다. 전체 stream의 첫 step만 모은 cold 집합은
**8회/10 cycle**이다. 방법별 warm-up 1회. 모두 주 결과 뒤 별도 실행하고 기술 통계로만
보고한다. Stream 통계 합을 주 whole-workload 시간으로 대체하지 않는다.
Profiler 원인 분해는 이번에 수행하지 않는다.

전체 실행 후 별도 같은 모델 검토자가 새 출력 경로에서 **정확히 한 번** 동일 명령을
재현한다. 결정적 산출물은 byte-identical 비교, timing은 양쪽 모두 보고하고 동일성 대상에서
제외한다. `T_on-T_off`와 네 경로 difference-in-differences는 관측 차이일 뿐 특정 counter
하나의 정확한 CPU 비용이 아니다. 추가 benchmark·정책 재설계 없이 인수인계로 끝낸다.

외부 자연어 의미, LLM 토큰·요금·응답 품질, 미완료 요청·실제 실행 증거의 일반적 보존,
독립 reader 충분성, concurrency, 물리 RSS, SOOM 운영 적용은 미실행이다.
