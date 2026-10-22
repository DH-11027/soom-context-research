# Phase10 별도 재현과 원시 재집계

작성 역할: Phase09/10의 평가·감사 담당인 별도 동일 모델 역할.
새 calibration이나 주평가를 설계한 외부 검증자가 아니며 같은 머신에서 별도 process로 재현했다.

**결론:** 지정 재현 session을 정확히 한 번 실행했고, 결정적 산출물 8개가 원본과
byte-identical이었다. 새 1,176 prefix의 보존 계약 실패는 0이었다. 예측 오차의 수치 조건은
원본·재현 모두 통과했지만, 공통 material speedup이 **0개**여서 손익 방향을 구별하는
가설은 식별되지 않았다. 따라서 **전체 H10 지지는 성립하지 않는다.**

## 1. 실행 기준과 실제 명령

직접 기준은 Phase09 공개 완료 `0c08785fcee9ab146f33fa8a7d94a4b7700833aa`다.
이번 재현의 HEAD는 Phase10 로컬 freeze
`24dcc812eb962e55157ac89e2b44dd615740532b`였다.
Freeze의 checkpoint는 `f1ca8766f777ddbe44b8d5d6a41c9a551efe0bd7`,
동결 시각은 **2026-10-22 13:53:04.871627 UTC**다.
이는 로컬 기록이며 외부 사전 등록이 아니다.

작업 경로 `/workspace/scratch/ff70ac34eaeb/soom-context-phase10`에서 다음을 실행했다.

```bash
python research/phase10/run_study.py --verify
python research/phase10/holdout_builder.py --check
python research/phase10/run_study.py --run \
  --session reproduction \
  --output /tmp/soom-phase10-reproduction \
  --compare research/phase10/results
```

기존 출력 경로가 없음을 확인했고 모두 종료 코드0이었다. 앞의 두 명령은 새 timing을
수행하지 않는다. 세 번째 명령만 정해진 재현 timing session을 실행했다.
Command 실행의 바깥 시작/종료는 **13:57:41.271377–14:00:20.371411 UTC**이고,
실행기 내부 receipt는 **13:57:41.378829–14:00:20.346352 UTC**다.
이 값들은 feature/gold 감사와 저장 작업도 포함한 명령 구간이며 runtime 비교값이 아니다.

검증 명령의 stdout/stderr·시각·종료 코드는 `reproduction_commands.json`,
재현 명령 원문과 전체 stdout/stderr는 `reproduction_execution.json`에 남겼다.
기존 Phase09 timing과 Phase10 calibration을 다시 실행하지 않았다.
느리거나 불리한 결과를 이유로 timing을 더 실행하지 않았다.

## 2. Prediction 봉인과 frozen model

두 session 모두 저장된 `calibration/model.json`을 predict에 사용했다.
원래 calibration의 feature·시간에서 모델을 다시 계산한 `model_refit.json`은
고정 coefficient 동일성 witness다. 새 재현 시간으로 학습하거나 보정하지 않았다.

| 항목 | 원본 | 별도 재현 |
|---|---|---|
| Prediction 봉인 UTC | 13:53:40.943582 | 13:58:00.272812 |
| Worker 시작 UTC | 13:53:41.276997 | 13:58:00.639703 |
| Worker 종료 UTC | 13:56:01.607306 | 14:00:20.304113 |
| 계약 실패 | 0 | 0 |

각 session의 prediction은 그 session의 timing 전에 저장·hash 봉인됐다.
Freeze SHA-256은 `0cefac067755fd2f571b04df748b0a3d56ac0c5dd1afdff33a83188eb7d5fd83`,
모델 SHA-256은 `160ecc6b568a475878473eed411a1caff96d99ede41ee984231ecb5016621365`,
prediction SHA-256은 두 session 모두
`db62c145df97d0426184fac031713cee8d571e9a80740b7effa15c81d8d83041`이다.

## 3. 결정적 동일성 및 원격 전달용 복사

| 산출물 | 원본↔재현 직접 byte 비교 |
|---|---|
| audit.json | 동일 |
| model_refit.json | 동일 |
| holdout_features.json | 동일 |
| predictions.json | 동일 |
| holdout_results.json | 동일 |
| holdout_rows.json.gz | 동일 |
| holdout_states.json.gz | 동일 |
| data_profile.json | 동일 |

