# Phase10 동결 전 평가·feature·수치 구현 감사

검토 역할은 Phase09 평가·재현 담당과 같은 별도 동일 모델 역할이다.
외부 독립 검증이 아니며, Phase10 새 holdout 원문·gold·builder를 읽지 않았다.

**현재 결론:** 알려진 Phase09의 5 stream/20 prefix에서 10개 feature를 별도 실제 작업
trace로 재구성하여 모두 exact equality를 확인했다. 별도 수치 fixture에서는 고정 ridge
구현을 다른 좌표계·선형해법으로 대조했다. 이 감사는 예측 정확도를 아직 평가하지 않으며,
**새 timing session을 실행하지 않았다.**

## 1. 직접 읽은 코드와 상속한 보존 계약

직접 검토한 Phase10 코드는 `bridge.py`, `development.py`, `features.py`,
`time_model.py`, `time_worker.py`다. 필요한 Phase09 `evaluator.py`, `execution.py`,
`off_fresh.py`, `off_selective.py`와 Phase08 action/encode/admission 코드를 함께 읽었다.
출발점·hash·기존 재현 증거는 [INHERITANCE_AUDIT.md](INHERITANCE_AUDIT.md)에 있다.

Phase10은 정책 복제본을 새로 만들지 않는다. `bridge.verify_base()`가 공개 Phase09의
동결 source/data 및 그 이전 source hashes를 확인하고, 같은 off 함수들을 호출한다.
정책·용량·threshold·meaning parser·전체 snapshot 검증·현재 demand/copy/render 계약을
변경한 실험이 아니다. 다만 feature 추출은 전체 stream의 두 실행을 실제로 수행하는
**offline 진단**이다. 이 비용이 없어졌다거나, 미래를 모르는 온라인 정책이 같은 정보를
가지고 선택할 수 있다고 주장하지 않는다.

`features.extract`는 먼저 Phase09의 네 경로 평가기를 호출한다. 그 실행의 Obs/π/실제
trace 비교와 gold·구조 검사가 실패하면 feature 결과를 확정하지 않는다. 그다음 별도
두 off replay에서 문자 수를 얻고, 기존 별도 감사 실행의 호출 계수·trace hash·정책 trace
hash·반환 관찰과 대조한다. 이 추가 replay의 hash 대조를 첫 실행의 **직접 exact
live 비교**와 혼동하지 않는다.

## 2. Feature의 정확한 뜻과 독립 재계산

| Feature | 정의 | 별도 감사가 대조한 실제 자료 |
|---|---|---|
| `stream_constant` | Stream당 1 | 입력 stream 수 |
| `queries` | 해당 stream의 step 수 | Prepared public/namespace 쌍 수 |
| `records_visited` | Fresh 실제 cheap 호출 수 | Fresh parser trace의 cheap event 수 |
| `raw_encode_bytes` | Fresh cheap 입력 UTF-8 길이 합 | 같은 trace 원문을 UTF-8로 encode한 길이 |
| `saved_stage_calls` | Fresh−selective의 cheap/scope/detail 실제 호출 차 | 두 trace의 stage event 수 차 |
| `saved_stage_characters` | 위 실제 stage 입력의 Unicode 문자 수 합 차 | 실제 원문 `len(text)`를 단계마다 합산 |
| `exact_probe_bytes` | 모든 exact get 호출의 context+raw key bytes 합 | Selective get trace의 exact byte key |
| `encoded_context_payload_bytes` | Context 및 stage payload encode 출력 길이 합 | Off `encode` 함수의 실제 반환 bytes 길이를 직접 기록 |
| `admission_attempts` | 실제 admit 호출 수 | Selective admit trace |
| `policy_control_actions` | Phase08이 선언한 action count 합 | On 경로 `action` 호출의 count를 별도 합산 |

