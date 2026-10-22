# Phase08 실행 전 계획 — 비용 인지 순수 해석 보관

작성: 2026-10-22 KST. Phase07 기준 `6da051c0132811184ecf39975d7ff647a1f47842`.
이 계획은 새 Phase08 원문·라벨·평가 결과를 열기 전에 작성한다. 동결 시각과
hash는 `freeze.json`, 실제 local commit은 `freeze_commit.json`에 남긴다.
공개 GitHub 전달은 실험 이후일 수 있으며 로컬 동결을 외부 사전 등록이라 하지 않는다.
변경은 `research/phase08/`에만 추가한다. SOOM 운영 변경은 없다.

## 1. 비판적 출발과 하나의 주가설

Phase07은 300 step에서 실제 파서 실행을 67.28% 줄였지만 P7을 107.38% 늘렸다.
이번 시작 재현에서도 결정적 다섯 결과가 원본과 동일했다. 그 결과는 그대로 보존한다.
특히 cheap를 먼저 실행해서 cache 여부를 결정하면 남은 최대 2L의 절약이
기존 key 생성·probe 2L+C를 넘지 못한다. 원문을 해석하기 전 필요한 단계 수를
공짜로 안다고 가정하지 않는다. 전체 snapshot 검증도 매 질문 유지한다.

**H8:** 동일 의미 선택기에서, 실제로 관측한 해석 단계와 결과 크기만 사용하고
원문 key의 불필요한 조회를 거르는 선택적 보관 정책이, 새 합성 stream의 cold 시작
전체 가중 작업점수를 frozen fresh보다 줄이면서 기존 관찰을 보존한다.

주가설의 성공 조건은 (a) 보존/적용 가능한 gold 오류 0, (b) 실제 파서 실행 감소,
(c) 전체 `P8(selective) < P8(fresh)`의 동시 성립이다. 어느 하나라도 실패하면
이 자료에서 주가설을 지지하지 않는다. 보존의 조건부 수학 정리, 실제 호출 감소,
비용 감소, 시간 결과는 각각 구별해 보고한다. 전체 출력 감소를 기대하지 않는다.
모든 유한 stream에서 fresh 이하라는 가설은 세우지 않는다. 양의 최초 투자 뒤
stream이 끝나는 최소 반례가 있기 때문이다.

## 2. 고정 정책

1. 원래 snapshot/질문 검증 후 원래 역방향 경로를 따른다. 모든 방문 원문에서
   `len(text)`의 문자 수만 읽는다. 256문자 미만이면 원래 파서를 실행한다.
2. 보관된 후보의 문자 길이 directory를 조회한다. 같은 길이 후보가 없으면 exact
   key 조회를 생략한다. 이는 부정 필터이며 같은 길이라는 이유로 값을 재사용하지 않는다.
3. 후보가 있으면 ordered entities, 의미 fingerprint, namespace의 정확 context와
   원문 UTF-8 전체로 비교한다. digest 단독 또는 record ID key를 쓰지 않는다.
4. miss에서 **현재 원래 경로가 요청한 단계만** 실제 실행한다. cheap=havoc,
   scope=(None,global), detail까지 실제 요청한 complete bundle만 보관 후보다.
   query-local TOP/답/선택/copy 당시 값은 저장하지 않는다.
5. payload를 실제 encode/freeze하여 R을 잰 다음
   `b = L − C − R − 8×8`이 양수인 후보만 고려한다. 이 b는 query당 context
   생성비와 다른 기록을 제외한 예상 warm surplus이다. query 전체 이득 보장이 아니다.
6. 논리 보관 크기는 `C+L+R+80`; 전체 65,536, 항목 64 한도다. 80은 control과
   directory의 고정 논리 allowance이며 Python RSS 추정치가 아니다.
7. 여유가 부족하면 기존 항목의 `w=(min(h,255)+1)b`/size를 정수 교차곱으로
   비교해 낮은 순서대로 victim 계획을 만든다. 후보 b가 victim w의 합보다
   **클 때만** 전체 계획을 적용한다. tie는 최초 보관 순서다. 미래 빈도/정답/family는 모른다.

