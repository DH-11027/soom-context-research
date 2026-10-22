# Phase10 사후 수학·해석 검토

이 문서는 동결 commit `24dcc812eb962e55157ac89e2b44dd615740532b` 이후
작성한 별도 검토다. 동결된 이론·코드·모형·자료·판정 기준을 수정하지 않는다.
초기 검토 시 원본 timing은 완료되었고 별도 역할의 재현은 진행 중이었다.
이 최종본에는 재현 완료 후 [combined_results.json](combined_results.json)과
[reproduction_receipt.json](reproduction_receipt.json)의 수치를 반영했다.

## 1. 최종 결론: 수치 예측의 개선과 양방향 판별의 미확인을 구별한다

원본·재현 session 모두 **수치 예측 조건을 통과**했다. 그러나 원본에서 동결된
material-speedup label을 받은 stream은 0개이므로 두 session의 공통 resolved
집합에도 speedup은 존재할 수 없다. 따라서 양 class 각각 4개를 요구한
**부호 조건은 식별 불가이며 joint H10은 지지했다고 결론낼 수 없다.**
수치 예측이 좋아졌다는 사실을 speedup과 slowdown을 모두 구별하는 능력의
검증으로 바꾸어 말하면 안 된다.

이 결론의 부호 부분은 재현 결과를 기다리지 않고도 집합 관계로 확정할 수 있었다.
원본·재현의 resolved-speedup 집합을 각각 \(R_-^{(1)},R_-^{(2)}\)라 두면

\[
 R_-^{common}=R_-^{(1)}\cap R_-^{(2)},\qquad
 R_-^{(1)}=\varnothing\ \Longrightarrow\ R_-^{common}=\varnothing.
\]

이는 실제로 빨라질 수 있는 stream이 하나도 존재하지 않는다는 정리가 아니다.
정해진 자료·측정·3% margin·개별 interval 규칙에서 필요한 한 class가 확보되지
않았다는 뜻이다. 최종 공통 집합은 slowdown 32, speedup 0이며, 동결 코드의
최종 label은 `not_established_sign_classes_insufficient`다. 사후에 margin을
줄이거나, 좋은 family를 추가하거나, 반복 횟수를 늘려 이번 단계의 joint
성공을 만들지 않는다.

## 2. 원본·재현 수치 결과의 정확한 의미

[원본 scores](results/scores.json)와 [재현 scores](reproduction_scores.json)의
모든 48개 stream을 포함한 결과다. 아래 값은
\(E=\operatorname{mean}_i|\widehat d_i-d_i|/f_i\)다.

| 예측기 | 원본 E | 재현 E |
|---|---:|---:|
| 10-feature ridge | 0.037932860912951206 | 0.05267747105017678 |
| zero change | 0.20033760317982593 | 0.21421885627257972 |
| per-query | 0.16568260267779952 | 0.17448134064251247 |
| calibrated P8 | 0.17368122598019067 | 0.19248427137384988 |

두 session 모두 최고 baseline은 per-query다. Model/best-baseline error 비는
원본 0.22894896808639995, 재현 0.3019089081743443으로 error 감소는 각각
**77.105103%와 69.809109%**다. Model의 fresh 기준 평균 절대오차는
**3.793286%와 5.267747%**로, 양쪽 모두 \(E\le0.10\) 및 최고 baseline보다
error를 25% 이상 줄이는 numerical 조건을 통과했다.

두 session에서 prediction 파일은 동일했다. 관측 target과 fresh 분모가 달라져
E도 달라졌다. 이 두 값은 두 환경 표본으로 만든 confidence interval이 아니며,
같은 48개 stream을 재측정한 것이므로 96개의 새 대화로 합산하지 않는다.

이 수치는 다음 의미로 한정된다.

- Target은 7-replay interval을 7로 나눈 시간의 **paired 차이 중앙값**이다.
  개별 질문 latency, marginal 중앙값의 차이, paired ratio 중앙값이 아니다.
- 분모는 해당 stream의 fresh marginal 중앙값이다. 3.793286%는 시간차
  \(d\) 자체를 분모로 한 MAPE나 \(R^2\)가 아니다.
