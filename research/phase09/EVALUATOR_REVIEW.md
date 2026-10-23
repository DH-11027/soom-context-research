# Phase09 평가기·정책 상태 감사 설계

작성일: 2026-10-23 KST. 주 구현자와 역할을 분리한 동일 모델 검토자의 코드다.
외부 독립 검증 또는 외부 자연어 의미 평가가 아니다.

## 독립 비교의 범위

`audit_equivalence.py`는 네 경로를 각 stream의 빈 cache에서 시작해 순서대로 실행한다.
계측판은 새로 재구현하지 않고 Phase08 `evaluation.run`을 직접 호출한다.
비계측판은 Phase09의 `run_fresh`와 `run_selective`를 호출한다.

매 입력 prefix가 끝날 때 다음을 **직접 동등 비교**한다. 아래 hash는 큰 상태와 trace를
원시 행에 압축 기록하기 위한 영수증이며 동등성 판단은 hash 비교로 대신하지 않는다.

1. `cost`만 제거한 결과의 모든 필드와 각 필드의 존재 여부, 실제 근거 렌더의 전체 bytes.
   현재 `status`, `reason`, `prediction`, `selected`, `output_bytes`,
   `remaining_input_facts`, `scope_trace`가 포함되며 예상하지 못한 추가 필드도 검사한다.
2. 계측/비계측 selective의 resident exact key, dict 순회 순서, stage immutable 값과
   실제 encode payload 길이, size, characters, surplus, hits, insertion order.
3. Directory의 실제 내용과 순회 순서, retained bytes, next order, directory 사용 여부,
   max entries와 max bytes. 통계 전용 peak는 정책 projection에서 제외한다.
4. On/off 각각의 실제 cheap/scope/detail 호출 순서, 원문, ordered entities.
5. 전체 snapshot SHA-256 호출 횟수와 전달된 직렬화 bytes 전체.

호출 감사는 별도 정확성 실행에서 함수의 진입점을 임시 wrapping하고 반드시 복원한다.
주 timing은 이 평가기를 호출하지 않아야 하며, 호출 수를 얻기 위해 timing 안에
wrapper를 다시 넣으면 비계측 성능 결과로 인정할 수 없다.

## 추가 구조 검사

- 입력 public이 변경되지 않았는지 확인한다.
- 무효 snapshot과 미지원 질문의 early exit가 resident 상태를 바꾸지 않는지 확인한다.
- 실제 호출과 기존 계측 장부가 일치하는지 확인한다.
- Directory가 resident characters의 Counter인지, retained 합이 entry size 합인지,
  모든 resident가 immutable complete bundle인지 검사한다.
- 실제 key가 `(context bytes, exact raw bytes)`인지와 character 길이·logical size·surplus·
  hit cap·insertion order·capacity를 독립 식으로 재계산한다.
- 렌더 길이와 output bytes를 대조한다.

평가기 자체의 검출력은 synthetic resident state를 직접 변조한 여덟 mutant로 확인한다.
Hit 갱신 삭제, surplus 변경, entry order 변경, next order 변경, directory 변경,
retained 변경, 같은 길이 다른 raw key, stage 값 변경이 대상이다. 이는 실제 runtime에서
그 결함을 발견했다는 뜻이 아니며, 보존 관찰과 별도로 정책 상태를 검사해야 한다는
평가기의 계약 확인이다.

## Gold 재사용의 경계

Gold 관련 검사는 기존 Phase07 `study.assess`와 Phase06 evaluator를 읽기 전용으로
재사용한다. 따라서 새 의미 평가기를 독립 구현했다고 주장하지 않는다.
False certification, 주변부 containment, selected-gold 공동 투영은 서로 다른 검사이며,
unsupported 질문에 대한 전체 이력 선택 검사는 답변 성공으로 세지 않는다.
Validity와 gold 적용 여부의 교집합·차집합을 별도로 세는 summary 필드를 둔다.

## 동결 전 실행 상태

이 문서는 동결 전 감사 설계이며 실행 완료 결과는 `development_results_v2/`와
최종 `POSTFREEZE_REVIEW.md`에서 확인한다. Phase08 재현과 읽기 범위는
`INHERITANCE_AUDIT.md`에 있다. 이 역할은 Phase09 평가 자료·builder를 동결 전 읽지 않는다.

## 동결 전 실제 실행 결과

`development_results_v2/`에 기존 자료의 별도 감사 실행을 보존했다.
초기 `development_results/`의 결과도 그대로 남겼다. 필드 부재와 명시적 `None`을
동일시하지 않고 예상하지 못한 결과 필드도 검출하도록 관찰 비교를 강화한 뒤,
동결 전에 전체 자료를 다시 검사한 것이 v2다. Runtime·정책은 변경하지 않았다.

| 자료 | Prefix | 네 경로 raw rows | 실패 |
|---|---:|---:|---:|
| Phase08 이전 주평가, 이번에는 개발 자료 | 432 | 1,728 | 0 |
| Phase08 개발 자료 | 89 | 356 | 0 |
| Phase05·06·07 역사 회귀 | 1,356 | 5,424 | 0 |
| 합계 | 1,877 | 7,508 | 0 |

이 합계는 새 평가나 독립 대화 1,877개가 아니다. 관찰·resident 상태·실제 parse/hash trace·
구조·gold 검사에서 실패가 없었다. 여덟 resident state mutant와 세 observation mutant
(reason 부재/None 차이, prediction 삭제, 예상하지 못한 필드 추가)를 모두 검출했다.
Fresh 비계측판의 `scope_from_text`가 import 당시 별도 alias로 잡혀 있음을 발견하여,
감사 wrapper가 그 alias도 실제로 관측하도록 개발 단계에서 수정한 후 위 실행을 했다.
이는 runtime 버그가 아니라 호출 감사 구현에서 피해야 하는 측정 누락이다.

정상 감사 종료마다 함수 identity를 확인하고, 고의 예외 종료에서도 6개 관련 바인딩이
원래 함수 객체로 돌아오는 것을 별도 확인했다(`development_results_v2/receipt.json`).
주 timing에서는 호출 추적 context에 진입하지 않는다.

## Timing 설계 검토

동결 전 `benchmark.py`를 직접 읽었다. 네 방법의 24개 permutation을 모두 한 번씩
사용하므로 각 순서 위치와 선행 방법이 균형을 이룬다. 비교는 full-workload interval을
포함한 block 내부 비율이며, 각 interval에서 3회 workload를 수행하되 매 stream마다
빈 parser cache를 생성한다. Off/off가 주 비교이고, 보조 stream·첫 step timing은
별도 기술 통계다. GC는 켠 상태이고 timing process는 허용된 첫 CPU 하나에 묶는다.
자료 로딩·gold·감사 wrapper는 전체 시간 구간 바깥이다.

24 block의 bootstrap은 고정 합성 자료와 그 로컬 timing 세션의 조건부 불확실성을
표현한다. Block 교환 가능성이 필요하며 시계열 의존성이 배제된 것은 아니다.
독립 dialogue 표본이나 플랫폼 일반화에 대한 신뢰구간으로 바꾸어 말할 수 없다.
`rejects_practical_speedup_here`는 사전 정의한 **5% 실질적 개선 기준**에 대한 판단이다.
예를 들어 안정적인 2% 개선을 관측하더라도 이 라벨이 붙을 수 있으므로 모든 작은
속도 감소가 없다고 해석해서는 안 된다. 추가 반복·이상치 제거·유리한 실행 선택을
결과 확인 후 허용하지 않는 동결 계획이 필요하다.
