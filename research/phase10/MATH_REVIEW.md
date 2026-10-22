# Phase10 수학·추정 계약 검토

검토 기준 commit: `0c08785fcee9ab146f33fa8a7d94a4b7700833aa`.
초안은 개발 calibration 시간과 새 holdout 결과를 보기 전 작성했다.
같은 모델의 별도 수학 역할이 수행한 검토이며 외부 독립 검증은 아니다.
Phase09 동결 파일은 수정하지 않았고, 새 timing 실행도 하지 않았다.
추가 정적 검토의 BA 유리수 경계 정정은 계획 checkpoint 후 calibration
명령을 시작한 뒤 결과를 회수·열람하기 전에 반영했다. 이 역할은 calibration
시간 label과 새 holdout을
열지 않은 상태를 유지했다. 그 시점과 영향은 §4에 별도로 기록한다.

## 1. 검토 결론

고정된 Phase09 off 구현의 실제 시간차를 완료된 stream의 trace로 예측하는
방향은 Phase09의 부정 결과에서 이어지는 제한된 연구 질문으로 타당하다.
P8 작업점수의 개선을 CPU 가속으로 바꾸어 말하는 대신, 새 시간 label에
대한 반박 가능한 prediction task를 정의한다. 정책 변경이나 runtime gate를
동시에 넣지 않으므로 그 두 효과와 혼동하지 않는다.

검토한 소스의 ridge 계산, feature whitelist, target, 주 error, common-resolved
sign 판정은 [THEORY.md](THEORY.md)의 식과 일치한다. 코드 검토에서 이
수학 계약을 무효화하는 오류는 발견하지 못했다. 다음 경계는 성능 결과와
무관하게 유지해야 한다.

1. 전체 stream의 실제 trace를 먼저 얻는 **offline 분석 모형**이다.
2. 144개 개발 stream은 알려진 36개의 길이 변형이며 독립 표본 144개가 아니다.
3. Ridge 해가 유일하다는 사실은 causal CPU 단가의 식별이 아니다.
4. 실제 feature 충돌은 발견했지만 충돌 쌍의 elapsed-time 차이는 측정하지
   않았다. Feature-only 보편적 보장에는 추가 가정이 필요하다는 결론이다.
5. 시간 성능과 예측 성능은 수학 정리로 선결하지 않는다. Joint H10의
   numerical 조건과 sign 조건을 결과에서 각각 판정해야 한다.

## 2. 읽은 자료와 읽지 않은 자료

### 직접 읽거나 이전 Phase09 역할에서 검토한 자료

- Phase09 `HANDOFF_BACK.md`, `PROTOCOL.md`, `THEORY.md`, `MATH_REVIEW.md`,
  `counterexamples.py`, `execution.py`, `benchmark.py`, `evaluator.py`.
- Phase09에서 검토한 AST erasure와 off 구현의 계약. 이번에 새 실행 경로를
  구현하지 않고 `bridge.py`의 import와 source-hash 검증을 대조했다.
- 필요한 부분의 Phase08 `runtime.py`, Phase06 `scoped.py`,
  Phase05 `revision02/engine.py`: context encoding, admission·density tie,
  실제 entity regex 구성과 parser의 complete-bundle 동작.
- Phase10 `bridge.py`, `development.py`, `features.py`, `time_model.py`,
  `time_worker.py`, `scoring.py`, `run_study.py`의 전체 source와 `PROTOCOL.md`.
- 반환 형식 `docs/RETURN_TEMPLATE.md`.

### 프로그램으로 확인한 자료

`counterexamples.py`를 한 번 실행해 `counterexample_results.json`을 생성했다.
구성한 8개 stream의 26개 prefix에 네 실행 경로를 적용했다. 실제 Obs,
각 on/off의 실행 trace·policy trace, selective의 exact prefix state, 보관
불변식의 assertion이 모두 통과했다. 이 104개 method 실행은 104개의 독립
대화가 아니고, gold 품질 평가도 아니다.

해당 실행의 `verify_base()`는 기존 Phase09 freeze·baseline source hashes를
확인한다. 이런 hash 검사는 동일 bytes 확인이며 의미 보존을 별도로 증명하지
않는다. 244개 유리수 부호 오차 사례와 추상 ridge·중앙값 반례도 같은 실행에서
확인했다.

### 미열람·미실행

- Phase10 `holdout_builder.py`, holdout raw, manifest, gold, family별 실제 내용.
  파일이 존재한다는 정보와 부모 역할이 전달한 48개·1,176-step 명세만 알았다.