이 비교는 새 재현 실행이 직접 생성한 파일과 원본 파일의 비교다. 시간·시각 receipt는
동일성 대상이 아니다. 다음 네 파일은 `/tmp/soom-phase10-reproduction/`에서 이 폴더로
**byte 그대로** 복사했고 다시 직접 비교했다.

| 보존 파일 | SHA-256 |
|---|---|
| reproduction_timing.json | `103af7d90fd0766dc154dd57ed398dd35027a4201d54f3d044c10059d32158d2` |
| reproduction_receipt.json | `ac409a6f2573ae901152382b67e58d6ffc5b1959002a2037a5b1f8b25ecef02a` |
| reproduction_scores.json | `52f204b00d1784098179665997a8163bcf1f9a439f31544993105c334ad90755` |
| reproduction_prediction_receipt.json | `e59bd1d6a6279399d04598b4a8719ec9aa1d028e39bcdd8d690187ad1a3a8a35` |

공개 저장 파일만으로 원시 재집계를 실행할 수 있도록 같은 `/tmp` 디렉터리 전체도
`research/phase10/reproduction/`에 보존했다. 15개 파일·총1,652,941 bytes를 복사한 뒤
원본과 파일 집합 및 모든 파일의 byte 동일성을 직접 확인했다. 여기에는 결정적 산출물8개,
시간·점수·receipt, prediction receipt, 마지막 progress, stdout/stderr가 모두 포함된다.
위 네 alias와 `reproduction/`은 **동일한 재현 session의 복사본**이며 추가 측정이 아니다.

## 4. 환경과 측정 범위

두 session 모두 CPython **3.12.14**, Linux **6.18.55 x86_64**, glibc **2.39**,
보고된 CPU **AMD EPYC 9V74 80-Core Processor**다. 허용 CPU0–8 중 첫 CPU0에
affinity를 고정했고 오류는 없었다. `PYTHONHASHSEED=0`, GC 활성, threshold `[700,10,10]`이다.
Clock은 `CLOCK_MONOTONIC`, 보고 resolution은 1ns다. 다른 머신이나 interpreter 재현은 아니다.

48개 stream 각각 **24 paired round ×방법별7 replay**, 제외하되 보존한 warmup1회다.
2-round block마다 방법 순서가 뒤집히고 각 round의 stream 순서도 고정 seed로 섞인다.
재현 seed는 `20261022102`로 원본 `20261022101`과 다르다. 원시 표본을 버리지 않았다.

고정 Phase09 off의 cold cache 생성/파괴·전체 snapshot 검증·parsing·key/payload·정책·
현재 demand/state/copy·근거 render가 시간 구간 안에 있다. Import·자료 로딩·gold·
feature·모델·사전 GC collection은 밖이다. Parser cache cold를 CPU/OS cache cold로
표현하지 않으며 호스트 전체의 부하를 완전히 격리한 측정도 아니다.

## 5. 수치 예측 조건은 통과했다

각 stream \(i\)의 target은 paired 차이 중앙값 \(d_i\), 분모는 fresh marginal 중앙값
\(f_i\)다. 주 오차는 \(E=48^{-1}\sum_i|\widehat d_i-d_i|/f_i\)다.
아래 %는 fresh 시간에 대한 평균 절대오차의 percentage-point 크기이며 시간 가속률이 아니다.

| 고정 predictor | 원본 E | 별도 재현 E |
|---|---:|---:|
| Trace ridge | **3.7933%** | **5.2677%** |
| Zero change | 20.0338% | 21.4219% |
| Per-query | 16.5683% | 17.4481% |
| Calibrated P8 | 17.3681% | 19.2484% |

두 session 모두 모델 E≤10%였고, 최선 고정 baseline인 per-query보다 오차가 각각
**77.11% /69.81% 작았다.** 따라서 수치 조건 두 개를 모두 통과했다.
오차는 재현에서 커졌으며 원본만 골라 보고하지 않는다. E에 독립 대화 모집단에 대한
신뢰구간을 붙이지 않는다. 48개는 고정 합성 stream이며 같은 family·문법·자료 작성 규칙을 공유한다.