- 각 stream에 같은 가중치를 준 평균이다. 질문·byte·전체 실행시간에 비례한
  가중 평균도 아니고, 모든 stream의 오차가 3.793286% 이내라는 보장도 아니다.
- 고정된 합성 stream의 관측 error다. 같은 grammar·모형을 공유하는 작성
  경계를 벗어난 실제 대화 모집단에 대한 일반화 구간을 추정하지 않았다.

평균에 가려질 수 있는 큰 오차도 남아 있다. 원본
`pressure_working_set-02`는 실제 \(d=2683.288857\) μs, 예측
1569.021690 μs로 normalized absolute error가 **12.778361%**다.
`phase_shift-02`는 실제 933.626357 μs, 예측 586.376409 μs로
**11.220936%**다. 둘 다 slowdown을 과소예측했다.
재현의 최대 normalized error도 `long_deep_churn-01`에서 **13.866374%**였다.
평균 기준의 성공을 점별 10% 오차 보장으로 표현해서는 안 된다. 이 오차 원인이
특정 누락 feature, CPU 상호작용, timing noise 중 무엇인지 이번 관측만으로
분해하지 않는다.

12개 stream은 적어도 한 feature가 개발의 coordinate별 min/max 범위를
벗어났고, 모두 horizon 64였다. 이는 보고용 extrapolation 표지다. 각 좌표가
개발 범위 안에 있다고 joint feature 조합이 개발 support 안에 있는 것은
아니며, 범위 밖 12개에서 관측한 결과도 임의 외삽의 정확도 보장이 아니다.

## 3. Speedup label 0개와 음의 관측값 0개는 다르다

[원본 timing](results/timing.json)과 [재현 timing](reproduction_timing.json)의
material label 분포는 다음과 같다.

| 집합 | speedup | slowdown | unresolved 또는 sign 제외 |
|---|---:|---:|---:|
| 원본 48개 | 0 | 35 | 13 |
| 재현 48개 | 0 | 36 | 12 |
| 두 session 공통 resolved 집합 | 0 | 32 | 16 |

공통 집합에서 제외된 16개는 양쪽 unresolved 9개, 원본만 unresolved 4개,
재현만 unresolved 3개다. 수치 error 평가에는 모두 포함했다.

한편 원본에서 paired point estimate가 음수인 stream은 2개였다.

| Stream | \(d/f\) point estimate | 저장된 interval을 고정 \(f\)로 나눈 구간 | 동결 label |
|---|---:|---:|---|
| `fit_working_set-02` | −3.539837% | [−4.361719%, −1.945215%] | unresolved |
| `fit_working_set-03` | −2.609429% | [−4.986162%, +4.695215%] | unresolved |

첫 사례의 개별 interval은 0 아래지만 전체가 −3% 아래에 있지는 않다.
따라서 “원본에서 가속이 전혀 관측되지 않았다”는 표현도 정확하지 않다.
**동결된 실질적 가속 판정 조건을 충족한 stream이 없었다**고 써야 한다.
재현의 `fit_working_set-02`도 point는 −5.384483%, 구간은
[−7.929677%, −2.846673%]여서 같은 margin 규칙에서는 unresolved였다.
관측된 음의 값과 사전 고정한 실질적 class 판정은 계속 구별한다.

Model은 `fit_working_set-01/-02/-03`의 세 stream에 음의 \(\widehat d\)를
예측했다. 그중 `-01`의 원본 point estimate는 작게 양수였고 세 사례 모두
unresolved다. Raw sign을 사후 label로 바꾸어 양방향 성공 사례를 만드는
것은 동결 규칙과 다르다.

원본 resolved slowdown 35개에서 model의 예측 부호는 모두 slowdown이다.
최종 공통 slowdown 32개도 모두 맞혔다. 그러나 per-query와 always-slowdown
baseline도 공통 집합에서 32개를 모두 맞혔다. 이 정확도를 양방향 분별력으로
발표해서는 안 된다. Speedup class 분모가 0이면 동결된 balanced accuracy는
**정의되지 않으며** 1, 0.5, 0 중
임의의 값으로 대체하지 않는다.

