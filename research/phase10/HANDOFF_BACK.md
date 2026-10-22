# Phase10 반환 — 시간차 크기의 예측은 지지, 양방향 손익 판별은 미확인

**한 연구 단계를 완료했다.** 고정된 Phase09 비계측 실행의 시간차를 예측한
10-feature ridge는 새 합성 48 stream에서 두 시간 session 모두 수치 조건을
통과했다. Fresh 시간으로 정규화한 평균 절대오차는 **3.793286% / 5.267747%**였다.
그러나 동결한 3% margin·구간 규칙을 만족한 speedup class가 두 session 모두
0개였다. 따라서 양 class 각각 4개를 요구한 방향 질문은 미확인이고,
**결합 H10은 지지되지 않았다: `not_established_sign_classes_insufficient`.**

자료·반복 수·margin·특징량을 바꾸어 성공을 만들지 않았다. 실제 실행 정책을
바꾸지 않았으며 SOOM 운영 변경도 없다. 결과의 완전한 산식·원시값은
[combined_results.json](combined_results.json), [독립 재집계](recount_results.json),
[사후 수학 검토](POSTFREEZE_REVIEW.md)에 있다.

## 출발 상태

### 기준 commit과 이전 결과의 인수인계

- 저장소: <https://github.com/DH-11027/soom-context-research>.
- 직접 출발점: Phase09 공개 완료 `0c08785fcee9ab146f33fa8a7d94a4b7700833aa`.
- Phase09 PR: <https://github.com/DH-11027/soom-context-research/pull/4>.
- 새 branch: `research/phase10-time-prediction`.
- 연구·평가일: 2026-10-22 UTC / 한국 시간 2026-10-22.
- GitHub 전달: 2026-10-22 UTC / 한국 시간 2026-10-23.
- 변경 범위: `research/phase10/`의 새 파일만. 기존 동결 코드·자료·결과 보존.

Phase09에서는 계측 제거의 관찰·정책 상태 보존이 확인됐지만, selective off의
전체 workload 시간은 fresh off 대비 원본 +17.93%, 재현 +16.78%였다.
이 값은 Phase09의 paired log-ratio 중앙값에 따른 결과다. Phase10에서
그 시간을 새로 측정했다고 표현하지 않는다. Phase09의 기존 결정적 원본·재현
파일 8개를 직접 byte/hash 대조하고, archive·AST erasure·freeze·builder·bundle의
다섯 검증 명령을 다시 실행했다. 새 Phase09 timing session은 0회다.

이번 인수인계에서 Phase09 수치를 정정할 오류는 발견하지 않았다.
Phase10은 이전 자료·시간을 보고 방향을 정했으므로 Phase09 자료를 전부
**알려진 개발 자료**로 사용한다. 근거와 실행 로그는
[INHERITANCE_AUDIT.md](INHERITANCE_AUDIT.md), [inheritance/receipt.json](inheritance/receipt.json)에 있다.

### 읽고 확인한 범위

| 확인 방식 | 실제 범위 |
|---|---|
| 주 구현자의 직접 읽기·구현 | Phase09 반환·계약·실행 연결과 필요한 off 소스, Phase10 protocol·feature·모델·worker·집계·반환 형식, 개발·평가 수치와 봉인·동결 기록 |
| 별도 수학 역할의 직접 검토 | Phase09 조건부 보존 계약, 필요한 Phase08 정책·Phase06 scope·Phase05 parser, Phase10 식·source·반례·사후 해석 |
| 별도 평가/재현 역할 | Phase09 상속 증거, Phase10 feature 독립 재계산·평가기·수치 solver·실행 순서, 별도 재현과 raw 재집계 |
| 별도 자료 작성/검토 역할 | 새 builder·typed plan·분포·중복·사후 데이터 검토. 작성 시 Phase10 모델·계수·시간 미열람 |
| 프로그램 검사 | source/data hashes, exact live Obs·π·trace, 구조·gold 계약, 결정적 파일 byte 비교, raw 시간·장부·예측 재집계 |
| 확인하지 않은 것 | 저장소 전체 수기 재검토, 과거 모든 실험의 재실행, 외부 자연어 reader, 외부 머신·사용자 모집단 평가 |

주 구현자·수학·평가 역할은 최종 동결 전 새 holdout 원문·gold·builder를
열지 않았다. 작성자가 전달한 수량·분포·hash만 받았다. 동결 후 주 구현자는
작성 경계 문서와 manifest의 주요 항목·builder 구조를 읽고, 실제 입력은
평가기·feature 추출기로 검사했다. 원문 전체를 사람이 독립 판정한 것은 아니다.
세부 열람·미열람 경계는 각 검토 문서에 따로 기록했다. 모든 역할은 같은
모델이며 공개 문법을 공유한다. **외부 독립 검증이 아니다.**

