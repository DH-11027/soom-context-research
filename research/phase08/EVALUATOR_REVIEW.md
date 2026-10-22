# Phase08 평가기·실행기 동결 전 검토

검토자: 주 구현자와 다른 동일 모델 에이전트. 작성: 2026-10-22 KST.
새 Phase08 holdout 원문·gold·builder·결과는 열지 않았다.
공개 연구 설계를 공유한 역할 분리이며 **외부 독립 검증이 아니다.**

## 검토 의견

**아래에서 실제 검토·검사한 범위에서는 동결과 사전 계획대로의 주 실행을 막는
미해결 결함을 발견하지 못했다.** 이것은 모든 입력의 구현 무결성 또는 실제
자연어 의미 정확성을 인증하는 의견이 아니다. 동결 이후 결과가 좋든 나쁘든
사전 주 비교와 분모를 유지하고 모든 산출물을 보존해야 한다.

## 실제 읽은 범위

- `frozen.py`: 고정 Phase05/06 소스 hash 및 의미 fingerprint 결합.
- `runtime.py`: raw-only 입력 경로, 단계별 값 수집, admission, 용량·directory·victim 관리.
- `evaluation.py`: 기존 P7 import·`MeteredLRU`·public 분리·gold 판정·집계·비교·timing.
- `development.py`: 공개 9개 stream/89 step 생성 규칙, 별도 typed gold·question contract.
- `run_study.py`: checkpoint 확인, freeze/verify, 새 출력 경로, 결정적 압축 산출물과 timing 분리.
- `PROTOCOL.md`: 주가설, 비교군, 고정 상수, 지표, 데이터 분리, 실패와 재현 규칙.
- `audit.py`: 이 검토자가 작성한 개발 검사의 전체 코드.

Phase07 및 이전의 실제 검토 범위와 시작점 재현은 [INHERITANCE_AUDIT.md](INHERITANCE_AUDIT.md)에
기록했다. 이번 새 평가 자료는 해시 동결 전 열지 않았고, builder를 실행하지도 않았다.
주 구현자가 전달한 개발·역사 자료 결과는 개발/회귀 결과로만 취급한다.

## 1. 선택기와 평가 라벨의 경계

`evaluation.evaluate`는 `S7.public_of`를 통해 공개 입력 네 필드
`records/entities/snapshot/query`만 복사하고 namespace를 별도로 전달한다.
gold AST, question contract, family/split, 미래 step, 미래 hit count를 정책에 넘기지 않는다.
개발 검사에서 gold와 가상의 future label을 바꿔도 이 public 입력이 같음을 확인했다.
`runtime.py`와 `frozen.py`는 evaluator나 fixture를 import하지 않는다.

admission은 원래 현재 질문이 요청한 세 단계 결과를 실제 얻은 뒤 판단한다.
payload encode/immutable 준비 비용과 관측 결과 수집 action을 부과한다.
같은 문자 길이는 exact lookup을 시도할 가능성만 알려주며 semantic identity나
예상 단계 수로 사용하지 않는다. false positive는 비용 손실을 만들 수 있으나
실제 값 재사용에는 정확 context·raw 비교가 필요하다.

## 2. 보존·gold·분모

각 후보 결과를 원래 fresh와 `status/prediction/selected/remaining demand/trace/reason`
및 **직접 렌더한 UTF-8 bytes**로 비교한다. 길이나 digest만 같은지를 보지 않는다.
각 stage의 논리 요청 수가 fresh의 호출 수와 같고 `requests=calls+reused`인지 확인한다.
invalid와 unsupported에서는 정책/cache 접근이 없어야 한다.

평가기는 기존 P7의 별도 typed gold 실행과 엄격한 질문 필드 검사를 사용한다.
false certification, 주변부 containment, 선택 gold의 공동 답집합 투영 보존을 구별한다.
gold를 적용하지 않은 invalid snapshot 및 정의하지 않은 membership 투영은
gold 성공 분모에서 제외한다. 해당 조건에서도 baseline parity와 구조 검사는 남는다.
unsupported의 selected-gold 검사는 전체 이력 선택 확인이지 답변 성공이 아니다.

개발용 정상 인증 사례를 명시하고 다음 9개 mutant를 모두 검출했다:
빈 예측, 필수 필드 누락, 틀린 단일값, 복수값 인증, 잘못된 타입,
지원 질문의 unsupported 처리, 원인 사건을 빠뜨린 선택, 일부 이력만 낸 fallback,
유효 snapshot을 integrity failure로 처리한 결과.
이 유한 음성 대조군은 모든 평가기 결함의 부재 증명이 아니다.

