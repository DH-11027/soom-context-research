# 코드와 증거 지도

59개 역사적 파일은 [manifest](../archive-manifest.json)에 경로·크기·SHA-256으로 열거되어 있다. 이 문서는 다음 연구자가 관련 파일만 읽기 위한 지도다.

## 단계별 진입점

| 단계 | 코드 | 입력·동결 | 핵심 결과와 JSON 키 |
|---|---|---|---|
| 01 | [experiment.py](../research/experiment.py) | 코드 안의 고정 seed와 합성 세계 | [results.json](../research/results.json): `counterexamples`, `fixed_cases`, `noise.rows`, `noise.samples` |
| 02 | [study.py](../research/phase02/study.py) | [fixtures.json](../research/phase02/fixtures.json) | [results.json](../research/phase02/results.json): `calibration`, `summaries`, `math_checks`, `rows` |
| 02 사후 진단 | [diagnose_links.py](../research/phase02/diagnose_links.py) | 동일 fixture와 결과 재사용 | [link_diagnostic.json](../research/phase02/link_diagnostic.json): `reports` |
| 03 | [extractor.py](../research/phase03/extractor.py), [evaluate.py](../research/phase03/evaluate.py), [fixtures.py](../research/phase03/fixtures.py) | [frozen_protocol.json](../research/phase03/frozen_protocol.json), [development.json](../research/phase03/development.json), [evaluation_fixtures.json](../research/phase03/evaluation_fixtures.json) | [results.json](../research/phase03/results.json): `results.heldout.summary`, `results.stress.summary`, 각 split의 `rows`, `validation` |
| 03 사후 라벨 감사 | [audit_labels.py](../research/phase03/audit_labels.py) | 동결 정책 그대로 | [label_audit.json](../research/phase03/label_audit.json): `reports.<split>.label_changes`, `reports.<split>.policies` |
| 04 | [model.py](../research/phase04/model.py), [study.py](../research/phase04/study.py) | [protocol.json](../research/phase04/protocol.json), [worlds.json](../research/phase04/worlds.json) | [results.json](../research/phase04/results.json): `summary`, `diagnostics`, `answer_class_counts`, `rows`, `checks` |
| 04 별도 구현 감사 | [audit.py](../research/phase04/audit.py) | 같은 유한 세계 | [audit.json](../research/phase04/audit.json) |
| 05 기본 | [engine.py](../research/phase05/engine.py), [fixtures.py](../research/phase05/fixtures.py), [study.py](../research/phase05/study.py) | [protocol.json](../research/phase05/protocol.json), [corpus.json](../research/phase05/corpus.json) | [results.json](../research/phase05/results.json): `summary.main`, `summary.stress`, `rows`, `families`, `fault_checks`, `scaling`, `checks` |
| 05 기본 구체 실행 감사 | [audit.py](../research/phase05/audit.py) | 9개 연산 길이 4 | [audit.json](../research/phase05/audit.json); 최소 비용 예시는 아래 정정 참고 |
| 05 최초 비용 확장 | [reducer.py](../research/phase05/reducer.py), [reduction_study.py](../research/phase05/reduction_study.py) | [reduction_protocol.json](../research/phase05/reduction_protocol.json) | [reduction_results.json](../research/phase05/reduction_results.json): 0개 strict improvement |
| 05 결함 진단 | 진단 자료 자체 | [reduction_diagnosis.json](../research/phase05/reduction_diagnosis.json) | `parse_results`, `base.status`, `diagnosis` |
| 05 revision02 | [engine.py](../research/phase05/revision02/engine.py), [reducer.py](../research/phase05/revision02/reducer.py), [reduction_study.py](../research/phase05/revision02/reduction_study.py) | [reduction_protocol.json](../research/phase05/revision02/reduction_protocol.json) | [reduction_results.json](../research/phase05/revision02/reduction_results.json): `strictly_smaller_queries`, `posthoc_original_corpus_regression`, `cancellation_example`, `examples` |
| 05 revision02 회귀 | [공개 재현 helper](../tools/check_revision.py) | 원래 corpus·v1 결과와 v2 엔진 | [corpus_regression.json](../research/phase05/revision02/corpus_regression.json) |

