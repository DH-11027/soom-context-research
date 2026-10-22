# Phase10 자료·분모·원시 결과의 사후 검토

## 1. 결론과 검토 범위

새 자료의 **48 stream / 1,176 prefix**를 원시 입력, 네 경로의 **4,704행**, 정책 상태 witness
**1,176개**, 두 세션의 저장된 timing round에서 다시 집계했다. 분모, 관찰 동등성 기록, 정책 상태
witness의 용량·directory 불변식, 수치 오차, bootstrap 구간과 material label은 기존 산출물과 일치했다.
이것은 같은 모델의 자료 작성자가 수행한 별도 집계다. 외부 독립 검증이 아니다.

수치 예측 조건은 두 세션에서 통과했다. 그러나 **material speedup이 원본·재현 모두 0개**여서
양방향을 구별한다는 H10은 확인되지 않았다. 원본과 재현 모두 음의 paired 점추정은 2개씩 있었다.
따라서 이 결과를 “음의 시간차 관측이 없다”거나 “모든 stream이 확실하게 느려졌다”로 바꾸면 안 된다.
새 자료의 P8 합계 변화는 **+0.0521%**이고, 별도 전체 workload의 paired 경과시간 변화는
**+16.3727% / +18.4952%**다. 예측 오차가 작다는 결과와 정책의 실행시간 개선은 다른 주장이다.

본 작성자는 동결 전 `holdout_builder.py`와 자료·gold를 작성했으며 공개 Phase09 결과를 알고 있었다.
Phase10 구현·계수·개발 시간·새 시간 결과는 동결 후에 열었다. 그 경계는
[`docs/HOLDOUT_AUTHOR.md`](docs/HOLDOUT_AUTHOR.md)에 남아 있다. 여기서는
[`PROTOCOL.md`](PROTOCOL.md), 저장된 모델·feature·prediction·timing·점수의 구조를 읽고,
압축 원시 입력과 행 전체를 프로그램으로 검사했다. 모든 원문을 사람이 한 줄씩 의미 판정했다는
주장을 하지 않는다. 별도 selector 실행, feature 재추출, 계수 재학습, 새 timing은 수행하지 않았다.

재집계 코드는 [`data_review.py`](data_review.py), 전체 수치는
[`data_review.json`](data_review.json)에 있다. 표준 라이브러리만 사용하며 runtime/evaluator/scoring
모듈을 import하거나 그 summary 함수를 호출하지 않는다. 입력 파일별 SHA-256도 JSON에 남긴다.

```bash
python research/phase10/data_review.py --output /tmp/soom-phase10-data-review-check.json
cmp research/phase10/data_review.json /tmp/soom-phase10-data-review-check.json
```

출력 경로가 이미 있으면 새 이름을 사용한다. 이 명령은 저장된 자료의 재집계이고 새 성능 측정이 아니다.
본 검토 코드·JSON·문서는 동결 후 추가물이며, 동결된 코드·자료·gold·모형·평가 기준은 수정하지 않았다.

## 2. 분모와 보존 검사의 정확한 대상

네 경로 모두 다음 판정과 출력 크기가 같았다. 네 방법의 4,704행은 독립적인 4,704개 대화가 아니다.

| 판정 | 방법별 step 수 |
|---|---:|
| `certified_model` | 1,009 |
| `ambiguous` | 67 |
| `opaque_fallback` | 55 |
| `integrity_failure` | 28 |
| `unsupported_query` | 17 |
| 합계 | 1,176 |
| 실제 전체 이력 출력 | 72 |
| 출력 UTF-8 bytes 합계 | 1,674,542 |

전체 이력 출력 72건은 opaque 55건과 unsupported 17건이다. 전체 이력 출력과 certified 여부를
섞지 않는다. Gold 적용 1,128건도 답변 성공 수가 아니다.