## 이번 가설과 계약

### 왜 이 한 방향인가

파서 호출이 줄어도 실제 시간이 늘어났다는 Phase09 결과에서, 논리 바이트
점수와 실행시간의 관계를 더 확인할 필요가 생겼다. 이번에는 정책 변경을
섞지 않고 **완료된 stream의 trace 요약이 새 stream의 실제 시간차 크기를
예측할 만큼 유용한가**로 질문을 좁혔다. 별도 microbenchmark의 부품 시간을
그대로 더할 수 있다고 가정하지 않는다.

H10은 개발 시간으로 보정한 고정 10-feature 모형이 새 stream의
`selective_uninstrumented − fresh_uninstrumented` 시간차를 단순 기준보다
잘 예측하고, 두 session에서 확인되는 실질적인 가속·감속을 모두 구별한다는
결합 가설이다. 이 중 수치 부분과 방향 부분을 따로 판정한다.

이는 **전체 public stream을 실제로 replay한 뒤 쓰는 offline 분석**이다.
Prefix만 보고 미래 반복을 알아내는 온라인 정책이 아니다. Feature 추출에는
실제 실행 비용이 들며, predictor 자체의 운영 가속이나 계산 절감을 주장하지 않는다.

### 입력·출력·정책 상태와 계측 경계

실행 입력은 `records`, ordered `entities`, `snapshot`, `query`, parser
namespace로 제한한다. Gold·family·author metadata는 selector에 전달하지 않는다.
Predictor의 수치 입력은 고정 feature 10개이고 baseline만 `ΔP8`를 추가로 쓴다.
ID는 join, family는 보고·개발 group-CV 용도다. Gold는 correctness gate에만 쓰며
모형의 feature나 label로 전달하지 않는다. 예측 출력은 전체 stream의 시간차 μs다.

Phase09의 네 경로를 별도 감사에서 비교한다. 주 timing은 두 off 경로만 쓴다.
Phase09 off 함수 자체를 source hash로 확인해 그대로 import하므로 cache
capacity 65,536, 최대 64항목, 256 Unicode 문자 gate, admission·surplus·victim·
hit 갱신·directory·자료구조는 바뀌지 않았다.

\(Obs\)는 `cost`를 제외한 반환 필드 전체와 정확한 rendered UTF-8 bytes다.
\(\pi\)는 configuration, resident exact keys, immutable stage 값과 encoded
lengths, hits·surplus·size·insertion order, directory, retained bytes,
next order를 포함하는 다음 정책 결정 상태다. 통계 ledger나 report peak는 제외한다.

모든 입력 prefix \(t\)에서 요구한 계약은

\[
Obs(Run_{on}(prefix_t))=Obs(Run_{off}(prefix_t)),\qquad
\pi(S_t^{on})=\pi(S_t^{off}).
\]

같은 namespace·초기 상태·입력에서 이 계약을 승계한다. Finite builtin JSON,
UTF-8 encodable 문자열, 순수·고정 parser/encoder, single-thread, 외부 mutation
없음, 충분한 자원이라는 기존 가정을 유지한다. Resource exception, custom
object side effect, concurrent mutation의 동등성은 포함하지 않는다.

Phase10에서 새로 제거한 runtime 계산은 없다. Phase09의 계측 제거판을 그대로
사용한다. Fresh에서 삭제된 계측용 UTF-8 encode와 달리 selective의 raw encode는
그대로 남아 있으며 짧은 bypass의 eager encode도 남는다. Exact key·context·
payload·L/C/R·surplus·hit·directory·victim 관리·전체 snapshot 검증·현재 demand·
copy·상태 실행·근거 render도 유지한다. 별도 feature 수집기의 계수·wrapper를
주 timing 안에 다시 넣지 않는다.

### 고정 feature와 추정식

| Feature | 고정 정의 |
|---|---|
| `stream_constant` | Stream당 1, penalty를 받는 constant |
| `queries` | Stream 전체 step 수 |
| `records_visited` | Fresh의 실제 cheap 호출 수 |
| `raw_encode_bytes` | 해당 cheap 입력의 UTF-8 길이 합; selective 방문별 encode 입력 크기의 witness |
| `saved_stage_calls` | Fresh−selective 실제 cheap/scope/detail 호출 합 |
| `saved_stage_characters` | 실제 세 stage 입력 Unicode 문자 수 합의 차 |
| `exact_probe_bytes` | 별도 on 실행의 exact key probe 길이 합 |
| `encoded_context_payload_bytes` | Payload encode bytes + context를 쓴 step당 한 번의 context encode bytes |
| `admission_attempts` | 거절된 후보를 포함한 admission 진입 수 |
| `policy_control_actions` | 같은 정책 전이에 대한 원래 P8 선언 action 합 |

