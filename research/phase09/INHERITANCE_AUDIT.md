# Phase09 출발점 감사 — Phase08 고정 commit 재현

작성: 2026-10-22. 주 구현자와 별도 역할을 맡은 동일 모델 에이전트.
같은 실행 환경의 별도 실행이며 외부 독립 재현·외부 자연어 정답 검증은 아니다.

## 1. 기준과 실제 읽은 범위

읽기·재현 기준은 공개 완료 commit
`efba3224dd09d5c5e2bf9d9be11734fa10b32502`다. 현재 연구 checkout의 새 branch에
원래 파일을 그대로 두고, 이 문서와 증거만 `research/phase09/` 아래에 추가했다.
Phase08 로컬 freeze commit `4a128204cad4abbf374fea7326b6c844f800812f`와 공개 완료
commit은 다르다. 이번 bundle 검증도 그 둘을 합치지 않는다.

지정된 `HANDOFF_BACK.md`, `PROTOCOL.md`, `THEORY.md`, `POSTFREEZE_REVIEW.md`,
`DATA_REVIEW.md`를 순서대로 읽었다. 구현·평가 계약을 위해 Phase08 `frozen.py`,
`runtime.py`, `evaluation.py`, `audit.py`, `run_study.py`와 Phase07 `baseline.py`,
`cached.py`, `study.py`, Phase06 `scoped.py`를 읽었다. Phase08 `MATH_REVIEW.md`,
`EVALUATOR_REVIEW.md`, `DEVELOPMENT_AUDIT.md`의 관련 감사 내용을 확인했다.
반환 형식은 `docs/RETURN_TEMPLATE.md`에서 확인했다.

프로그램으로 검사한 범위는 아래 명령의 source hashes, builder가 생성한 자료와
저장 자료의 일치, 모든 결정적 재현 결과, 주평가 1,728행 및 회귀 5,424행의 재집계다.
새 Phase09 holdout 원문·builder·라벨은 이 감사 중 열지 않았다. 저장소 전체를 읽거나
Phase01부터 모든 실험을 새로 실행한 작업은 아니다. Phase08의 모든 자연어 원문과
typed gold를 외부 정답으로 다시 판정하지 않았다.

## 2. 실제 실행한 명령

```bash
python tools/verify_archive.py
python research/phase08/run_study.py --verify
python research/phase08/holdout_builder.py --check
python research/phase08/run_study.py --run \
  --output /tmp/soom-phase08-repro-for-phase09 \
  --compare research/phase08/results
python research/phase08/recount_results.py \
  --output /tmp/soom-phase08-recount-for-phase09.json
git bundle verify research/phase08/pre_evaluation.bundle
```

6개 명령 모두 종료 코드 0이다. 명령별 시작·종료 시각과 실제 stdout/stderr는
[`inheritance/command-01.json`](inheritance/command-01.json)부터
[`inheritance/command-06.json`](inheritance/command-06.json)에 보존했다.
전체 환경·증거 hash는 [`inheritance/receipt.json`](inheritance/receipt.json)에 있다.
원본 결과를 덮어쓰지 않았다. 후속 재현은 이미 존재하지 않는 새 output 경로를 사용해야 한다.

환경은 Python **3.12.14 / CPython / Linux 6.18.55 x86_64 / glibc 2.39**다.
Phase08 실행 시작은 `2026-10-22T11:55:06.406607+00:00`(한국 20:55:06),
종료는 `2026-10-22T11:55:14.330290+00:00`(한국 20:55:14)다.
이번 Phase08 전체 실행기는 약 7.93초에 끝났으며, 이것은 아래 workload timing과 다른 양이다.

## 3. 검증·동일성 결과

- 최초 archive 59파일, 기존 frozen source 결합 18개 검증 통과.
- Phase08 모든 동결 및 기준 source hash 검증 통과.
- Builder 재생성 검사: 12 family / 36 stream / 432 step, schema와 gold 검사 통과.
- 적용 가능한 gold 411 step, 지원 gold 402, invalid 12, membership 제외 9,
  unsupported 9라는 자료 분모가 원래 기록과 같았다.
- Phase08 freeze bundle 검증 통과. Bundle은 Phase07 공개 완료 commit
  `6da051c0132811184ecf39975d7ff647a1f47842`를 prerequisite로 요구한다.
  로컬 freeze가 외부 사전 등록이었다는 증거는 아니다.

| 새 실행 결과 | Phase08 원본과 비교 |
|---|---|
| `audit.json` | byte-identical |
| `holdout_results.json` | byte-identical |
| `holdout_rows.json.gz` | byte-identical |
| `regression_results.json` | byte-identical |
| `regression_rows.json.gz` | byte-identical |

