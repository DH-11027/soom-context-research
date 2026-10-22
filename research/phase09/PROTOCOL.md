# Phase09 실행 전 동결 계획 — 동일 정책에서 계측을 지운 실제 시간

직접 기준 `efba3224dd09d5c5e2bf9d9be11734fa10b32502` (Phase08 공개 완료).
Phase08의 주평가·시간을 보고 방향을 정했으므로 그 자료는 전부 개발·회귀다.
새 자료의 원문·gold·builder를 주 구현자와 수학/평가 검토자가 열기 전에 쓴 계획이다.
로컬 동결은 외부 사전 등록이 아니다. 기존 연구·SOOM 운영은 변경하지 않는다.

## 1. 하나의 중심 가설과 선택 이유

**H9:** Phase08 정책·의미·전체 검증을 그대로 유지한 비계측 selective가,
새 합성 고정 workload의 cold 포함 전체 실행시간을 비계측 fresh보다 실질적으로 줄인다.

Phase08은 P8 점수 개선과 실제 시간 증가가 공존했다. 새로운 보관 정책을 설계하기보다
현재 장부 비용을 지워도 남는 실제 계산을 먼저 판별한다. 계측이 slowdown의 원인이라는
결론을 선행하지 않는다. 이 단계는 policy/admission/replacement/directory 최적화를 하지 않는다.

## 2. 입력, 출력, 상태 계약

입력은 JSON형 builtins의 records·ordered entities·snapshot·query, namespace다.
문자열은 UTF-8 encodable, 호출 중 불변, 유한 실행, 단일 thread, 동결 순수 파서,
정상 자원 가용성을 가정한다. OOM/kill/임의 사용자 객체의 side effect까지 동등하다고 하지 않는다.
Gold, family, 미래 질문이나 반복 수는 실행기에 제공하지 않는다.

`Obs`는 반환 dict에서 `cost`만 제외한 모든 값 및 동일 선택 결과의 실제 UTF-8 근거 렌더다.
status/reason/prediction/selected/output_bytes/remaining_input_facts/scope_trace의 유무도 비교한다.
반환 `output_bytes`와 근거 렌더는 유지한다. 길이만 같은 문자열로 충분하다고 하지 않는다.

`π(S)`는 fresh에서 빈 persistent state, selective에서 다음 전체 상태다.
resident exact (context bytes, raw bytes) keys와 dict 순서, immutable stage 값과 payload 길이,
size/characters/surplus/hits/order, directory 내용, retained_bytes, next_order,
max_entries/max_bytes/directory mode. 보고용 peak와 cost/event history만 지운다.
각 입력 prefix t의 Obs 동일성과 `π(S_on,t)=S_off,t`를 요구한다.
별도 감사 실행에서 실제 파서·scope·snapshot·렌더 호출 순서까지 비교한다.

단순 답 비교가 불충분한 hit-counter 반례와 증명은 THEORY/MATH_REVIEW를 따른다.
동등성이 하나라도 깨지면 성능과 무관하게 **계측 제거 계약 실패**이며 주 timing을 시작하지 않는다.

## 3. 삭제와 유지

`erase.py`는 hash 결합한 원본 AST에서 명시적 cost writes, action calls, 내부 timers,
report-only peak, finish 장부를 제거해 정적 파일을 만든다. 생성은 timing 밖에서 완료한다.
Fresh read의 UTF-8 size 계산은 오직 파서 입력 bytes 장부에 흐르므로 제거한다.
두 원래 fresh wrapper는 비용 장부/타이머만 더하므로 off에서 원래 의미 run으로 직접 내려간다.
이 비대칭을 숨기지 않는다.

Selective의 raw/context/payload encoding과 L/C/R, surplus/weight, hit saturation,
victim 비교·정렬·계획·삭제·삽입, directory, 논리 보관량은 유지한다.
raw encoding은 짧은 bypass 방문에도 원래 위치에 남겨 둔다. state-dependent lazy encoding까지
도입하는 최적화는 하지 않는 보수적 삭제다. 사용하지 않는 payload length unpack 등도 남을 수 있다.
따라서 전역적으로 최소화한 실행비 또는 모든 계측 overhead를 제거한 유일 구현이라는 주장은 없다.
전체 snapshot JSON/UTF-8/SHA256와 현재 demand·실행·copy·근거 렌더는 양쪽에 남는다.

상수는 Phase08 그대로: MIN_CHARS=256, MAX_BYTES=65536, MAX_ENTRIES=64,
META_BYTES=80, HIT_CAP=255, ACTION_WEIGHT=8, WARM_ACTIONS=8.
8은 정책 수식의 상수이므로 장부가 없어져도 남는다. 실제 CPU 환산율로 재보정하지 않는다.

## 4. 비교와 자료

네 경로를 모두 측정한다: fresh_instrumented, fresh_uninstrumented,
selective_instrumented, selective_uninstrumented. on은 Phase08 원본을 그대로 호출한다.
주 비교는 **fresh_uninstrumented → selective_uninstrumented**다.
다른 비교는 계측 제거의 총효과이며 부품별 정확 CPU 비용의 식별이 아니다.