`raw_encode_bytes`가 fresh에서 실제 실행된 encode라는 뜻은 아니다. Char와
byte, 전체 records와 실제 방문, context access와 최초 encode, write 성공과
후보 payload encode를 구분했다. 별도 감사의 작은 사례에서 context access
12회/실제 encode 4회, write 0회/후보 payload encode 12회, 6,273문자/9,945bytes,
전체 records 36개/방문 32개가 실제로 달랐다.

개발 stream \(i\)에서
\(d_i=median_r(T_{S,i,r}-T_{F,i,r})\), \(f_i=median_r(T_{F,i,r})>0\)라 한다.
시간 단위는 μs다. \(s_j=RMS_i(x_{ij}/f_i)\), zero column은 \(s_j=1\),
\(Z_{ij}=x_{ij}/(f_is_j)\), \(y_i=d_i/f_i\)로 두고

\[
\theta=(Z^TZ/n+0.01I)^{-1}Z^Ty/n,\qquad
\beta_j=\theta_j/s_j,\qquad \widehat d=x^T\beta
\]

로 고정했다. 이는

\[
\min_\beta\frac1n\sum_i\frac{(x_i^T\beta-d_i)^2}{f_i^2}
+0.01\sum_j s_j^2\beta_j^2
\]

의 유일한 해다. 양의 ridge 때문에 공선성도 허용한다. RMS 정의로 정규화
Gram의 trace가 활성 column 수 이하이므로 정확한 산술에서 ridge 행렬
\(Z^TZ/n+0.01I\)의 조건수는 1,001 이하다. Gram 자체는 공선성이 있으면
singular일 수 있다. 실제 정상방정식 잔차는 `2.7755575615628914e-17`이었다.
이것은 수치 해의 성질이며 holdout 정확도나 causal CPU 단가의 증명이 아니다.
새 예측에는 holdout 시간이 들어가지 않는다.

Baseline은 zero change, 개발 `median(d/q) × 새 q`, 개발 시간에 비음수 단일
계수를 맞춘 `ΔP8`이다. λ·feature·threshold 선택은 하지 않았다. 개발
leave-one-family-out 12fold도 사전에 고정한 진단이며 그 결과로 모델을 고르지 않았다.

### 증명과 실행 가능한 반례

[THEORY.md](THEORY.md)에는 가중 ridge·조건수·단위변환, feature 충돌 오차
하한, 미래 horizon의 부호 불가능성, 중앙값 비가산성, material-sign 오차
경계를 증명했다. [counterexamples.py](counterexamples.py)는 구성한
8 stream/26 prefix/104 method 실행과 유리수 경계 244개를 확인한다.

- **같은 10개 feature, 다른 실행 입력:** `aa`와 `[]` entity를 쓴 두 stream은
  feature가 같지만 regex source 길이는 9와 11이고 raw trace가 다르다.
- **같은 aggregate, 다른 다음 재사용:** A/B는 각각 20,319, C는 30,319의
  논리 보관 크기를 가진다. `A,B,C`와 `B,A,C`는 feature가 같지만 insertion
  order tie로 resident가 `B,C`와 `A,C`가 된다. 같은 다음 A를 붙이면
  saved calls가 0과 3이다. Feature가 정책의 충분 상태라는 주장은 반박된다.
- **조건부 충돌 하한:** 같은 feature에 다른 target \(a,b\)가 대응하면 어느
  결정적 predictor도 최대 절대오차 \(|a-b|/2\)보다 작게 둘을 맞힐 수 없다.
  정규화 최대오차 하한은 \(|a-b|/(f_X+f_Y)\)다. 위 실제 충돌 쌍의 시간은
  재지 않았으므로 서로 다른 CPU target까지 실증한 것은 아니다.
- **미래 종료의 한계:** 최초 투자 \(I>0\), 반복 순절약 \(h>0\)를 가정한
  추상 모형에서 지금 멈추면 \(I>0\), \(k>I/h\)회 반복하면 \(I-kh<0\)다.
  같은 prefix만 본 보편적 부호 보장은 불가능하다. 실제 Python hit의 순절약이
  항상 양수라고 가정하지 않았다.
- **평균 오차와 class 정확도는 다르다:** 4개 음의 target과 44개 양의 target에
  모두 양수를 예측하면 평균 오차가 약 0.006667이어도 BA는 0.5일 수 있다.

Phase08의 최초 투자 후 종료, cheap 선지불 뒤 남은 stage 절약, 과거 인기
고착, 같은 길이의 다른 raw, 동시 보관량 경계도 유지된다. D8을 CPU 시간
정리로 바꾸지 않았다. 상세 가정과 실행 경계는 [MATH_REVIEW.md](MATH_REVIEW.md)에 있다.

