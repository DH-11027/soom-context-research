# Phase 07 다중 질문·snapshot holdout 작성 기록

작성일: 2026-10-22. 고정 seed: `2026102207`.

## 작성 분리와 정보 경계

이 데이터는 구현 담당자와 다른 **동일 모델의 에이전트**가 작성했다. 작성자는
단계별 순수 parse memoization, LRU, 다중 질문·수정 snapshot이라는 가설과
사전에 정한 기본 예산인 64 entries / 65,536 serialized key+payload bytes를
알고 있다. 부모 대화와 공개 Phase06 의미 모형·문법·질문 계약도 공유했다.
따라서 방법을 모르는 블라인드 작성이나 외부 독립 평가가 아니다.

작성자는 새 Phase07 선택기·캐시·평가기 소스와 평가 결과를 열지 않았다.
Phase07 알고리즘 또는 Phase06 언어 파서를 실행하여 문장을 맞추지 않았다.
기존 Phase06 파일도 수정하지 않았다. 구현 담당자는 알고리즘 동결 전 이
holdout의 본문·gold·예상 성능을 읽지 않기로 했으며, 작성자는 분모와 파일
경로·hash만 전달한다. 이 분리는 **새 구현과 출력에 맞춘 데이터 튜닝을 하지
않았다는 작성 절차**를 의미하며 동일 모델·공유 가설의 상관성을 없애지 않는다.

## 규모

| 항목 | 개수 |
|---|---:|
| family | 10 |
| family별 parameterization | 3 |
| stream | 30 |
| stream별 step | 10 |
| 전체 step | 300 |
| 유효 snapshot step | 288 |
| 무효 snapshot step | 12 |
| `gold_applicable=true` step | 276 |
| 명시적인 미지원 질문 | 9 |
| 유효·gold 적용 가능·지원 질문 step | 267 |

stream 내부의 질문·이력은 의도적으로 반복되거나 수정된다. 따라서 300개의
독립 대화 표본으로 세지 않는다. 서로 다른 stream도 같은 family 템플릿을
공유한다. 캐시는 stream 시작마다 비우는 연구 계약으로 작성했다.

## Family의 목적과 조건

| Family | 작성한 조건 |
|---|---|
| `same_history_query_rotation` | 같은 전체 이력에 질문의 요구 필드만 순환 |
| `append_then_correction` | 기존 이력에 상대 이동·절대 지정·늦은 정정·복사를 순서대로 추가 |
| `historical_text_edit_same_id` | 과거 기록 ID를 유지하면서 원문 값과 대응 gold를 변경 |
| `valid_reorder_delete_reinsert` | 초기 네 필드를 유지하고 후행 변경·복사의 순서를 바꾸거나 제거·재삽입 |
| `entity_environment_change` | 같은 roster의 순서 변경과 roster membership 변경을 구분 |
| `no_reuse_high_churn` | step마다 새 값·새 짧은 인용 원문을 생성하여 재사용이 드문 조건 구성 |
| `long_short_text_mix` | 동일 긴 인용 원문과 일부 짧은 원문을 반복·조합 |
| `query_scope_and_unsupported` | 시간·시간/장소·두 시간 질문 및 과정·실행·원문 질문의 교체 |
| `parser_namespace_rotation` | parser 동작은 고정하고 namespace label만 교체·복귀 |
| `malformed_snapshot_then_recovery` | digest·seq·head·순서가 잘못된 snapshot과 정상 복구를 교대 |

high-churn에는 step마다 10개의 새 짧은 인용을 넣었다. 긴 원문의 payload
길이는 64/2,048/24,000 Unicode 문자로 고정했다. 가장 긴 조건은 byte 예산을
넘는 입력에 대한 처리도 확인하기 위해 포함한 인위적 경계 조건이다. 이것을
현실 대화에서 흔한 길이 분포라고 해석하지 않는다. 길이 또는 반복 비중을
실행 결과를 보고 바꾸지 않았다. 바이트·시간 총합은 이런 조건의 비중에 영향을
받으므로 family별 결과와 함께 보고해야 한다.

namespace family는 **동일 parser 구현의 label만 바꾸는 검사**다. 실제 parser
업그레이드나 의미 변화에 대한 안전성 검증이 아니다. label 경계를 넘어 재사용하는지
여부와 출력 동등성의 검사 범위까지만 해석할 수 있다.

## 스키마와 선택기 입력

각 stream은 다음 키를 갖는다.

```text
id, family, split, steps
```

각 step은 다음 키를 갖는다.

```text
step_id
parser_namespace
public = {records, entities, snapshot, query}
gold = [record별 typed event]
question_contract = {supported, required_fields}
expected_integrity = "valid" | "invalid"
gold_applicable = true | false
```