## 3. 비교군과 비용 장부

주 비교는 `selective` 대 원래 `fresh`이며, 더 비싼 `lru` 또는 `no_directory`만
이겼다고 주가설을 지지하지 않는다. `MeteredLRU`는 기존 알고리즘과 용량을 유지하고
추가 control 장부만 붙인다. 개발 chronology 10 visits에서 원래 P7의 모든
비시간 cost 필드·출력·resident 순서·보관 bytes가 원래 구현과 일치했다.

P7의 원래 바이트 장부를 그대로 남기고 P8에 명시한 8×control actions를 더한다.
8은 CPU 또는 bytes의 실측 환산율이 아니다. 장부에 없는 Python allocator,
hash/equality 세부 동작, 정규식 조기 종료 등을 실제 시간으로 따로 관측한다.
source bytes를 CPU의 실제 완전 원문 순회 수로 부르면 안 된다.

개발 50 visits에서 P7 합, action 종류별 합, `P8=P7+8×actions`,
현재 snapshot hash 호출/bytes의 기준 일치를 검사했다. cold와 warm 모두 포함한다.
고정 정책에 대한 λ=0/8/32/128 점수 민감도는 **동일 실행의 재채점**이며,
각 λ에 맞춰 정책을 다시 설계·튜닝한 결과가 아니다. 주 판정은 λ=8에 고정한다.

원문 길이 gate 때문에 짧은 기록에서도 양의 control 비용이 생길 수 있다.
첫 admission 뒤 stream 종료, hit가 있지만 전체 손실, 같은 길이의 무익한 probe,
인기 있었던 stale resident의 고착 반례를 개발 감사에 남겼다.
이 정책의 universal dominance나 미래 최적 교체를 주장할 수 없다.

## 4. 동결·실행·재현 절차

`freeze()`는 core·protocol·review·자료 파일이 이미 checkpoint `HEAD`에 존재하며
작업트리 bytes와 같아야 진행한다. 생성한 development도 파일과 정확히 같아야 한다.
checkpoint commit/tree와 파일 hash, baseline hash, 시각을 기록한다.
새 holdout은 byte hash만 계산하며 내용이 root에게 출력되지 않는다.
이는 로컬 동결이며 외부 사전 등록이 아니다.

`--run`은 verify를 먼저 수행하고 새 출력 디렉터리만 사용한다. 이미 있는 경로는
거절한다. 파일 hash 검증은 trusted working tree의 무결성 gate이며 adversarial한
파일 시스템·소스 monkey patch까지 막는 보안 경계로 주장하지 않는다.

결정적 대상은 audit, 주평가 요약/원시 행, 역사 회귀 요약/원시 행의 5개 파일이다.
gzip filename을 비우고 mtime=0으로 만들어 압축 bytes의 재현을 가능하게 한다.
시각·플랫폼·시간 표본은 별도 receipt/timing 파일이므로 같은 bytes를 요구하지 않는다.
동결 이후 알고리즘·라벨·주비교·주지표를 수정해야 하면 원래 실행과 별도 정정이 필요하다.

7회 timing은 매 stream마다 새 연구 cache를 쓰고 warm-up cache를 버린다.
cache 생성부터 검증·파싱·정책·추론·렌더까지 포함한다. CPU/OS cache가 모두
차갑다는 뜻은 아니며, imports/자료 로딩/offline gold/LLM은 제외한다.
통계적 유의성이나 모집단 성능을 추정하지 않는다.

## 5. 실행한 검사와 미실행

검토자 실행: `python research/phase08/audit.py`.
최종 개발 검사에서 parity 50 visits, 원래 LRU counter 보존 10 visits,
평가기 mutant 9개와 위의 비용·capacity·immutable 검사가 통과했다.
상세 수치와 반례는 [DEVELOPMENT_AUDIT.md](DEVELOPMENT_AUDIT.md)에 있다.

아직 실행하지 않은 항목: 새 Phase08 주평가, 그 별도 재현, 새 원시 행 재집계,
holdout 모든 원문의 외부 의미 재판정, 실제 LLM 비용·토큰·품질,
concurrency와 실제 배포 성능. 해당 항목은 완료했다고 표현하지 않는다.
**SOOM 운영 변경 없음.**
