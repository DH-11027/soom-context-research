# Phase08 동결 전 개발 감사

이 문서는 주 구현자와 다른 동일 모델 에이전트가 작성한 개발 검사 기록이다.
새 holdout과 그 builder는 열지 않았다. **외부 독립 검증이나 새 성능 평가가 아니다.**
기준 의미 구현은 변경하지 않은 Phase06 `text_scoped`, 비용 비교 기준은 Phase07 완료
커밋 `6da051c0132811184ecf39975d7ff647a1f47842`의 원래 `fresh`와 `lru`다.

## 1. 읽고 검토한 범위

- `frozen.py`, `runtime.py`, `evaluation.py`를 읽었다.
- Phase07 인수인계 감사에서 읽은 `cached.py`, `study.py`, `audit.py`,
  Phase06 `scoped.py`, `evaluate.py`, Phase05r2 `engine.py`를 참고했다.
- 개발 검사 `audit.py`를 작성하고 실행했다. 새 holdout 파일·builder·결과는 읽지 않았다.
- 정책 구현을 직접 수정하지 않았다. 구현자는 수학 검토 후 관측 값 수집과 payload 준비
  control action을 추가했으며, 이 변경을 반영해 cold 25 / warm 9 action 수식을 확인했다.

한 개발 평가기 fixture에서 자연스러운 한국어 `공원으로`를 써 기준 파서가 fallback한 것을
발견했다. 동결 전에 이미 지원되는 `카페로`로 그 fixture를 바꾸고 기준 결과가
`certified_model`인지 명시적으로 assert했다. 파서 문법과 새 평가 라벨을 수정한 것이 아니다.
이 사례는 개발 검사도 제한된 문법 계약을 정확히 따라야 함을 보여준다.

## 2. 검사 구성과 결과

```bash
python research/phase08/audit.py
```

`audit.run()`은 JSON 직렬화 가능한 기록을 반환하며 assertion 실패 시 실행을 멈춘다.
현재 검사 구성은 다음과 같다. 반복 방문을 독립 대화나 독립 의미 표본으로 세지 않는다.

| 개발 검사 묶음 | 검사 수 | 관측 |
|---|---:|---|
| 선택기 관찰·계측·memory invariant 검사 | 50 visits | 불일치 0 |
| 원래 Phase07 LRU와 `MeteredLRU` | 10 visits | 원래 모든 비시간 counter·결과·LRU 순서 일치 |
| 작은 authored gold를 이용한 평가기 mutant | 9 mutants | 9개 모두 검출 |
| 정확 cold/warm·8회 합계 수식 | 2식 묶음 | 잔차 0 |
| 두 항목 합계 용량 경계 | 1쌍 | 3 bytes 초과 시 계획된 eviction과 invariant 확인 |
| 불변 값 mutation/alias | 4종 + 결과 alias 재실행 | 저장값 오염 없음 |

50 visits마다 다음을 검사한다.

- `status`, `prediction`, `selected`, `remaining_input_facts`, `scope_trace`, `reason`,
  출력 길이 및 **실제 렌더 UTF-8 bytes**가 기준과 같은지.
- 현재 snapshot hash 호출·bytes와 reparse가 기준과 같은지.
- 각 단계의 `requests = calls + reused` 및 기준 논리 요청과 일치하는지.
- P7 항의 합, control action 종류별 합, `P8=P7+8×actions`의 장부 일치.
- retained bytes와 실제 저장 item 합의 일치, entries/bytes 한도, peak 한도.
- length directory가 실제 resident 문자 길이의 정확한 Counter인지.
- 모든 resident가 실제 얻은 cheap/contract/detail의 완전한 묶음이고,
  cheap는 `havoc`, contract 범위는 `None`인지.
- entry size가 `C+L+R+80`, surplus가 `L−C−R−64`이며 양수인지.

원문 수정·동일 ID·동일 문자 길이 충돌·엔터티 순서·membership·namespace 변경,
역사적 copy source 수정·질문 demand 변경·재정렬·삭제·재삽입·동일 원문 다른 기록,
빈 이력·잘못된 snapshot·unsupported 경로를 포함한다.

invalid snapshot과 unsupported에서는 cache와 정책에 접근하지 않는 것까지 검사한다.
항목이 이미 warm이어도 이를 우회하지 않는다. 반환된 prediction을 수정해도 저장된
순수 값은 바뀌지 않음을 재실행으로 확인한다.

`MeteredLRU` 검사에서는 원래 P7 `ParseCache`와 같은 용량의 두 cache에 같은 chronology를
주고 원래 cost 필드 전체(시간 제외), 의미 결과, 렌더, resident key 순서를 직접 비교한다.
따라서 새 control 장부를 추가하면서 원래 P7 바이트 수치를 바꾸지 않았는지를 확인한다.

## 3. 실제 계산된 개발 비용식

한 long deep quote와 한 short set, namespace `audit-v1`에서
`C=99`, `L=1271`, `R=154`였다. short set은 cache에 넣지 않는다.
cold는 length directory가 비어 있어 exact probe를 하지 않지만 현재 세 단계 실행,
payload 준비, key 생성, write, 메타데이터를 모두 지불한다.