`records`의 각 항목에는 `seq`, 무작위 opaque `id`, `text`만 있다. 선택기에는
`public`만 넘기고 namespace는 실행 설정으로 전달한다. family, gold, 질문
정답 필드 목록, 유효성 정답은 선택기에 넘기지 않는다. `required_fields`는
`[entity, field]` 쌍의 목록이며 지원하지 않는 질문에서는 빈 목록이다.

동일 ID의 원문 수정에서는 ID만 유지하고 새 원문에 맞는 snapshot digest를
만든다. 정상 reorder/delete/reinsert는 현재 배열 순서에 맞춰 `seq`를 다시
매기고 새 digest를 만든다. 잘못된 snapshot은 별도의 invalid step으로 표시한다.
digest의 직렬화는 기존 형식과 같은 UTF-8 JSON, `ensure_ascii=False`,
`sort_keys=True`, `separators=(",", ":")`다. 구현은 `hashlib`와 `json`으로
독립 작성했으며 기존 파서·선택기를 import하지 않는다.

## Gold 의미와 평가 제외 조건

gold는 계획 상태의 `noop`, `set`, `add`, `copy`, `maybe_set` 전이로 작성했다.
의도적으로 상태를 바꾸지 않는 긴/짧은 인용은 `noop`이다. `copy`는 그 사건이
발생한 시점의 값을 읽는다. `maybe_set`은 명시된 두 필드 중 정확히 하나에
지정을 적용한다. 시간은 일반 정수이며 실제 달력·시간대·실행 여부를 모델링하지
않는다. 모든 유효하고 gold를 적용할 수 있는 step은 처음 네 기록으로 두 모임의
시간·장소를 모두 초기화한다.

roster의 순서만 바뀌는 step은 같은 모형을 유지하므로 gold 평가에 포함한다.
membership이 바뀌는 **12개 step**은 `gold_applicable=false`다. 이때 기존 gold를
새 universe의 noop으로 바꾸거나 모형 밖 엔터티 의미를 임의로 발명하지 않았다.
해당 step은 uncached/cached의 **출력 동등성만** 평가한다. 이 gold를 새로운
roster로 실행해서 정확성 분모에 넣으면 안 된다.

무효 snapshot **12개 step** 역시 `gold_applicable=false`다. 이 경우는 정해진
무결성 거절 동작 및 캐시 전후 출력 동등성 검사 대상이다. 미지원 질문 **9개**는
유효하고 gold를 적용할 수 있는 이력에 속하지만, 현재 상태의 정답과 비교하여
답변 성공으로 세지 않는다. 질문 지원 범위와 전체 이력 동작을 별도로 보고한다.

## 실제 실행한 작성 검사

```bash
python research/phase07/holdout_builder.py --check
```

생성기는 표준 라이브러리만 사용하며 새 선택기·평가기를 import하지 않는다.
처음 생성하려면 `--check` 없이 실행한다. 이미 다른 내용의 파일이 있으면
덮어쓰기를 거절한다.

실제로 실행한 검사는 다음과 같다.

- 30 stream / 300 step 분모와 stream별 step ID 유일성.
- 공개 입력의 키 경계, record별 키·ID 유일성, 원문/gold 길이 정합성.
- 직접 계산한 digest 및 seq/head 조건과 `expected_integrity` 라벨의 일치.
- 질문 계약의 지원 여부·필드 목록 형태와 roster 포함 관계.
- gold 적용 가능 step의 초기 네 필드 지정과 typed 전이 실행 가능성.
- gold 전이를 수행한 뒤 모든 상태 필드가 초기화되어 있는지 확인.
- 생성한 JSON의 재생성 바이트 동일성.

typed 전이 검사는 원문을 해석하지 않는 저자의 별도 간단한 라벨 실행기다.
따라서 자연어 라벨의 독립 정확성 검증이 아니다. 템플릿과 gold 대응은 작성자가
검토했으며 외부 사람의 검증은 받지 않았다. **선택기 성능, 캐시 hit/miss,
eviction, 절감률, 실행 시간 결과는 생성 단계에서 측정하지 않았다.**

## 고정 파일

| 파일 | SHA-256 |
|---|---|
| `holdout_builder.py` | `0b7474e9915f163100d0c9e72f395790ac1316711442d8b20377da277b83a1d4` |
| `data/holdout.json` | `76a93ffa695c4abcc6d240382a40211d4d406b2c9d84352e5d2c9c181c0f9f98` |

데이터 파일 크기는 **1,966,152 bytes**다. 전체 snapshot을 각 step에 저장하여
이력 반복도 파일에 그대로 나타난다. 이는 재현용 artifact 크기이며 실제 프롬프트
토큰·네트워크 비용·캐시 메모리 사용량 또는 성능 개선 수치가 아니다.

후속 검사에서 라벨 오류를 발견하면 원래 자료와 결과를 보존하고 사후 정정으로
따로 기록해야 한다. 이 자료를 본 뒤 변경한 정책의 결과를 같은 미열람 평가로
부르면 안 된다.
