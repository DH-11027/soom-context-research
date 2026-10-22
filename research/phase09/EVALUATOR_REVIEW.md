# Phase09 동결 전 평가기·정책 상태·timing 경계 검토

검토자: 주 구현자와 역할을 분리한 동일 모델 에이전트. 2026-10-22.
Phase09 새 holdout 원문·builder·라벨·결과를 열지 않고 작성했다.
공개 연구 설계는 공유했으며 외부 독립 검증·외부 블라인드 자연어 평가는 아니다.

## 1. 의견과 실제 읽은 범위

현재 개발 검사와 직접 읽은 코드 범위에서 계측 제거 계약의 미해결 불일치를
발견하지 못했다. 정확성·정책 동등성의 한 사례라도 실패하면 주 timing을 하지 않는
실행기 규칙을 유지해야 한다. 이 검토는 실제 가속, 임의 Python 입력 정상 종료,
실제 자연어 의미 정확성의 증명이 아니다.

Phase08 인수인계·문서·코드와 재현 범위는 [INHERITANCE_AUDIT.md](INHERITANCE_AUDIT.md)에
구별해 기록했다. Phase09 `bindings.py`, `erase.py`, `off_fresh.py`, `off_selective.py`,
`execution.py`를 직접 읽었고, `evaluator.py`와 `audit.py`는 이 검토 역할이 작성했다.
주 구현자가 작성한 `benchmark.py`, `run_study.py`, `PROTOCOL.md`도 직접 읽고
평가와 timing의 연결을 확인했다. 주 구현자도 평가기 전체를 별도로 읽었다.
고정 의미 함수는 재작성하지 않고 Phase05/06의 원래 함수를 연결한다.

## 2. 비교하는 것은 답뿐 아니라 다음 정책 결정의 전체 상태다

`Obs`는 결과 dict에서 `cost`만 제외한 모든 필드와 실제 근거 UTF-8 bytes다.
누락된 필드와 빈 필드를 혼동하지 않으며 출력 길이만 비교하지 않는다.
비교군 4개를 같은 순서의 입력에 실행하고 fresh 계측 결과와 나머지 세 결과를
각 step마다 직접 비교한다.

`policy_state`가 구현한 π는 다음을 포함한다.

- Resident exact `(context bytes, raw bytes)` key와 dictionary 삽입 순서.
- Stage table의 순서, immutable 값의 타입·내용, 저장 payload 길이.
- 각 항목의 `size`, `characters`, `surplus`, `hits`, `order`.
- Length directory의 길이별 개수, `retained_bytes`, `next_order`.
- `max_entries`, `max_bytes`, `directory` mode.

π는 보고용 peak 두 필드와 cost/event 장부를 제외한다. 정책 상수·의미 fingerprint는
코드 동결 hash와 고정 모듈 binding으로 보장하며 살아 있는 실행 중 변경은 계약 밖이다.
Bytes와 값은 **직접 비교**한다. SHA-256은 저장된 receipt를 작게 표현하는 용도이고
동등성 판정에 hash만 사용하지 않는다. State raw rows는 양쪽이 같으면 한 상태와
exact-equality flag를 저장하고, 다르면 양쪽 상태를 모두 저장한다.

추가 invariant 검사에서는 용량·retained 합, directory Counter, complete global
bundle, payload encode 길이, size/surplus 식, hit 상한, 문자 길이와 raw key의
일치를 확인한다. 상태 occupancy를 여러 질문에 걸쳐 더해 비용으로 부르지 않는다.
요약은 state 필드를 cost 합계에서 제외하고, step 종료 시 최대 보관량·항목 수 및
계측판의 별도 peak만 보고한다.

## 3. 실제 호출 감사는 별도 correctness 실행이다

`actual_work`는 현재 방법의 실제 parse/scope/digest/render 함수와 cache의
`possible/get/admit`을 일시적으로 감싼다. 각 실행 뒤 `finally`에서 원래 함수를
복원한다. 주 timing은 별도 프로세스이며 이 평가기를 import하지 않는다.

이 감사는 다음을 직접 비교한다.