| 검사 집합 | 분모 | 발견된 위반 |
|---|---:|---:|
| `certified_model`의 false certification | 1,009 | 0 |
| Gold 적용·지원 질문의 containment | 1,111 | 0 |
| Selected-gold 공동 답집합 투영 | 1,128 | 0 |
| 유효·지원 질문 | 1,131 | 해당 수 자체는 성공 판정 아님 |
| Gold 제외: invalid snapshot | 28 | 제외 사유 |
| Gold 제외: membership 변경의 투영 미정의 | 20 | 제외 사유 |

유효 snapshot은 1,148개다. Gold 적용 1,128에는 unsupported 17개의 전체 이력 선택 검사가
들어간다. 유효·지원 1,131에는 membership 변경 20개가 들어가지만 unsupported 17개는 빠진다.
따라서 두 분모는 다르다. 원문의 자유로운 자연어 의미를 외부 reader가 독립 판정한 gold가 아니다.
Typed event를 별도로 구성해 제한 모형의 유한 실행·공동 투영을 검사한 것이다.

원시 행에서 fresh 계측 경로와 나머지 세 경로의 저장된 관찰 필드를 대조했고,
각 on/off 쌍의 audit·실행 trace hash·정책 trace hash·보관량·entry 수가 같음을 확인했다.
상태 파일의 `exact_policy_state_equal`, `exact_policy_trace_equal`은 원 실행의 직접 비교 결과다.
재집계에서는 저장된 한쪽 witness의 entry 크기 합과 directory 길이별 개수를 다시 검사했다.
두 상태를 모두 다시 실행하거나 hash만으로 두 상태의 동일성을 새로 증명한 절차는 아니다.
기록된 최대 보관량은 **64,086**, 최대 entry 수는 **9**로 고정 한도 65,536 / 64 안이다.

## 3. 길이·horizon·Unicode·중복의 실제 분포

각 family에 horizon 2/8/24/64가 한 번씩 있으므로 family마다 4 stream, 98 step이다.
Horizon별 stream 수는 같지만 질문 수와 입력 bytes는 같지 않다.

| Horizon | Stream | Step | 전체 step 비중 | 원문 bytes 합계 | 각 stream 최대 record bytes의 범위 |
|---|---:|---:|---:|---:|---:|
| 2 | 12 | 24 | 2.04% | 874,708 | 81–77,287 |
| 8 | 12 | 96 | 8.16% | 2,549,662 | 81–71,139 |
| 24 | 12 | 288 | 24.49% | 8,887,967 | 81–77,177 |
| 64 | 12 | 768 | 65.31% | 28,835,189 | 81–70,384 |

표의 원문 bytes는 각 snapshot의 record occurrence를 모두 더한 값이다. 같은 원문을 반복해서
센다. 실제 파서 입력량, 보관 크기, 물리 메모리나 실행시간이 아니다. 전체 10,370 occurrence의
원문 합계는 **41,147,526 bytes**, 고유 raw string은 **1,008개**다. 개별 원문은
**45–77,287 UTF-8 bytes**, **19–71,109 Unicode code point**다.

| 개별 원문의 UTF-8 bytes 구간 | Record occurrence |
|---|---:|
| 850 미만 | 9,078 |
| 850–2,100 | 116 |
| 2,101–6,999 | 0 |
| 7,000–19,000 | 464 |
| 19,001–47,999 | 296 |
| 48,000–63,000 | 250 |
| 63,001–67,999 | 0 |
| 68,000 이상 | 166 |

256문자 미만 occurrence는 9,078개, 이상은 1,292개다. 이 자료에서는 두 구분의 작은 구간 수가
우연히 위 표와 같지만 **정책의 256은 bytes 임계값이 아니다**. 원문 자체가 65,536 bytes를 넘는
occurrence는 7 stream에 걸쳐 166개다. 이것을 admission 거절 수와 동일시하지 않는다.
Cheap 단계에서 끝나거나 무효 입력인 경우 등 실제 정책 경로를 거치지 않는 조건이 있다.