`raw_encode_bytes`는 fresh가 실제 raw key encoding을 한다는 뜻이 아니다. Phase09 fresh는
그 계측용 encode를 지웠다. 고정 selective의 각 방문이 raw encode를 수행하고, 같은
입력을 방문하는 fresh cheap trace가 그 원문 길이의 witness가 된다는 정의다.
Fresh cheap 요청·selective cheap 요청·방문 수의 연결은 고정 source와 on/off 보존에
의존한다. Feature 이름을 실제 fresh CPU 작업으로 읽지 않는다.

`policy_control_actions`는 선언된 논리 action 수다. 실제 CPU instruction, 분기 예측
실패 수, 메모리 traffic을 직접 센 값이 아니다. 새 ridge coefficient를 곱해도 개별
action의 인과적 CPU 가격을 식별한 것이 되지는 않는다.

Context는 semantic fingerprint·namespace·**ordered** entities를 encode한다.
한 step의 `context_access` event가 여러 번 발생해도 lazy context encode는 최대 한 번이다.
따라서 feature 구현의 `context_access > 0` indicator가 필요하다. Payload는 admission이
거절돼도 정책의 size/surplus 계산 전에 encode되므로, 성공 write만 세면 안 된다.

## 3. Bounded 실행과 비간섭 검사

`audit.py`는 기존 Phase09의 다음 다섯 stream에서 첫 네 step만 사용한다.

- `long_deep_repeat-00`: 재사용과 여러 byte를 쓰는 문자.
- `long_deep_repeat-02`: 개별 oversize admission 거절.
- `fit_working_set-01`: 한 step의 여러 후보와 lazy context.
- `same_length_misses-00`: 문자 길이가 같은 다른 원문의 exact miss.
- `integrity_unsupported_recovery-00`: 무효 snapshot·미지원 질문·회복.

총 20 prefix에 대해 기존 네 경로의 계약 검사를 통과했다. 별도 독립 replay에서는
off 두 방법마다 **wrapper 없는 plain 실행과 diagnostic wrapper 실행의 Obs 및 π를
prefix마다 직접 비교**했다. 40개 prefix 비교가 같았고 입력 객체 변경도 없었다.
`encode` 및 `action` wrapper와 기존 감사 wrapper는 모두 `finally`에서 원복한다.

10개 feature는 다섯 stream 모두 독립 재계산과 정확히 일치했다. 특히 다음 작은 반례가
서로 다른 계수를 강제한다.

| 잘못된 집계 | 실제 반례 |
|---|---|
| Access마다 context를 encode했다고 계산 | Fit 4 step의 access 12회, 실제 context encode 4회 |
| 보관에 성공한 경우에만 payload encode를 계산 | Oversize admit 4회, write 0회, payload encode 12회 |
| Unicode 문자 대신 UTF-8 bytes를 사용 | 절약 stage 입력 6,273문자와 9,945bytes가 다름 |
| 전체 records 수를 실제 방문 수로 사용 | Fit의 record occurrence 36개, 실제 방문 32개 |

각 feature 좌표를 +1 오염시킨 10개 집계 mutant를 독립 reference와 대조한다.
위 네 개의 구체적 오집계와 아래 두 개의 missing-field replay mutant도 검출했다.
이 16개 결과를 일반적인 모든 오류 검출 보장으로 확대하지 않는다. 단순 좌표 오염 검사와
실제 계산 경계의 반례를 같은 수준의 반례로 세지 않는다.

원시 witness와 검사 결과는 [development_audit.json](development_audit.json)에 있다.

## 4. 동결 전에 발견하고 보완한 관찰 검사

초기 `character_trace`는 실제 반환값의 key만 골라 기존 row와 비교했다. 이 방식은
새 replay에서 `scope_trace` 또는 `prediction` key가 사라져도 남은 key의 값이 같으면
통과할 수 있었다. Parser trace와 그 hash가 같더라도 반환 관찰의 key 존재 여부는 다르다.

주 구현자가 **동결 전에** Phase09에서 가능한 Obs key들의 whitelist를 정하고, 기존 row에
있는 key 전체를 기대값으로 사용하도록 수정했다. `audit.py`의 두 실제 replay mutant는
반환 직후 key 하나를 제거하며, 수정된 검사가 둘 다 거절함을 확인했다. 이는 Phase09
기존 공개 결과의 오류가 아니라 새 Phase10 추가 replay 검사의 개발 중 보완이다.