- Fresh on/off의 실제 cheap/scope/detail 호출 순서·정확 원문·ordered entities·반환값.
- Selective on/off의 같은 실제 실행 trace.
- 네 방법의 전체 snapshot 직렬화 bytes와 digest 결과, 근거 렌더 bytes.
- Selective on/off의 `possible/get/admit` 순서와 반환값, 각 get/admit 전후의 전체 π.

따라서 query 끝에서 우연히 상태가 되돌아온 경우만 검사하는 구조가 아니다.
실제 admission·축출 과정의 상태 변화도 비교한다. 계측판 장부의 파서 호출 수와
snapshot bytes는 이 외부 감사의 직접 계수와 다시 대조한다.
비계측판에는 가짜 P7/P8/cost 장부를 만들지 않는다. `audit` 열은 이 별도 검사 실행에서
얻은 수치이고, timing 실행의 내부 측정값이라고 부르지 않는다.

Public 입력은 매 방법마다 `records/entities/snapshot/query` 네 필드를 whitelist
복사하고 namespace만 별도 인자로 전달한다. Family, gold, 미래 반복 정보는 runtime에
전달하지 않는다. Raw 결과의 `cost`가 없는 off 경로도 같은 gold 평가기를 거친다.

## 4. 실행한 개발 검사와 작은 반례

`python research/phase09/audit.py --output <새 경로>`를 실제 실행했다.
최종 개발 산출물은 [development_audit.json](development_audit.json)이다.

| 검사 | 실제 범위와 결과 |
|---|---|
| 작성한 chronological 경계 | 20 prefix ×4방법, Obs·실행 trace·π 불일치 0 |
| Phase08 공개 개발 자료 | 89 step ×4방법, 구조·gold·Obs·trace·π 실패 0 |
| 원본 계측 경로 대조 | 20 prefix ×2계측방법, 원래 Phase08 결과·모든 비시간 장부·π 일치 |
| 정책 상태 mutant | 15개, 모두 답이 같아도 π 차이를 검출 |
| Gold 평가기 mutant | 9개 모두 검출 |
| 정확 source→AST 삭제 | 생성 3파일과 저장 파일의 exact bytes 일치 |

20 prefix에는 cold/warm, 같은 길이 원문 수정, 같은 길이의 cheap false positive,
ordered entities·membership·namespace 변화, copy 이전 원문 수정, 현재 demand별
scope 변화, 같은 query 안의 중복 raw, invalid digest/order, unsupported, 빈 이력,
32k–34k UTF-8 원문의 기본 65,536 용량 압박을 포함한다.
89개 기존 개발 step과 이 20 prefix는 독립 대화 표본이 아니며 새 성과 분모에 더하지 않는다.
상속된 전체 1,877 prefix 회귀는 주 구현자의 동결 전 실행기가 별도로 수행한다.

15개 정책 mutant는 hit, surplus, size, characters, entry order, next_order,
directory count, retained bytes, raw key, context key, payload length, stage value,
dictionary insertion order, capacity, directory mode를 각각 변조한다.
그 뒤 짧은 질문만 실행하면 답은 전부 그대로지만 π가 다르므로 검출된다.
이는 각 mutant의 검출이지 모든 가능한 오류의 부재 증명이 아니다.

### Hit를 통계로 오인해 지운 실제 세 요청 반례

기본 용량과 정책 상수를 그대로 두고 긴 noop A, B를 만든다. A의 surplus는
**32,146**, B의 surplus는 **33,346**이며 크기는 각각 **32,812 / 34,012**다.
각각은 보관 가능하지만 합 **66,824 > 65,536**이므로 함께 보관할 수 없다.

실행 순서는 A, A, B다. 올바른 구현은 두 번째 A에서 hit를 1로 올려
victim weight가 `2×32,146=64,292`가 된다. B의 surplus 33,346이 이보다 작으므로
B를 거절한다. Hit 갱신을 지운 mutant는 weight가 32,146에 머물러 B가 더 크다고
판단하고 A를 축출한다. **세 요청의 Obs는 모두 같지만 두 번째부터 π가 다르고,
세 번째에서는 admission·victim 결과까지 달라진다.**

