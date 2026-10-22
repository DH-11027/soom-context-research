# Phase08 — 비용 인지 순수 해석 재사용

Phase07 기준 `6da051c0132811184ecf39975d7ff647a1f47842` 위의 연구 전용 추가다.
SOOM 운영과 기존 동결 파일은 변경하지 않는다.

**새 합성 36 stream/432 step에서 호출 −12.52%, 전체 P8 작업점수 −4.28%.
그러나 전체 로컬 시간은 원본 +12.37%, 재현 +15.21%로 늘었다.**
최종 누적 이득은 8/36 stream에 집중됐다. 실제 LLM 비용·토큰·품질 개선은 측정하지 않았다.

## 먼저 읽을 파일

1. [HANDOFF_BACK.md](HANDOFF_BACK.md): 결과·증명·한계·재현·다음 한 가지 연구를 묶은 반환 문서.
2. [INHERITANCE_AUDIT.md](INHERITANCE_AUDIT.md): Phase07 재현과 계측 한계 확인.
3. [PROTOCOL.md](PROTOCOL.md), [THEORY.md](THEORY.md): 동결 가설·계약·반례.
4. [POSTFREEZE_REVIEW.md](POSTFREEZE_REVIEW.md), [DATA_REVIEW.md](DATA_REVIEW.md): 별도 재현·재집계·자료 분포.

## 구현

`frozen.py`는 기존 의미 코드를 hash로 결합한다. `runtime.py`는 pure stage만 보관한다.
256문자 미만 bypass, resident 문자 길이 음성 필터, 정확한 raw/context key,
실제 관측한 complete 3stage bundle, 크기·과거 hit를 사용하는 보관 정책이다.
질문별 TOP·답·선택·copy 당시 값은 저장하지 않는다. 모든 snapshot 검증은 유지한다.

`evaluation.py`는 public 필드만 raw-only 선택기에 전달한다. 비교군은 frozen `fresh`,
Phase07 `lru`, 새 `selective`, 길이 음성 필터만 끈 `no_directory`다.

기존 논리 바이트 장부 P7을 유지하고, 정책 판단·관리 event를 포함해
**P8=P7+8×control_actions**를 주지표로 동결했다. P8은 가중 작업점수이며 CPU나 byte의 실측치가 아니다.

| 주평가 합계 | fresh | selective |
|---|---:|---:|
| 실제 파서 실행 | 4,768 | 4,171 |
| 파서 입력 bytes | 21,831,216 | 13,204,284 |
| Snapshot 검증 bytes | 8,431,437 | 8,431,437 |
| 출력 UTF-8 bytes | 165,238 | 165,238 |
| P8 | 30,427,891 | 29,124,198 |
| 원본 전체 시간 중앙값 | 61.849 ms | 69.497 ms |

오류는 방법별 false certification 0/378, containment 0/402, selected-gold 공동 투영
0/411이다. Gold 제외는 invalid 12+membership 투영 미정의 9다. 411에는 unsupported 9의
전체 이력 선택 확인도 포함된다. 후보 세 방법과 fresh의 관찰 불일치는 0/1,296이다.
정확성·비용 분모와 외부 의미 평가 미실행 경계는 반환 문서를 따른다.

## 재현

Python 3.12.14 / Linux x86_64 / glibc 2.39에서 실행했다. 표준 라이브러리만 필요하다.
저장소 root에서 존재하지 않는 새 경로를 사용한다. 원본 결과를 덮어쓰지 않는다.

```bash
python tools/verify_archive.py
python research/phase08/run_study.py --verify
python research/phase08/holdout_builder.py --check
python research/phase08/run_study.py --run \
  --output /tmp/soom-phase08-repro-new \
  --compare research/phase08/results
python research/phase08/recount_results.py \
  --output /tmp/soom-phase08-recount-new.json
```

별도 실행의 결정적 5개 파일은 바이트 단위로 일치했다. Timing은 일치 비교에서 제외했다.
원본 결과·행은 [results/](results/), 별도 실행은 [reproduction_receipt.json](reproduction_receipt.json)과
[reproduction_timing.json](reproduction_timing.json), 원시 행 재집계는
[recount_results.json](recount_results.json)에 있다.

## 자료·동결

새 자료 seed는 2026102208이다. 12 family×3 parameters×12 step이며 별도 동일 모델 작성자가
공개 설계를 공유해 작성했다. 1,728행은 432 step×4방법이다. 외부 독립 자연어 평가가 아니다.
긴 원문은 제한 문법의 noop quote이며 긴 여섯 family가 fresh byte score의 97.50%를 차지한다.
Phase07 자료·사후 진단은 알려진 개발 정보, Phase05/06/07의 1,356질문은 회귀다.

로컬 freeze는 2026-10-22 11:19:06 UTC이며 commit은
`4a128204cad4abbf374fea7326b6c844f800812f`다. 전체 hash는 [freeze.json](freeze.json)에 있다.
GitHub 공개는 평가 후다. 로컬 동결을 외부 사전 등록이라고 하지 않는다.
공개 Git commit과 로컬 동결 commit의 차이는 반환 문서에 설명했다. 원본 로컬 Git 객체는
[pre_evaluation.bundle](pre_evaluation.bundle)에 보존했다.

```bash
git bundle verify research/phase08/pre_evaluation.bundle
git fetch research/phase08/pre_evaluation.bundle \
  refs/heads/research/phase08-cost-aware-reuse:refs/heads/phase08-local-freeze-evidence
```

다음 연구는 동일 의미·검증을 유지하면서 fresh와 selective 양쪽의 계측을 제거한 시간용
경로의 실제 전체 시간이다. 장부 산출 경로와 각각의 관찰·resident 결정을 검증하며,
정책 결정에 필요한 key·payload encoding과 크기 계산은 유지한다.
이번 결과를 운영에 적용하지 않는다.
