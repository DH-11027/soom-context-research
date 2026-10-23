# Phase09 새 합성 자료 작성 경계

작성일: 2026-10-23 KST. Seed: `2026102309`.
읽기 기준: Phase08 공개 완료 commit `efba3224dd09d5c5e2bf9d9be11734fa10b32502`.

## 1. 역할과 실제 접근 범위

작성자는 구현자와 다른 **동일 모델 에이전트**다. 사용자 요청, 기존 정책의 공개 설명,
제한 문법과 연구 목적을 공유했다. 외부 작성자·외부 블라인드 자연어 평가가 아니다.

실제로 읽은 파일은 다음과 같다.

- `research/phase08/holdout_builder.py`: 기존 stream/step/public/gold schema와 작성 규칙.
- `research/phase08/HOLDOUT_AUTHOR.md`: 이전 작성 경계와 gold 제외 계약.
- `research/phase05/revision02/engine.py`: 공개 원문 문법과 typed 상태 의미.
- `research/phase06/scoped.py`의 앞부분: 공개 scope whitelist·검증·렌더 계약.

Phase09 runtime, benchmark, 개발 결과, 주평가 결과를 **읽거나 실행하지 않았다**.
Phase08/Phase07 selector도 실행하지 않았다. Phase05/06 파서를 실행하여 원문이나
gold를 조정하지 않았다. 이전 raw holdout JSON을 새 stream으로 복사하지 않았다.
기존 문법과 schema helper의 형식은 재사용하고 이름·값·ID·payload·history 조합·순서·
질문 순서·horizon·길이를 새로 구성했다.

구현자에게 동결 전 전달한 내용은 파일 이름·hash·stream/step 분모와 생성 검사
통과 여부다. 이 문서와 manifest의 구체 길이 분포, builder, 원문·gold는 동결 이후에
열도록 요청했다. 같은 모델과 공유 설계에 따른 상관성이 제거된 것은 아니다.

## 2. 사전 구성과 분포

12 family × 3 parameterization = **36 stream / 622 step**이다. Horizon은 입력
조건의 일부다. 각 stream은 연구 cache가 비어 있는 상태에서 시작하도록 설계한다.
실제 workload 실행 순서·timing 반복은 연구 프로토콜이 정하며 작성자가 성능을 보고
순서를 조정하지 않았다.

| Family | 세 stream의 step 수 | 구성 |
|---|---|---|
| `cold_terminal` | 1 / 1 / 1 | 첫 구축 직후 종료; deep quote 850 / 18,000 / 68,000 UTF-8 bytes |
| `short_repeated` | 24 / 24 / 24 | 모든 원문 256 Unicode 문자 미만; 같은 history, 질문 순환 |
| `short_churn` | 12 / 12 / 12 | 값·copy·상대 이동과 6개 짧은 quote가 매 step 변경 |
| `long_cheap_repeated` | 24 / 24 / 24 | cheap noop quote 2,400 / 14,500 / 62,500 bytes 반복 |
| `deep_finite_horizons` | 3 / 8 / 32 | deep noop quote 2,400 / 14,500 / 62,500 bytes 반복 후 종료 |
| `same_length_churn` | 12 / 12 / 12 | 같은 byte·문자 길이의 다른 원문; 매 세 번째 방문은 한 원문 재방문 |
| `working_set_fit` | 24 / 24 / 24 | 2 / 3 / 4개 deep quote; 원문 합 14,000 / 34,000 / 54,000 bytes |
| `working_set_pressure` | 24 / 24 / 24 | 2 / 3 / 4개 deep quote; 원문 합 73,000 / 75,000 / 82,000 bytes |
| `phase_shift` | 24 / 24 / 24 | 8회 기존 두 quote → 4회 단발 quote → 12회 새 두 quote |
| `revisions_copy_reorder` | 16 / 16 / 16 | 같은 ID의 원문 수정, copy와 add 재정렬·삭제; 255 / 256 / 257문자 quote |
| `scope_context_rotation` | 16 / 16 / 16 | maybe-set·frame·정정, namespace·entity 순서·membership 변경 |
| `integrity_unsupported_recovery` | 16 / 16 / 16 | digest·seq·원문·순서·누락·head 오류, 미지원 질문과 정상 복구 |

`deep_finite_horizons`는 길이와 horizon이 함께 변한다. 독립적인 길이 효과나 반복
효과를 추정하는 완전 요인설계가 아니다. Cheap/deep의 세 원문 길이는 같지만
전체 horizon은 같지 않으므로 그 family 합만으로 파서 단계의 독립 효과를 추정하면 안 된다.

원문당 최소·최대는 **45–68,000 UTF-8 bytes**, **19–51,982 Unicode 문자**다.
ASCII 중심, 한국어 중심, emoji와 combining codepoint를 포함한 세 payload 구성을
사용했다. Python `len(str)`의 문자는 Unicode codepoint 수이며 화면의 grapheme 수가 아니다.
전체 step에서 관측되는 원문 기록은 중복을 포함해 5,137개이고, 256문자 이상은
846개다. 원문 bytes 합은 **16,031,353**이다. 검증 직렬화 bytes·전체 출력·cache
보관량과 같다는 뜻이 아니다.

Working-set 합은 원문만의 합이다. Context·payload·metadata를 제외하므로 실제
cache retained bytes를 측정한 수치가 아니다. `fit`이라는 입력 설계 이름 역시 실제
admission 성공이나 특정 보관 상태를 측정한 결과가 아니다.