## 4. 개별 interval과 공통 subset의 한계

각 stream의 interval은 고정된 24 rounds를 2-round cycle 12개로 묶어
4,000번 resample한 paired-delta percentile interval이다. 새 stream을
resample하거나 대화 모집단을 표집한 것이 아니다. 같은 입력의 7 replays,
24 rounds, 두 방법 행을 독립 대화로 세지 않는다.

이 사후 검토는 저장된 interval을 읽었으며 bootstrap을 다시 실행하지 않았다.
다음 해석 제한은 원본 결과가 좋든 나쁘든 동일하다.

1. **개별 95%는 동시 95%가 아니다.** 48개 stream과 두 session의 모든
   판정이 한꺼번에 95%로 맞는다는 보장은 없다. 사후 multiple-testing
   보정을 새 성공 기준으로 끼워 넣지도 않는다.
2. 분모 \(f\)는 관측된 값을 고정했다. Interval은 분모와 분자를 함께
   resample한 시간비율의 joint interval이 아니다.
3. Cycle 교환가능성은 근사다. Host drift, GC·allocator·runtime cache,
   같은 머신에서의 연속 session 효과가 있을 수 있다. 실제 finite-sample
   coverage나 session 간 독립성을 증명하지 않았다.
4. 두 session에서 같은 resolved sign인 집합은 **측정 결과로 선택된 subset**이다.
   신호가 크거나 변동이 작은 사례가 남기 쉽다. 그 subset의 정확도를
   unresolved·session-discordant 사례나 전체 자료에 전이하지 않는다.

Numerical \(E\)에서는 모든 48개 stream을 유지한다. Sign 집합의 제외 수와
각 class 수는 별도 공개한다. 이번 자료에서는 speedup class 자체가 없으므로,
subset 평가를 정교하게 계산하더라도 빠진 class의 recall을 복원할 수 없다.

## 5. 같은 정책의 시간차를 예측했으며 정책을 가속한 것은 아니다

Phase10은 Phase09의 off 함수를 그대로 실행했다. [원본 receipt](results/receipt.json)는
preservation failure 0과 prediction seal이 timing보다 앞섰음을 기록한다.
Model seal은 `2026-10-22T13:53:40.943582+00:00`, 원본 timing 시작은
`2026-10-22T13:53:41.276997+00:00`이다. 동결 model hash는
`160ecc6b568a475878473eed411a1caff96d99ede41ee984231ecb5016621365`다.
이는 로컬 기록이며 외부 사전 등록이 아니다.

재현 receipt는 model·features·predictions·보존 결과를 포함한 결정적 산출물
8개의 byte 동일성과 preservation failure 0을 기록했다. 시간은 이 동일성
비교 대상이 아니다. 재현에서도 기존 calibration의 같은 동결 coefficient를
사용했으며 재현 시간을 학습으로 돌려보내지 않았다. 두 session의 기록된
Python·OS·CPU model·affinity는 같으며 다른 머신 일반화 실험이 아니다.

원본의 별도 whole-workload 보조 측정에서는 paired-delta 중앙값이
36,666.915750 μs, fresh marginal 중앙값이 223,951.491250 μs여서
\(d/f=+16.372704\%\)였다. 저장된 delta interval을 고정 fresh 중앙값으로
나눈 값은 [12.264125%, 17.296853%]다. 이 값도 ratio 중앙값이나 marginal
시간 중앙값의 차가 아니다. 같은 보조 실행의 selective marginal 중앙값은
251,276.067750 μs이다. 두 marginal 중앙값의 차를 위 paired-delta와
혼용하면 다른 숫자가 나온다.

재현의 같은 보조 지표는 \(d=41,032.057500\) μs,
\(f=221,852.562500\) μs로 \(d/f=+18.495192\%\)였고, 저장된 정규화
interval은 [14.866775%, 24.344212%]였다. 두 세션 모두 전체 workload의
관측 방향은 slowdown이다. 이 보조값은 stream별 numerical E와도, stream별
paired 중앙값을 더한 값과도 다른 추정량이다.

