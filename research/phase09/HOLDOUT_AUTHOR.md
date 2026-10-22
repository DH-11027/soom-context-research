# Phase09 새 합성 평가 자료의 작성 경계

작성 역할: 별도 동일 모델 에이전트 `/root/holdout_author`.
작성 기준: Phase08 공개 완료 commit `efba3224dd09d5c5e2bf9d9be11734fa10b32502`.
최종 작성 시각은 상위 연구자의 동결 기록과 구별한다. 본 문서는 새 자료를 동결하기 전에 작성했다.

## 1. 공유한 정보와 읽지 않은 정보

공유한 정보는 연구 질문, Phase08 정책의 공개 상수와 동작 설명, 새 자료의 family·길이·반복 설계,
기존 공개 입력 schema와 제한 문법이다. 실제로 읽은 파일은 다음과 같다.

- `research/phase08/holdout_builder.py`: 공개 schema, snapshot 직렬화, typed gold 형식.
- `research/phase06/scoped.py`: 공개 scope whitelist와 질문별 처리의 의미 경계.
- `research/phase05/revision02/engine.py`: 공개 cheap/detail/query 문법, typed event 의미.
- 이 세션의 사용자가 제시한 Phase08 결과와 연구 경계. 상위 역할의 전체 대화가 상속되었으므로
  이전 성능 수치를 전혀 모르는 작성자라고 주장하지 않는다.

Phase09 runtime·평가기·개발 결과·실행 결과는 읽지 않았다. 어떤 selector나 timing 경로도 실행하지 않았다.
새 코드·자료·typed labels는 이 역할이 작성했고, 구현자에게는 동결 전 hash·크기·집계 분포만 전달한다.
원문·typed labels를 생성한 작성자 자신의 구조 검사는 외부 의미 판정과 다르다.

**공개 문법과 연구 설계를 공유하는 같은 모델의 역할 분리다. 외부 독립 검증이나 외부 블라인드
자연어 평가가 아니다.** 이 자료는 실제 SOOM 대화의 모집단 표본도 아니다.

## 2. 고정 자료 구성

Seed `2026102209`; 12 family × 3 parameterization × 12 step = **36 stream / 432 step**.
모든 stream은 별도 cache로 시작한다는 평가 계약을 전제로 작성했지만, 자료 작성기 자체는 cache를 만들지 않는다.
같은 step에 여러 방법을 실행한 결과 행과 timing 반복을 독립 대화로 세지 않는다.

| Family | 의도한 진단 조건 |
|---|---|
| `short_repeated` | 256문자 미만의 같은 raw를 서로 다른 지원 질문에서 반복 |
| `short_churn` | 짧은 값·copy·증감·분기·quote 조합을 매 step 변경 |
| `long_cheap` | cheap 문법에서 끝나는 긴 noop quote, 현재 질문과 위치 변화 |
| `long_deep_repeat` | 세 단계 문법의 긴 noop quote 반복, 순서와 현재 demand 변화 |
| `long_deep_churn` | 각 step의 새로운 긴 quote; 항목당 미래 반복 0 |
| `fit_working_set` | 원문 합계 14–58k 범위의 2/3/5개 quote, 순환 순서 변경 |
| `pressure_working_set` | 개별 60k 미만, 원문 합계 77–116k의 2/3/5개 quote |
| `phase_shift` | 이전 반복 구간, 새 반복 구간, 이전 항목 재등장, 마지막 세 step 단일 사용 |
| `same_length_misses` | 문자 길이는 같지만 raw가 다른 다섯 quote, 일부 namespace 변경 |
| `revisions_copy_context` | 같은 id의 수정, copy 순서 변경·삭제, entity 순서/membership·namespace 변경 |
| `scope_ambiguity` | typed 분기, 알려진 frame, 현재 copy, 이후 값으로 불확실성 해소 |
| `integrity_unsupported_recovery` | 정상 cache 사용 전후에 무효 snapshot·미지원 질문·정상 회복 |

주요 긴 quote 길이는 parameter별 UTF-8 **900–1,900 / 9,000–18,000 / 57,000–74,000 bytes**에서
family마다 따로 고정 난수로 정한다. Fit와 pressure는 위 표의 별도 working-set 합계 범위를 따른다.
이는 실행시간 결과를 보고 선택한 값이 아니다. 65,536 한도 아래/위가 섞이는 큰 길이 구간을 그대로 유지한다.
정확한 보관 크기에는 context·payload·metadata가 더해진다. 따라서 원문 합계와 실제 resident 크기를 혼동하지 않는다.

긴 payload는 같은 문자 조성의 Unicode 문자열이고, 길이는 bytes와 Python `str` 문자 수를 모두 기록한다.
`same_length_misses`는 서로 다른 다섯 raw의 문자 길이가 실제로 같음을 작성기에서 assert한다.
이 가족 이름은 실제 cache hit/miss 결과를 보장하지 않는다. 용량 초과나 context 차이로 구체 동작이 달라질 수 있다.

12 step의 고정 생존 기간은 설계상의 제한이다. 이를 보완하려고 단일 사용 family와 종료 직전 신규 후보를
포함했지만, 임의 길이 또는 실제 자연 대화의 종료 분포를 평가한 것은 아니다.

## 3. 이전 자료와의 차이

