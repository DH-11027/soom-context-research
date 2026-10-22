# 재현 방법

## 환경

Python 3.12 표준 라이브러리만 필요하다. 원래 실험은 Windows / CPython 3.12.13에서 실행되었다. 이 저장소에는 모델 호출, API 키 요구, DB 연결, pip 설치 단계가 없다. 다른 OS에서의 실행 경로는 상대 경로로 작성했지만, 실제 확인한 플랫폼은 [게시 시 재현 기록](PUBLICATION_VALIDATION.md)을 따른다.

Git clone 또는 GitHub의 소스 ZIP을 푼 뒤 저장소 루트에서 실행한다. Windows에서 `python`이 없고 Python launcher를 설치했다면 `py -3.12`로 대체할 수 있다.

```bash
python tools/verify_archive.py
python tools/reproduce.py --phase all --reports
```

`verify_archive.py`는 59개 보관 파일의 크기와 SHA-256, 기존 동결 프로토콜의 코드 hash, JSON 파싱, Python 구문, 노트북 기본 구조, 로컬 문서 링크를 확인한다. 이것만 통과한 상태는 실험 재현 성공과 다르다.

`reproduce.py`는 새 `.reproductions/<UTC>/research/`에 전체 보관 자료를 복사한 뒤 subprocess로 실험을 실행한다. 결과 JSON을 보관 결과와 비교하고 로그와 `receipt.json`을 남긴다. 실패하면 실패한 스크립트와 로그 경로를 표시한다. 원래 파일을 덮어쓰지 않으며 기존 출력 디렉터리를 재사용하지 않는다.

선택 실행도 가능하다.

```bash
python tools/reproduce.py --phase 01
python tools/reproduce.py --phase 02
python tools/reproduce.py --phase 03
python tools/reproduce.py --phase 04
python tools/reproduce.py --phase 05
python tools/reproduce.py --phase 05r2
python tools/check_revision.py
```

`05r2`는 최신 비용 최적화의 비공허성 검사와 기존 2,688개 모드·질문 비교를 포함한다. `check_revision.py`는 보관 결과와 수정 엔진을 직접 비교하는 읽기 전용 검사다. 원래 v1 보존 실험의 한계를 이해하려면 Phase 05의 역사도 읽어야 한다.

## 원래 명령의 의미

아래 명령들은 **복사본의 각 폴더**에서 실행하는 원래 entrypoint다. 원본 보관 폴더에서 실행하면 결과 파일을 덮어쓸 수 있으므로 기본적으로 위 wrapper를 사용한다.

| 폴더 | 실행 순서 |
|---|---|
| `research/` | `python experiment.py`, `python make_note.py` |
| `research/phase02/` | `python study.py`, `python diagnose_links.py`, `python make_report.py` |
| `research/phase03/` | `python evaluate.py --dev`, `python evaluate.py --test`, `python audit_labels.py`, `python make_report.py` |
| `research/phase04/` | `python study.py --run`, `python audit.py`, `python make_report.py` |
| `research/phase05/` | `python study.py --run`, `python audit.py`, `python reduction_study.py --run`, `python make_report.py` |
| `research/phase05/revision02/` | `python reduction_study.py --run` |

`--freeze`는 호출하지 않는다. 이미 동결된 자료를 다시 동결하면 당시 증거가 사라진다. revision02의 `audit.py`는 import용 helper로 사용하며 standalone으로 실행하지 않는다.

## 비교에서 제외하는 항목

실험 숫자를 넓은 허용 오차로 비교하지 않고 JSON 구조와 값을 정확히 비교한다. 아래 경로만 환경 차이로 제외한다.

| 파일 | 제외 경로 | 이유 |
|---|---|---|
| Phase 01 `results.json` | `elapsed_seconds`, `python` | 실행 시간·인터프리터 버전 |
| Phase 02 `results.json` | `elapsed_seconds`, `python` | 동일 |
| Phase 03 `results.json` | `elapsed_seconds`, `python` | 동일 |
| Phase 05 `results.json` | `scaling[i].seconds_one_local_run` | 단일 실행 벽시계 시간 |
| Phase 04 `audit.json` | `results_sha256` | OS별 줄바꿈 등 JSON 직렬화 바이트 차이 가능; **새 결과의 실제 SHA와 일치하는지는 별도로 검사** |

JSON 객체의 키 순서는 의미 비교에서 무시하고 배열 순서는 유지한다. coverage, 오류, 선택된 출처, byte 비용, 호출 수, 비교 개수, protocol/source hash는 무시하지 않는다. HTML/노트북은 재생성할 수 있지만 바이트 동일성 비교 대상은 아니다.

완전한 자연어 정확성, 모든 환경 호환성, 통계적 일반화는 재현 통과의 의미에 포함되지 않는다. 특히 동일한 잘못된 해석을 그대로 재현할 수 있으므로 [연구 연대기의 정정](RESEARCH_LOG.md)을 함께 읽는다.

## 새 연구를 이어갈 때

기존 manifest의 59개 파일은 그대로 둔다. `research/phase06/` 같은 새 폴더에 가설·코드·데이터·동결 프로토콜·결과·실패 사례를 넣는다. 기존 데이터에서 방법을 고른 뒤 같은 데이터를 독립 평가로 보고하지 않는다. 모델이나 외부 데이터가 필요하면 그 의존성과 비용을 새 연구의 재현 문서에 별도로 명시한다.