- Calibration timing, fitted coefficients, 새 holdout timing·평가 결과.
- 새 benchmark, profiler, causal component timing, hardware cache flush.
- 임의 자연어 자료, LLM token·요금·답변 품질, 일반적 미완료 요청·실행 증거
  보존에 대한 실험.

## 3. 핵심 수학 검토

### 3.1 Fit은 정상화된 가중 ridge이며 자유 intercept가 없다

`fit`의 `normalized`, `scales`, `z`, `y`, `gram`, `rhs`, `theta`, `beta`는
THEORY T1의 식을 순서대로 구현한다. 모든 column에 `RIDGE=.01`이 더해지므로
constant column도 regularize된다. `predict`는 raw feature와 동결 coefficient의
내적을 사용한다. 학습에서 사용한 fresh 시간은 holdout prediction에 필요한
입력이 아니다.

RMS 정규화 때문에 Gram trace가 활성 column 수 이하이고, exact arithmetic의
condition number는 1,001 이하이다(T2). 이 제한은 공선성을 허용하며 unique
ridge solution을 준다. Coefficient 부호에는 제약이 없고 predictive parameter로
해석한다. 하나의 음의 계수를 “해당 작업이 실제로 CPU 시간을 절약한다”는
인과적 주장으로 읽으면 안 된다.

학습은 상대 residual의 squared error이고 평가는 normalized absolute error다.
이를 서로 같은 최적화라고 쓰지 않았다. `per_query`는 train의 `d/q` 중앙값,
`p8_calibrated`는 train의 단일 nonnegative scalar weighted least squares다.

### 3.2 가산성·feature 충분성은 증명된 가정이 아니다

Counterexample C1은 실제 10개 feature가 같아도 서로 다른 regex source와 raw
trace가 존재함을 보였다. C2는 같은 aggregate trace에서 insertion order가
달라져 같은 다음 입력의 재사용 수가 달라짐을 보였다. 따라서 feature가
모든 실행 입력이나 policy Markov state를 보존한다는 주장을 배제했다.

T4의 collision error 하한은 **서로 다른 target**을 조건으로 둔다. C1·C2에서
elapsed time을 재지 않았으므로 이를 CPU target이 다른 실증 사례라고 쓰지
않았다. C3은 median의 비가산성만 증명한다. 실제 GC·locality가 얼마의 차이를
만드는지는 이 검토에서 모른다.

T5의 prefix impossibility도 양의 초기 투자와 양의 반복 순절약을 전제하는
추상 비용 모형이다. Selective의 warm hit가 언제나 실제 CPU 순절약이라는
가정은 추가하지 않았다. 현재 모형은 full-stream offline이므로 이 정리가
현재 평가의 실패를 예고하는 것도 아니다.

### 3.3 부호 평가가 별도로 필요한 이유

T6은 점별 오차와 material-sign 오분류 사이의 정확한 필요조건을 증명한다.
평균 error가 작아도 소수 class에 오차가 집중할 수 있다. C4에서는 error가
약 0.006667이지만 balanced accuracy는 0.5이다. 양 class 최소 4개와 BA
조건을 별도로 두는 설계와 일치한다.

개발 residual의 최댓값이나 training MAE를 holdout에 대한 deterministic
error bound로 전이하지 않는다. 양 class가 충분하지 않으면 sign 질문을
확인했다고 말할 수 없으며 joint H10도 미확립이다.

## 4. 실제 코드와 평가 식의 대조

### Feature·policy 경계

`features.vector`는 사전에 정한 10개 key를 순서대로 구성하고 정수·비음수임을
검사한다. `records_visited`는 fresh의 실제 cheap 호출 수를 사용한다.
`saved_stage_characters`는 별도 actual invocation trace의 문자열 길이 합에서
얻는다. Byte count에서 character count를 역산하지 않는다.

Context access가 여러 번이어도 P8의 step-local `get_context()`는 최초 한
번만 encode한다. Vector도 access 유무가 양수인 step에 context 길이를 한
번 더한다. Admission payload는 후보가 거절되어도 이미 encode되므로
`value_encode_bytes`를 그대로 포함한다. `policy_control_actions`는 off에서
삭제된 ledger의 숫자이며, 같은 정책 branch를 추적하는 feature로만 사용한다.
그 수를 off 경로가 실제로 수행한 instruction 수라고 부르지 않는다.

Four-path exact audit를 통과한 후 ledger feature를 사용한다. Gold 실패가
있으면 추출이 실패하나 gold label을 수치 feature에 넣는 경로는 없다. Family와
base-stream metadata는 보고와 개발 group split에 쓰이며 `predict`는 명시적
feature whitelist와 `p8_delta`만 읽는다.

