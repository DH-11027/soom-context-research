# Phase08 새 합성 stream 작성 기록

작성: 2026-10-22. seed `2026102208`. 기준 문법은 Phase07 완료 commit
`6da051c0132811184ecf39975d7ff647a1f47842`에 포함된 Phase05r2/Phase06이다.

## 1. 역할 분리와 공개한 정보

작성자는 구현 담당자와 다른 **동일 모델 에이전트**다. 작성자는 사용자 요청,
공개된 제한 문법·평가 schema·연구 목적을 공유하며, 구현 담당자로부터 아래의
사전 family/규모/원문 길이 범위 계약을 받았다. 따라서 외부 작성자 평가나
알고리즘 가설을 모르는 블라인드 평가가 아니다.

- 12 family × 3 parameterization × 12 step = 36 stream / 432 step.
- 각 stream은 빈 연구 캐시에서 시작한다.
- 앞의 8 family는 비용 조건, 뒤의 4 family는 의미 동등성·행동 경계 중심이다.
- 긴 단일 기록의 길이는 parameterization별 1,000–4,000 / 12,000–24,000 /
  60,000–75,000 UTF-8 bytes 구간에서 seed로 정한다.
- fit에는 2–4개 큰 후보의 원문 합이 20,000–50,000 bytes인 조건을 둔다.
- pressure에는 2–4개 큰 후보가 각각 16,000–48,000 bytes이고 합은 65,536을
  넘는 조건을 둔다. 64 entries / 65,536 logical bytes라는 기존 예산은 공개 정보다.
- 짧은 두 family는 모든 원문이 256 Unicode 문자 미만이다.
- 반복, 단일 사용, 반복 중단, working-set 교체, copy/정정/재정렬, ambiguity,
  namespace/roster 변경, invalid snapshot, unsupported와 복구를 포함한다.

작성자는 **새 Phase08 정책 소스·개발 자료·실험 결과를 읽지 않았고, Phase08이나
Phase07의 selector/cache runtime을 실행하지 않았다.** Phase06/Phase05 파서도
실행하여 원문을 조정하지 않았다. 초기 생성과 재생성 확인은 독립 작성한 builder의
schema, 질문 계약, snapshot, typed gold 검사를 통해서만 수행했다.

작성자가 실제 읽은 자료는 Phase07 `holdout_builder.py`, `study.py`,
`HOLDOUT_AUTHOR.md`, Phase06 `scoped.py`의 공개 scope 문법·실행 계약,
`evaluate.py`의 질문·gold schema, Phase05r2 `engine.py`의 공개 원문 문법이다.
기존 Phase07 raw holdout JSON이나 결과를 새 stream으로 복사하지 않았다.
기존 문법의 cheap/deep quote 표면형은 그대로 사용하되 names, 값, payload,
history 조합, 순서, query 순서, 원문 길이와 ID를 새로 구성했다.

구현 담당자에게는 동결 전 파일 위치·hash·분모·생성 검사 통과 여부만 전달했다.
본문·개별 gold·구체 길이·예상 cache 성능을 전달하지 않았다. 이 문서와 builder는
구현 담당자가 동결 이후에 읽는 자료다. 역할 분리가 같은 모델과 공유 설계에서
발생하는 상관성을 없애지는 않는다.

## 2. 규모와 분모

| 항목 | 개수 |
|---|---:|
| family / parameterization / stream | 12 / 3 / 36 |
| stream별 step / 전체 step | 12 / 432 |
| 유효 snapshot | 420 |
| 무효 snapshot | 12 |
| gold 적용 | 411 |
| membership 변경으로 gold 제외 | 9 |
| 명시적인 미지원 질문 | 9 |
| 유효·gold 적용·지원 질문 | 402 |

방법별 raw rows가 늘어도 독립 대화 수가 늘지 않는다. stream 안에는 의도적
반복과 변경이 있고, 서로 다른 stream도 family·문법·길이 설정을 공유한다.
432개 독립 자연어 대화를 검증하는 자료가 아니다.

## 3. family 구성