평균이 모든 stream의 오차를 상계하지는 않는다. 예를 들어 `pressure_working_set-02`는
고정 예측1,569.02μs에 대해 원본 target2,683.29μs, 재현2,623.43μs였다.
정규화 오차는 **12.78% /12.28%**로 둘 다 평균보다 크다. 재현의
`long_deep_churn-01`은 예측390.58μs, target528.17μs, 정규화 오차 **13.87%**였다.
이 사례들을 제외해 주 오차를 다시 정의하지 않았다.

## 6. 방향 질문은 식별되지 않았다

| 개별 stream의 material label | 원본 | 별도 재현 |
|---|---:|---:|
| Speedup | **0** | **0** |
| Slowdown | 35 | 36 |
| Unresolved | 13 | 12 |

두 session에서 같은 material 방향을 얻은 공통 집합은 **32개**, 모두 slowdown이었다.
필수 조건인 class별 최소4개 중 speedup class가 없다. Balanced accuracy는 **null**이며
0이나1로 채우지 않는다. 모델은 이 32개 slowdown을 모두 맞췄지만 always-slowdown도
32개를 모두 맞춘다. 이를 "손익 양방향을100% 구별했다"고 주장할 수 없다.

다른16개도 수치 E에는 모두 포함했다. 개별 bootstrap 구간으로 선택된 이 방향 집합을
새로운 독립 표본이라고 하지 않는다. 관측된 slowdown들에서 방향 오류가 적다는 것과,
실제 이득을 알아보는 능력은 다른 주장이다.

최종 결합 규칙은 `H10_supported=false`,
`numerical_rule_both_sessions=true`,
`sign_question_identifiable_under_rule=false`,
`conclusion=not_established_sign_classes_insufficient`이다.
수치 예측의 제한된 성과와 방향 검증 미완료를 함께 남기며 새 이득 stream이나 timing을
추가해 이번 평가를 늘리지 않는다.

## 7. 별도 전체 workload 시간은 보조 관측이다

별도 whole-workload **16 round ×2 replay**도 고정 계획대로 수행했다.
Per-stream 시간을 합한 값이 아니며 같은 주 오차 E도 아니다.

| 전체 workload 보조 관측 | 원본 | 별도 재현 |
|---|---:|---:|
| Fresh marginal 중앙값, ms | 223.951 | 221.853 |
| Selective marginal 중앙값, ms | 251.276 | 265.677 |
| Paired 차이 중앙값, ms | +36.667 | +41.032 |
| Paired 차이 /fresh 중앙값 | +16.37% | +18.50% |

Paired 차이 중앙값은 위 두 marginal 중앙값의 차와 다르다. Phase09의 log-ratio
주추정량과도 다르므로 동일 지표처럼 숫자를 이어 붙이지 않는다. 이번 연구는 predictor를
검토했으며 원래 selective가 실제로 빨라졌다는 결과가 아니다.

## 8. 보존 분모와 별도 감사 비용

4,704개 method row는 1,176개 입력 prefix를 네 경로로 비교한 행이다.
방법별 status는 certified1,009·ambiguous67·opaque55·integrity28·unsupported17로 같았다.
전체 이력 선택72는 opaque55+unsupported17이다.

| 보존 검사 | 결과 |
|---|---:|
| Exact Obs 불일치 | 0/3,528 |
| On/off 실제 trace 불일치 | 0/2,352 |
| Selective π 불일치 | 0/1,176 |
| Selective 정책 trace 불일치 | 0/1,176 |
| 방법별 false certification | 0/1,009 |
| 방법별 containment 위반 | 0/1,111 |
| 방법별 selected-gold 투영 실패 | 0/1,128 |

Gold1,128은 invalid28+membership 투영 미정의20을 제외하며 unsupported17은 포함한다.
유효·지원1,131은 invalid28+unsupported17을 제외한 다른 집합이다.
Gold1,128을 답변 성공 수로 표현하지 않는다.

별도 정확성 감사에서 파서 호출은 **13,401→11,472(−14.39%)**,
입력 bytes는 **113,371,823→72,423,086(−36.12%)**였다.
Snapshot 직렬화40,946,856bytes와 출력1,674,542bytes는 네 경로가 같았다.
Hash1,157회는 유효1,148과 hash까지 도달한 invalid9이며, 나머지 invalid19는 먼저 거절됐다.
이 계수는 주 비계측 timing 안에 wrapper를 다시 넣어 센 것이 아니다.

