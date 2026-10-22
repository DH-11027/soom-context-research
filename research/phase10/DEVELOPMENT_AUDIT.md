# Phase10 개발 경계와 실행 이력

## 개발 자료와 목표

Phase09 공개 완료 `0c08785fcee9ab146f33fa8a7d94a4b7700833aa`의 코드·결과를
직접 기준으로 삼는다. Phase09의 시간과 자료를 보고 후속 방향을 정했으므로,
그 36 stream은 모두 알려진 개발 자료다. Horizon 1/4/12/36으로 자르거나
순환한 144 stream도 새 독립 평가로 세지 않는다.

Phase10은 실행 정책을 바꾸지 않는다. 전체 stream의 별도 untimed trace에서
고정 특징량을 추출하고, 기존 비계측 fresh/selective의 실제 시간차를 예측한다.
전체 trace가 필요하므로 온라인 미래 예측이나 배포 비용 절약을 주장하지 않는다.

`PROTOCOL.md`에 특징량 10개, ridge 0.01, 세 수치 baseline, 두 방향 class의
최소 수, 주 오차식·성공 기준·시간 반복 수·순서·구간·중단 조건을 개발 시간
calibration 전에 적었다. 결과가 나온 뒤 이 규칙을 선택하지 않는다.

## 동결 전 발견과 수정

1. 추가 character replay의 초기 Obs 대조는 실제 반환 key만 골라 비교했다.
   이 방식은 반환 key가 빠지는 오류를 놓칠 수 있었다. 기대 row의 고정 Obs
   whitelist를 기준으로 비교하도록 수정했다. `scope_trace`와 `prediction`
   제거 mutant가 모두 거절됨을 별도 감사가 확인했다.
2. `raw_p8_sign`의 0은 수학적 부호 함수가 아니라 slowdown으로 분류하는
   결정 규약임을 코드와 문서에 명시했다. 수치 zero-change baseline은 그대로 0이다.
3. 감사 초안이 전체 records와 방문 수가 다를 것으로 예상한 long-deep fixture에서는
   실제로 두 값이 같아 assertion이 실패했다. 이미 선택한 fit fixture의 36대32를
   쓰도록 감사 코드만 수정했다. 정책·자료·특징량·예측 규칙은 바꾸지 않았다.
4. 보정 실행 전 추가 source review에서 재현 시 원 calibration의 재계산과 새 시간에
   대한 재학습을 명시적으로 분리했다. Prediction에는 저장 frozen model을 읽어 쓰고,
   재계산 결과는 동일성 witness로만 저장한다. 실패 시 단계·예외·실제 progress 유무·
   가능한 stdout/stderr를 남기도록 실행 receipt도 보완했다.
5. 단순 기준 오차와 모델 오차가 모두 0일 때 `0≤0.75×0`을 25% 개선으로 잘못
   부를 수 있는 수치 경계를 발견했다. 최소 baseline 오차가 양수여야 개선 조건을
   통과하도록 보정 시간 실행 전에 명시했다. 수치 실패와 방향 class 부족이 겹치면
   수치 실패를 결론 label에서 먼저 표시하고 방향 미확인은 별도로 남긴다.

개발 감사는 기존 5 stream/20 prefix를 썼다. 네 경로의 계약 검사,
plain/diagnostic 두 off의 40 prefix Obs·π 직접 비교, 특징량의 독립 재계산이
통과했다. 별도 합성 수치 24개에 대한 β좌표 Cholesky 해와 주 구현의 정규화
Gauss–Jordan 해 최대 절대차는 `2.957634137601417e-13`이었다.
이는 수치 구현 검사이고 실측 시간 데이터가 아니다.

## 역할과 새 자료의 열람 경계

- 주 구현자: 실행 연결·특징량·예측식·시간 worker·집계·동결.
- 별도 수학 역할: 정리·가정·실행 가능한 반례. 새 자료 미열람.
- 별도 평가/재현 역할: 상속한 Phase09 증거, 특징량·수치 구현 감사. 새 자료 미열람.
- 별도 자료 작성 역할: 새 48 stream/1,176 step을 작성하며 selector·모형·시간 결과를
  실행하거나 읽지 않았다. 구현자에게는 설계 분포·수량·hash만 전달했다.