위 5파일의 SHA-256과 직접 비교 결과는
[`inheritance/reproduction_receipt.json`](inheritance/reproduction_receipt.json)에 있다.
시간 표본·receipt 시각은 동일성 비교 대상이 아니다.

원래 `recount_results.py`를 별도 실행한 결과도 원래 `recount_results.json`과
byte-identical이었다. 주평가 **1,728행 = 432 step ×4방법**, 역사적 회귀
**5,424행 = 1,356질문 ×4방법**을 각각 재집계하여 mismatch 0이다.
별도 directory state replay는 432 prefix의 전체 resident 상태 mismatch 0,
864 결과·비시간 장부의 원본 일치를 다시 확인했다.
재집계는 기존의 별도 집계 구현을 재실행한 것이며 새로 독립 작성한 평가기는 아니다.
그 전체 JSON은 [`inheritance/recount_results.json.gz`](inheritance/recount_results.json.gz)에
결정적 gzip으로 보존했다. 압축 해제한 SHA-256과 원본 일치는 receipt에 기록했다.

## 4. 재확인한 결과와 새 시간 관측

Fresh→selective의 결정적 값은 파서 호출 **4,768→4,171**, P8
**30,427,891→29,124,198**, 출력 **165,238→165,238 bytes**로 같았다.
최종 손익은 이득 8/36 stream, 손해 28/36이다. 원래 합계·분모를 정정할 오류는
이 재현에서 발견하지 못했다.

이번 새 로컬 전체 workload 시간은 다음과 같다. 같은 432 step, 7회 반복의 중앙값이다.

| 방법 | 중앙값 ms | 최소 ms | 최대 ms |
|---|---:|---:|---:|
| fresh | 60.488 | 57.381 | 63.892 |
| lru | 78.662 | 75.145 | 83.737 |
| selective | 66.014 | 64.643 | 69.383 |
| no_directory | 68.138 | 61.163 | 69.833 |

이번 selective는 fresh보다 **9.136% 느렸다**. Phase08 원본 +12.37%, 당시 별도
재현 +15.21%를 대체하거나 정정하는 값이 아니다. 반면 이번 selective는
no_directory보다 빨랐으므로, 두 이전 관측의 directory 시간 대소와 부호가 바뀌었다.
이를 directory의 일반 가속이나 장부의 CPU 대응을 증명한 결과로 해석하지 않는다.
유리한 실행을 골라 보고하지 않으며 이 재현을 더 반복해 좋은 숫자를 찾지 않았다.
원시 7회 표본과 family별 시간은
[`inheritance/reproduction_timing.json`](inheritance/reproduction_timing.json)에 보존했다.

주의: `recount_results.py`가 출력한 `timing_comparison`은 Phase08에 저장되어 있던
원본 및 당시 재현 파일을 읽은 것이다. 이번 새 시간은 위 별도 파일에서만 읽었다.

## 5. Phase09에 중요한 코드 의존성 발견

`SelectiveCache`의 admission·victim 판단은 `cost` 합계나 event 수를 읽지 않는다.
실제 분기 입력은 stage 값, `len(context)`, raw UTF-8 크기, 실제 encode한 payload
크기, resident의 `size/surplus/hits/order`, directory, retained bytes, 용량이다.
따라서 `cost`의 수치 갱신과 event 기록을 지우는 방향은 코드의 데이터 흐름과 맞는다.
그러나 다음 계산을 통계처럼 지우면 정책 자체가 바뀐다.

- Raw와 context의 정확 encoding 및 비교.
- Payload encoding과 길이, immutable stage 값 및 payload 크기 보관.
- 포화 hit 갱신, surplus, victim weight/density, 삽입 순서와 크기 합.
- Directory 갱신, capacity 검사, 전부 수락하기 전 victim 계획 보존.

Fresh의 방문별 `size=len(text.encode("utf-8"))`는 파서 source-byte 장부에만
사용된다. 전체 snapshot의 JSON 직렬화·UTF-8·SHA-256은 별도의 검증 입력이므로
없앨 수 없다. 지원 입력의 semantic 결과와 policy state는 같더라도, OOM·시간 제한·
비표준 Python 객체의 부작용까지 자동으로 동등해지는 정리는 아니다.

이 코드는 제거 후 속도 대소를 알려 주지 않는다. Fresh에서도 계측을 제거해야 하며,
selective에 남는 실제 key/payload/정책 비용을 숨기지 않는 네 경로 비교가 필요하다.
Phase08 자료는 이제 개발·회귀 자료이며 다음 성과의 독립 평가 분모에 더할 수 없다.

**운영 변경 없음. 기존 동결 코드·자료·결과를 보존했다.**
