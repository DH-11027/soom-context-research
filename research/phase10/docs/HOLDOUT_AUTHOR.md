# Phase10 새 합성 평가 자료의 작성 경계

별도 동일 모델 자료 작성자 `/root/holdout_author`가 동결 전에 작성했다.
직접 참고 기준은 Phase09 공개 commit `0c08785fcee9ab146f33fa8a7d94a4b7700833aa`다.
기존 Phase09 및 이전 단계의 파일은 수정하지 않았다.

## 1. 공유 정보와 미열람 경계

공유된 것은 공개 제한 문법·schema, 고정 정책을 유지한다는 연구 경계, 개발 자료로 보정한 trace 기반
실행시간 차이 예측을 새 자료에서 검사한다는 H10의 질문, 요청받은 family·horizon·길이 범위다.
이 작성자는 Phase09 자료를 작성하고 사후 결과를 재집계한 같은 역할이므로 Phase09의 성능 수치를
전혀 모르는 작성자라고 표현해서는 안 된다.

이번 단계에서는 Phase09 `holdout_builder.py`의 입력·typed event·snapshot 형식을 읽고 재사용했다.
이미 알고 있던 Phase05/06의 공개 문법은 그대로 따른다. Phase10 구현·trace 모델·보정 계수·개발 결과·
시간·평가 결과는 열지 않았다. Selector·parser·trace 추출·시간 측정 경로를 실행하지 않았다.
본 작성기는 표준 라이브러리만 import하고 typed plan의 자체 구조 일관성만 검사한다.

작성 중 원문·gold·builder 본문을 주 구현자에게 전달하지 않고 메타데이터·hash·분포만 알린다.
이것은 같은 모델의 역할 분리이며 공개 설계를 공유한다. 외부 독립 자료, 외부 블라인드 자연어 평가,
실제 SOOM 대화 모집단의 무작위 표본이라는 주장을 하지 않는다.

## 2. Horizon과 길이 배치

Seed는 **2026102210**이다. 12 family ×4 parameterization =**48 stream**이며 각 family에
horizon **2, 8, 24, 64**를 한 번씩 배치한다. 따라서 총 step은

`12 × (2 + 8 + 24 + 64) = 1,176`이다.

Stream 수는 horizon별12개로 같지만 step 가중치는24/96/288/768로 다르다.
모든 step 합계를 사용한 값에서 horizon64가65.31%를 차지한다. Stream별 평가와 step별 합계는 서로 다르다.
이들은 독립적인1,176개 대화가 아니며, 같은 stream의 prefix와 반복은 의존한다.

일반 긴 quote의 사전 UTF-8 구간은 다음 네 가지다.

1. 850–2,100 bytes.
2. 7,000–19,000 bytes.
3. 48,000–63,000 bytes.
4. 68,000–83,000 bytes.

`band=(parameter+family_index) mod4`로 구간을 순환한다. 설계상 각 horizon에 각 band index가
세 stream씩 배치된다. 다만 short/scoped 가족은 큰 quote를 사용하지 않고, fit/pressure 가족은 별도
working-set 합계 범위를 사용한다. 이 배치 표를 실제 모든 길이 구간의 완전 요인설계라고 표현하면 안 된다.
일반 긴 quote를 사용하는 가족들에서도 각 horizon에 서로 다른 길이 구간이 섞이며, 한 horizon에
하나의 길이만 고정하지 않는다.

실제 corpus 전체 원문 길이는 **45–77,287 UTF-8 bytes**, 문자 수는 **19–71,109**다.
기록 occurrence는 **10,370**, snapshot별 중복을 포함한 원문 bytes 합은 **41,147,526**이다.
이는 실제 파서 스캔량, 고유 원문 크기, 논리 cache 보관량 또는 물리 RAM이 아니다.

## 3. Family와 반복·working set

| Family | 작성한 조건 |
|---|---|
| `short_repeated` | 256문자 미만의 고정 raw, copy·증감·현재 질문 변화 |
| `short_churn` | 짧은 값·분기·copy·인용을 매 step 새 조합으로 변경 |
| `long_cheap` | Cheap 문법의 긴 noop, history 안의 위치 변화 |
| `long_deep_repeat` | Detail까지 요청되는 문법의 같은 긴 noop 반복, 위치·질문 변화 |
| `long_deep_churn` | 항목당 단일 사용의 긴 noop, 원문 길이는 고정하되 내용은 매번 변경 |
| `fit_working_set` | 후보 원문 합20k–58k, 2/3/4/6개 quote, 순환·역순 배치 |
| `pressure_working_set` | 후보 원문 합75k–130k, 2/3/4/6개 quote, 순환·역순 배치 |
| `phase_shift` | Horizon 비율에 따른 이전·새 반복 구간과 재등장, 마지막 step 신규 단일 사용 |
| `same_length_misses` | 같은 문자 길이의 서로 다른7개 raw, 고정 재방문 순서와 namespace 변경 |
| `revisions_copy_context` | 같은 id의 원문 수정, copy 순서·구성 변경, entity 순서·membership·namespace 변경 |
| `scope_ambiguity` | Typed 분기·copy·frame·나중 값 설정이 현재 demand에 미치는 조건 |
| `integrity_unsupported_recovery` | 유효/무효 snapshot과 미지원 질문을 섞고 마지막 step에서 정상 회복 |