감사 fixture 자체도 한 번 보완했다. 초안은 long-deep fixture에서 전체 records와 방문 수가
다를 것이라 잘못 기대해 assertion이 실패했다. 실제로는 그 fixture에서 같았다. 이미 선택해
둔 fit fixture의 36대32를 반례로 사용하도록 **감사 코드만** 수정했다. 원본 자료·정책·
예측 feature 정의를 바꾸지 않았다. 실패가 있었던 초안을 성공한 실행으로 기록하지 않는다.

`raw_p8_sign`은 수학 함수 `sign(0)`가 아니라 방향 결정 baseline의 이름이다.
주 구현자가 exact zero를 **slowdown(+1)**으로 처리하는 규약을 주석으로 명시했고,
감사는 그 규약을 검사한다. Zero-change 수치 baseline은 별도로 0을 예측한다.

## 5. Gold·family·time의 데이터 의존성

`bridge.prepare`는 records/entities/snapshot/query와 parser namespace만 실행에 넘긴다.
`features.vector`는 지정된 audit count·계측 ledger와 이 public 입력만 읽고, 임의 row
전체를 feature로 펼치지 않는다. Family와 base-stream ID는 보고 및 개발 CV grouping에만 쓴다.

감사는 feature 집계 입력 row의 family/gold/timing/ID 메타데이터를 오염시켜도 vector가
변하지 않음을 확인했다. 고정 모델의 예측 입력에 같은 메타데이터를 추가해도 수치 예측이
변하지 않았다. Fit에 쓰지 않는 별도 timing row를 추가해도 모델이 같았다.

Gold 자체를 거짓으로 고친 뒤 전체 `extract`가 성공해야 한다고 요구하지는 않는다.
그 경우 선행 Phase09 gold 검사가 거절하는 것이 맞다. **Gold를 correctness gate에 쓰는 것과
gold가 예측 vector나 regression 입력으로 흘러가는 것은 다른 관계**다.
계측 ledger도 별도 진단의 witness로 읽을 뿐, 주 timing의 off 경로에 다시 넣지 않는다.

## 6. 고정 normalized ridge의 수학·수치 검토

개발 stream \(i\)의 feature를 \(x_i\), paired 차이 중앙값을 \(d_i\), fresh의 marginal
중앙값을 \(f_i>0\)라 한다. 시간 단위는 microseconds다.

\[
d_i=\operatorname{median}_r(S_{ir}-F_{ir}),\qquad
f_i=\operatorname{median}_rF_{ir}.
\]

서로 다른 두 marginal 중앙값을 빼는 값이 아니다. 수치 반례
\(F=(10,100,110)\), \(S=(110,101,112)\)에서 paired 차이 중앙값은 2지만
중앙값 차이는 10이다. 이 수치는 **단위 검사에 작성한 숫자**이며 실측 시간이 아니다.

구현은
\(s_j=\sqrt{n^{-1}\sum_i(x_{ij}/f_i)^2}\)를 계산하고, 모두 0인 열에서는 \(s_j=1\)로 둔다.
\(z_{ij}=x_{ij}/(f_is_j)\), \(y_i=d_i/f_i\), \(\beta_j=\theta_j/s_j\)로 변환하므로
해당 ridge는 다음 목적함수와 동치다.

\[
\min_\beta\quad
\frac1n\sum_i\frac{(x_i^\mathsf T\beta-d_i)^2}{f_i^2}
+0.01\sum_j s_j^2\beta_j^2.
\]

Stream constant도 penalty를 받는다. Unpenalized intercept라고 설명하면 틀리다.
양의 ridge는 열의 선형 독립성이 없어도 정규화된 정상방정식을 양의 정부호로 만든다.
계수는 부호 제약이 없으며, 상관된 feature의 개별 coefficient를 CPU 부품의 가격으로
해석할 수 없다. Holdout의 fresh 시간은 prediction에 필요하지 않다.
\(\widehat d=x^\mathsf T\beta\)는 고정 coefficient와 untimed feature만으로 계산한다.