\[
\Delta_{cold}=2C+2L+2R+25\cdot8=3248.
\]

완전 warm은 quote 세 단계를 재사용하고 short set은 다시 파싱한다. 질의당 context
생성 bytes와 short set의 gate 비용을 포함하면

\[
\Delta_{warm}=2C-L+R+9\cdot8=-847.
\]

기록 하나의 surplus 조건에는 질의당 context 생성비와 다른 기록의 비용이 모두 들어가는
것이 아니다. 위 식은 그 항까지 포함한 작은 전체 질문의 계산이다.
8회 합계는 `3248+7×(−847)=−2681`로 장부와 정확히 일치했다.
이는 직접 구성한 개발 조건의 수식 검사이며 holdout 성과가 아니다.

## 4. 실제 남긴 실패·반례

| 개발 조건 | 결과·의미 |
|---|---|
| 첫 방문 직후 종료 | ΔP8=+3,248. 다음 방문이 없으면 구축비를 회수하지 못한다. |
| 같은 long deep를 2회 방문 | 실제 호출 8→5이고 hit가 있지만 전체 ΔP8=+2,401. |
| 동일 문자 길이의 long cheap 문장 | exact-key miss가 안전성을 지키지만 호출 절감 없이 ΔP8=+2,804. |
| 인기 있었으나 다시 쓰이지 않는 resident 뒤에 작은 새 항목 4회 | 새 항목을 계속 거절하고 그 4회의 ΔP8=+1,588. 과거 hit에는 aging이 없다. |
| length만 key로 쓰는 잘못된 정책 | 마침표→물음표의 같은 길이 원문에서 `certified_model`과 `opaque_fallback`을 혼동한다. 실제 정책은 exact raw/context로 구별한다. |
| cheap 결과만으로 깊이를 추정 | cheap `havoc`만으로 2단계 scoped 경로와 3단계 deep 경로를 구분할 수 없다. 실제 정책은 현재 자연 실행에서 단계 결과를 얻은 후 admission한다. |

capacity 검사에서는 두 항목의 합 `3208 bytes`에 맞춘 budget에서 둘 다 보관되고,
두 번째 항목에 한글 한 글자를 더해 `3211 bytes`가 되면 한 항목을 축출해 한도를 유지한다.
거절된 victim 계획은 resident를 부분 삭제하지 않는다. 이 관측이 모든 working set에서
유리한 교체를 보장하지는 않는다. popular stale resident 반례가 그 한계를 보여준다.

## 5. 평가기 검토

공개 입력은 `records/entities/snapshot/query` 네 필드 whitelist와 명시적인 namespace다.
gold, family, 가상의 future-hit label을 바꿔도 public 입력은 바뀌지 않음을 검사했다.
정책 모듈은 evaluator나 자료를 import하지 않는다.

평가기 mutant는 빈 인증 예측, 필수 질문 필드 누락, 틀린 단일값, 복수값 인증,
잘못된 값 타입, 지원 질문의 unsupported 오분류, 선택 근거의 원인 사건 누락,
일부 이력만 내는 fallback, 유효 snapshot의 integrity failure 오분류다.
이 9개를 모두 검출했다. 이는 알려진 빈틈을 검사하는 음성 대조군이며 모든
가능한 평가기 오류의 부재 증명이 아니다.

평가기는 P7의 엄격 gold 해석을 사용한다. 주변부 containment, 단일값 certification,
선택 gold의 공동 투영 보존을 분리하고, invalid 및 정의하지 않은 membership 투영의
gold 제외를 유지한다. 전체 원문과 digest만 받은 reader의 독립 의미 검증은 하지 않는다.

## 6. 남은 한계와 동결 전 결론

조건부 의미 보존 경로의 구현 불일치는 현재 검사에서 발견하지 못했다.
`frozen.verify_sources()`는 실행기가 호출해야 하며 runtime 단독 호출은 매번 코드 파일을
해시하지 않는다. 살아 있는 cache 중간에 parser 규칙을 바꾸는 mutation은 계약 밖이다.
namespace 교체는 분리 검사이며 실제 배포된 parser 업그레이드 실험이 아니다.

P8의 control action 가중치 8은 명시한 논리 점수이며 실측 CPU·RAM 바이트·LLM 비용이 아니다.
개별 Python 연산을 전부 동일한 실측 비용으로 환산한 것도 아니다. 실행시간을 별도 보고하고,
가중치 민감도는 고정 정책의 점수 재계산이라는 경계를 유지해야 한다.

hit cap 검사는 개발 시 메타데이터를 상한으로 놓아 다음 hit에서 포화가 유지되는지 확인한 것이다.
정책 벤치마크에 미래 정보나 임의 hit count를 제공하지 않는다.
concurrency, 외부 자연어 의미, 실제 토큰·요금·답 품질, 물리 메모리 상한은 검증하지 않았다.
**SOOM 운영 변경 없음.**