## 파일을 해석할 때의 우선순위

1. 결과의 분모와 조건은 해당 frozen protocol과 실제 evaluator를 따른다.
2. 숫자는 JSON에 있고, HTML/노트북과 새 Markdown은 그 숫자의 설명이다.
3. 사후 진단·라벨 감사는 원래 시험을 대체하지 않는다. 원래 결과와 함께 읽는다.
4. 발견한 오류는 원본을 고치지 않고 새 revision과 해석 정정으로 기록한다.

특히 Phase 05 `audit.json`의 `minimum_byte_counterexample`는 base status를 빠뜨린 초기 해석이다. 후속 `reduction_diagnosis.json`은 그 예시가 실제로 `opaque_fallback`이었다고 보여준다. **인증된 상쇄 최적화의 증거는 revision02의 `certified_cancellation_reduced`와 `cancellation_example`이다.**

`research/phase05/revision02/audit.py`는 원래 concrete evaluator를 가져온 helper다. revision02 실험에서 import하며, standalone 실행 진입점은 이전 폴더 구조를 기대한다. 별도로 실행하지 말고 `revision02/reduction_study.py --run` 또는 제공한 재현기를 실행한다. 이것은 보관 코드의 알려진 실행 경계다.

## 보고서 생성기와 노트북

Phase 01의 `make_note.py`, 나머지 각 phase의 `make_report.py`는 JSON을 읽어 HTML과 노트북을 만든다. [연구 색인](../research/index.html)은 로컬 브라우저에서 보고서를 연결한다. 보고서·노트북도 당시 버전을 그대로 보존했다.

노트북은 설명과 실행용 셀을 포함한 미실행 문서다. 보관된 실험 결과는 CLI 실행에서 나왔다. 새 재현 시에는 `--reports` 옵션으로 복사본의 보고서를 재생성할 수 있으며, 재생성 보고서의 바이트 동일성은 요구하지 않는다.

## 동결과 출처

| 동결 파일 | UTC 시각 | 의미 |
|---|---|---|
| Phase 03 `frozen_protocol.json` | 2026-10-22 07:18:36 | 개발 후 heldout/stress 전의 코드 hash |
| Phase 04 `protocol.json` | 2026-10-22 07:45:15 | 유한 세계·코드·판정 계획 |
| Phase 05 `protocol.json` | 2026-10-22 08:17:00 | corpus·코드·기본 시험 계획 |
| Phase 05 revision02 `reduction_protocol.json` | 2026-10-22 08:26:12 | 관측된 결함 수정과 비공허성 검사 계획 |

Phase 01·02는 결과에 source hash를 남겼지만 후속 단계와 같은 별도 사전 동결 문서를 갖지 않는다. 그것을 소급해서 사전 등록 연구라고 부르지 않는다. timestamp는 로컬 연구 기록이며 외부 기관의 시각 인증이 아니다.

## 공개 자료의 경계

보관 파일은 연구 디렉터리의 `.py`, `.json`, `.html`, `.ipynb`만 골라 바이트 그대로 복사했다. 실행 cache는 제외했다. 합성 이력의 프로젝트·모임 이름과 문장은 fixture 생성기가 만든 것이다. 운영 DB, 개인 대화 캡처, 인증 정보, 설정, 비공개 운영 소스는 포함하지 않는다.

공개용 무결성 manifest는 원래 실험의 사전 동결을 새로 만든 것이 아니다. **게시한 파일이 현재 보관본과 일치한다는 증거**다. 추후 연구에서는 기존 파일을 덮어쓰지 않고 새로운 경로를 추가한다.