## 변경과 재현

### 개발·새 평가·시간 계획

개발은 알려진 Phase09 36 stream을 horizon 1/4/12/36으로 자르거나 순환한
144 derived stream/1,908 prefix다. 독립 144개 대화가 아니다. 한 보정 session만
실행했다. 개발 full-data E는 4.377995%, family-out 진단 E는 4.831593%였다.
그 결과 이후 λ·feature·baseline·평가 조건을 바꾸지 않았다.

새 자료는 같은 모델의 별도 작성자가 공개 문법을 공유해 작성한 12 family ×
4 parameterization = 48 stream/1,176 step이다. Horizon 2/8/24/64를 각 family에
한 번씩 배치했다. 각 horizon은 12 stream이지만 horizon 64가 step의 65.31%다.
주 오차는 모든 stream을 같은 가중으로 계산한다. 긴 원문은 제한 문법의 noop
quote이며 자연어 의미 추론의 난도를 나타내지 않는다.

Timing은 새 interpreter에서 `PYTHONHASHSEED=0`, CPU affinity 0, 정상 GC를
사용했다. 각 interval의 사전 `gc.collect()`는 구간 밖이다. Calibration은
12 rounds, 새 원본·재현은 각각 24 rounds, 각 method interval은 whole stream
7 replays를 외부 timer 한 쌍으로 측정해 7로 나눴다. 두 round마다 FS/SF를
한 번씩 배치하고 stream 순서도 고정 seed로 섞었다. Warmup 한 round와
모든 원시 표본을 보존하고 outlier를 삭제하지 않았다.

별도로 whole-workload 16 rounds ×2 replays를 각 session에서 측정했다.
구간에는 cache 생성·cold 구축·소멸, 전체 snapshot 검증, parse, key/payload,
policy, 현재 상태·copy·render가 포함된다. Import·자료 loading·gold·feature·
model은 제외했다. Parser cache의 cold는 CPU/OS/runtime cache cold가 아니다.
준비한 Python 입력 객체는 반복에서 재사용한다. 전용 물리 host를 격리한 실험은 아니다.

개별 interval은 2-round block을 4,000회 bootstrap한 paired-delta 구간이다.
Fresh 분모를 고정했으며 joint ratio CI나 48 stream 동시 95% 보장이 아니다.
Resampling 단위는 고정 입력의 순서 균형 block이고 대화가 아니다. 주 평균
오차 E에 대화 모집단 CI를 붙이지 않았다. 정확한 계획은 [PROTOCOL.md](PROTOCOL.md)다.

### 실행 전 기록과 실제 동결

| 기록 | 값 |
|---|---|
| 보정 전 계획 시각 | 2026-10-22 13:46:53.968456 UTC / 22:46:53 KST |
| 보정 전 계획 commit | `c18d0d5b2522a7291871a67563a65ab261645eff` |
| 모델·코드 checkpoint | `f1ca8766f777ddbe44b8d5d6a41c9a551efe0bd7` |
| 최종 freeze 시각 | 2026-10-22 13:53:04.871627 UTC / 22:53:04 KST |
| 로컬 freeze commit | `24dcc812eb962e55157ac89e2b44dd615740532b` |
| 원본 prediction seal | 13:53:40.943582 UTC |
| 원본 timing 시작 | 13:53:41.276997 UTC |
| 재현 prediction seal | 13:58:00.272812 UTC |
| 재현 timing 시작 | 13:58:00.639703 UTC |

| 산출물 | SHA-256 |
|---|---|
| Frozen model | `160ecc6b568a475878473eed411a1caff96d99ede41ee984231ecb5016621365` |
| 새 gzip 자료 | `e1cca1bad32e230ac9cc9dc667533ab9c49cf1ee96fb7669bf76823cb94660b5` |
| 해제 JSON bytes | `53380abc1d54d0be127f699b30b0320393482863b60f1e4acd581cad14480e5f` |
| Holdout feature | `87de999b4b0e636483a4323f16fb7b0371c70fdc9b4e42e82e02fd828aa157ad` |
| 봉인 prediction | `db62c145df97d0426184fac031713cee8d571e9a80740b7effa15c81d8d83041` |
| Freeze manifest | `0cefac067755fd2f571b04df748b0a3d56ac0c5dd1afdff33a83188eb7d5fd83` |

전체 source·자료·calibration hash는 [freeze.json](freeze.json), Git 객체는
[pre_evaluation.bundle](pre_evaluation.bundle)에 있다. **GitHub 공개는 평가 후다.
로컬 동결을 외부 사전 등록으로 부르지 않는다.** 공개 Git commit은 로컬
freeze commit과 구별한다. 원격 전달·동일성 증거는 별도 delivery 기록을 따른다.