### Timing 구간·집계

`time_worker.timed()`는 GC precollection 후 외부 `perf_counter_ns()` 하나로
7번 `E9.workload()` 실행을 둘러싼다. 결과를 동일하게 생성·폐기하며 각
replay의 cache는 비어 시작한다. Audit monkeypatch와 feature 수집은 이
worker에서 실행하지 않는다. 기존 binding 때문에 과거 evaluation module이
import될 수 있으나 gold 평가나 실제 호출 감사가 interval에 들어가는 것은
아니다.

개발은 12 rounds, 새 평가는 24 rounds다. 각 stream마다 두 round를 한
cycle로 묶어 방법 순서를 뒤집으므로 각 cycle의 위치가 균형을 이룬다.
Round마다 stream 순서는 별도로 섞는다. 7 replay를 독립 round 7개로
집계하지 않는다. Warmup과 모든 raw round를 보관하고 outlier를 삭제하지
않는다. Secondary whole-workload는 16 rounds·2 replay의 다른 interval이다.

Bootstrap은 round 2개를 함께 resample하며, target은 paired 차이의 중앙값이다.
Observed fresh marginal median으로 나눈 interval은 분모 추정 불확실성을
함께 bootstrap한 ratio CI가 아니다. 개별 interval의 95%를 모든 stream
동시 coverage로 읽지 않는다. 이 작은 cycle 수와 시간 drift 하에서는 정확한
finite-sample coverage가 보장된다는 정리도 없다.

### Joint score와 실행 순서

`score`는 모든 stream의 normalized absolute error에 같은 가중치를 준다.
최고 baseline의 error가 0인 경우 model과의 0/0 동률을 25% 개선으로
인정하지 않도록 `baseline > 0`도 요구한다. 이 경계 정정은 calibration 전에
반영되었다. Numerical 조건 실패는 joint 결론에서도 우선 명시하며 sign
class 부족 여부는 별도 field로 남긴다.
`joint`는 두 session에서 같은 resolved sign인 subset을 만들고 나머지를
명시적으로 제외 기록한다. 양 class 각각 4개, BA≥.75, 최고 baseline보다
≥.10 높은 조건을 모두 요구한다. Calibrated P8를 sign baseline 목록에도
넣었지만 coefficient가 nonnegative라 그 sign은 raw P8 또는 always slowdown과
동일하다. 따라서 이 중복 baseline은 사전 spec의 최고값을 바꾸지 않는다.

추가 정적 검토에서는 정확한 이산 경계의 float 판정 오류를 찾았다. 계획
checkpoint `c18d0d5` 후 calibration 명령을 시작하고 결과를 회수·열람하기 전,
시간 label과 holdout을
읽지 않은 상태에서 구성한 반례다. Class counts 4/15, model correct 4/10,
baseline correct 4/7이면 정확한 BA가 5/6와 11/15이고 차이는 1/10이다.
하지만 기존 float 표현은 `0.8333333333333333 < 0.7333333333333334 + .10`이
되어 원래의 ≥.10 조건을 잘못 탈락시킬 수 있었다.

수정은 BA를 correct/class 정수 비율로 만든 `Fraction`으로 계산하고,
≥3/4 및 baseline 대비 차이≥1/10을 정확하게 비교하는 것이다. Float는
표시용으로만 유지한다. 성공 기준, class 선택, prediction 부호, 모형·자료는
바꾸지 않는다. Calibration·fit·CV는 `joint`를 호출하지 않으므로 이 정정은
해당 calibration의 자료·fit·numerical score·CV 결과에 영향을 주지 않는다.
실제 timing worker 종료는 13:49:29 UTC, 부모 역할의 첫 결과 회수·열람은
13:50:40 UTC로 보고되었으므로 발견·수정 당시에 worker가 계속 실행 중이었다고
단정하지 않는다. 별도 큰 재실행이나 timing을 추가하지 않았다.

`run_study.calibrate`는 known Phase09-derived 자료만 읽는다. `freeze`는
model을 동일 calibration bytes에서 refit해 equality를 확인하고 commit에
기록된 source/data bytes와 비교한다. `run`은 verify 이후 feature를 계산하고
prediction 파일·seal을 만든 뒤 새 subprocess timing을 시작한다. 재현도
새 timing으로 refit하지 않고 기존 calibration의 같은 model을 사용한다.
동결된 model 파일을 직접 prediction에 사용하며, 동일 calibration으로
계산한 refit은 equality witness로만 저장한다.
결정적 산출물의 byte comparison과 timing comparison을 혼동하지 않는다.