모든 역할은 같은 모델이며 공개 문법을 공유한다. 외부 독립 검증이 아니다.
개발 계획과 코드 checkpoint, calibration, 최종 동결은 로컬 기록이다.
GitHub 공개는 평가 이후에 하며 외부 사전 등록으로 표현하지 않는다.

이 문서의 calibration 결과와 최종 동결 정보는 실행 후 별도 절로 덧붙인다.
원래 계획의 선택 기준을 소급해서 고치지 않는다. 기존 연구와 SOOM 운영 변경 없음.

## 계획 commit 이후, 새 평가 전 발견한 정확 산술 경계

계획 commit `c18d0d5b2522a7291871a67563a65ab261645eff`를 기록하고 개발
calibration을 시작한 뒤, 아직 calibration 시간 label과 holdout을 읽지 않은
상태에서 BA의 정수비율 경계를 작은 수치 열거로 확인했다. Class 크기 4/15,
모델 정답 수 4/10, 기준 정답 수 4/7이면 BA는 각각 `5/6`, `11/15`다.
차이는 정확히 `1/10`이므로 사전 규칙을 통과해야 한다. 그러나 float로는
`0.8333333333333333 < 0.8333333333333334`가 되어 경계에서 실패했다.

최종 동결 전에 `scoring.joint`의 두 BA threshold 판정만 정수 count의
`Fraction`으로 바꾸었다. 규칙의 .75 및 +.10은 그대로다. Float 출력은
표시용으로 남는다. 이것은 평가 결과를 보고 경계를 옮긴 변경이 아니다.
Calibration의 `score`, fitting, CV와 timing은 `joint`를 사용하지 않으므로
이 수정의 영향을 받지 않는다. 보정 session을 다시 실행하지 않는다.
계획 commit과 최종 동결의 source가 완전히 같다고 주장하지 않으며 두 버전을
Git bundle에 보존한다. 해당 작은 반례도 동결 전에 감사 코드에 추가한다.

## 단 한 번의 개발 보정 결과

- 계획·source 기록 commit: `c18d0d5b2522a7291871a67563a65ab261645eff`.
- 계획 timestamp: `2026-10-22T13:46:53.968456+00:00`.
- Calibration 실행: `13:46:58.832095`–`13:49:29.634037 UTC`.
- 그 안의 worker: `13:47:24.644089`–`13:49:29.532582 UTC`.
- 주 구현자가 완료 출력을 처음 회수·열람한 시각: `13:50:40 UTC`.
- 알려진 144 derived stream/1,908 prefix의 보존 실패 0;
  Obs 5,724비교, on/off 실제 trace 3,816비교, policy state/trace 불일치 0.
- 시간 session 1회, stream당12round, interval당7 whole-stream replay.
  모든 raw time·warmup·순서·progress를 `calibration/`에 보존했다.

| 개발 normalized absolute error | Full-data fit | Leave-family-out 진단 |
|---|---:|---:|
| `trace_ridge` | 0.043779954354 | 0.048315927612 |
| `zero_change` | 0.211891913124 | 0.211891913124 |
| `per_query` | 0.172257087841 | 0.192227284991 |
| `p8_calibrated` | 0.161649152097 | 0.162633943982 |

Normal-equation 최대 잔차는 `2.7755575615628914e-17`다.
최종 모델 SHA-256은 `160ecc6b568a475878473eed411a1caff96d99ede41ee984231ecb5016621365`다.
개발 결과를 읽은 뒤 feature, lambda, baseline, 성공 기준, 새 자료를 바꾸지 않았다.
Full-data 모델 한 개와 사전에 정한 12개 family fold의 진단을 구별한다.
CV는 모델 선택에 쓰지 않았다. 이후 동일 raw calibration에서 refit하는 것은
알고리즘·파일 동일성 검사이고 새 시간으로 재보정하는 session이 아니다.

이 수치는 모두 개발 자료의 결과다. 개발 오차가 작다는 사실이 새 stream의
성공이나 온라인 예측 가능성을 뜻하지 않는다. 다음 단계는 코드·모형·새 자료
hash를 최종 동결한 후, 새 자료의 관찰·정책 상태 감사 및 prediction 봉인이다.