256, 255, 80, 64, 65,536, action 가중치 8은 새 평가 전 고정하며 결과에 따라
탐색하거나 바꾸지 않는다. 256은 짧은 frozen 문법을 우선 bypass하는 간단한
설계 선택이고 보편 최적 threshold가 아니다. 255는 과거 hit counter의 포화값,
80은 열 개 8-unit control slot의 모델링 선택이다. 기존 Phase07의 긴/짧은
원문·용량 실패를 보고 정책을 설계했으므로 해당 자료는 개발 정보다.

## 3. 비교군과 ablation

| 이름 | 실행 |
|---|---|
| `fresh` | 수정하지 않은 Phase06 text_scoped, Phase07의 기존 계측 wrapper |
| `lru` | Phase07의 동일 cache 알고리즘·용량; Phase08 controller event 계측만 추가 |
| `selective` | 위 정책, 주 비교는 항상 fresh |
| `no_directory` | 같은 정책·용량·길이 gate에서, resident가 있으면 정확 key를 조회; directory 음성 필터만 비활성 |

LRU adapter는 개발에서 원본 Phase07과 의미 및 기존 P7 바이트 장부가 같은지 검사한다.
no_directory의 실제 resident 집합은 추가 조회로 바뀌지 않지만, 추가 조회비는 낸다.
선택적 보관과 단순 LRU의 여러 차이를 각각 독립 인과효과로 분해했다고 주장하지 않는다.
ablation은 새 길이 필터가 피한 key work만 구별한다.

## 4. 비용 계약 — 바이트 장부와 가중 작업점수를 구분

기존 P7 정의는 바꾸지 않는다.

`P7 = output + hash + parser_source + key_build + key_probe + value_encode + payload_read + cache_write`.

각 항은 기존 동일 가중 **논리 바이트 작업량**이다. 실제 RAM traffic/CPU 읽기
횟수/LLM 토큰·요금·품질이 아니다. fresh도 size 관측용 UTF-8 encode를 하지만,
새 경로가 raw bytes를 key로 사용하면 P7의 L key-build charge를 유지한다.
전체 snapshot 직렬화·hash 비용은 같은 경로에서 계상한다. 원문 검증의 재사용이나
incremental snapshot, digest-only identity는 이번에 구현하지 않는다.

정책 판단·관리를 숨기지 않기 위해 새 주지표는 다음과 같이 고정한다.

`P8 = P7 + 8 × control_actions`.

**P8의 단위는 가중 작업점수**다. 8은 경험적으로 보정한 CPU/바이트 환산율이
아니라 공개한 모델링 선택이다. P7 항별 합, action별 수, P8을 모두 보고하며
가중치 0/8/32/128의 사전 민감도도 별도 보고한다. 민감도에서 유리한 값으로
주가설 판정을 교체하지 않는다. 실제 wall time이 다르면 별도로 판정한다.
민감도는 가중치 8로 이미 고정한 동일 정책·동일 동작의 재채점이다. 각 가중치에
맞춰 보관 정책을 다시 최적화한 결과가 아니다.

control action은 Python 명령의 완전 계수가 아니라 명시한 추상 정책 작업이다.
신규 계산의 판단/관리 경로마다 event를 둔다. 주요 event는 문자 길이 gate,
directory/resident 확인, context 접근, exact lookup, bounded hit 갱신,
hit stage 읽기, eligible miss stage 관측, bundle 적합성 확인, payload 준비,
후보 크기·점수 계산(2), 양의 점수 확인, 용량 확인, resident 점수 읽기,
density 비교마다 1, victim 계획의 항목마다 1, victim 이득 확인이다.
항목 제거는 4, 초기화는 10 action이다. init 10에 대응하는 metadata 80은
cache_write_bytes에 중복 가산하지 않는다. hash/equality 내부 probe, Python
allocator/GC, 정규식 조기 종료, 실제 big-int multiplication 비용을 이 event
장부가 정확히 측정한다는 주장은 하지 않는다. 모두 로컬 시간에 들어간다.

LRU에도 exact lookup, LRU touch, stage slot 확인, payload 준비, size/capacity/
membership 검사, replacement, removal, initialization event를 추가한다. 기존
P7 장부는 유지하며 fresh의 cache-specific action은 0이다.