긴 원문은 모두 고정 문법이 인식할 수 있는 **noop quote**다. 길이는 커도 typed 상태는
바뀌지 않는다. 일반 자연어 의미 추론 난이도·실제 대화 분포를 대표하지 않는다.
큰 입력과 반복 working set이 합계 시간에 큰 비중을 차지할 수 있으므로 family별
입력 비중, 실제 timing 비중, stream별 손익을 함께 보고해야 한다.

## 3. 입력·gold·분모

각 stream은 `id`, `family`, `split`, `steps`를 갖는다. 각 step은 아래의 schema다.

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

Selector에는 `public`의 네 필드와 namespace만 전달해야 한다. Gold, 질문 정답
필드, family, split, exclusion 이유, 미래 step/horizon은 정책 입력이 아니다.

| 분모 | 수 |
|---|---:|
| 전체 step | 622 |
| 유효 snapshot | 610 |
| 무효 snapshot | 12 |
| Gold 적용 | 601 |
| Membership 변경으로 gold 제외 | 9 |
| 명시적 미지원 질문 | 9 |
| Gold 적용·지원 질문 | 592 |

Gold는 작성자가 먼저 정한 `set`, `add`, `copy`, `maybe_set`, `noop`의 계획 상태다.
Copy는 그 사건 실행 시점의 source 값을 읽고, maybe-set은 명시된 둘 중 정확히 하나를
바꾸는 joint branch다. Quote는 noop이다. Frame의 gold는 실제 `set`이며, 원래
선택기가 TOP으로 보수화하더라도 정답을 그 출력에 맞춰 수정하지 않는다.

Gold 적용 이력은 첫 네 사건에서 두 entity의 time/place를 초기화한다. 시간은 일반
정수이며 실제 달력의 시간 유효성이나 외부 실행 성공을 모델링하지 않는다.

Membership 변경 9 step은 기존 사건 universe의 의미 투영을 정의하지 않았으므로
`entity_membership_undefined`로 제외한다. Entity 순서만 바뀌면 gold를 적용한다.
무효 snapshot 12 step도 제외한다. 유효한 미지원 질문 9 step은 gold 적용 자료지만
답변 성공으로 세지 않으며, 전체 이력 반환과 unsupported 판정의 검사 대상이다.
Namespace 교체 시 실제 파서 의미는 변하지 않는다.

## 4. 생성·검증·오류 기록

선택기를 import하지 않는 builder를 실행해 구조와 작성자의 typed-state 일관성만
검사했다. 첫 구조 검사가 전체 step의 산술 오기를 검출했다. 사전 보고에서 722라고
잘못 합산했으나 family별 horizon의 합은 622다. **Horizon·입력 설계는 바꾸지 않고
합계 assertion만 정정했다.** 첫 실패는 자료 쓰기 전에 발생했다. 두 번째 `--check`
시도도 같은 오기에서 실패했으며 selector나 timing 결과는 발생하지 않았다.

정정 뒤 다음 두 명령이 성공했다.

```bash
python research/phase09/holdout_builder.py
python research/phase09/holdout_builder.py --check
```

검사 범위는 stream·step·history 내 record ID 유일성, schema whitelist, 원문/gold
정렬, Unicode 길이 조건, 독립 snapshot 계산과 무결성 라벨, 별도 exact-string
질문 계약, typed joint-state 실행, deterministic bytes 재생성이다. 자연어 문장을
외부 사람이 독립 판정한 의미 감사가 아니다. Cache hit·admission·eviction·성능은
이 생성 단계에서 측정하지 않았다.

| 고정 파일 | SHA-256 |
|---|---|
| `holdout_builder.py` | `96261e055f8938ca07b4c694c53b9f331f1e92e7e078ed90d4767c885cc685bc` |
| `data/holdout.json.gz` | `bc56abfc5be274cd8ae6e0d574ad314bc3ddcff94999eac71d1cd6de81aafaad` |
| `data/holdout_manifest.json` | `e37434f0f348bf3a53f9dfa3aeae1a7063207d0f9ad65a8506ae7062511d611c` |
| 압축 해제한 JSON bytes | `f24d7e73550ee87d03442b660f93f0cd234b409f516db3c983d8ca3ef080a732` |

동결 전에 GitHub 전달 크기를 줄이기 위한 포장 변경만 수행했다. `mtime=0`, 빈
filename, level 9인 deterministic gzip으로 저장하며 파일은 **328,088 bytes**다.
압축 해제 bytes는 최초 작성한 **18,327,551 bytes JSON과 정확히 같음**을 확인했고,
새 포장으로 `--check`도 통과했다. 새 미동결 원문 JSON만 제거했으며 기존 연구 자료는
변경하지 않았다. Manifest에는 압축·비압축 bytes의 hash와 크기를 모두 기록했다.
분포·원문·gold·horizon의 변경은 없다. 이 포장 크기를 LLM 토큰·요금·실제 입력
전송량·물리 메모리 절감이라고 해석하지 않는다.

첫 평가 이후 발견하는 자료·라벨 오류는 원본을 보존한 새 정정 문서로 남겨야 한다.
결과를 보고 유리한 family를 남기거나 가중치를 바꾸어 새 주평가로 보고하지 않는다.
동일 자료 반복 timing은 독립 대화 표본을 늘리지 않는다.