실제 전체 원문의 code point occurrence를 세면 ASCII 23,600,760개, 한글 3,826,098개,
기타 BMP 3,544개, 보조 평면 1,514,460개다. UTF-8 폭별로는 1-byte 23,600,760개,
3-byte 3,829,642개, 4-byte 1,514,460개이며 2-byte code point는 없다.
보조 평면 문자를 가진 raw occurrence는 829개다. 여기의 보조 평면 문자는 작성한 emoji payload에서
나온다. “ASCII style”도 한국어 문법까지 ASCII라는 뜻은 아니며 payload 조성의 이름이다.
큰 원문은 모두 제한 문법의 **noop quote**다. Unicode를 다양화했다고 복잡한 자연어 의미 능력을
검사한 것은 아니다. 길이 band는 horizon과 순환 배치했지만 short/scoped와 working-set의 별도
규칙 때문에 실제 길이의 완전 요인설계는 아니다.

| Exact 직렬화 기준 | 전체 1,176 step | 유효 1,148 step |
|---|---:|---:|
| `records` 배열 전체 | 879 | 862 |
| id·seq를 제외한 ordered raw history | 523 | 518 |
| Ordered raw history + ordered entities | 523 | 518 |
| Public 입력 + namespace | 927 | 907 |

Gold 적용 step의 exact typed-event 배열은 **346개**다. Canonical JSON에서 순서·이름·값을
보존한 동일성 통계다. 518개 독립 프로그램이나 346개 의미 동치류를 발견했다는 뜻이 아니다.
서로 다른 horizon, 같은 family, 같은 원문의 반복도 독립 자연어 대화 표본으로 취급하지 않는다.

## 4. Working set: 동시 원문 합계와 전체 pool을 구별한다

Fit/pressure의 아래 값은 실제 원문에서 다시 센 서로 다른 긴 noop의 개수와 동시 원문 bytes 합이다.
이 가족에서는 전체 pool과 각 snapshot의 동시 집합이 같으며 작성 metadata와 일치했다.

| Family | Horizon | Quote 수 | 동시 raw bytes | 가장 큰 raw bytes |
|---|---:|---:|---:|---:|
| `fit_working_set` | 2 | 3 | 32,194 | 11,345 |
| `fit_working_set` | 8 | 4 | 41,768 | 11,084 |
| `fit_working_set` | 24 | 6 | 56,100 | 10,021 |
| `fit_working_set` | 64 | 2 | 20,800 | 11,100 |
| `pressure_working_set` | 2 | 4 | 112,834 | 28,822 |
| `pressure_working_set` | 8 | 6 | 124,847 | 21,450 |
| `pressure_working_set` | 24 | 2 | 75,705 | 38,524 |
| `pressure_working_set` | 64 | 3 | 99,398 | 33,833 |

실제 보관에는 raw 외에 context, immutable stage payload, metadata가 필요하다. 위 raw 합계를
정책 보관량이나 RAM으로 바꾸어 읽지 않는다. Source 원문을 담는 순간에도 후보 전체를 보관할 수
없는 pressure 조건과 fit 조건은 분리된다. Family 이름 자체가 실제 hit나 admission을 보장하지 않는다.

다른 family에서는 동시 합과 전체 pool이 다르다. 예를 들어 64-step `long_deep_churn`은
긴 noop 64개를 한 번씩 제시해 고유 pool이 **4,497,152 bytes**지만 한 snapshot의 긴 noop은
**70,268 bytes**다. `same_length_misses`의 사전 pool은 7개지만 2-step stream에서 실제로 나타난
원문은 **2개**뿐이다. 나머지 horizon에서는 7개가 나타난다. `quote_pool_count` metadata를 모든
stream의 실제 관측 고유 수로 그대로 복사하지 않았다. `phase_shift`의 마지막 새 원문과 churn의
단일 사용은 cold 투자 이후 추가 회수를 보장하지 않는 종료 조건으로 남아 있다.

## 5. 논리 비용과 cold 구축비

다음 값은 별도 정확성·상태 감사의 계측 경로에서 집계했다. Off 주 timing 안에 카운터를 넣어서
얻은 값이 아니다. 이 행들의 on/off 실제 호출 trace가 동일하다는 감사와 시간 측정은 구별한다.