감사는 별도 **24개 합성 수치 record**에 대해 \(\beta\) 좌표의 weighted 정상방정식을
직접 만들고 Cholesky로 풀었다. 주 구현의 정규화 좌표 Gauss–Jordan 해와 최대 coefficient
절대차는 **2.957634137601417e−13**이었다. 공통 시간 단위를 1000배 바꿀 때 coefficient도
1000배가 되는지, zero feature 열의 RMS fallback, 고정 ridge=0.01을 함께 검사했다.
검사 허용오차는 수치 구현을 확인하기 위한 것이며 과학적 예측 허용오차가 아니다.

비교 baseline도 확인했다.

- Zero change는 정확히 0이다.
- Per-query는 개발 \(\operatorname{median}_i(d_i/q_i)\)에 새 query 수를 곱한다.
- P8 scalar는 \(p_i=\Delta P8_i\)에 대해
  \(a=\max(0,\sum_i p_id_i/f_i^2\,/\,\sum_i p_i^2/f_i^2)\)다.
  분모 0과 음의 unconstrained slope에서는 0으로 둔다.
- Leave-family-out CV는 지정 family의 모든 record를 같이 뺀다. 감사의 네 합성 family에서
  held/training partition과 예측 대상 ID를 확인했다. 실제 개발 자료의 144 derived stream은
  36개 기존 base stream의 horizon 변형이며 독립 대화 144개가 아니다.

Ridge·feature·threshold를 CV 결과에 맞춰 다시 고르는 구현은 이 모델에 없다.
이 수치 감사는 실제 elapsed-time 데이터의 예측 성능을 대신하지 않는다.

## 7. 주 timing과의 분리 및 남은 범위

읽은 `time_worker.py`는 Phase09 off 함수와 prepared public 입력을 별도 process에서 실행한다.
`features`, `evaluator`, `audit`, `time_model`의 import 및 profiler/trace hook 부재를 검사한다.
전체 stream의 cold cache 생성/파괴·snapshot 검증·parsing·정책·현재 상태·근거 렌더가
외부 timer 안에 있고, 자료 로딩·gold·feature 추출·모델 적합과 GC 사전 collection은 밖이다.
CPU/OS cache cold를 주장하지 않는다.

이 단계의 감사에서 해당 worker를 실행해 실제 시간을 새로 재지는 않았다. 실측 표본 수는 0이다.
새 결과 뒤에는 frozen coefficient를 재적합하지 않는 별도 재현, deterministic feature/prediction
동일성, 원시 시간·예측오차의 독립 재집계를 확인해야 한다. 그 결과를 이 사전 문서로 소급하지 않는다.

자연어 의미 정확성·미완료 요청·실행 증거 일반 보존, LLM 토큰·요금·품질,
다른 하드웨어의 시간, online gate의 유용성, feature 수집 비용을 포함한 배포 이득은 검증하지 않았다.
**SOOM 운영 변경 없음. 기존 연구 보존. 새 holdout 미열람.**

## 8. Calibration 전 최종 orchestration·scoring source 검토

추가로 `run_study.py`, `scoring.py`, `counterexamples.py`와 최종 protocol을 읽었다.
이 절의 검토와 숫자 fixture도 **첫 calibration timing 전에** 끝냈다.

실행 순서는 frozen hashes 확인 → 알려진 자료 감사 → 저장 모델 동일성 witness →
새 자료의 별도 보존/feature 추출 → prediction 파일 저장 → prediction hash·시각 receipt 저장 →
재현 시 결정적 파일 8개 직접 byte 비교 → 별도 worker timing → scoring이다.
Prediction이 측정 시간보다 먼저 봉인됐는지도 worker의 시작 시각으로 다시 검사한다.
Source 검토에서는 이 순서의 역전이나 holdout 시간이 fit으로 되돌아가는 경로를 찾지 못했다.