개발 과정에서 Obs 누락 key 검사, zero-baseline tie, 실패 receipt를 보완했다.
계획 commit 뒤 보정 결과 회수·열람 전에 BA의 float 경계 반례도 발견했다.
`5/6 − 11/15 = 1/10`은 원래 조건을 통과해야 하지만 float에서는 경계에서
탈락했다. 최종 동결 전에 정수 count의 `Fraction` 비교로 고쳤다. Threshold는
그대로이고 calibration의 fit·score·CV는 `joint`를 사용하지 않아 영향이 없다.
계획 source와 최종 freeze source가 완전히 같다고 주장하지 않는다.
정확한 이력은 [DEVELOPMENT_AUDIT.md](DEVELOPMENT_AUDIT.md)에 보존했다.

### 구현 파일과 재현 방법

| 역할 | 파일 |
|---|---|
| 기존 실행 연결·개발 자료 | `bridge.py`, `development.py` |
| 특징량·고정 예측기 | `features.py`, `time_model.py` |
| 시간·판정·동결 실행 | `time_worker.py`, `scoring.py`, `run_study.py` |
| 감사·반례 | `audit.py`, `counterexamples.py`, 각 결과 JSON·검토 문서 |
| 새 자료 | `holdout_builder.py`, `data/`, `docs/HOLDOUT_AUTHOR.md` |
| 학습·실험·재현 | `calibration/`, `results/`, `reproduction/`, reproduction 요약 복사본 |
| 사후 독립 검토 | `recount_results.py`, `data_review.py`, `report_results.py`, 결과 JSON·검토 문서 |
| 그림 | `plot_results.py`, `figures/phase10_results.png`, `figures/phase10_results.svg` |

핵심 실험은 Python **3.12.14 / CPython / Linux 6.18.55 x86_64 / glibc 2.39 /
AMD EPYC 9V74**에서 표준 라이브러리만 사용했다. 그림은 실험 후 저장 결과를
Matplotlib 3.10.8로 그렸으며 실험의 의존성이 아니다.

저장된 결과를 새 timing 없이 재집계하려면 저장소 root에서 실행한다.

```bash
python tools/verify_archive.py
python research/phase10/run_study.py --verify
python research/phase10/holdout_builder.py --check
git bundle verify research/phase10/pre_evaluation.bundle
python research/phase10/recount_results.py --reproduction research/phase10/reproduction --output /tmp/soom-phase10-stored-recount.json
python research/phase10/report_results.py --output /tmp/soom-phase10-combined-recount.json
```

다른 경로에서 별도 실제 시간을 재현하려면 다음을 쓴다. 기존 output이 있으면
새 이름을 택한다. 이 명령은 새 timing session이며 저장된 원본과 시간 자체가
byte-identical할 것을 요구하지 않는다. 새 시간을 학습에 넣지 않는다.

```bash
python research/phase10/run_study.py --run --session reproduction --output /tmp/soom-phase10-your-reproduction --compare research/phase10/results
python research/phase10/recount_results.py --reproduction /tmp/soom-phase10-your-reproduction --output /tmp/soom-phase10-your-recount.json
python research/phase10/counterexamples.py --output /tmp/soom-phase10-your-counterexamples.json
```

별도 재현은 정확히 한 session 실행했다. 결정적 `audit`, `model_refit`,
`holdout_features`, `predictions`, `holdout_results`, gzip rows/states,
`data_profile`의 **8파일이 byte-identical**이었다. `model_refit`은 저장된 원
calibration의 동일성 재계산이며 새 재현 시간으로 학습하지 않는다.
독립 재집계는 예측·집계·timing 구현 함수를 import하지 않고 원시 round,
고정 feature의 내적, 비용·상태 witness, 모든 판정 산식을 별도로 계산했다.
시간은 결정적 동일성 대상이 아니다. 자세한 실행 경계와 명령은
[REPRODUCTION_REVIEW.md](REPRODUCTION_REVIEW.md)에 있다.

## 실제 결과

### 주 비교: 모든 48 stream의 시간차 예측 오차

주 지표는 \(E=\frac1{48}\sum_i|\widehat d_i-d_i|/f_i\)다.
모든 stream에 같은 가중치를 준다. 시간차 자체를 분모로 한 MAPE가 아니며
개별 질문 latency 오차나 모든 항목의 최대오차 보장도 아니다.

| 예측기 | 원본 E | 별도 재현 E |
|---|---:|---:|
| 고정 trace ridge | **3.793286%** | **5.267747%** |
| Zero change | 20.033760% | 21.421886% |
| Per-query | 16.568260% | 17.448134% |
| Calibrated P8 | 17.368123% | 19.248427% |