| 지표 | Fresh | Selective | 변화 |
|---|---:|---:|---:|
| 실제 cheap/scope/detail 호출 | 13,401 | 11,472 | −14.3944% |
| 파서 입력 bytes | 113,371,823 | 72,423,086 | −36.1190% |
| Snapshot 검증 bytes | 40,946,856 | 40,946,856 | 0 |
| 출력 UTF-8 bytes | 1,674,542 | 1,674,542 | 0 |
| P7 | 155,993,221 | 155,896,639 | −0.0619% |
| Control actions | 0 | 22,234 | +22,234 |
| P8 | 155,993,221 | 156,074,511 | +0.0521% |

절약한 파서 bytes 40,948,737에서 cache 장부 40,852,155를 지불하면 P7 이득은 96,582만 남는다.
Control 가중치 8의 비용 177,872를 더하면 P8은 81,290 증가한다.

`ΔP8 = −40,948,737 + 40,852,155 + 177,872 = +81,290`.

이 계산은 고정 작업점수의 장부 항등식이다. 실제 CPU 또는 경과시간의 가산 분해가 아니다.
특히 계측 fresh에 있던 통계용 UTF-8 encode와 비계측 fresh의 비용은 다르므로,
P8 수치를 off의 실제 작업 명령 수로 해석할 수 없다. Phase08/09의 다른 corpus에서 얻은
P8 변화율을 정정하는 결과도 아니다.

48 stream의 첫 step만 더하면 다음과 같다.

| 첫 step 48개의 합 | Fresh | Selective |
|---|---:|---:|
| 실제 호출 | 578 | 578 |
| 파서 입력 bytes | 4,402,494 | 4,402,494 |
| Snapshot 검증 bytes | 1,600,256 | 1,600,256 |
| 출력 bytes | 21,051 | 21,051 |
| P7 | 6,023,801 | 7,914,113 |
| Control actions | 0 | 1,629 |
| P8 | 6,023,801 | 7,927,145 |

Cold 첫 step에서 호출 절약은 없고 P8은 **+31.5971%**다. **Phase10은 첫 step latency를 별도로
측정하지 않았다.** 이 논리 비용 차이를 첫 질문의 실측 지연 증가율로 보고하면 안 된다.

P8 기준 step 이득/동일/손해는 **427/45/704**, 최종 stream 이득/손해는 **13/35**다.
13개 P8 이득 stream 중 원본 timing material label은 slowdown 8, unresolved 5이고,
재현은 slowdown 7, unresolved 6이다. P8 감소가 실질적인 실행시간 감소를 보장하지 않는
구체적인 관측이다. 개별 step의 실측 손익은 측정하지 않았으며 stream 시간에서 역산하지 않았다.

## 6. 큰 원문 family와 horizon이 차지한 비중

아래 시간 비중의 분모는 **별도로 측정한 각 stream의 fresh 중앙값을 더한 값**이다.
원본 245.436 ms, 재현 235.326 ms이며, 직접 측정한 전체 workload 시간과 다르다.
Family별 실측 실행시간 분포를 설명하기 위한 집계이지 전체 workload의 시간을 부품별로
인과 분해한 값이 아니다. P8와 parser 열은 원시 audit 합계의 비중이다.

| Family | Fresh 시간 비중 원본 | 재현 | Fresh P8 비중 | Fresh parser bytes 비중 |
|---|---:|---:|---:|---:|
| `pressure_working_set` | 19.68% | 19.33% | 24.21% | 24.91% |
| `long_deep_churn` | 12.88% | 12.94% | 15.60% | 16.02% |
| `same_length_misses` | 11.01% | 11.30% | 14.92% | 15.33% |
| `fit_working_set` | 9.53% | 9.61% | 7.98% | 8.17% |
| `long_deep_repeat` | 8.35% | 8.35% | 9.87% | 10.11% |
| `phase_shift` | 8.20% | 8.19% | 11.23% | 11.53% |
| `revisions_copy_context` | 6.46% | 6.53% | 6.44% | 6.27% |
| `long_cheap` | 6.04% | 5.93% | 2.35% | 1.58% |
| `integrity_unsupported_recovery` | 6.00% | 6.09% | 6.78% | 5.75% |
| `short_churn` | 4.57% | 4.68% | 0.29% | 0.18% |
| `short_repeated` | 4.33% | 4.16% | 0.19% | 0.12% |
| `scope_ambiguity` | 2.96% | 2.89% | 0.13% | 0.05% |