Phase08 corpus를 복사하거나 seed만 바꿔 재사용하지 않았다. 문법상 합법적인 출력 template와 공개 schema는
재사용하되, 현재 연구의 독립 구현 코드에서 새 기록 조합·copy 순서·수정·membership 변경·후반 단일 사용을 구성했다.
Working-set 가족은 같은 raw pool을 순환 재배열한다. 긴 반복의 quote 위치도 일부 step에서 변경한다.
Phase08에 별도 family였던 entity/namespace 변경은 긴 raw와 현재 copy 수정에 결합했다.

이 차이가 통계적 독립성을 만들지는 않는다. 같은 제한 문법, 유사한 목적별 family, 같은 모델의 작성 규칙을 공유한다.
이 자료에서 Phase08보다 좋은 수치를 얻더라도 실제 대화 일반화나 외부 검증으로 표현할 수 없다.

## 4. Gold와 제외 분모

Typed event는 원문 template를 생성하는 시점에 함께 구성한다. Parser 출력에서 gold를 역산하지 않는다.
작성기 자체의 `execute_gold`는 이 typed plan만 실행하여 초기값·대상 좌표·copy·분기의 구조 일관성을 검사한다.
원문을 읽고 의미를 판정하는 별도 모델이나 외부 인간을 사용한 것은 아니다.

모든 history의 처음 네 사건은 두 entity의 time/place 값을 초기화한다. 유효 membership에서 미정 초기값이 남지 않는다.
Invalid snapshot과 entity membership 변경의 의미 투영 미정의 경우는 gold 적용에서 제외한다.
Entity의 순서만 달라지고 구성원이 같은 경우는 ordered entity context를 바꾸되 gold를 계속 적용한다.

| 집합 | 개수 |
|---|---:|
| 전체 step | 432 |
| 유효 snapshot | 420 |
| 무효 snapshot | 12 |
| Gold 적용 | 414 |
| Gold 제외 membership 변경 | 6 |
| Gold 제외 invalid snapshot | 12 |
| 미지원 질문 | 9 |
| Gold 적용이며 지원하는 질문 | 405 |

Gold 적용 414에는 미지원 9의 전체 이력 선택 검사 대상이 포함된다. 414를 답변 성공 수로 표현하면 안 된다.
유효·지원 질문은 411이며, gold 적용 414와 다른 집합이다. 이것은 자료 정의의 분모이며 selector 판정은 아직 없다.

큰 원문은 모두 grammar-defined **noop quote**다. 긴 자연어의 의미 추론, 암묵적 정정,
미완료 요청, 자유로운 참조, 실제 도구 실행 성공이나 실행 증거의 일반적 보존을 검증하지 않는다.

## 5. 작성기 검증과 고정 파일

`holdout_builder.py`는 표준 라이브러리만 사용하고 selector·runtime·결과 파일을 import하지 않는다.
원문 입력의 네 public key, record id 유일성, record seq와 expected digest의 관계,
질문 template와 필드 계약, gold 대상 좌표·초기값을 검사한다.

```bash
python research/phase09/holdout_builder.py --check
```

`--check`는 새로 생성한 corpus가 저장된 `data/holdout.json.gz`를 해제한 bytes와 같은지 확인하고,
고정 gzip 설정으로 다시 압축한 bytes와 저장된 gzip 자체의 동일성도 검사한다. Manifest 역시 byte-identical인지 확인한다.
기존 경로에 다른 bytes가 있으면 덮어쓰지 않고 실패한다.

| 파일 | SHA-256 |
|---|---|
| `holdout_builder.py` | `2d5256c434c027be5f8ba511763de305995e27c58757e75cf9ca301ed19ba290` |
| `data/holdout.json.gz` | `1a36ee60f57c7e0ad7f6f91f098e9803db212d4de2e00920510740e5b5ee20e6` |
| 해제한 원래 JSON bytes | `c659d9c89126d5184ddc4a59102050ec50a8e6a8bfb2a3306d04fe4f526c6740` |

Corpus UTF-8 내용 크기는 13,030,700 bytes이며 표준 산출물은 228,838 bytes의 gzip이다.
동결 전에 전달 크기를 줄이기 위해 저장 형식만 JSON에서 deterministic gzip으로 변경했다.
`gzip.GzipFile(filename='', mtime=0, compresslevel=9)`를 사용하며 변경 전 JSON의 SHA-256과
변경 후 해제한 bytes의 SHA-256이 위 표처럼 같음을 확인했다. 원문·labels·분포·순서는 변경하지 않았다.
기존 untracked Phase09 JSON은 동일성 검증 후 gzip으로 대체했고 Phase08 파일은 변경하지 않았다.
이 크기는 step별 기록을 중복 저장한 파일 크기이며 cache 보관량·파서 작업량이 아니다.
세부 family 길이·원문 발생량·중복 통계는 `data/holdout_manifest.json`에 있다.
동결 시점의 전체 파일 hash·commit은 상위 역할의 freeze 기록을 따른다.

동결 전 구현자에게 새 raw/typed labels/성능은 공개하지 않았다. 작성기는 성능을 측정하지 않았으므로,
이 문서에도 어떠한 선택기 정확성·호출 감소·시간 이득 결론을 넣지 않는다.