초기 구현은 동일한 calibration 원시 시간으로 모델을 다시 계산한 값을 곧바로 predict에
사용했다. 이 값은 frozen 모델과 같도록 검사됐으므로 holdout 누출은 아니었지만,
"frozen model을 사용한다"는 계약을 명확하게 하기 위해 주 구현자가 예측에는 저장된
`calibration/model.json`을 직접 사용하도록 바꿨다. 기존 calibration에서의 재계산은
동일성 검사용 `model_refit.json` witness일 뿐이다. 재현 timing으로 학습하거나 coefficient를
새 환경에 다시 맞추지 않는다.

Byte-identical 비교 대상은 다음 여덟 개다.

1. `audit.json`
2. `model_refit.json`
3. `holdout_features.json`
4. `predictions.json`
5. `holdout_results.json`
6. `holdout_rows.json.gz`
7. `holdout_states.json.gz`
8. `data_profile.json`

시간과 prediction seal의 시각·feature 감사 wall duration은 결정적 동일성 대상이 아니다.
후자의 duration은 네 경로 보존/gold 감사와 두 trace replay를 포함하므로 최소 feature
추출 비용이나 최소 prediction 비용으로 읽을 수 없다.

지정 CLI를 새 Python process로 실행할 때 `import audit`는 Phase10 `audit.py`이고
`audit.run()`이 본 문서의 사전을 반환한다. `counterexamples.py` 안의 `audit()`는
그 모듈에 속한 함수이며 Python module `audit`를 대체하지 않는다. Phase09 평가기는
`bridge.evaluator()`의 `evaluator` module로 따로 연결한다. 임의의 interactive interpreter가
미리 같은 module 이름을 import한 경우까지 보장하는 설계는 아니며 지정된 새 process
재현 명령을 사용한다.

실패 보존도 source에서 확인했다. Timeout은 900초이며 포착된 stdout/stderr를 보존하고
progress 파일의 **실제 존재 여부**를 기록한다. Worker의 nonzero exit도 stdout/stderr와
return code를 남긴다. `--calibrate`/`--run`의 일반 Python `Exception`은 단계·traceback·
이미 생성한 artifact hashes를 `failure_receipt.json`에 기록하고 다시 발생시킨다.
실패 뒤 자동 재시작하거나 완료된 일부 stream만 성공 결과로 바꾸지 않는다.

이 보장은 일반 Exception과 포착된 timeout의 범위다. **KeyboardInterrupt·SIGKILL·프로세스
강제 종료에는 failure receipt 생성을 보장하지 않는다.** 그 경우 마지막으로 디스크에
작성된 progress와 기존 artifact가 남는 범위만 보존되며, 미완료 구간을 복원했다고 할 수 없다.
실패를 실제로 일으키는 worker나 새 timing은 이 감사에서 실행하지 않았다.

### Scoring의 두 논리 경계와 공통 resolved 집합

모든 stream은 세션별 동일가중 normalized absolute error에 남는다. 방향 평가만 두 세션에서
같은 material label을 얻고 unresolved가 아닌 교집합을 사용한다. 각 class 최소4,
모델 balanced accuracy 최소0.75, 최선 방향 baseline보다 최소0.10 높다는 규칙을 확인했다.
이 측정으로 선택된 집합은 고정 모집단이나 동시 신뢰구간으로 표현하지 않는다.

두 source 경계를 발견해 calibration 전에 보완했다.

- Best baseline 오차와 모델 오차가 모두 0이면 `0 <= 0.75*0`은 참이지만 25% 개선은
  정의할 수 없다. 이제 baseline 오차가 양수여야 수치 개선 규칙을 통과한다.
- 수치 조건이 실패하고 방향 class도 부족하면, 이미 관측된 수치 실패를 숨기지 않도록
  결론을 `not_supported_numerical_rule`로 우선 보고한다. 방향 식별 부족은 별도 필드에 남는다.

