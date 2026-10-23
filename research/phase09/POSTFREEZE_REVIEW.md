# Phase09 동결 후 별도 재현·원시 집계 검토

작성: 2026-10-23 KST. 주 구현자와 역할을 나눈 동일 모델 에이전트.
같은 머신·CPython·공개 설계의 재현이며 외부 독립 검증이나 다른 플랫폼 재현이 아니다.
이 문서는 새 결과 확인 후 작성했으며 동결 source·자료·정책·판정 기준을 변경하지 않았다.

## 1. 실행 경계와 원본 보존

로컬 동결 commit은 `b4a844efcaca73483f2c0d8b8339a1e352872745`,
freeze 시각은 `2026-10-23T00:00:28.677080+00:00`이다. GitHub 외부 사전 등록이 아니다.
원본 실행 완료 후 다음 명령으로 별도 프로세스에서 **한 번만** 재현했다.

```bash
PYTHONHASHSEED=0 python research/phase09/run_study.py --run \
  --output /tmp/soom-phase09-independent-reproduction \
  --compare research/phase09/results
python research/phase09/recount_results.py \
  --results research/phase09/results \
  --output /tmp/soom-phase09-recount-original.json
python research/phase09/recount_results.py \
  --results /tmp/soom-phase09-independent-reproduction \
  --output /tmp/soom-phase09-recount-reproduction.json
```

재현 시작/종료는 00:02:35.114169 / 00:03:36.050339 UTC
(09:02:35 / 09:03:36 KST)다. 원본과 재현 timing을 동시에 실행하지 않았다.
추가 timing·유리한 반복 선별·이상치 삭제를 하지 않았다.

`reproduction_receipt.json`, `reproduction_timing.json`에 별도 실행을 보존했고,
`recount_results.json`, `reproduction_recount.json`에 두 실행의 독립 재집계를 보존했다.
원본 `results/` 파일은 덮어쓰지 않았다.

## 2. 결정적 결과는 6개 모두 byte-identical

다음 6파일이 원본과 바이트 단위까지 같았다.

- `audit_mutants.json`
- `counterexamples.json`
- `holdout_results.json`
- `holdout_rows.json.gz`
- `regression_results.json`
- `regression_rows.json.gz`

시간과 wall-clock 영수증은 동일성 대상이 아니다. Freeze hash는
`89713911799d7dc6e583d3aaf062bdfa24e3eba98cc7572ed53510adf941b3e8`다.
별도 재현 시간 파일 SHA-256은
`714487b7a0307982879f658b5527e1d323f0efec8194840cb4c63e7fbf5bf2e5`다.
나머지 artifact hash와 비교 결과는 영수증에 모두 있다.

새 평가의 622 prefix / 네 경로 2,488행, 역사 회귀 1,788 prefix / 네 경로 7,152행에서
보존·정책 상태·실제 parser/hash trace·gold 검사 실패가 0이었다.
새 36 stream은 동일 문법·작성 절차의 합성 자료다. 네 방법의 2,488행이나 반복된 timing을
독립 대화 표본 수로 세지 않는다. 회귀 1,788은 Phase08 432 + 기존 1,356이며 새 평가가 아니다.

## 3. 독립 재집계가 확인한 것

`recount_results.py`는 runtime·평가기·benchmark summary helper를 import하지 않는다.
원시 행의 method/stream/step 유일성, 네 경로 pair, 결과 필드 존재 여부·값·관찰 digest,
state·실제 호출 trace의 저장된 receipt, 분모·상태·합계를 다시 계산했다.

정책 상태의 **원 객체와 bytes 직접 비교**는 감사 replay가 수행했다. 재집계는 그때 기록한
state/trace digest와 행을 확인한다. Hash만으로 모든 상태를 독립 재검증했다고 표현하지 않는다.
Gold의 원래 의미를 새 외부 판정자가 검증한 것도 아니다.

시간은 24개 method permutation 전부의 존재, 각 interval의 3 cycle, 원시 nanosecond 정규화,
네 방법의 중앙값·사분위수, 네 비교의 paired ratio·고정 bootstrap 구간·두 절반 중앙값,
보조 stream·첫 step 집계까지 독립 산식으로 확인했다.
두 실행 각각 **306,537 assertion, mismatch 0**이다. Assertion 수는 독립 평가 표본 수가 아니다.