개발: Phase08 holdout/development 및 지정 반례. 기존 Phase05–07은 회귀.
주평가: 별도 동일 모델 작성자, seed 2026102209,
12 family ×3 parameterization ×12 step =36 stream/432 step.
short repeated/churn, long cheap/deep repeat/deep churn, fit/pressure working set,
phase shift, same-length misses, revisions/copy/context, scope/ambiguity,
integrity/unsupported/recovery를 포함한다. 상세 미열람 원문·라벨은 gzip으로 저장하고 동결한다.
길이·반복·working-set 범위는 작성 manifest에 공개하며 긴 quote는 제한 문법 noop이다.
일부 마지막 step은 회수할 미래가 없는 신규 candidate다.
모든 stream을 합쳐 주 지표로 삼고 유리한 family를 고르거나 가중치를 바꾸지 않는다.
외부 블라인드 자연어 평가, 독립 대화 432개, 1728개 독립 표본으로 표현하지 않는다.

## 5. 동결·timing·중단 규칙

개발 감사 후 source/protocol/reviews/자료 bytes hashes를 checkpoint commit에 넣는다.
freeze.json은 checkpoint SHA/tree·UTC/KST 시각·전체 hashes를 기록한다.
그다음 freeze commit과 실행 직전 commit 기록을 남긴 뒤에만 새 자료를 연다.
코드/label/주지표 수정이 필요하면 기존 실패를 남기고 연구 계약 실패/수정으로 명시한다.

주 timing은 별도 interpreter에서 실행하며 `PYTHONHASHSEED=0`, 가능하면 최초 허용 CPU 한 개에
affinity를 고정한다. 실패하면 그대로 기록하며 유리한 CPU 탐색을 하지 않는다.
정상 GC는 켜 둔다. 각 interval 전 gc.collect는 양쪽 동일하게 **구간 밖**에서 한다.
CPU/OS cache는 초기화하지 않는다. parser cache만 stream 및 replay마다 비어 있다.

2회 warmup(네 방법 ×전체 workload ×3 replay)은 주집계에서 제외하되 원시값을 보존한다.
본 측정은 **40 round**, 각 round 4방법, 각 interval은 **전체 workload 3 replay**를
외부 perf_counter_ns 한 쌍으로 측정한다. 3으로 나눈 초를 저장한다.
방법 순서는 네 방법에 균형을 맞춘 Williams order 4개를 한 cycle로 하며, 10 cycle 내
순서를 고정 seed로 섞는다. 원본 seed 2026102209, 별도 재현 2026102210.
Cache 생성/파괴, 전체 검증, 파싱, key/payload, 정책, 현재 상태/copy, 렌더를 포함한다.
Import/자료 로딩/gold/감사/별도 계측은 모두 제외한다. monkeypatch/profiler는 주 timing에 없다.

주추정량은 round별 log(T_selective_off/T_fresh_off)의 중앙값을 지수화한 비율 ρ다.
각 방법 시간의 중앙값·최소·최대·IQR와 ratio-of-marginal-medians도 별도 보고한다.
Bootstrap은 **연속 4 round cycle 전체**를 단위로 10개 cycle을 복원 추출, 20000회,
seed902026, percentile 95% 구간이다. 대화/질문/파서 호출을 resampling하지 않는다.
추정 대상은 같은 고정 workload의 이 측정 세션이며 실제 대화 모집단이 아니다.
Cycle 간 충분한 교환가능성을 가정한다. 임의 host drift나 장시간 의존성에는 보장되지 않는다.
10개 cycle은 작고 이 구간은 엄밀한 분포무관 성능 보증이 아니다.

실질 차이 기준은 **3%**로 고정한다. 각 세션에서 구간 상한<0.97이면 실질 개선,
하한>1.03이면 실질 slowdown, 구간 전체가 [0.97,1.03] 안이면 실질 차이 미확인,
그 밖은 잡음/불확실성이 남음으로 보고한다. H9 지지는 동등성 통과와 **원본·재현 모두
상한<0.97**을 요구한다. 두 세션 방향이 다르면 편한 한쪽을 택하지 않고 미확인으로 남긴다.

별도 기술 통계는 8회/방법으로 각 stream 전체와 해당 stream 첫 step의 cold 시간을 측정한다.
주 timing 안에 질문/stream별 타이머를 넣지 않는다. 분해 집계는 다른 실행이며 주시간의
정확한 덧셈 분해가 아니다. family/stream·cold 손익, 큰 원문 점유율, 중복 정의를 모두 보고한다.
보조 profiling은 이번 단계에서 하지 않는다. 인과 원인으로 counters/encoding/GC를 단정하지 않는다.

원본 full session 1회와 별도 역할/프로세스 재현 1회만 실행한다. 유리한 결과를 위해 반복을 늘리지 않는다.
정확성 실패·예외·외부 중단은 즉시 보존·중단하며, 성공을 위한 자료 삭제나 임의 timing rerun은 없다.
단순 느린 결과는 실패한 실험 실행이 아니고 완성된 부정 연구 결론이다.

## 6. 전달 범위

결정적 감사/행/상태/분포 결과는 별도 재현에서 byte-identical 비교한다. 시간은 비교 대상에서 제외한다.
원시 timing 재집계는 주 집계 함수를 호출하지 않는 별도 코드로 검토한다.
새 branch는 research/phase09-instrumentation-erasure. 열린 Phase08 위 base를 쓰되 전달 전에 PR 상태를 다시 확인한다.
자연어 의미 정확성, 미완료 요청·실행 증거 일반 보존, 외부 reader 충분성, LLM 토큰·요금·품질,
RSS, 다른 하드웨어·interpreter, 동시성, 운영 배포는 검증하지 않는다.