| Family | 새로 만든 조건 |
|---|---|
| `short_repeated` | 짧은 deep 지정, 사건 시점 copy, 상대 이동, 두 종류 quote 후 같은 history에서 query 순환 |
| `short_churn` | step마다 다른 초기 값·deep 지정·copy·상대 이동과 8개 새 짧은 quote |
| `long_cheap_repeated` | 같은 긴 cheap quote를 12회 방문하며 요구 필드 순환 |
| `long_deep_repeated` | 같은 길이의 긴 deep quote를 12회 방문하며 요구 필드 순환 |
| `long_deep_single_use` | step마다 salt가 다른 긴 deep quote; 같은 긴 원문은 재방문하지 않음 |
| `working_set_fit` | 2/3/4개 deep quote가 동시에 있는 고정 history를 반복 |
| `working_set_pressure` | 개별로는 기존 한도 안에 들 수 있지만 원문 합만으로 한도를 넘는 2/3/4개 deep quote를 고정 순서로 반복 |
| `phase_shift` | 4회 고정 deep quote → 4회 새 cheap/deep quote → 4회 다른 고정 deep quote; 중간에 늦은 정정 추가 |
| `revisions_copy_reorder` | 같은 과거 ID의 값·표면형 수정, 두 방향 copy와 상대 이동의 순서 변경, 삭제·재삽입, 늦은 절대 지정 |
| `scope_and_ambiguity` | maybe-set의 정확한 joint branch, 시간/장소 frame, query 교체, 마지막 구간의 정정으로 ambiguity 해소 |
| `entity_namespace_rotation` | entities 순서 변경과 membership 변경, 같은 parser의 namespace label 교체·복귀 |
| `integrity_unsupported_recovery` | 잘못된 digest, seq/순서/원문 변조, 누락/gap, head 오류와 정상 복구; 과정·실행·원문 질문 |

긴 cheap/deep/repeated/single-use와 phase-shift의 길이는 같은 parameterization에서
맞췄다. 비교할 때 원문 길이와 파서 단계 차이를 혼동하지 않도록 한 사전 설계다.
이것이 결과가 유리한 길이를 사후 선택했다는 뜻은 아니다. 실제 seed가 만든 길이는
3,514 / 12,770 / 70,214 bytes다. 마지막 값은 기존 65,536 예산보다 큰 원문도 포함한다.

fit의 큰 원문 합은 25,870 / 26,172 / 25,271 bytes이고, pressure의 큰 원문 합은
77,083 / 77,951 / 83,703 bytes다. 이 수치는 입력 생성의 제약 확인이며 실제
cache retained bytes나 성공한 admission·hit의 측정이 아니다. context와 payload가
추가되므로 원문 길이와 캐시 보관 크기는 동일하지 않다.

이 길이 분포와 반복 비중은 비용 경계를 관찰하기 위해 구성한 **인위적인 분포**다.
실제 대화 길이·반복 빈도를 대표하지 않는다. 긴 원문이 byte 합계와 시간 합계에서
더 큰 비중을 가질 수 있으므로 전체 합과 family별 결과를 함께 해석해야 한다.
작성 과정에서 selector 성능에 맞춰 길이·반복·가중치를 조정하지 않았다.

## 4. 공개 입력과 gold의 분리

각 stream은 `id`, `family`, `split`, `steps`를 가진다. 각 step에는 다음이 있다.

```text
step_id
parser_namespace
public = {records, entities, snapshot, query}
gold = [record별 typed event]
question_contract = {supported, required_fields}
expected_integrity
gold_applicable
gold_exclusion_reason
```

`records`에는 `seq`, opaque `id`, `text`만 들어간다. 선택기에 전달할 수 있는 것은
`public`의 네 항목과 실행 namespace뿐이다. family, split, gold, 질문 정답 필드,
무결성 정답, exclusion 이유를 정책에 전달하면 평가 계약을 위반한다.

snapshot은 현재 record 배열을 `ensure_ascii=False`, `sort_keys=True`,
`separators=(",", ":")`로 직렬화한 UTF-8 bytes의 SHA-256이다. 정상 수정·재정렬은
seq와 digest를 새로 만든다. invalid 조건에서는 오류를 의도적으로 남긴다.
Builder의 이 계산은 표준 라이브러리 구현이며 기존 selector를 import하지 않는다.

## 5. Gold 의미와 제외