양쪽 모두 최고 baseline은 per-query였고, 그 대비 오차는 **77.105103% /
69.809109% 감소**했다. E≤10%와 최고 baseline 대비 25% 이상 감소 조건은
두 session 모두 통과했다. 같은 frozen prediction을 사용했지만 관측 d와
분모 f가 달라져 E가 달라졌다. 두 session을 합쳐 96개 대화로 세지 않는다.

### 방향 판정: 필요한 speedup class가 없었다

| 집합 | Material speedup | Material slowdown | Unresolved 또는 sign 제외 |
|---|---:|---:|---:|
| 원본 | 0 | 35 | 13 |
| 재현 | 0 | 36 | 12 |
| 공통 resolved | 0 | 32 | 16 |

3% margin과 개별 구간 전체를 사용한 사전 규칙의 결과다. 양 class 각각
4개가 필요했지만 speedup 분모가 0이다. BA는 **정의되지 않는다**. Model과
always-slowdown은 공통 32개를 모두 맞혔으며 이 단일 class 정확도를 양방향
능력으로 발표하지 않는다. Sign에서 제외된 16개도 numerical E에는 남아 있다.
Class 수가 충분했다면 BA≥0.75 및 최고 방향 baseline보다 0.10 이상 높은 BA를
모두 요구했을 것이다. 이 threshold는 count의 정확한 유리수로 비교한다.
분모가 없는 이번 결과에 0, 0.5 또는 1을 대신 넣어 통과 여부를 만들지 않았다.

Speedup label 0은 음의 관측값 0이 아니다. `fit_working_set-02`의 원본
d/f는 −3.539837%, 구간은 [−4.361719%, −1.945215%]였다. 재현은 −5.384483%,
구간 [−7.929677%, −2.846673%]였다. 둘 다 point는 음수지만 구간 전체가
−3% 아래가 아니어서 unresolved다. 이 사례를 살리려고 margin을 낮추거나
반복을 추가하지 않았다.

### 실제 실행시간은 개선되지 않았다

별도 whole-workload 측정은 전체 **48 stream/1,176 step**의 실행시간이다.
질문 한 건의 latency가 아니다. 이것은 예측 E와 다른 보조 측정이다.

| 전체 workload의 시간 추정량 | 원본 | 재현 |
|---|---:|---:|
| Fresh off marginal 중앙값 | 223.951491 ms | 221.852563 ms |
| Selective off marginal 중앙값 | 251.276068 ms | 265.677112 ms |
| Paired 차이 중앙값 d | +36.666916 ms | +41.032058 ms |
| d / fresh marginal 중앙값 | **+16.372704%** | **+18.495192%** |
| Delta interval / 고정 fresh 중앙값 | [12.264125%, 17.296853%] | [14.866775%, 24.344212%] |

두 marginal 중앙값의 차는 paired 차이 중앙값과 같지 않다. Stream별
중앙값의 합도 위 whole-workload 중앙값이 아니다. Phase09의 paired log-ratio와
동일한 추정량으로 비교하지 않는다.

시간 변동은 남았다. 원본 whole-workload fresh의 IQR은 208.028155–240.116308 ms,
재현은 212.414438–251.809203 ms였다. Selective도 각각
247.477984–278.867134 ms, 256.445824–291.145897 ms였다. 모든 원시 값은
보존했다. Drift·allocation·GC·runtime cache 중 어느 요소의 정확한 CPU
기여인지는 이번 연구에서 분리하지 않았다.

### 별도 감사에서 센 작업량과 보존

| 감사 합계 | Fresh | Selective |
|---|---:|---:|
| 실제 parser 실행 | 13,401 | 11,472 |
| Parser 입력 bytes | 113,371,823 | 72,423,086 |
| Snapshot 검증 bytes | 40,946,856 | 40,946,856 |
| 출력 UTF-8 bytes | 1,674,542 | 1,674,542 |
| On 경로의 P8 점수 | 155,993,221 | 156,074,511 |

호출은 **14.394448%**, parser 입력 bytes는 **36.118972% 감소**했지만 전체
시간은 늘었다. P8 합계는 +0.052111%였다. P8은 별도 on 감사의 논리 작업점수이고
off의 CPU instruction·RAM traffic·실제 token·요금이 아니다. 이 수치는
다른 분포의 Phase08/09 결과를 정정하는 값도 아니다. 계수에 시간을 맞췄다고
그 feature 하나의 causal CPU 단가를 식별한 것도 아니다.

네 경로의 상태 분포는 모두 같았다.