좋아진 것은 **고정 실행의 시간차에 대한 예측 error**다. 이 모형은 실행
경로를 바꾸거나 selector에 의사결정을 제공하지 않는다. 따라서 이 연구의
수치 성공을 selective의 실제 가속, 운영 계산 절감, token·요금 절감으로
바꾸어 해석할 수 없다.

또한 예측에는 완료된 전체 stream을 여러 경로로 replay한 feature가 필요하다.
[prediction receipt](results/prediction_receipt.json)의 원본 audit+feature wall time은
18.231712초다. 이것은 네 경로 보존·gold 감사와 두 추가 trace replay가
포함된 연구 경로이며 최소한의 predictor-only 실행비가 아니다. 이를 운영
추출 비용으로 단정하거나, 반대로 추출 비용을 0으로 간주하면 둘 다 틀린다.
Feature 추출비까지 포함한 단일 호출 손익·online routing의 유용성은 측정하지
않았다.

이 결과가 지지할 수 있는 범위는 고정 환경과 공유 문법의 새 합성 stream에서
완료된 trace 요약이 단순 baseline보다 시간차 크기를 잘 설명했다는 것이다.
관측 범위를 벗어난 양방향 부호 판별, 다른 machine으로의 calibration 전이,
새 자연어 grammar로의 일반화는 미확인이다.

## 6. 예측 coefficient를 CPU 단가로 읽으면 안 되는 실제 사례

[동결 model](calibration/model.json)의 일부 coefficient는 다음과 같다.

| Feature | 동결 coefficient, μs/feature |
|---|---:|
| `queries` | −0.06032764516799917 |
| `raw_encode_bytes` | +0.0006130265803946536 |
| `saved_stage_calls` | −4.500460431356451 |
| `encoded_context_payload_bytes` | +0.09994132676321678 |
| `admission_attempts` | +8.545562442969073 |
| `policy_control_actions` | −0.03016994607097888 |

음의 control-action 계수에서 “control action을 더 실행하면 빨라진다”는
결론은 나오지 않는다. 이 feature는 off 실행에서 삭제된 ledger가 같은
branch를 세는 trace 요약이다. 다른 feature와 독립적으로 action 하나만
추가하는 intervention을 수행하지 않았고, 그런 feature 조합이 고정 프로그램에서
실현 가능한지도 자동으로 보장되지 않는다.

양의 payload-byte 계수와 raw-byte 계수 역시 실제 byte의 CPU 단가가 아니다.
Admission·payload·context·control counts가 연관되고, omitted interactions나
잔차를 각 열이 나누어 설명할 수 있다. Ridge는 예측식과 penalty에 대해
유일한 수치 해를 정할 뿐 causal decomposition을 식별하지 않는다.

수학적으로 \(d=x^T\beta+r\)에 대해 임의의 \(c\)를 택하면

\[
 d=x^T(\beta+c)+(r-x^Tc)
\]

도 같다. 잔차 구조를 제약하는 추가 가정이나 intervention 없이 실제 전체시간을
부품별 원인 비용으로 유일하게 나눌 수 없다. [THEORY T4 및 C1/C2](THEORY.md)는
실제 feature가 같아도 raw regex 입력·policy insertion order가 다를 수 있음을
이미 보였다. 해당 충돌 쌍의 시간차는 측정하지 않았으며, 이번 새 결과가 그
미측정 조건을 자동으로 채워 주는 것도 아니다.

Model error의 감소는 이 모형의 예측적 유용성에 관한 관측이다. 각 coefficient의
인과 해석, 부품별 정확한 CPU 가격표, 고정 grammar 밖의 충분통계라는 주장은
추가하지 않는다.

## 7. 후속 한 가지 질문: 짧은 원문의 eager encoding을 조건부로 없앨 수 있는가