Fit/pressure의 원문 길이는 약간 불균등하다. 실제 정책 보관 크기에는 context·payload·metadata가 더해지며,
작성기는 그것을 runtime으로 계산하지 않는다. 큰 일반 quote 구간에는 개별 원문만으로65,536을 초과하는
조건도 포함된다. Family 이름은 selector의 실제 hit·miss·admission 결과를 보장하는 라벨이 아니다.

Horizon2에서도 초기 네 typed set으로 두 entity의 time/place를 모두 초기화하고 올바른 snapshot을 만든다.
무결성 가족의 마지막 step은 지원 질문·유효 snapshot으로 회복한다. 이 때문에 horizon2의 해당 stream은
오류 사건 없이 정상 두 step일 수 있다. Longer horizon의 오류·회복 조건과 분모를 합쳐 읽지 않는다.

현재 public에는 `records/entities/snapshot/query`만 넣는다. Stream의 `author_design`, family, horizon,
raw band, typed gold, 적용 여부는 평가·설명용 metadata이며 selector 입력이 아니다.
Trace 모델에 어떤 metadata를 허용할지는 별도 연구 protocol이 정해야 하며, 작성기 metadata를 몰래
predictor feature로 전달하도록 요구하지 않는다.

## 4. Unicode와 의미 경계

Payload는 ASCII, 한글 중심, emoji 포함, ASCII·한글·emoji 혼합의 네 조성을 사용한다.
원문 UTF-8 bytes와 Python `str` 문자 길이를 따로 기록한다. Exact-length 작성기는 Unicode code point를
중간에서 자르지 않으며 newline을 삽입하지 않는다. 같은 길이 가족은 style과 byte 길이를 고정해 실제
문자 길이도 같고 raw는 서로 다름을 assert한다.

큰 payload는 모두 제한 문법이 정의하는 **noop quote**다. Unicode 구성을 다양화했다고 자유로운
자연어 의미 추론이나 새 참조·정정·미완료 요청·실제 실행 증거의 일반 보존을 평가한 것이 아니다.
새 entity 이름·값·copy 순서·quote 위치·반복 스케줄을 구성했지만 공개 template와 구조를 공유하므로
새 corpus가 이전 연구와 통계적으로 독립이라고 표현할 수 없다.

## 5. Typed gold와 분모

원문 template를 만들 때 별도 typed event를 함께 구성한다. Parser 결과를 gold로 재사용하지 않는다.
`execute_gold`는 typed plan만 유한 실행해 초기값·대상 좌표·copy·분기의 일관성을 검사한다.
외부 인간이나 모델이 원문을 독립적으로 읽어 정답을 판정한 절차는 아니다.

| 집합 | 개수 |
|---|---:|
| 전체 step | 1,176 |
| 유효 snapshot | 1,148 |
| 무효 snapshot | 28 |
| 미지원 질문 | 17 |
| 유효·지원 질문 | 1,131 |
| Gold 적용 | 1,128 |
| Gold 적용·지원 질문 | 1,111 |
| Gold 제외: invalid snapshot | 28 |
| Gold 제외: membership 투영 미정의 | 20 |

Gold 적용1,128에는 미지원17의 전체 이력 선택 검사 대상이 포함되며 답변 성공 수가 아니다.
Entity 순서만 바뀌고 구성원이 같으면 gold를 적용한다. 구성원이 바뀐20step은 기존 규약처럼
의미 투영을 정의하지 않아 제외한다.

유효 ordered raw history의 exact 종류는 **518**, gold 적용 step의 exact typed-event 배열은 **346**,
전체 public+namespace의 exact 종류는 **927**이다. Canonical JSON에서 순서·이름·값을 보존해 센다.
의미 동치류나 독립 프로그램 수가 아니다. 세부 family·stream 분포는 manifest에 남긴다.

## 6. 저장·검사·동결 전 전달

```bash
python research/phase10/holdout_builder.py --check
```

`--check`는 재생성한 corpus와 gzip 해제 bytes의 동일성, 고정 설정으로 재압축한 gzip bytes의 동일성,
manifest bytes의 동일성을 모두 검사한다. 기존 경로의 다른 내용을 덮어쓰지 않고 실패한다.
Selector·trace 모델·timing을 실행하지 않는다.

| 산출물 | SHA-256 |
|---|---|
| `holdout_builder.py` | `ab2eb58254333f7b406d3504c8866c304237ed163c6c6ac678361a796334bd0f` |
| `data/holdout.json.gz` | `e1cca1bad32e230ac9cc9dc667533ab9c49cf1ee96fb7669bf76823cb94660b5` |
| 해제한 JSON bytes | `53380abc1d54d0be127f699b30b0320393482863b60f1e4acd581cad14480e5f` |

표준 산출물은 **805,628 bytes**의 gzip이며 해제한 JSON은 **45,779,143 bytes**다.
압축은 `gzip.GzipFile(filename='', mtime=0, compresslevel=9)`로 수행했다.
이는 저장과 전달 형식이며 연구 실행시간의 압축 성과로 보고하지 않는다.
동결 시각·commit·전체 source/data hash는 상위 연구자의 freeze 기록을 따른다.

원문·gold·builder를 구현자가 열기 전 코드·모델·protocol과 함께 동결할 수 있도록 자료 작성을 마쳤다.
이 문서에는 Phase10의 예측 정확성·호출 감소·시간 개선 결과를 넣지 않았다. 아직 어떤 selector나
trace 모델의 결과도 보지 않았으므로 그런 결론을 쓸 근거가 없다.
