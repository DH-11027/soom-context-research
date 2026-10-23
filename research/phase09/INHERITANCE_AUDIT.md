# Phase09 출발점 재현·평가기 인수 감사

작성일: 2026-10-23 KST. 검토자: 주 구현자와 역할을 나눈 동일 모델 에이전트.
외부 독립 검증이 아니며, 다른 환경의 재현도 아니다.

## 기준과 보존

직접 기준 commit은 `efba3224dd09d5c5e2bf9d9be11734fa10b32502`다. Phase08 원본
코드·자료·결과를 수정하지 않고 모든 실행 산출물을 새로운 `/tmp` 경로에 작성했다.
최종 전달에 필요한 증거는 `research/phase09/inheritance/`에 복사했다.
Phase08 공개 완료 commit과 로컬 freeze `4a128204cad4abbf374fea7326b6c844f800812f`는
서로 다르며, 후자의 Git 객체를 담은 원본 bundle은 검증에 통과했다.

## 실제 실행

```bash
python tools/verify_archive.py
python research/phase08/run_study.py --verify
python research/phase08/holdout_builder.py --check
git bundle verify research/phase08/pre_evaluation.bundle
python research/phase08/run_study.py --run \
  --output /tmp/soom-phase08-repro-for-phase09-audit \
  --compare research/phase08/results
python research/phase08/recount_results.py \
  --output /tmp/soom-phase08-recount-for-phase09-audit.json
```

첫 네 명령의 stdout·stderr·종료 코드는 `inheritance/prechecks.json`에 있다.
주 실행 영수증은 `inheritance/phase08_receipt.json`, 시간 전체 원시값은
`inheritance/phase08_timing.json`, 재집계 결과는 `inheritance/phase08_recount.json`이다.

- Archive 59개 파일, 18개 동결 소스 결합 검증 통과. 이는 무결성·패키징 확인이며
  원래 모든 실험의 재수행이나 과학적 주장의 증명이 아니다.
- Phase08 freeze·baseline hash가 모두 일치했다.
- 자료 builder의 36 stream / 432 step, gold·schema 검증 통과.
- `audit.json`, `holdout_results.json`, `holdout_rows.json.gz`,
  `regression_results.json`, `regression_rows.json.gz`의 결정적 5개 파일이
  기존 결과와 **byte-identical**이었다.
- 주평가 1,728행과 회귀 5,424행을 별도 집계하여 불일치 0.
- Selective와 no_directory의 resident 상태는 매 step 432/432에서 같았다.
  이는 기존 고정 runtime replay이며 별도 구현한 캐시나 독립 의미 파서 검증이 아니다.

## 결과 재확인과 시간 변동

Phase08 주평가의 fresh→selective 파서 실행은 4,768→4,171,
P8 합계는 30,427,891→29,124,198(−4.2845%)으로 재현됐다.
8/36 stream이 최종 점수 이득, 28/36이 최종 손해였고,
이득 family는 long_deep_repeated, working_set_fit, working_set_pressure 세 개다.
기존 수치를 정정할 근거를 발견하지 않았다.

이번 **계측된 Phase08 경로**의 전체 workload 시간 중앙값은 fresh 61.835218 ms,
selective 70.742949 ms(+14.4056%)다. 원본 +12.37%와 이전 별도 재현 +15.21%를
대체하지 않는 새 로컬 관측이다. 이 재현에는 새 Phase09 비계측 경로가 없다.
no_directory는 75.594985 ms여서 이번에는 selective보다 느렸다. 기존 두 실행에서
길이 directory 경로가 더 느렸던 순서가 이번 실행에서는 뒤집혔다. 이 차이만으로
필터의 CPU 이득이나 시간 차이 원인을 입증할 수 없다.

실행 환경은 Python 3.12.14 / CPython / Linux 6.18.55 x86_64 / glibc 2.39다.
원래 7회 반복·방법 순서·계측을 그대로 사용했다. 유리한 재현만 고르거나 추가 반복으로
이 값을 교체하지 않았다. 새 주가설을 선택한 이상 Phase08 자료는 개발·회귀 자료이며
Phase09의 새 독립 평가 분모에 합치지 않는다.

## 실제 읽기 범위와 감사 경계

이 역할은 `docs/RETURN_TEMPLATE.md`, Phase08 `run_study.py`, `evaluation.py`,
`runtime.py`, `frozen.py`, Phase07 `baseline.py`, `cached.py`, Phase06 `scoped.py`와
위 실행으로 생성·검증한 영수증·요약·시간 자료를 직접 읽었다.
원시 행·gold·hash는 기존 builder와 재집계 프로그램으로 검사했다.
저장소 전체, 모든 과거 raw 원문, 외부 자연어 정답을 읽거나 수기 검증했다고 주장하지 않는다.
Phase09 미열람 자료는 동결 전 이 역할에서 읽지 않는다.

## 계측 제거에 관한 초기 평가기 관찰

Phase08 selective의 admission/replacement는 `cost` 합계가 아니라 실제 raw/context/payload
길이와 resident의 hits/surplus/size/order에 의존한다. 그 자체로 cost 장부 삭제의 근거가
되지만, 실제 크기 계산·stage eligibility 관측·hit 갱신·정렬·directory 갱신은 보존해야 한다.
P7 LRU adapter의 `cache_entry_hits` 차이 검사는 추가 `lru_touch` event를 기록하기 위한
것으로, 이번 주 비교인 fresh/selective의 정책 동등성 증명에 전용할 필요는 없다.
검증 실패와 미지원 질문의 early exit는 resident 상태를 바꾸지 않아야 한다.
