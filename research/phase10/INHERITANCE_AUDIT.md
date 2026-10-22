# Phase10 인수인계 감사 — Phase09 공개 결과의 보존과 재확인

검토 역할: Phase09 평가기·정책 상태 감사와 별도 재현을 담당했던 동일 모델의 별도 역할.
Phase10에서도 외부 독립 검증자로 표현하지 않는다.

**결론:** 공개 Phase09 완료 commit `0c08785fcee9ab146f33fa8a7d94a4b7700833aa`에서
출발했고, 아래 다섯 무시간 검증이 모두 통과했다. 기존 원본과 별도 재현의 결정적
산출물 8개를 다시 직접 byte 비교했으며 SHA-256도 두 공개 receipt와 일치했다.
**Phase09의 새 timing session은 실행하지 않았다.** 직전에 완료한 원본·재현 관측을 상속한다.

## 1. 기준과 실제 확인 범위

작업 경로는 `/workspace/scratch/ff70ac34eaeb/soom-context-phase10`이다.
확인 당시 `git rev-parse HEAD`는 위 공개 완료 commit과 같았고, 작업 시작 상태는 clean이었다.
새 증거는 `research/phase10/inheritance/`에만 추가했다. Phase09 및 이전 동결 파일을 수정하지 않았다.

이 역할은 직전 Phase09 단계에서 `HANDOFF_BACK.md`, `README.md`, `PROTOCOL.md`,
`THEORY.md`, `EVALUATOR_REVIEW.md`, `POSTFREEZE_REVIEW.md`와 평가·재현 구현을 직접
검토했다. 이번 인수인계에서는 `run_study.py`, 공개 원본·재현 receipt,
`PROTOCOL.md`, `DATA_REVIEW.md`를 다시 읽고 아래 검증 명령을 실행했다.
원시 artifact의 byte/hash 재확인은 프로그램 검사이며, 원문 전체의 자연어 의미를
다시 수기 판정한 작업은 아니다. 저장소 전체를 새로 읽거나 과거 연구를 전부 재실행하지 않았다.

Phase10의 새 holdout 원문·gold·builder는 이 인수인계 역할이 열지 않았다.

## 2. 실제 실행한 검증

실행 시각은 **2026-10-22 13:24:15.985277–13:24:16.704777 UTC**다.
각 명령은 표준 출력·표준 오류·종료 코드·시작/종료 시각을 보존했다.
새 임시 증거 경로는 `/tmp/soom-phase09-verify-for-phase10-7cy3_6yc`다.
이 경로의 증거를 `inheritance/`로 복사했다. Python bytecode 작성을 막는
`PYTHONDONTWRITEBYTECODE=1`을 공통 설정했으며 연구 코드의 실행 의미는 바꾸지 않았다.

| 명령 | 종료 코드 | 확인한 내용 |
|---|---:|---|
| `python tools/verify_archive.py` | 0 | Archive 59파일, 18 source 결합, 포장/구문/로컬 링크 무결성 |
| `python research/phase09/erase.py --check` | 0 | 원본 AST로 생성한 비계측 source와 저장 출력의 정확한 동일성 |
| `python research/phase09/run_study.py --verify` | 0 | 동결 source/data와 기존 source hashes, AST 삭제 결과 |
| `python research/phase09/holdout_builder.py --check` | 0 | 기존 36 stream/432 step의 직렬화·schema·typed plan |
| `git bundle verify research/phase09/pre_evaluation.bundle` | 0 | 로컬 freeze 객체와 Phase08 prerequisite 결합 |

`holdout_builder.py --check`의 `selector_evaluated`는 false다.
무결성·생성 동일성 검사는 새로운 의미 정확성 증명이나 새 performance 결과가 아니다.
실행 원문은 `inheritance/command-01.json`–`command-05.json`, 종합 receipt는
[`inheritance/receipt.json`](inheritance/receipt.json)에 있다.

## 3. 기존 결정적 산출물 8개 재대조

이번 검사는 공개 `research/phase09/results/`와 **이미 실행을 마친**
`/tmp/soom-phase09-reproduction/`의 다음 파일을 `read_bytes()`로 직접 비교했다.
동시에 공개 원본 receipt 및 `reproduction_receipt.json`의 SHA-256과 대조했다.

| 파일 | 직접 byte 동일 | 원본 receipt hash | 재현 receipt hash |
|---|---|---|---|
| `audit.json` | 참 | 일치 | 일치 |
| `holdout_results.json` | 참 | 일치 | 일치 |
| `holdout_rows.json.gz` | 참 | 일치 | 일치 |
| `holdout_states.json.gz` | 참 | 일치 | 일치 |
| `regression_results.json` | 참 | 일치 | 일치 |
| `regression_rows.json.gz` | 참 | 일치 | 일치 |
| `regression_states.json.gz` | 참 | 일치 | 일치 |
| `data_profile.json` | 참 | 일치 | 일치 |