| 상태·검사 | 결과 |
|---|---:|
| `certified_model` | 1,009 |
| `ambiguous` | 67 |
| `opaque_fallback` | 55 |
| `integrity_failure` | 28 |
| `unsupported_query` | 17 |
| 실제 전체 이력 출력 | 72 |
| False certification | 0 / 1,009 |
| Containment violation | 0 / 1,111 |
| Selected-gold 공동 투영 실패 | 0 / 1,128 |
| Exact observation 불일치 | 0 / 3,528 비교 |
| On/off 실제 trace 불일치 | 0 / 2,352 비교 |
| Exact policy state·policy trace 불일치 | 각각 0 / 1,176 prefix |

Gold 적용 1,128에는 unsupported 17의 전체 이력 선택 검사가 포함된다.
유효·지원 질문 1,131과 서로 다른 집합이며 답변 성공 1,128개라는 뜻이 아니다.
Gold 제외는 invalid snapshot 28과 membership 투영 미정의 20이다.
원시 행은 네 방법의 4,704개이며 독립 대화 4,704개가 아니다.

### 데이터 분포·실패와 예측의 한계

새 자료의 raw 길이는 45–77,287 UTF-8 bytes, 문자 수는 19–71,109다.
10,370 record occurrence의 bytes 합은 41,147,526이며 snapshot 반복을
포함한다. 일반 quote는 약 850–2,100 / 7,000–19,000 / 48,000–63,000 /
68,000–83,000-byte 설계 구간을 썼다. Short/scope는 예외이고 fit/pressure는
각각 원문 working set 합계 20k–58k / 75k–130k의 별도 규칙을 쓴다.
Band index 순환은 완전 요인설계가 아니다.

유효 1,148 step의 exact records 배열은 862개, ordered raw history는 518개,
gold 적용 step의 exact typed-event 배열은 346개다. 이름·순서·값을 보존한
직렬화 동일성 통계이며 독립 프로그램 수나 의미 동치류 수가 아니다.
실제 길이·중복·cold·가중치 집중·stream 손익의 자세한 재집계는
[DATA_REVIEW.md](DATA_REVIEW.md)와 [data_review.json](data_review.json)에 있다.

긴 noop를 포함한 9 family가 fresh P8의 **99.3883%**, parser bytes의
**99.6556%**, 별도 stream별 fresh 시간 중앙값 합의 **88.1430% / 88.2696%**를
차지했다. 이는 해당 family 전체의 비중이며 quote 자체의 인과 비용 비율이
아니다. Horizon 64의 12개 stream은 step의 65.3061%, fresh P8의 69.3463%,
stream별 fresh 시간 중앙값 합의 66.4109% / 66.2804%를 차지하지만, 주 오차
E에서는 48개 중 **25% 가중치**다. 직접 whole-workload 시간과 이 중앙값 합도
구별한다.

P8 합계 이득 stream은 13/48이었지만 그중 원본 8개, 재현 7개는 material
slowdown이었다. 논리 점수 이득과 실제 시간 이득을 같은 label로 쓰지 않는다.
48개 stream의 첫 step을 모으면 parser 호출은 578→578이고 P8은 +31.60%였다.
이것은 별도 감사의 cold 구축 장부다. 첫 step의 실제 latency는 따로 재지
않았으며, 주 timing의 whole stream 안에 구축비를 포함했다.

평균 오차가 작아도 개별 오차는 컸다. 원본 `pressure_working_set-02`는
실제 d=2,683.288857 μs, 예측 1,569.021690 μs여서 오차가 fresh의 12.778361%였다.
`phase_shift-02`는 11.220936%였다. 재현 최대는 `long_deep_churn-01`의
13.866374%였다. 점별 10% 정확도 보장은 없다. 원인별 분해도 하지 않았다.

12개 horizon-64 stream은 적어도 한 feature가 개발 좌표별 min/max를 벗어났다.
다른 36개가 joint support 안에 있다는 뜻은 아니다. 범위 밖에서 관측한
오차를 임의 길이·기계·grammar의 외삽 보장으로 해석하지 않는다.
범위 밖 12개의 평균 E는 2.811% / 3.427%, 나머지 36개는 4.121% / 5.881%였다.
이번 자료의 큰 오차를 단순히 좌표별 범위 이탈 때문이라고 설명할 근거도 없다.

원본 audit+feature wall time은 18.231712초였다. 네 경로 보존·gold 검사와
두 추가 trace replay를 포함한 연구 경로이며, 최소 feature 추출비가 아니다.
이 값을 predictor-only 운영 비용으로 단정하거나 추출이 공짜라고 주장하지 않는다.

## 해석과 다음 차례

### 지지·기각·미확인