긴 noop를 포함한 앞의 9 family는 fresh P8의 **99.3883%**, parser bytes의 **99.6556%**,
fresh stream 중앙값 합의 **88.1430% / 88.2696%**를 차지한다. 이것은 그 family의 **전체** 비용
비중이며 quote 원문 자체에 직접 귀속한 비용 비율이 아니다.

64-step 12개는 전체 step의 65.3061%, fresh P8의 **69.3463%**, fresh parser bytes의
**69.3920%**, fresh stream 중앙값 합의 **66.4109% / 66.2804%**를 차지한다.
H10의 수치 지표 E에서는 이들 12개가 48개 중 25%의 가중치를 가진다. 합계 비용과 동일가중
예측 오차를 섞지 않는다.

Family별 P8 합은 fit −20.10%, deep repeat −22.16%, pressure −7.05%,
integrity/recovery −16.76%인 반면, 각 family의 paired stream 시간 중앙값 합에서 음수인 것은
두 세션 모두 fit뿐이다(−0.505 / −0.211 ms). 이 합은 family 단위 불확실성 구간을 가진 새로운
추정치가 아니다. 나머지 family 합은 양수였다. 장부 절약 family를 골라 시간 성과로 발표할 수 없다.

## 7. 직접 측정한 전체 경과시간과 paired 추정량

주 시간 경로는 `fresh_uninstrumented`와 `selective_uninstrumented`다. 저장된 외부
`perf_counter_ns` 구간은 wall elapsed time이다. CPU process time이 아니다. Full snapshot 검증,
cache cold 생성과 파괴, key/payload, 정책 관리, 현재 실행과 동일 render를 포함한다.
Import·자료 로딩·gold·감사·trace 추출·모형 계산·구간 전 GC는 제외한다.

| 직접 whole-workload 측정 | 원본 | 재현 |
|---|---:|---:|
| Fresh marginal 중앙값 | 223.951 ms | 221.853 ms |
| Selective marginal 중앙값 | 251.276 ms | 265.677 ms |
| Paired `median(Ts−Tf)` | +36.667 ms | +41.032 ms |
| Paired 차 / fresh 중앙값 | +16.3727% | +18.4952% |
| 고정 fresh 분모로 나눈 Δ bootstrap 구간 | [+12.2641%, +17.2969%] | [+14.8668%, +24.3442%] |
| Material label | slowdown | slowdown |

`median(Ts−Tf)`는 `median(Ts)−median(Tf)`가 아니다. 후자는 원본 +27.325 ms,
재현 +43.825 ms로 다르다. 이 차이는 계산 오류의 증거가 아니라 서로 다른 추정량이다.
위 표는 whole-workload 16 round의 직접 측정이고, 앞 절의 stream 중앙값 합과 대체할 수 없다.
Phase09의 paired log-ratio 추정량과도 다르다.

Stream별 각 24 round와 whole workload의 2-round block을 저장된 seed로 4,000회 재표집해
percentile 구간을 다시 만들었으며 기존 구간과 일치했다. 반복은 같은 입력·환경에서의 시간 잡음에
관한 것이고 독립 대화 모집단 표본이 아니다. 분모 fresh 중앙값은 점추정으로 고정하므로 joint ratio
CI가 아니며, 48개 stream 전체에 대한 동시 신뢰구간도 아니다. Block 교환가능성, host drift,
같은 호스트·구현의 한계는 남는다. Parser cache는 cold지만 CPU·OS cache는 flush하지 않았다.

## 8. 예측 오차와 material label의 반례

수치 지표는 전체 48개 동일가중의

`E = mean_i abs(predicted_delta_i − median_round(Ts_i−Tf_i)) / median_round(Tf_i)`