## 4. 정확성·상태·gold의 정확한 분모

아래는 방법별로 동일하다.

| 검사 또는 상태 | 건수 |
|---|---:|
| 전체 step | 622 |
| 유효 snapshot | 610 |
| 유효·지원 질문 | 601 |
| Gold 적용 | 601 |
| Gold 적용·지원 질문 / containment 대상 | 592 |
| Gold 적용 certified / false certification 대상 | 565 |
| Selected-gold projection 검사 | 601 |
| `certified_model` | 565 |
| `ambiguous` | 21 |
| `opaque_fallback` | 15 |
| `integrity_failure` | 12 |
| `unsupported_query` | 9 |

False certification **0/565**, containment 위반 **0/592**, selected-gold projection 실패
**0/601**이다. 유효·지원 601과 gold 적용 601은 같은 크기의 다른 집합이다.
Gold는 membership 변경 9와 invalid 12를 제외하며 unsupported 9의 전체 이력 선택 검사를
포함한다. 601개의 답변을 성공했다는 뜻이 아니다.

Fresh on/off의 실제 parser 호출 trace, selective on/off의 실제 parser 호출 trace가 각각
모든 prefix에서 일치했다. Selective의 전체 policy projection도 모든 prefix에서 일치했다.
네 방법의 exact 관찰 불일치가 없었다. 이 결과는 제한 모형과 고정 입력의 계약이며 일반
자연어 의미 정확성·실행 증거·미완료 요청의 일반적 보존을 검증하지 않는다.

## 5. 주 시간 비교: 두 실행 모두 비계측 selective가 느렸다

표의 값은 **622 step 전체 workload**의 method별 중앙값이며 질문 하나의 latency가 아니다.
각 외부 timing interval은 workload 3회를 포함하고, 값은 1회 workload로 나누어 표시한다.

| 방법 | 원본 중앙값 ms | 별도 재현 중앙값 ms |
|---|---:|---:|
| `fresh_instrumented` | 138.316 | 137.396 |
| `fresh_uninstrumented` | 109.357 | 110.859 |
| `selective_instrumented` | 146.225 | 147.029 |
| `selective_uninstrumented` | 134.894 | 131.813 |

주 추정량은 위 두 method 중앙값의 비가 아니라 **block 내부 off/off 비율 24개의 중앙값**이다.

| 주 비교 | 원본 | 별도 재현 |
|---|---:|---:|
| Median paired ratio | 1.235945 | 1.158004 |
| 변화율 | **+23.5945%** | **+15.8004%** |
| 조건부 95% bootstrap ratio 구간 | [1.145990, 1.312707] | [1.135810, 1.239072] |
| 첫 절반 중앙 비율 | 1.235945 | 1.159013 |
| 둘째 절반 중앙 비율 | 1.255426 | 1.147986 |
| Selective가 빨랐던 block | 0/24 | 0/24 |
| 사전 5% 실질 개선 판정 | 기각 | 기각 |

주가설 H9는 이 고정 합성 자료·환경에서 지지되지 않았다. 두 실행 모두 각 24 block에서
selective off가 fresh off보다 느렸고 조건부 구간도 1보다 컸다. 관측 범위에서는 작은
전체 속도 개선도 보이지 않았다. 이 사실을 모든 자료·플랫폼에서 캐싱이 느리다는 정리로
일반화하지 않는다.

원본 off/off 비율 범위는 약 1.0177~2.0875, 재현은 1.0335~1.4774로 변동이 있었다.
원본·재현의 slowdown 크기 차이도 작지 않다. 24 block bootstrap은 그 세션의 고정 자료에
대한 조건부 구간이며 block 교환 가능성 가정이 필요하다. 직렬 의존성·공유 머신 잡음이
배제되지 않았고, 새로운 대화 모집단이나 여러 환경의 통계 검정으로 해석하지 않는다.

## 6. 계측 제거 자체의 변화와 가법 분해 금지

같은 방법의 on→off에 대한 paired 변화는 다음과 같다. 이는 주 비교를 대체하지 않는다.

| 비교 | 원본 | 별도 재현 |
|---|---:|---:|
| Fresh 계측 제거 | −19.6047% | −19.2785% |
| Selective 계측 제거 | −7.4208% | −9.1488% |
| 계측판 selective 대 fresh | +8.1421% | +7.5795% |

