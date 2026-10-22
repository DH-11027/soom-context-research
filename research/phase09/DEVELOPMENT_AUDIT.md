# Phase09 개발 종료 기록

새 holdout 원문·gold·builder를 구현자가 열기 전에 작성했다.
정책·동결 의미 코드를 수정하지 않고 계측 제거와 평가기를 개발했다.

## 실제 검사

- `erase.py --check`: 원본 소스로 재생성한 두 비계측 파일과 삭제 manifest의 exact bytes 일치.
- `counterexamples.py`: hit 삭제와 같은 길이 identity 오류의 실행 가능한 반례.
- `audit.py`: 새로 작성한 20 prefix, Phase08 개발 89 step, 원본 계측 경로 40회 대조,
  정책 상태 mutant 15개, gold 평가기 mutant 9개. 실패 0.
- `run_study.py --dev`: Phase08 개발 89 + 이전 주평가 432 + Phase05–07 회귀 1356
  = **1877 prefix**, 507 stream container, 7508 method rows.
  관찰 5631비교, on/off 실제 실행 trace 3754비교, policy 상태·decision trace 각1877비교에서
  불일치 0. 구조·적용 가능한 gold 검사 실패 0.

507 stream container나 반복 실행을 507개의 새 독립 대화 표본으로 해석하지 않는다.
개발89가 audit와 전체 회귀에 둘 다 들어가며, 이를 합산해 별개 평가 분모를 만들지 않는다.
이 단계에서 새 주평가 timing은 실행하지 않았다.

## 동결 전 수정과 두 개발 산출물

첫 `development_results/`와 최종 `development_final/`을 둘 다 보존한다.
첫 검사 후 summary의 모든 int를 무조건 더하던 표현을 정제했다. Peak/retained/entries/
directory 등 occupancy는 시간에 걸쳐 더한 비용이 아니므로 비용 합에서 제외하고
별도의 최대값으로 보고하도록 바꾸었다. Runtime/정책/입력/실제 결과는 바꾸지 않았다.
최종 개발 재실행에서 policy states gzip은 첫 실행과 byte-identical이다.
Rows에는 이 최대값 재집계에 필요한 상태 보고 필드가 추가되어 파일 bytes가 달라진다.

Gold mutant의 첫 fixture가 문법 밖 place 표현이라 정상부터 opaque였던 문제는
`EVALUATOR_REVIEW.md`에 기록한 대로 지원 문법으로 고치고 certified 전제를 assert했다.
이는 새 평가 전 검사 fixture 수정이며, 기존 Phase08 자료 또는 새 holdout 결과를
보고 맞춘 변경이 아니다.

최종 개발 결과와 실행기는 모두 보존한다. 기존 Phase01–08과 SOOM 운영 변경은 없다.