주지표는 모든 새 step의 cold-inclusive P8 **합계**다. 큰 raw가 더 큰 비중을
차지한다. family별 비율/stream별 누적 손익분기점/행별 개선 수/최초 step 비용,
실제 파서 단계별 호출·입력 bytes/출력/eviction/reject/보관 peak를 함께 보고한다.
좋은 family만 남기거나 긴 사례를 제외해 주결과를 다시 만들지 않는다.

## 5. 데이터와 미열람 경계

- 공개 개발: `development.py`의 짧은 반복, 긴 cheap/deep, 단일 사용, 같은 문자
  길이 충돌, 함께 보관/압박, 인기 고착, 원문 수정·copy·namespace·invalid 사례.
- Phase07 300 step와 사후 18 cell/144질문은 알려진 개발·진단 정보다. 원래
  결과 재현 및 새 구현 회귀에 써도 새 독립 평가로 세지 않는다.
- Phase05 672와 Phase06 384질문은 역사적 회귀다.
- 새 holdout: 별도 동일 모델 작성자, seed `2026102208`, 12 family ×3
  parameterization ×12 step =36 stream/432 step. 원문·라벨·builder·작성 기록은
  root가 동결 전 열지 않는다. 역할은 분리했으나 공개 연구 설계는 공유했고,
  외부 독립 자연어 의미 평가가 아니다.

새 family는 `short_repeated`, `short_churn`, `long_cheap_repeated`,
`long_deep_repeated`, `long_deep_single_use`, `working_set_fit`,
`working_set_pressure`, `phase_shift`, `revisions_copy_reorder`,
`scope_and_ambiguity`, `entity_namespace_rotation`, `integrity_unsupported_recovery`다.
긴 원문 조건은 사전에 1k–4k/12k–24k/60k–75k UTF-8 부근으로 요청했다.
fit은 전체 후보 20k–50k, pressure는 개별 65,536 이내·합 초과인 2–4항목이다.
이 분포는 진단용 인위 구성이고 실제 대화 길이/반복 빈도를 대표하지 않는다.

public 4필드만 whitelist 복사하고 namespace만 별도 전달한다. gold AST,
question_contract, expected_integrity, family/split/미래 step은 선택기에 전달하지 않는다.
gold는 작성자가 원문 template와 함께 별도 typed 프로그램으로 만든다. invalid
snapshot과 새 membership 의미 투영을 정의하지 않은 조건은 gold 성공 분모에서
제외한다. unsupported의 selected-gold 확인은 전체 원문 선택 확인일 뿐 답변 성공이 아니다.
containment는 주변부 포함, selected-gold projection은 공동 답집합 투영 비교로 분리한다.

## 6. 동결·실행·재현·실패 규칙

개발/감사 완료 후 source, 평가기, 조건, 개발 자료, 새 자료의 hash를 동결한다.
동결 전 checkpoint commit을 기록하고 freeze commit 후에 새 자료를 처음 연다.
hash 검증은 새 실행의 필수 선행 조건이다. code/label/비교군/주지표를 사후
바꿔야 할 오류가 생기면 원본 실행을 보존하고 별도 정정으로 남긴다.

7회 로컬 timing: 방법 순서 회전, 폐기 warm-up, 매 stream/반복 새 cache.
cache 생성·검증·파서·정책·추론·렌더 포함; import/자료 로딩/gold/LLM 제외.
이는 연구 cache의 cold 시작이지 CPU/OS cache 전체 초기화가 아니다.
중앙값/최소/최대/모든 반복을 저장한다. 유의성 검정과 population 추정은 하지 않는다.

원본 후 별도 담당자가 다른 새 출력 경로로 실행하고 결정적 결과·압축 raw rows를
바이트 단위 비교한다. timing은 동일성 비교에서 제외하고 원본과 재현 모두 보존한다.
완료 시 실패/미확인/인위 분포/외부 언어평가 미실행을 명시하고
`docs/RETURN_TEMPLATE.md` 형식으로 반환한다. 의미 있는 위험을 해소한 뒤
추가 benchmark를 늘리지 않는다. PR은 열린 Phase07 branch 위 별도 branch로
전달하고 기존 branch 덮어쓰기와 merge는 하지 않는다.
