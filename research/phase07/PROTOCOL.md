# Phase 07 실행 전 계획 — 질문 사이의 순수 해석 결과 재사용

작성: 2026-10-22 19:12 KST (10:12 UTC), 구현·새 평가 전.
기준은 공개 Phase06 `13d166dc106fa3ab33128ad0626679fafdce5019`이며 기존
Phase01–06 동결 코드·자료·결과와 SOOM 운영은 변경하지 않는다.

## 선택한 질문과 이전 제안과의 관계

Phase06의 다음 후보는 원문 scope 추출기의 외부 검증이었다. 이번에는 외부
독립 작성자/실제 LLM 평가를 확보한 것처럼 진행하지 않고, 관측된 비용 병목 중
**여러 질문에서 같은 원문의 해석을 반복하는 부분**을 분리한다. scope 언어는
확장하지 않는다. 따라서 답변 범위나 출력이 더 좋아지는 가설은 없다.

- H7-S: 순수 cheap/scope/detail 결과를 올바른 key로 재사용하면 현재 이력의
  재실행과 status/prediction/selected/output/remaining demand/trace가 정확히 같다.
- H7-P: persistent 재사용이 실제 순수 파서 실행을 줄인다. hits만으로 성공 판정하지 않는다.
- H7-C: 캐시 관리까지 포함한 사전 동일 가중 byte-work proxy가 감소한다.
- H7-T: cold 시작부터 전체 stream의 계측된 로컬 실행 시간이 감소한다.
  위 네 판정은 분리한다. time이 좋아도 byte 실패를 숨기거나 지표를 바꾸지 않는다.

## 알고리즘과 계약

원문 내용, 순서 있는 entities, 실제 동결 파서/scope fingerprint, 실행 namespace를
정확 key에 포함한다. SHA digest만 key로 삼지 않고 원문 key의 정확 동등성을 유지한다.
한 기록에서 key를 한 번 준비해 cheap/scope/detail stage에 공유한다. stage별 결과는
별도 슬롯에 보관한다. query-dependent 최종 TOP/선택/답/참조 시점 값은 저장하지 않는다.
trace/index/역방향 요구/현재 상태 실행은 각 질문마다 계산한다.

immutable stage 값을 사용한다. cache hit가 과거 질문에 의해 변형된 dict/list를
돌려주지 않게 한다. LRU 한도는 **64 entries와 65,536 logical serialized bytes**로
미리 고정한다. oversized 항목은 보관하지 않는다. 이것은 CPython RSS 상한이 아니다.
후보 간 cache를 공유하지 않고 각 stream과 timing 반복은 empty에서 시작한다.
전체 snapshot 순서/hash 검증은 매 질문 동일하게 실행하고 cache가 우회하지 못한다.

## 비교군

1. `fresh`: 수정하지 않은 Phase06 `text_scoped` 재실행.
2. `disabled`: 같은 새 경로와 key 비용을 지불하되 용량 0.
3. `reset`: 같은 bounded cache를 매 질문 비움. 질문 안의 중복 원문 효과.
4. `lru`: stream 전체에서 bounded cache 유지. 주 비교는 fresh와의 차이.

동일 snapshot의 정확 답 캐시나 incremental semantic index는 구현하지 않는다.
namespace label 교체는 cache 분리 검사이며 실제 파서 배포 변경 실험은 아니다.
버전 변경의 의미가 바뀌는 경우는 별도의 작은 순수 함수 반례로만 검사한다.

## 데이터 분리

root의 새 development stream에서 구현·최소 반례만 조정하고 동결한다.
별도 동일 모델 작성자가 10 family×3 parameterization의 새 stream을 만든다.
반복 질문, 추가/늦은 정정, 같은 ID의 과거 편집, 재정렬/삭제/재삽입, 엔터티 환경,
재사용 적은 churn, 긴/짧은 원문, 질문 범위/미지원, namespace 교체,
잘못된 snapshot/복구를 포함한다. root는 동결 전 개별 내용·라벨·결과를 읽지 않는다.
같은 모델과 공개 설계를 공유하므로 외부 블라인드 평가가 아니다.

gold AST와 독립 question contract는 public 입력 밖에 둔다. 선택기는 공개 원문,
entities, query, snapshot과 실행 namespace만 받는다. roster membership 변경처럼
gold 투영 규약을 새로 만들지 않은 조건은 `gold_applicable=false`로 표시하여
gold 정확성 분모에서 제외하고 실행 동등성은 검사한다. invalid snapshot 역시
독립 integrity 판정과 동등성을 검사하며 실제 답 정확성으로 집계하지 않는다.

기존 Phase06 384질문과 Phase05 672질문은 모두 회귀 검사다. 이번 연구가
작성한 query 순서에서 cache를 적용해도 새로운 독립 의미 평가가 아니다.

## 사전 비용 정의

기존 output/hash/실제 cheap/scope/detail/reparse 입력 바이트에 다음을 더한다.

- `key_build_bytes`: query당 context의 canonical UTF-8 encoding, lookup당 raw text UTF-8 encoding.
- `key_probe_bytes`: lookup마다 exact context+raw key의 전체 논리 길이. native dict의
  hash/equality probe를 나타내는 보수적 논리 traffic이며 실제 RAM bus 계측이 아니다.
- `cache_read_payload_bytes`: 실제 재사용한 stage 값의 canonical 길이. immutable
  객체를 반환하며 hit마다 JSON decode/clone을 수행하지 않는다.
- `value_encode_bytes`: miss에서 stage 값을 canonical 표현으로 크기 계산한 길이.
  저장이 비활성화되거나 oversized라도 실제 수행한 encoding을 포함한다.
- `cache_write_bytes`: 새/갱신 항목 key와 stage payload의 canonical 길이.

`P7 = output + hash + parser_source + key_build + key_probe + value_encode + cache_read_payload + cache_write`.
memory는 retained key+stage payload의 canonical 길이와 entry 수/peak로 별도 보고한다.
LRU/hash/immutable conversion/추상 계산 등의 CPU는 실제 wall time에 포함한다.
호출수, cache hit/miss, stage reuse, actual executions avoided, eviction/oversize,
cumulative stream break-even과 family별 결과를 보고한다. 초기 miss/구축을 제외하지 않는다.

매 stage마다 원문 key를 새로 만들면 key bytes가 기존 parse bytes를 상쇄할 수
있으므로 key 준비는 기록당 공유한다. 그래도 cheap-only/unique/churn stream은
손해일 수 있다. 전체 snapshot/hash와 출력은 동등하므로 그 비용은 그대로 남는다.
실제 LLM 비용·토큰·자연어 답 품질이나 운영 성능은 측정하지 않는다.

실행 시간은 동일 stream의 순서를 보존하고 방법 순서만 회전해 7회 측정한다.
warm-up은 폐기 cache에서 수행한다. 중앙값/최소/최대와 개별 반복을 저장하며
통계적 유의성이나 population 효과를 주장하지 않는다.

## 판정과 완료

동결 후 code/gold/조건을 유리하게 수정하지 않는다. 모든 실패를 원시 결과에 남긴다.
출력 동등성, 엄격한 gold 판정, invalid 입력·잘못된 cache key 음성 대조군,
immutable 값, eviction/oversize를 검사한다. 검사가 통과해도 실제 파서 실행이
감소하지 않으면 재사용 성공이라고 하지 않는다. 결과·한계·재현·다음 한 가지
제안을 RETURN_TEMPLATE 형식으로 기록하고 별도 branch/PR로 전달한다.