다. 작은 Δ로 나눈 상대오차가 아니라 **fresh 실행시간 대비 절대 예측오차**다.

| 예측기 | 원본 E | 재현 E |
|---|---:|---:|
| 고정 trace ridge | 0.03793286 | 0.05267747 |
| Zero change | 0.20033760 | 0.21421886 |
| Per-query | 0.16568260 | 0.17448134 |
| P8 calibrated | 0.17368123 | 0.19248427 |
| Trace / 가장 좋은 baseline | 0.22894897 | 0.30190891 |

모형의 3.7933 / 5.2677 percentage-point 평균 오차는 사전 수치 기준을 만족한다. 개별 stream의
오차가 모두 10% 이하라는 뜻은 아니다. 계수를 새 결과에 맞춰 다시 학습한 값도 아니다.
저장된 feature와 계수의 내적을 독립 계산해 prediction과 확인했다. Feature 중 queries,
saved calls, ΔP8은 원시 행으로 재확인했지만, 문자 trace를 다시 실행해 독립 추출하지는 않았다.

| Stream 수준 구분 | 원본 | 재현 |
|---|---:|---:|
| Paired 점추정 Δ < 0 | 2 | 2 |
| Paired 점추정 Δ > 0 | 46 | 46 |
| Material speedup | 0 | 0 |
| Material slowdown | 35 | 36 |
| Unresolved | 13 | 12 |

두 세션에서 같은 material label을 얻은 집합은 speedup **0**, slowdown **32**다.
나머지 16개는 방향 검사의 공통 집합에서만 빠지며 수치 E에는 48개 모두 포함된다.
최소 각 방향 4개의 사전 조건을 만족하지 않아 balanced accuracy로 양방향 구별 성능을 확인할 수 없다.
Always-slowdown이 모두 맞히는 단일 클래스에서 높은 정확도를 얻는 것은 H10의 성공 근거가 아니다.

Material label은 Δ 구간 전체가 `−0.03 f` 아래이면 speedup, `+0.03 f` 위이면 slowdown,
나머지는 unresolved다. 실제 음의 점추정들은 다음과 같다.

| 세션·stream 접미사 | Paired Δ / fresh | 구간 / 고정 fresh | Label |
|---|---:|---:|---|
| 원본 `fit_working_set-02` | −3.540% | [−4.362%, −1.945%] | unresolved |
| 원본 `fit_working_set-03` | −2.609% | [−4.986%, +4.695%] | unresolved |
| 재현 `fit_working_set-02` | −5.384% | [−7.930%, −2.847%] | unresolved |
| 재현 `scope_ambiguity-00` | −0.430% | [−9.940%, +1.903%] | unresolved |

특히 fit-02는 두 구간 모두 0보다 작지만 상한이 −3% 아래가 아니다. “효과가 정확히 0이다”라는
판정도, “요구한 실질 가속을 확인했다”라는 판정도 아니다. Scope-00 재현은 paired Δ가
−0.664 μs인데 marginal 중앙값 차는 +11.159 μs다. 작은 경계 사례에서 추정량을 섞으면 부호도
바뀔 수 있다. 측정 후 threshold를 낮추거나 유리한 세션을 선택하지 않았다.

## 9. Training 범위 이탈과 가장 큰 예측오차

개발 feature 144개에서 min/max를 다시 계산해 저장된 training bounds와 대조했다.
새 48개 중 **12개**가 적어도 한 raw feature 축의 training 범위를 벗어난다. 모두 64-step이다.

| Feature | Training 범위 | Holdout 범위 | 상한 초과 stream |
|---|---:|---:|---:|
| `stream_constant` | 1–1 | 1–1 | 0 |
| `queries` | 1–36 | 2–64 | 12 |
| `records_visited` | 6–408 | 12–682 | 8 |
| `raw_encode_bytes` | 348–3,818,484 | 833–6,381,056 | 4 |
| `saved_stage_calls` | 0–525 | 0–414 | 0 |
| `saved_stage_characters` | 0–4,340,070 | 0–5,764,500 | 2 |
| `exact_probe_bytes` | 0–3,300,201 | 0–3,754,800 | 1 |
| `encoded_context_payload_bytes` | 0–15,330 | 0–26,650 | 3 |
| `admission_attempts` | 0–75 | 0–129 | 1 |
| `policy_control_actions` | 6–2,656 | 14–3,116 | 1 |