두 방법 모두 중앙값 기준 빨라졌으나 fresh가 더 크게 개선됐다. 따라서 selective에서만
장부를 제거하고 계측 fresh와 비교하는 방식으로 성과를 발표하면 잘못된 결론을 만들 수 있다.
Fresh에는 오직 통계용이던 raw UTF-8 encode가 제거됐고, selective에는 정책 operand로 남았다.
그러나 위 시간 차이를 그 encode 한 부품의 정확한 CPU 비용이라고 귀속하지 않는다.
할당·GC·분기·자료 접근·wrapper 제거의 상호작용을 분해하는 profiling은 하지 않았다.

비계측 구현은 고정 source의 보수적 erasure다. Policy의 `ACTION_WEIGHT=8`과
surplus의 `8×8=64`는 실제 control event 기록을 지워도 정책 결정에 남는다.
모든 가능한 dead branch를 최적으로 없앤 compiler나 가장 빠른 동등 구현을 찾은 것은 아니다.

## 7. 호출 절약은 실제로 있었지만 시간 승리로 이어지지 않았다

별도 호출 감사의 직접 측정이며 timing 안의 계측으로 얻은 수가 아니다.

| 전체 합 | Fresh off | Selective off |
|---|---:|---:|
| 실제 cheap/scope/detail 실행 합 | 7,221 | 5,631 |
| 실제 parser 입력 bytes | 43,264,845 | 15,694,905 |
| 전체 snapshot hash 호출 | 614 | 614 |
| 전체 snapshot 직렬화 bytes | 16,314,040 | 16,314,040 |
| 출력 UTF-8 bytes | 282,813 | 282,813 |

실제 parser 호출 **−22.0191%**, parser 입력 bytes **−63.7237%**여도 전체 시간은
두 실행 모두 늘었다. Parser 입력 bytes는 실제 regex가 훑은 byte 수나 CPU instruction 수가 아니다.
Snapshot hash 횟수 614에는 유효 610 외에 digest 불일치로 거절되는 invalid 입력도 포함된다.

보조 stream timing의 paired 중앙값은 원본 **2/36** stream에서 개선, **34/36**에서 악화였고,
재현은 **1/36** 개선, **35/36** 악화였다. 원본에서 빨랐던 두 stream은 working_set_fit-00
(−1.66%)과 working_set_fit-01(−3.75%)이며, 재현에서는 fit-01만 −9.50%였다.
이 보조 결과에 별도 다중비교 보정이나 독립 추론을 하지 않았고 유리한 stream만 새 주평가로
승격하지 않았다. Stream 순손익은 별도로 처음부터 끝까지 실행한 전체 stream 시간이다.

36 stream의 최초 step만 모은 cold 보조 workload는 **+47.0380% / +44.0190%**였다.
Main timing도 매 stream·cycle에 빈 parser cache로 시작하므로 이 구축비를 이미 포함한다.
빈 parser cache는 차가운 CPU·OS cache를 의미하지 않는다.

## 8. 완료된 결론과 미실행 부분

- 고정 입력 prefix의 관찰·정책 상태·실제 parser/hash trace를 유지한 계측 제거는 구현·검사됐다.
- 고정 환경·새 합성 자료에서 실질적인 전체 속도 개선이라는 중심 가설은 기각됐다.
- 계측이 기존 slowdown의 유일한 원인이라는 설명은 이 결과로 지지할 수 없다.
- 시간 원인의 가법 분해, profiling, 비동기·동시 실행, 다른 플랫폼·Python·GC 설정,
  장기 실제 대화, LLM token·요금·품질은 평가하지 않았다.
- 동결 후 자료·라벨·정책·반복 수·판정 기준을 바꾸지 않았다. 성능 결과를 좋게 만들기 위한
  추가 benchmark를 실행하지 않았다.
- SOOM 운영 변경 없음.

다음 연구자는 우선 위 재현 명령과 raw 재집계를 실행해 모든 결정적 결과의 동일성을
확인한 뒤, 정책을 바꾸지 않은 상태에서 어떤 필수 계산이 실제 시간을 차지하는지 별도의
원인 진단 실험으로 반박하는 것이 좋다. 현재 데이터에 맞춘 새 정책 최적화와 원인 진단을
동시에 수행하면 이번에 분리한 비용 원인 구별이 다시 흐려진다.