Selective hit643, admission506, write72, eviction6, capacity reject434(oversize158 포함),
gain reject0이었다. 최대 논리 보관64,086·resident9로 고정 한도를 지켰다.
계측 P8는155,993,221→156,074,511(**+0.0521%**)이다.
이를 off CPU 시간이나 부품별 인과 가격으로 읽지 않는다.

## 9. 독립 원시 재집계

재현 timing이 끝난 뒤 다음을 실행해 종료 코드0을 확인했다.

```bash
python research/phase10/recount_results.py \
  --results research/phase10/results \
  --reproduction /tmp/soom-phase10-reproduction \
  --output research/phase10/recount_results.json
```

`recount_results.py`는 Python 표준 라이브러리만 사용하며 `scoring`, `time_model`,
`time_worker`, `report_results`와 runtime/evaluator를 import하지 않는다. 다음을 다시 계산했다.

- 두 session의 각48×24 paired 원시값에서 중앙값·방법별 요약·4,000회 block bootstrap.
- 고정 seed에서 warmup·2-round 방법 순서와 global stream 순서의 재생성.
- Frozen feature와 coefficient의 별도 `fsum` dot product, baseline 수치와 P8 부호.
- 전체48의 E·family/horizon 집계·두 수치 조건·공통 class·Fraction balanced accuracy·결합 H10.
- 4,704 raw row·1,176 state witness의 분모·상태/출력·호출·byte 장부·P7/P8·용량·directory.
- 8개 직접 byte 동일성, prediction seal 순서와 모든 receipt hash.

독립 dot product와 저장 예측의 최대 차이는 이번 입력에서0이었다. 합산/보간 방식이 달라
다른 일부 요약에는 마지막 부동소수점 자리 차이가 있어 재집계의 고정 허용오차
`rel_tol=1e−11, abs_tol=1e−9`로 비교했다. H10의 count threshold는 별도로 정확한 Fraction을
사용한다. 이 tolerance는 hypothesis threshold를 완화하는 값이 아니다.
독립 결합 결과의 공통 판정 필드는 root의 `combined_results.json`과도 정확히 같음을
확인했다. 설명용 metadata와 별도 Fraction 표시는 두 JSON의 schema가 달라 byte 동일성
대상이 아니다.

보존한 디렉터리만 참조하는 다음 명령도 정확히 한 번 더 실행했다. 이 명령은 parser나
timing을 실행하지 않고 저장된 원시 수치와 witness를 재집계한다.

```bash
python research/phase10/recount_results.py \
  --reproduction research/phase10/reproduction \
  --output /tmp/soom-phase10-stored-recount.json
```

종료 코드0이며 결과는 먼저 `/tmp`의 원래 재현 디렉터리에서 만든
`research/phase10/recount_results.json`과 **byte-identical**이었다. 따라서 이 재집계는
공개 저장소에 포함된 파일만으로 수행할 수 있다. 원래 두 session의 시간 표본을 다시
계산했을 뿐, 세 번째 timing session이나 모델 재학습을 추가하지 않았다.

원시 row/state 형식 검사는 이전 Phase09의 표준 라이브러리 재집계 코드를 같은 형식에 맞춰
상속했다. 저장된 trace hash와 한쪽 state witness를 검토한 것이며, hash에서 원래 양쪽
live trace를 새로 복원한 것이 아니다. Character 합은 저장된 추가 trace 계수의 차를
재확인했고 parser를 다시 실행하지 않았다. Gold annotation의 외부 의미 정답성을 새로
판정한 검증도 아니다. 이러한 경계는 재집계 결과에도 남겼다.

## 10. 종료 범위

정해진 calibration1회·원본1회·재현1회가 끝났다. 이번 역할이 새로 실행한 timing은
재현1회뿐이다. 모델·정책·동결 source·새 데이터·threshold는 재현 후 변경하지 않았다.
Source를 지키면서 재현했고, 수치 예측 성과와 방향 미식별을 분리한 상태로 이 단계를 종료한다.

자연어 의미 정확성, 임의 미완료 요청·실행 증거 보존, LLM 토큰·요금·품질,
online 선택기의 절약, 추출 비용을 포함한 배포 이득, 다른 하드웨어·interpreter,
개별 coefficient의 인과 CPU 가격은 검증하지 않았다. **SOOM 운영 변경 없음.**