어떤 축의 하한보다 작은 새 stream은 없다. `pressure_working_set-03`은 7개 축에서 상한을 넘는다.
하지만 축 범위 밖 12개의 평균 E는 원본 **0.02811**, 재현 **0.03427**이고, 축 범위 안 36개는
**0.04121 / 0.05881**이다. 따라서 이번 오차를 단순히 “64-step 외삽 때문에 커졌다”로 설명할
수 없다. 이는 사후 기술통계이며, 외삽이 안전하다는 증명도 아니다. 축별 bounding box 안이라는
사실은 joint 분포·상관·상호작용의 학습 범위 안이라는 보증이 아니다.

가장 큰 오차를 숨기지 않기 위해 원본·재현 각각 상위 5개를 보인다. 이름 앞의 공통
`p10-holdout-`은 생략했다. E 열은 해당 stream의 `abs(predicted−observed)/fresh`다.

| 세션 | Stream | 예측 Δ μs | 관측 paired Δ μs | Stream E |
|---|---|---:|---:|---:|
| 원본 | `pressure_working_set-02` | 1,569.022 | 2,683.289 | 12.778% |
| 원본 | `phase_shift-02` | 586.376 | 933.626 | 11.221% |
| 원본 | `same_length_misses-03` | 5,230.188 | 7,108.089 | 9.646% |
| 원본 | `revisions_copy_context-01` | 654.244 | 841.716 | 7.964% |
| 원본 | `same_length_misses-01` | 335.436 | 389.052 | 7.008% |
| 재현 | `long_deep_churn-01` | 390.585 | 528.165 | 13.866% |
| 재현 | `integrity_unsupported_recovery-00` | 181.398 | 274.457 | 13.092% |
| 재현 | `same_length_misses-01` | 335.436 | 429.467 | 12.292% |
| 재현 | `pressure_working_set-02` | 1,569.022 | 2,623.427 | 12.279% |
| 재현 | `scope_ambiguity-00` | 17.765 | −0.664 | 11.935% |

`pressure_working_set-02`는 원본 최악이고 재현에서도 네 번째다. ΔP8은 **−715,556**이어서
P8 baseline은 **−762.004 μs**를 예측했지만 실측 Δ는 두 세션에서 약 **+2.6–2.7 ms**였다.
Trace 모형은 slowdown 부호를 예측했지만 크기는 충분히 설명하지 못했다. 이 사례는 비용점수와
실제 시간 방향의 불일치, trace 요약의 잔여 오차를 동시에 보여 준다. 그 오차를 Unicode,
할당·GC, locality, 특정 policy 부품 하나의 인과 효과라고 식별한 실험은 아니다.

## 10. 끝나는 주장과 남는 주장

이번 자료에서 재집계된 사실은 보존 감사의 일치, 고정 trace 모형의 두 세션 수치 오차 조건 통과,
양방향 material class 부족, 고정 선택 정책의 전체 workload slowdown이다.
따라서 **H10 전체는 `not established`**, 수치 예측 부분은 이 고정 환경·합성 자료에서 지지,
실질적 양방향 구별은 미확인으로 구분한다. 새로운 이득 stream을 얻기 위해 자료를 선택하거나
추가 timing을 반복하지 않았다.

모형은 전체 stream의 실현된 trace를 받는 offline 분석이다. 미래 반복을 온라인으로 예측한 것도,
trace 추출 비용이 없는 것도, 회귀 계수가 인과 CPU 단가인 것도 아니다. 실제 자연어 의미 정확성,
미완료 요청·실행 증거·자유로운 참조의 일반적 보존, LLM 토큰·요금·품질, 다른 환경의 가속,
새 정책의 개선은 이 자료로 검증하지 않았다. SOOM 운영에는 변경이 없다.