8개 모두 같았다. 이것은 **기존 재현 산출물의 재확인**이며 Phase10에서 Phase09 evaluator를
한 차례 더 실행했다는 뜻은 아니다. Exact live Obs/π/trace 비교 자체는 기존 Phase09 감사
실행의 증거를 상속한다. 저장된 한쪽 상태 witness와 hash만으로 양쪽 live 실행을 새로
복원했다고 주장하지 않는다.

파일별 크기·SHA-256·직접 비교 결과는
[`inheritance/deterministic_artifacts.json`](inheritance/deterministic_artifacts.json)에 있다.
Phase09 `freeze.json` SHA-256도
`776b11146a962fff666ddbacbba6b07e2766d0789816de490ea441d911594fbc`로 확인했다.
공개 완료 commit은 로컬 freeze `387b451a19d0c17abc22365b82daeb357b0d3ab3`와 다르다.
로컬 freeze를 외부 사전 등록으로 소급하지 않는다.

## 4. 시간은 재측정하지 않고 상속한다

Phase09 원본·재현 timing 파일의 현재 hash를 각각 해당 공개 receipt와 다시 대조했다.
새 측정값을 만들어 넣지 않았다. 아래 숫자는 모두 **Phase09에서 이미 실행한 두 session**이다.

| 상속한 Phase09 관측 | 원본 | 별도 재현 |
|---|---:|---:|
| Fresh off 전체 workload 중앙값, ms | 67.128 | 65.550 |
| Selective off 전체 workload 중앙값, ms | 79.719 | 78.313 |
| 주 paired ratio | 1.179341 | 1.167817 |
| 시간 변화 | +17.93% | +16.78% |
| 95% cycle bootstrap ratio 구간 | [1.151942, 1.213609] | [1.159105, 1.191448] |
| 고정 판정 | `material_slowdown` | `material_slowdown` |

주 ratio는 `exp(median(log(T_selective_off/T_fresh_off)))`이며 marginal 중앙값의
단순 비율과 다르다. 40 round를 구성한 10개의 순서 균형 cycle을 재표집한 구간이고,
독립 대화 모집단이나 새 하드웨어에 대한 구간이 아니다.

Phase09의 432 step에서 Obs 비교 1,296회·on/off 실제 실행 trace 비교 864회·정책 상태
및 정책 결정 trace 비교 각432회에 불일치는 0이었다. False certification 0/372,
containment 0/405, selected-gold 투영 실패 0/414였다. Gold414와 유효·지원411은
서로 다른 집합이고, gold414에는 unsupported9의 전체 이력 선택 검사가 포함된다.

실제 파서 호출 4,905→4,152와 입력 bytes 30,426,509→19,010,756은 별도 감사 실행의
계수다. 그 감소에도 실제 시간은 증가했다. 계측 P8 42,423,808→45,724,400(+7.78%)은
비계측 경로의 CPU 비용 장부가 아니다. Phase08의 다른 분포에서의 P8 개선을 정정하는 값도 아니다.

## 5. Phase10으로 넘기는 감사 경계

Phase09 자료·시간을 보고 Phase10의 offline 시간차 예측 문제를 정했으므로 이 자료는 이제
개발·보정 자료다. 이 자료에 잘 맞춘 예측기를 새 독립 평가에서 검증했다고 표현해서는 안 된다.

고정된 off policy의 trace가 보여 주는 것은 해당 실행의 활동량이다. Feature의 단위·수집 위치·
파서 실제 호출과 cache 관리 호출의 중복 계수·cold 구축 포함 여부를 명시해야 한다.
별도 trace가 runtime 상태나 순서를 바꾸지 않는지와, timed 실행에 feature 수집기·monkeypatch가
다시 들어가지 않는지는 서로 다른 검사다. 새 예측식의 적합성이 두 조건을 대신하지 않는다.

Offline으로 전체 stream의 trace를 읽는 분석은 미래 정보를 보지 않는 온라인 admission
정책과 같은 능력이 아니다. 예측 feature를 runtime selector에 전달하거나 정책·용량·threshold를
바꾸는 연구로 조용히 확대해서는 안 된다. 부품별 시간을 합하는 모형도 실제 전체 시간의
정확한 가산 분해를 전제하지 않으며, 잔차와 실패를 새 고정 자료에서 반박 가능하게 남겨야 한다.

이번 인수인계에서 Phase09 수치를 정정할 오류는 발견하지 않았다. 이 문서는 아직 Phase10의
새 feature 계약·예측 성능·새 holdout 결과를 검증한 문서가 아니다. 해당 검토와 새 연구 결과는
별도 기록한다. **SOOM 운영 변경 없음. Phase09 새 timing 0회. 기존 동결 파일 보존.**