gold는 `noop`, `set`, `add`, `copy`, `maybe_set`의 계획 상태 전이다. quote는
상태를 바꾸지 않는다. copy는 사건이 실행되는 시점의 source 값을 읽고,
maybe-set은 명시된 두 대상 중 정확히 하나를 변경하는 joint branch다. 시간은
일반 정수다. 실제 캘린더 작업, 완료 증거, 열린 요청의 완전한 수명주기, 자연어
정정의 일반적 의미를 검증하는 자료가 아니다.

유효하고 gold를 적용하는 모든 history는 첫 네 사건에서 두 entity의 time/place를
초기화한다. frame 문장의 gold는 작성한 실제 `set`이다. selector가 값을 못 읽어
TOP을 반환하더라도 그 결과에 맞춰 gold를 변경하지 않는다.

entities 순서만 바뀌면 같은 typed 모형을 적용한다. membership이 바뀌는 9개
step은 기존 사건의 universe 투영을 새로 정의하지 않아
`gold_applicable=false`, `gold_exclusion_reason="entity_membership_undefined"`다.
이들은 기존 fresh와 새 방법의 관찰적 동등성을 검사할 수 있지만 의미 정확성
성공 사례로 세면 안 된다.

무효 snapshot 12개도 gold에서 제외하며, 거절과 현재 검증 경로를 검사한다.
미지원 질문 9개는 유효하고 gold가 적용되는 history를 갖지만 현재 상태의 답변
성공으로 세지 않는다. 전체 history 선택 여부와 unsupported 판정을 평가한다.

namespace label 교체에서 parser 의미는 바꾸지 않는다. 실제 parser 배포 변경이나
숨은 설정 변경에 대한 안전성 실험으로 부르지 않는다.

## 6. 생성·검사와 고정 파일

실제로 다음 명령을 실행했다.

```bash
python research/phase08/holdout_builder.py
python research/phase08/holdout_builder.py --check
```

생성기는 다른 내용의 파일을 덮어쓰지 않는다. `--check`는 deterministic 재생성
bytes와 저장된 자료·manifest의 정확한 동일성을 검사한다. 수행한 검사는 다음과 같다.

- 36 stream / 432 step, stream·step·history 내 record ID의 유일성.
- public 키 whitelist와 원문/gold 정렬, 두 entity, 짧은 family의 문자 수 제한.
- 독립 계산한 seq/head/digest와 무결성 라벨의 일치.
- 별도 exact-string 질문 표와 `question_contract`의 필드·지원 여부 일치.
- gold 적용 history의 네 필드 초기화와 자체 typed joint-state 실행.
- gold 제외 이유의 명시와 구조 정합성.
- 생성 artifact bytes의 재현 동일성.

typed-state 검사는 원문을 해석하지 않는 작성자의 일관성 검사다. 원문과 gold의
자연어 의미를 외부 정답으로 검증한 것이 아니다. 작성자가 template/gold 대응을
검토했으며 외부 인간 평가자는 참여하지 않았다. **cache admission, hit, eviction,
전체 비용, 실행시간 또는 selector 정확성 결과는 생성 단계에서 측정하지 않았다.**

| 파일 | SHA-256 |
|---|---|
| `holdout_builder.py` | `29990e176c3b9ff30880e6b90bd33c8d923b5aeb2a15d00ca0dd377351c1ffbc` |
| `data/holdout.json` | `9f8c46a60d23eea8bea3f6dc7626908d4f74885a52b05d93d83c714ad6dc6613` |
| `data/holdout_manifest.json` | `a2291be3d7c86aaed0efc22aab3cea8873c85ef5aa1f32ed42917ca2905f67b1` |

자료 파일은 9,840,792 bytes다. 각 step에 전체 snapshot을 저장한 재현 artifact
크기이며 LLM 입력·요금·네트워크 전송량·cache 메모리 사용량과 동일하지 않다.

후속 평가에서 라벨 오류나 구현 결함을 발견하면 원본과 결과를 보존하고 정정
자료를 별도로 기록해야 한다. 자료를 열어 본 뒤 조정한 정책에 대해 같은 자료를
새 미열람 평가라고 발표해서는 안 된다.