| 주장 | 이번 판단 |
|---|---|
| 기존 비계측 실행·정책 상태의 보존 | 기존 가정 아래 승계, 새 모든 prefix 감사 통과 |
| 고정 trace ridge의 수치 오차 개선 | 두 session의 고정 합성 평가에서 지지 |
| 양방향 가속·감속 판별과 결합 H10 | 필요한 speedup class가 없어 미확인, H10 채택하지 않음 |
| 10-feature가 정책의 충분 상태 | 실제 삽입 순서 반례로 기각 |
| 새 모형으로 selective가 실제 빨라졌음 | 구현 변경 없음; 측정한 전체 workload는 양쪽 slowdown |
| 계수가 부품별 causal CPU 가격 | 식별되지 않음; 부호 해석 금지 |
| 온라인 선택·feature 추출비 포함 운영 이득 | 구현·측정하지 않음 |
| 자연어 의미, 미완료 요청·실행 증거 일반 보존, LLM token·요금·품질 | 검증하지 않음 |

동결 뒤 core·정책·자료·gold·판정 기준을 바꾸지 않았다. 좋은 family만
다시 측정하거나 새 stream을 추가하지 않았다. 예측 error에 맞춘 사후 모델
선택도 없다. 별도 문서·원시 재집계·그림만 추가했다. 사후 집계 스크립트의
첫 호출은 파일 위치 오타로 실행되지 않아 경로를 바로잡았다. 그림은 구간의
끝점이 축 밖으로 잘리지 않도록 한 번 수정했다. 둘 다 timing·학습·평가를
재실행한 것이 아니며 core 결과를 바꾸지 않았다.

### 다음 연구자가 먼저 재현하거나 반박할 부분

1. Source/data/model freeze와 original Git bundle을 확인한다. 공개 완료 commit과
   로컬 freeze를 구별하고, 계획 이후 정확 산술 정정의 diff도 확인한다.
2. 저장된 두 session의 raw 시간을 독립 재집계해 E와 공통 speedup 분모 0을
   확인한다. 수치 개선을 양방향 BA 성공으로 바꾸지 않는다.
3. `A,B,C`/`B,A,C` 반례에서 feature 동일·resident 다름·다음 saved calls 0/3을
   재현한다. 원래 Obs·π 보존과 예측 feature의 정보 손실을 혼동하지 않는다.
4. 같은 고정 모형으로 새 머신에서 bounded 재현하여 E의 환경 의존성을
   반박할 수 있다. 새 환경 calibration은 이번 검증과 다른 연구 조건이다.

### 다음 한 가지 가설

**256문자 미만 bypass에서 eager raw UTF-8 encode와 size 계산을 eligibility
판단 뒤로 늦추는 단일 변경이, Obs·π를 보존하며 실제 시간을 줄이는가?**

제안 근거는 계수 부호가 아니라 실제 데이터 의존성이다. 현재
`off_selective.read`에서 `eligible=False`이면 raw를 소비하는 `get_key`와
size를 소비하는 `admit`에 들어가지 않는다. 기존 builtin UTF-8 입력·pure·
single-thread·충분한 자원 가정 아래 조건부 삭제의 보존 논증을 할 수 있다.
긴 원문의 key·payload·정책과 전체 snapshot 검증·render는 그대로 둬야 한다.

삭제 가능성이 CPU 시간 감소를 보장하지는 않는다. 이 한 변화만 분리해
보존과 실제 시간을 다시 검증해야 한다. Phase11 구현이나 측정은 이번에
하지 않았다. **SOOM 운영 변경 없음. 연구 전용.**

### 전달

**[Phase10 PR #5](https://github.com/DH-11027/soom-context-research/pull/5)**로 전달했다.
2026-10-22 22:07:11 UTC에 PR #1–#4를 다시 확인했으며 모두 open/unmerged였고,
Phase09 head는 직접 기준 commit과 같았다. 새 branch의 base는
`research/phase09-instrumentation-erasure`이며 기존 branch를 덮어쓰거나 PR을 merge하지 않았다.

최초 공개 commit은 `eebaef726e97f702f136e25ace9c2a78510028d4`, 로컬 연구 완료
commit은 `79f06edb1528b59e89b59442bb115f12d0cf5a28`이다. Public git fetch로
다시 받은 전체 tree `dd7c1ac81e476d07c7b1f96ff4465214a052c53d`가 로컬과
정확히 같고 diff가 비어 있음을 확인했다. 최초 연구 파일 100개는 모두
`research/phase10/` 아래의 추가 파일이다.

이후 변경은 이 문서·README의 실제 PR 연결과 [DELIVERY.json](DELIVERY.json)
추가뿐이다. 최종 공개/로컬 commit과 전체 tree 동일성은 다시 fetch한 뒤 PR
본문에 기록한다. 자기 자신을 포함하는 commit hash를 문서 안에 소급 삽입하는
대신 그 식별자는 PR 본문에서 확인할 수 있다. 동결 source·자료·모델·결과와
실험 횟수는 바뀌지 않았다.