`worker` timeout·실패는 별도 receipt로 남기고 오류를 발생시킨다. 유리한
실행을 고르기 위한 자동 retry loop는 없다. `receipt.status=passed`가 H10
지지를 뜻하지 않는다는 구분도 명시되어 있다.
실패 단계와 기존 산출물은 `failure_receipt.json`에 남기며 timeout이 발생하면
실제 수신한 partial stdout/stderr와 progress 존재 여부를 보존한다.

## 5. 증거가 있는 반례와 재현 명령

```bash
python research/phase10/counterexamples.py --output /tmp/soom-phase10-math-replay.json
```

이 검토에서 실제 실행한 명령은 아래와 같다. 결과 파일은 exclusive create로
새로 만들었으며 기존 파일을 덮어쓰지 않았다.

```bash
python research/phase10/counterexamples.py --output research/phase10/counterexample_results.json
```

확인한 내용은 다음과 같다.

| 반례·검사 | 실제 검증 | 아직 주장하지 않는 것 |
|---|---|---|
| C1 `aa`와 `[]` | 10개 feature 동일, regex 길이 9/11, raw trace 다름 | 어느 쪽이 빠른지 |
| C2 `A,B,C`와 `B,A,C` | feature 동일, resident `B,C`/`A,C`, 같은 다음 A에서 절약 호출 0/3 | 실제 CPU 시간차 부호 |
| 추상 prefix 비용 | 4의 최초 투자 후 stop=4, 5회 순절약 뒤 −1 | Python warm-hit의 양의 순절약 |
| T4 collision radius | target −2/4의 common predictor error≥3 | 실제 충돌 쌍의 target 차이 |
| C3 median | 합의 중앙값 100, 중앙값의 합 0 | 실제 시간 부품별 가산성 |
| Rank-one ridge | 유일한 해·작은 normal-equation residual·조건수 1001 | 인과적 coefficient 식별 |
| C4 class imbalance | 평균 error≈0.006667, BA=.5 | 평가 stream들의 실제 class 수 |
| T6 sign 경계 | 244개 exact-rational 사례 통과 | 임의 holdout의 점별 error bound |

## 6. 검토한 source snapshot

아래 SHA-256은 이 기록 작성 시 직접 읽은 source snapshot이다. 최종 동결의
권위 기록은 `freeze.json`이며, 아래와 다른 source가 동결되면 차이를 검토해야
한다. Calibration이나 holdout 결과의 hash를 미리 작성한 표가 아니다.

| 파일 | SHA-256 |
|---|---|
| `bridge.py` | `4ef0b1066eb089bad6c5daa27225d5da2902a1d2f2e686305a7a7e4242f62806` |
| `features.py` | `fbb14dae74b13b41ee858d227e8fb356bb8a15782213cb6890380870642a397d` |
| `time_model.py` | `affd5f682544d3ef9626aaa714da6787438cc669215d96b5b1d4015098a23003` |
| `time_worker.py` | `86dce2234e3921030c48c8ae5f0cf855ac61a3c0f50506b02e9c34e3f4048186` |
| `scoring.py` | `1c6d861116c67c91a2ea32e3c6f6593814ef80bfeb7a40db565aceb483e1591b` |
| `development.py` | `9db3be08c9138eb5160dafc65cd9e22e4470dcf809f1eff72e33cf3f6ac01e27` |
| `run_study.py` | `a621b72fe872e628db6dab958e51290d05624e71cc2480b1f4bf0226f81f385a` |
| `PROTOCOL.md` | `f09b2c7a9f962a9baebeb0b915f933d121d550560ca1baa982570c68adb7192f` |
| `counterexamples.py` | `0076abd840340505670e4659031b7114b9261db004e2d416a06008c1c5abdea9` |
| `counterexample_results.json` | `1417c18f1ad2ac8ee1481c5c15ceb2e5f718a73992e66a6e4a1e408d070d6cb3` |
| `THEORY.md` | `63af0005ec1a74a1f97960860523f984ca526e098f516d018b0fd535566416ea` |

## 7. 남은 확인 사항

최종 결론을 수학으로 선결하지 않는다. 새 holdout의 예측 오차와 부호 판정을
측정하고, 원본과 별도 session 재현을 같은 동결 규칙으로 재집계해야 한다.
이 검토가 확인한 것은 source와 실행 가능한 경계 반례이며 새 평가의 성공이
아니다. 결과가 지지되지 않아도 이번 단계의 policy·feature를 재조정하지 않고,
그 부정 결과를 한 연구 단계의 결론으로 남긴다.