이 반례는 hit counter가 삭제 가능한 계측 장부가 아니라 정책 상태임을 보여 준다.
양쪽 모두 답을 맞혔다는 사실로 동일 정책의 계측 제거를 인증해서는 안 된다.

### 개발 중 수정한 검사 전제

첫 gold-mutant fixture 초안에는 기존 파서 문법에 없는 `공원으로 확정해줘`가 있어
정상 결과부터 opaque fallback이었다. 이 조건에서는 “복수값 인증” mutant라는
전제가 성립하지 않았다. 새 평가 전에 fixture를 기존 문법의 `카페로 확정해줘`로
바꾸고 정상 결과가 `certified_model`인지 assert를 추가했다. 원래 파서·자료·평가기나
Phase08 결과는 바꾸지 않았다. 이는 개발 fixture 수정이고 새 holdout 조정이 아니다.

## 5. Gold 경계

Gold 판정은 고정된 Phase07 `S7.assess`를 재사용하며, 구조·schema·false certification,
주변부 containment, selected-gold의 공동 투영 보존을 구별한다. Invalid snapshot과
membership 의미 투영 미정의는 gold 분모에서 제외한다. Unsupported의 전체 이력
선택 성공은 답변 성공이 아니다. Gold 적용 수와 유효·지원 수가 같아도 같은 집합이라고
표현하지 않는다. 각 수치의 분모를 summary에 별도로 보존한다.

빈 인증 예측, 필수 필드 누락, 틀린 singleton, 복수값 인증, 잘못된 타입,
지원 질문의 unsupported 분류, 원인 근거 누락, 부분 fallback, 잘못된 integrity
실패를 mutant로 검출했다. 라벨·family·가상의 future-hit 값을 바꿔도 public whitelist는
바뀌지 않음을 확인했다. 외부 reader의 충분성, 자연어 정답, 실제 실행 증거는 검증하지 않았다.

## 6. Timing·동결 실행기 검토

주 비교는 fresh_uninstrumented→selective_uninstrumented다. 네 경로의 cache 생성·파괴,
전체 검증·현재 파싱·key/payload·정책·상태 실행·렌더가 같은 외부 구간에 들어간다.
Selective만 계측을 제거한 불균형 비교를 주 성과로 삼지 않는다.

검토한 `benchmark.py`는 별도 interpreter에서 trace/profiler 부재와 audit/evaluator
미import를 확인한다. 내부 호출 수 패치는 없다. 각 측정은 전체 workload 3 replay를
외부 `perf_counter_ns` 한 쌍으로 재고, cache는 매 stream·replay 새로 만든다.
2회 warmup도 보존하며 40 round, 균형 순서 10 cycle을 고정한다. GC precollection은
양쪽 동일하게 구간 밖이고 정상 GC는 켜 둔다. CPU/OS cache cold를 주장하지 않는다.
여기서 미import는 **Phase09 `audit.py`/`evaluator.py`**를 뜻한다. 원본 계측 wrapper에
필요한 Phase08 `evaluation`과 그 binding은 import 구간에서 로드되며 주 구간 안에서
gold 판정·평가 함수를 실행하지 않는다.

Bootstrap 단위는 같은 고정 workload의 연속 4-round cycle이며 질문·대화가 아니다.
Cycle 10개는 작고 임의 host drift를 보장하지 않는다. 3% practical margin과
원본·별도 재현의 공통 성공 조건은 결과 전에 고정한다. 작은 진단 stream 시간은
별도 8회 실행이고 주시간을 더해 분해한 값이 아니다. 부품별 CPU 원인을 식별하지 않는다.

실행기는 correctness 실패가 하나라도 있으면 timing을 시작하지 않는다. 별도 재현에서는
시간을 제외한 8개 산출물을 byte-identical 비교한다. Source·생성 code·자료·protocol·
review hash를 checkpoint/freeze에서 결합한다. 로컬 동결을 외부 사전 등록으로 부르지 않는다.

**동결 전 검사에서 확인한 것은 계약 구현과 감사 구조다. 새 자료의 성능은 아직 읽거나
측정하지 않았고, SOOM 운영과 이전 frozen 연구 파일은 변경하지 않았다.**