`audit.scoring_audit()`는 실측 시간이 아닌 작은 수치 fixture로 다음을 검증한다.
모두 오차0인 tie는 성공이 아니고 비율은 null이다. 수치 실패와 방향 class 부족이 함께 있으면
수치 실패 결론이 남는다. 마지막 10개 수치 stream fixture에서는 공통 speedup4·slowdown4만
방향 검사에 포함하고, sign이 바뀐 하나와 unresolved였던 하나는 방향 검사에서만 제외한다.
10개 모두 수치 오차에 남아 재현 fixture의 모델 오차는 0.02가 되며, 이 구성에서는
모델 balanced accuracy1.0·최선 baseline0.5의 양의 지원 논리도 통과한다.
**이 마지막 통과는 scoring 단위 검사의 예상값이며 실제 H10 연구 결과가 아니다.**

추가 fixture를 포함한 최신 `development_audit.json`을 저장했다. 이전 성공한 개발 감사
artifact는 `/tmp/soom-phase10-development-audit-before-scoring.json`에도 보존했으며,
새 결과는 기존 20-prefix feature 검사에 `scoring_logic_checks`를 더한 것이다.
정책·자료·feature·ridge·주 metric threshold를 새 시간 결과에 맞춰 바꾼 것은 아니다.

## 9. Calibration 명령 시작 후 발견한 정확한 방향 threshold 경계

§8까지의 검토가 끝난 뒤, 주 구현자가 discrete count로 계산하는 방향 threshold에서
추가 부동소수점 오류를 발견했다. 발견 시점은 **개발 계획 commit 및 calibration 명령
시작 뒤, calibration 결과를 회수·열람하기 전이며 새 holdout 미열람 상태**였다.
이를 calibration 실행 전 발견이라고 소급하지 않는다. 실제 timed interval이 진행 중일 때
발견됐는지는 별도로 단정하지 않는다.

Class 크기가 speedup4·slowdown15이고 모델의 정답 수가 각각4·10,
최선 baseline의 정답 수가4·7이면 balanced accuracy는 정확히

\[
B_{model}=\tfrac12(4/4+10/15)=\tfrac56,\qquad
B_{base}=\tfrac12(4/4+7/15)=\tfrac{11}{15},\qquad
B_{model}-B_{base}=\tfrac1{10}.
\]

따라서 사전 규칙의 "최소0.10 우위" 경계에 정확히 포함된다. 그러나 표시용 float로
`B_model >= B_base + .10`을 계산하면 이 구성에서 false가 된다.
주 구현자는 protocol의 수학적 조건을 유지하면서, 정답 수/분모를 `Fraction`으로 계산해
`3/4`와 `1/10`의 threshold를 정확히 판정하도록 고쳤다. 표시값은 float로 유지한다.
Tolerance를 임의로 더하거나 성공 threshold를 낮춘 변경은 아니다.

`audit.scoring_audit()`에 19개의 합성 분류 record로 이 사례를 추가했다. 실측 시간·새 자료·
새 label을 사용하지 않고, 수치 조건은 이미 통과했다고 가정한 **방향 판정 단위 검사**다.
이 fixture에서 기존 표시 float 비교는 false, 수정된 exact-count 비교는 true임을 확인했다.
검사 결과는 `scoring_logic_checks.exact_balanced_accuracy_boundary`에 보존했다.

Calibration 완료 통보 뒤 기존 bounded audit 전체를 비시간 실행으로 다시 확인했다.
20-prefix feature/Obs/π 검사와 앞의 수치 검사는 그대로 통과했으며 새 timing은 실행하지 않았다.
이전 감사 artifact는 `/tmp/soom-phase10-development-audit-before-exact-ba.json`에 보존했다.
Calibration의 fit·`score`·grouped CV는 `joint`를 사용하지 않으므로 calibration session을
재실행하거나 이미 얻은 calibration 결과를 바꾸지 않았다. 이 변경을 이후 동결 manifest에
포함하고, 사후 결과를 보고 고친 threshold로 표현하지 않는다.