다음 단계의 후보는 `MIN_CHARS` 미만 원문의 eager raw UTF-8 encoding을
eligibility 판단 뒤로 늦추는 **한 가지 변경**이다. 이번 Phase10에서는
구현하거나 측정하지 않았다. Coefficient 부호가 아니라 다음 실제 데이터
의존성을 제안 근거로 삼는다.

[Phase09 off_selective.py](../phase09/off_selective.py)의 `read`에서는
`raw = text.encode('utf-8')`, `size = len(raw)`를 eligibility 이전에 계산한다.
이후 `eligible=False`이면 다음이 성립한다.

- `cache.possible`, `cache.get`과 `get_key`가 실행되지 않는다.
- Cache hit가 없으므로 원래 cheap/scope/detail 경로가 원문 문자열을 파싱한다.
- Stage 값은 admission을 위해 수집되지 않고, `cache.admit`도 호출되지 않는다.
- `raw`의 소비처인 `get_key`와 `size`의 소비처인 `admit`이 모두 실행되지 않는다.

따라서 이 경로에서 raw/size는 semantic output·policy state로 이어지는
데이터 의존성이 없다. Builtin UTF-8 encodable 입력, pure parser·encoder,
single-thread·입력 불변, 충분한 자원이라는 기존 범위 아래에서만 그 두
계산을 조건부로 삭제하는 보존 논증을 구성할 수 있다. `eligible=True`의
exact key bytes, L·C·R, surplus, admission, victim, immutable stages를
그대로 유지하고, 전체 prefix의 Obs와 \(\pi\)가 같은지 다시 검증해야 한다.

전체 snapshot serialization·UTF-8 encoding·hash와 최종 근거 rendering은
이 제안의 삭제 대상이 아니다. 원문 읽기·검증이 사라지는 제안이 아니다.
Resource exception이나 custom object side effect의 동등성도 기존 증명
범위를 넘어 추가 주장하지 않는다.

이 조건부 데이터 의존성은 **삭제 가능성**의 근거다. 실제 시간 감소의
보장은 아니다. Branch 배치·할당·runtime 상호작용 때문에 elapsed time의
단조성을 자동으로 얻을 수 없다. 다음 단계가 이 후보를 채택하더라도 단일
변경의 보존과 실제 시간을 별도 검증해야 하며, 이번 수치 결과로 그 실험을
대신할 수 없다. Phase11 실행은 현재 범위 밖이다.

## 8. 읽은 증거·아직 읽지 않은 부분·정정 범위

이 역할은 원본 `scores.json`의 모든 stream point/error·집계, 원본 timing의
environment·method summary·개별 interval·label, prediction seal·receipt,
동결 model, freeze 기록과 이론을 읽었다. 원시 round에 대한 bootstrap 재실행이나
새 timing, profiler, 새 dataset 생성은 하지 않았다. Holdout 원문·builder를
열어 사례를 고르지도 않았다. 별도 재집계·재현 역할의 검증과 이 해석 검토는
구별한다.
최종화 과정에서는 combined 결과의 모든 공통·제외 stream과 집계, 재현
receipt·scores 집계와 큰 오차·음의 point 사례, 재현 timing의 environment와
해당 사례의 저장 interval을 추가로 읽었다. 같은 모델의 역할 분리이며
외부 독립 검증으로 부르지 않는다.

Phase09 수치에 대한 새 정정은 없다. BA float 경계의 수정은 holdout 공개 전
개발 기록에 있는 구현 정정이다. 원래 ≥.10의 유리수 조건을 구현한 것이며,
새 결과를 보고 기준을 바꾼 사후 정정으로 서술하지 않는다. 자세한 시점과
영향은 [DEVELOPMENT_AUDIT.md](DEVELOPMENT_AUDIT.md)와 동결
[MATH_REVIEW.md](MATH_REVIEW.md)를 따른다.

양 session의 numerical 조건은 지지되고, 양방향 sign 조건은 필요한 class가
없어 미확인이다. 그래서 joint H10은 미확립이다. 이 두 결론을 함께 남기는
것이 동결한 질문에 대한 완성된 답이다. 동결 모형이나 판정 기준을 다시
최적화하지 않는다. SOOM 운영 변경은 없다.
