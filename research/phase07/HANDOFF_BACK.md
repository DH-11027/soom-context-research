# Phase 07 연구 인수인계 반환

## 출발 상태

### 읽은 기준과 연구 범위

- 저장소: <https://github.com/DH-11027/soom-context-research>.
- 최초 인수인계 기준: `780891f6c147cfd3c1a3b0d065792776aaa525f3`.
- 이번 단계의 직접 기준: 공개 Phase06 `13d166dc106fa3ab33128ad0626679fafdce5019`.
  로컬 직전 commit `b6c66cf`의 tree `6bac416f439768b220c42f7ab0df241085a2701a`가
  이 공개 기준 tree와 같았다.
- 연구자: ChatGPT와 동일 모델의 수학 검토·평가 검토·별도 자료 작성 에이전트.
- 날짜: 2026-10-22, 한국 시간. Python 3.12.14, Linux 6.18.55 x86_64, glibc 2.39.
- 기존 Phase01–06의 동결 코드·자료·결과와 SOOM 운영은 수정하지 않았다.

이 연속 연구에서 처음 읽은 순서는 `HANDOFF.md` → `docs/RESEARCH_LOG.md` →
`docs/MATHEMATICS.md` → `docs/NEXT_EXPERIMENT.md`였다. 이후 참고 문서와 핵심
Phase05r2 코드를 읽은 범위는 [Phase06 반환 문서](../phase06/HANDOFF_BACK.md)에
기록했다. 이번에는 Phase06의 `scoped.py`, `evaluate.py`, `THEORY.md`,
`HANDOFF_BACK.md`와 Phase05r2 `engine.py`의 파서·snapshot·질문 처리를 중심으로
검토했다. 모든 과거 연구를 다시 읽거나 다시 실행하지 않았다.

Phase07에서 주 구현자는 새 protocol, theory, cache, 평가기, 실행기와 개발 반례를
읽고 작성·검토했다. holdout은 로컬 동결 전 개별 원문·라벨·결과를 읽지 않았다.
동결 후 builder와 자료 작성 기록, 결과 요약, 비용 행을 확인했다. 별도 평가 검토자는
1,200개 원시 행을 재집계했다. 1.97 MB로 확장된 holdout의 모든 원문을 사람이
하나씩 독립 의미 판정했다고 주장하지 않는다.

### 이전 결론에 대한 정정과 새 발견

Phase06에서 답변 범위·출력의 일부 개선에도 전체 비용 proxy가 늘었다. 이번에는
그중 **질문이 바뀔 때 같은 원문을 반복 해석하는 비용**을 분리했다. Phase06의
다음 후보였던 원문 scope 추출기의 외부 검증은 이번에 수행하지 않았다. 새 언어
표현의 의미 정확도를 확장하는 연구와 반복 계산의 비용 연구를 섞지 않기 위해서다.

이전 수치를 소급 변경할 이유는 찾지 않았다. 이번 발견은 다음과 같다.

1. 순수 단계만 재사용하면 기존 결과와 정확히 같게 만들 수 있다. 현재 질문의 TOP,
   답, 선택 또는 copy 당시 값을 재사용하는 계약은 이보다 강하며 별도 증명이 필요하다.
2. 실제 파서 실행 수를 크게 줄여도 입력 바이트 절약은 작을 수 있다. 이번에는
   실행 −67.28%와 파서 입력 바이트 −15.38%가 동시에 관측됐다.
3. 캐시 overhead를 빼고 계산하면 143,492 proxy bytes를 절약한 것처럼 보이지만,
   overhead 2,391,270을 포함하면 순비용은 2,247,778 늘어난다.
4. 현재 raw-only scope whitelist와 deep grammar는 겹치지 않는다. 따라서
   “query-local TOP을 재사용해 다음 정확 답을 잃는다”는 일반 반례를 현재
   raw-only 엔진에서 실제 재현한 결함으로 부르지 않았다.
5. 사후 진단에서는 캐시 두 항목의 합이 한도를 넘자 원문 3 bytes 차이로
   P7 −12.23%가 +75.31%로 뒤집혔다. 이 조건부 결과는 주평가의 실패와 양립한다.

## 이번 가설과 계약

### 가설과 비교군

[PROTOCOL.md](PROTOCOL.md)에 새 평가 전 네 가설을 기록했다.

| 가설 | 뜻 | 이번 판정 |
|---|---|---|
| H7-S | 기존 Phase06과 관찰적 동등성 | 명시한 전제 아래 증명; 관측 검사 통과 |
| H7-P | 실제 순수 파서 실행 감소 | 지지: 2,292→750 |
| H7-C | 캐시 overhead를 포함한 P7 감소 | 이번 주평가에서 기각: +107.38% |
| H7-T | cold 시작부터 전체 로컬 시간 감소 | 원본·재현 모두 이득 관측 못함 |

`fresh`는 수정하지 않은 Phase06 `text_scoped`다. `disabled`는 같은 새 경로에서
용량 0, `reset`은 매 질문 새로 비우는 bounded cache, `lru`는 stream 동안 유지하는
bounded cache다. 주 비교는 항상 `lru` 대 `fresh`다. entry 한도 64와 논리적
보관 크기 65,536 bytes를 개발 단계에서 고정했다.

### 입력·출력과 보존할 의미

선택기는 public 원문 records, ordered entities, query, snapshot과 실행 namespace만
받는다. gold AST·정답 값·family·split은 선택기로 전달하지 않는다. 이번 Phase07에는
oracle may-write 방법을 추가하지 않았다. gold AST는 평가기의 joint-state 해석에만
쓰고, 실제 선택기는 원문에서 파싱한다.

단계 함수는 다음과 같다.

\[
f_{s,v}(E,t)=y,\qquad s\in\{cheap,scope,detail\}.
\]

v는 실제 동결 소스 fingerprint와 namespace, E는 순서를 보존한 entities,
t는 정확한 원문이다. key는 `(canonical_context_bytes, exact_raw_text_utf8)`이며
stage별 슬롯을 분리한다. digest만 같다는 이유로 다른 원문을 합치지 않는다.
값은 immutable로 저장한다. 시간·난수·과거 상태·외부 LLM 호출에 의존하는 파서는
현재 순수 함수 계약에 포함하지 않는다.

저장된 모든 stage에 대해 다음 불변식을 둔다.

\[
decode_s(cache[v,E,t][s])=f_{s,v}(E,t).
\]

빈 cache에서는 자명하다. miss는 같은 함수를 실행해 저장하고 hit는 같은 결과를
반환한다. eviction은 올바른 값을 삭제할 뿐이다. 현재 snapshot 검증과 논리적인
단계 요청, demand, 상태 실행, trace, 원문 렌더를 바꾸지 않으면 각 실행 단계에 대한
귀납으로 최종 관찰이 같다. stream의 다음 질문에도 불변식이 유지된다.

보존 관찰은 `status`, integrity reason, `prediction`, `selected`,
`remaining_input_facts`, 렌더된 UTF-8 출력, `scope_trace`다. 계측값은 같을 필요가 없다.
한도 0, eviction, oversized 항목에서도 의미 보존은 같고 비용만 달라진다.

이 보장은 기존 파서가 원문의 실제 의미를 맞췄다는 증명이 아니다. 원래 오류,
모호성, unsupported, 외부 reader의 독립적인 충분 근거 검증 부재도 그대로 남는다.
현재 실행은 단일 스레드이며 의미 namespace를 살아 있는 cache 중간에 몰래 바꾸지
않는다고 가정한다. 정확한 가정과 증명은 [THEORY.md](THEORY.md)에 있다.

### 데이터 구분과 동결

| 구분 | 크기·역할 | 독립성 경계 |
|---|---|---|
| 개발 | 5 stream / 26 step, 별도 39 parity 검사 | 구현·알고리즘 선택에 사용 |
| 새 holdout | 30 stream / 300 step | root 미열람으로 동결; 같은 모델·공개 설계 공유 |
| 기존 회귀 | Phase05 672 + Phase06 384질문 | 새 독립 의미 평가가 아님 |
| 사후 진단 | 18 cell / 144질문 | 주평가 후 구성한 비용식 검사; 독립 평가 아님 |

주평가의 10 family는 반복 질문, append·늦은 정정, 같은 ID의 과거 수정,
재정렬·삭제·재삽입, 엔터티 환경 변화, churn, 긴/짧은 원문, query 범위·미지원,
namespace 교체, invalid snapshot·복구다. 각 family에 3 parameterization,
각 stream에 10 step이 있다. seed는 `2026102207`이다.

로컬 동결은 **2026-10-22 19:17:37 KST / 10:17:37 UTC**이며 local commit은
`9039745d450b5207190ce1ed78c26b4819f60430`이다. GitHub 공개는 실험 이후이므로
외부 사전 등록으로 부르지 않는다. [freeze.json](freeze.json)은 core·자료·baseline의
hash를 기록한다. 동결 후 알고리즘·기존 라벨·주평가 조건은 바꾸지 않았다.

## 변경과 재현

### 변경 파일과 전달

새 파일은 모두 `research/phase07/` 아래다. 반환 branch는
[`research/phase07-parse-reuse`](https://github.com/DH-11027/soom-context-research/tree/research/phase07-parse-reuse)다.
Phase06 PR이 아직 열려 있으므로 새 PR의 base는 `research/phase06-scoped-opaque`로
둔다. 이 단계에서 PR을 merge하거나 SOOM 운영에 적용하지 않는다.

| 파일 | 역할 |
|---|---|
| `baseline.py`, `cached.py` | 동결 기준 로딩과 bounded immutable stage cache |
| `development.py`, `data/development.json` | 개발 자료 |
| `audit.py` | 잘못된 key·stage·copy 값의 반례, immutable·용량·무결성 검사 |
| `study.py`, `run_study.py` | public/gold 분리, 비용·시간·회귀·동등성 검사 |
| `holdout_builder.py`, `data/holdout.json`, `HOLDOUT_AUTHOR.md` | 별도 작성 새 stream와 출처·경계 |
| `PROTOCOL.md`, `THEORY.md`, `freeze.json` | 평가 전 가설·계약·동결 |
| `results/` | 원본 집계, 압축 원시 행, timing, receipt |
| `reproduction_receipt.json`, `reproduction_timing.json`, `POSTFREEZE_REVIEW.md` | 별도 실행·재집계 |
| `POSTHOC_PROTOCOL.md`, `cost_boundary_probe.py`, `posthoc/` | 사후 분리 진단과 동결·결과 |
| `BOUNDARY_ANALYSIS.md`, `plot_boundary.py`, `figures/` | 사후 수학 해설과 결과 그림 |
| `README.md`, `HANDOFF_BACK.md` | 진입점과 이 반환 문서 |

### 명령과 실행 환경

핵심 실행에는 Python 표준 라이브러리만 필요하다. figure 재생성만 matplotlib
3.10.8을 사용했다. 루트에서 다음처럼 **아직 없는 새 출력 경로**를 지정한다.

```bash
python tools/verify_archive.py
python research/phase07/holdout_builder.py --check
python research/phase07/run_study.py --run \
  --output /tmp/soom-phase07-repro-new \
  --compare research/phase07/results
python research/phase07/cost_boundary_probe.py \
  --output /tmp/soom-phase07-boundary-new.json
```

보관된 freeze나 결과를 다시 만들거나 덮어쓰지 않는다. 개발 검사를 별도로 원하면
`run_study.py --dev --output NEW_DIRECTORY`를 사용한다. 최초 인수인계의
`python tools/reproduce.py --phase 05r2`는 Phase06에서 실행해 기존 결과와의 정확한
일치를 확인했다. 이번 Phase07에서 그 명령을 또 실행했다고 표현하지 않는다.
Phase07에서는 동결 archive 확인과 기존 자료 1,056질문의 cache 회귀 검사를 했다.

| 객체 | SHA-256 |
|---|---|
| `freeze.json` | `2c1df3467a8c9a4592c87c46d216df7c8216cc619361c009a7948479b99a58cf` |
| `cached.py` | `101553dd0ce11b3f114e804d96305829e19e6debf71aa3b674598bc548f8fe93` |
| `data/holdout.json` | `76a93ffa695c4abcc6d240382a40211d4d406b2c9d84352e5d2c9c181c0f9f98` |

나머지 hash와 실제 원본 실행 시각·환경은 [freeze.json](freeze.json),
[results/receipt.json](results/receipt.json)에 있다. 같은 환경에서 별도 담당자가
실행한 [reproduction_receipt.json](reproduction_receipt.json)은 5개 결정적 산출물의
바이트 동일성을 확인했다. time은 변동하므로 그 5개에 포함하지 않는다.

## 실제 결과

### 분모, 답변 범위와 오류

네 방법은 같은 300 step에 적용된다. 1,200 raw rows를 1,200개의 독립 대화로
해석하지 않는다. 반복 질의는 stream 안에서 상관돼 있고 family의 문법도 공유한다.

| 각 방법의 결과 | 건수 / 300 | 비율 |
|---|---:|---:|
| `certified_model` | 243 | 81% |
| `opaque_fallback` | 21 | 7% |
| `ambiguous` | 15 | 5% |
| `unsupported_query` | 9 | 3% |
| `integrity_failure` | 12 | 4% |

전체 이력 출력은 30/300으로 opaque 21건과 unsupported 9건이다. 무결성 실패는
빈 결과로 거절하며 전체 이력 fallback으로 세지 않는다. 전체 300질문 기준 단일값
답변 범위는 81%이고, 유효 snapshot 288건과 유효·지원 질문 279건을 별도로 보고한다.
`certified_model`은 제한된 모형 안의 판정이며 실제 사실성이나 일정 변경 실행 인증이 아니다.

gold 적용은 276건이다. 제외 24건은 무효 snapshot 12건과, 유효하지만 엔터티
membership이 달라져 gold 투영 규약을 정하지 않은 12건이다. 후자 12건은 모두
opaque fallback이며 기준 구현과의 동등성만 검사했다. 새 의미 정답을 발명하지 않았다.

- false certification: **0/243**.
- supported 질문 containment 위반: **0/267**.
- 선택 gold 사건의 projection 실패: **0/276**. 여기의 unsupported 9건은 전체
  이력 선택을 확인한 것이며 답변 성공이 아니다.
- 기준과 status/prediction/선택/렌더/trace의 동등성 실패: **0**.

### 비용과 실제 동작

| 같은 300 step의 합 | `fresh` | `disabled` | `reset` | `lru` |
|---|---:|---:|---:|---:|
| 실제 파서 실행 | 2,292 | 2,292 | 2,292 | **750** |
| 출력 UTF-8 bytes | 107,223 | 107,223 | 107,223 | 107,223 |
| 전체 P7 proxy | 2,093,235 | 4,298,967 | 4,847,263 | **4,341,013** |
| 전체 로컬 중앙값 ms | 20.157 | 45.014 | 49.177 | **27.126** |

P7의 사전 정의는 다음과 같다.

\[
P_7=output+hash+parser\_source+key\_build+key\_probe
+value\_encode+cache\_read\_payload+cache\_write.
\]

key probe는 원문·context의 논리적 전체 길이로 계상한다. Python dict가 실제로 그만큼의
메모리 버스 traffic을 발생시켰다는 측정이 아니다. immutable payload를 hit에서
다시 JSON decode하지 않지만 재사용 payload의 canonical 길이를 proxy에 포함한다.
CPU 연산량의 모든 항을 이 바이트 지표로 표현하지 못하므로 실제 시간도 별도로 측정했다.

`lru`의 cache overhead 구성은 key build 935,156, key probe 1,104,878,
value encode 52,956, payload read 112,742, write 185,538이다. 합은 **2,391,270**이다.
파서 입력 바이트는 932,814→789,322로 143,492 줄고, snapshot 검증 바이트
1,053,198과 출력은 같다. 따라서

\[
\Delta P_7=2{,}391{,}270-143{,}492=2{,}247{,}778
\quad(+107.38\%).
\]

실제 단계 실행은 cheap 1,848→648, scope 231→51, detail 213→51이다.
전체 감소는 67.28%지만 파서 입력 바이트 감소는 15.38%다. 재사용된 짧은 호출이
많았고, 가장 긴 quote는 cache 한도를 넘었다. 긴 입력 family의 모든 항목이
oversized였다고 표현하지 않는다. longest parameterization의 영향이 크며 이
인위적 길이 분포를 실제 대화의 분포로 가정하지 않는다.

228/300질문에서 실제 실행 감소가 있었다. P7은 0/300에서 감소, 21/300에서 동일,
279/300에서 증가했다. 동일한 21건은 unsupported 9건과 integrity failure 12건이다.
30 stream 모두 누적 P7 손익분기점에 도달하지 못했다. 최적화가 한 번도 작동하지
않은 결과가 아니라, **실제로 작동한 최적화의 전체 비용이 더 컸던 결과**다.

`lru`는 `reset`보다 P7을 10.44% 줄였다. 하지만 원래 `fresh`보다 107.38% 늘었으므로
더 비싼 비교군만 택해 전체 개선이라고 부르지 않는다. cache lookup 1,848회,
entry hit 1,200회, eviction 174회, oversized 10회였다. 논리적 보관 크기의 최대는
18,626 bytes, entries 최대는 64였다. 전체 Python RSS의 상한은 측정하지 않았다.

### 시간과 재현 변동

매 stream·반복마다 연구 cache를 비우고 방법 순서를 회전하여 7회 측정했다.
캐시 생성, snapshot 검증, 파싱, immutable 변환·encoding, LRU, 추론, 렌더를
포함한다. import·자료 로딩·offline gold·LLM 호출은 제외한다. CPU/OS 내부 cache까지
차갑게 만드는 실험은 아니다.

| 관측 | 원본 | 별도 재현 |
|---|---:|---:|
| 전체 `fresh` 중앙값 ms | 20.157 | 20.994 |
| 전체 `lru` 중앙값 ms | 27.126 | 31.427 |
| 전체 변화 | **+34.57%** | **+49.69%** |
| 반복 질문 family 변화 | −10.56% | +2.37% |

원본 시간은 [results/timing.json](results/timing.json), 재현 시간은
[reproduction_timing.json](reproduction_timing.json)에 따로 보존했다. 두 전체
관측 모두 느렸지만 효과 크기는 같지 않다. 통계적 유의성 검정과 플랫폼 일반화는
하지 않았다. 반복 질문 family의 안정적인 시간 이득은 입증하지 못했다.

### 기존 자료의 회귀 검사

| 자료 | 질문 | 파서 실행: fresh→lru | P7: fresh→lru |
|---|---:|---:|---:|
| Phase05 | 672 | 3,033→1,705 | 1,744,307→2,644,846 (+51.63%) |
| Phase06 | 384 | 1,828→488 | 596,175→969,863 (+62.68%) |

회귀에서도 동등성·적용 가능한 엄격 gold 검사 실패는 0이었다. 이 자료로 캐시를
평가했다고 새 독립 자료가 되지는 않는다. 원시 4,224행과 요약은
[results/regression_results.json](results/regression_results.json)에 연결돼 있다.

### 반례와 사후 비용 경계

개발 반례는 ID만 사용한 key의 과거 수정 누락, cheap/detail 슬롯 혼동, entity
환경 누락, 역사적 copy 값을 저장한 오류를 포함한다. 의미가 달라진 버전의 반례는
시험용 순수 함수다. 실제 namespace rotation 자료에서는 parser 의미를 변경하지 않았다.
immutable alias, entries/bytes 한도, oversize, invalid snapshot과 unsupported도 검사했다.

사후에는 동일 의미 noop의 cheap·deep 표면형을 써 비용식을 확인했다.
2기록·8반복, deep stage 3개, context C=101, set 원문 S=45, payload 합 R=232에서
두 항목이 모두 들어가면

\[
\Delta_8=26C+10S-4L+9R=5164-4L.
\]

원문 길이 L>1291에서 전체 8회 P7 이득이 가능하다. 하지만 L=65,057에서
P7 −12.23%, L=65,060에서는 항목 합이 한도를 넘어 상호 축출되어 +75.31%였다.
개별 quote도 못 들어가는 L=65,282에서는 +50.16%였다. 18 cell의 144질문 모두
수식 잔차와 동등성 실패 0이다. [BOUNDARY_ANALYSIS.md](BOUNDARY_ANALYSIS.md)에
초기·warm·축출·oversize 각각의 식과 가정을 제시했다.

이 조건부 이득은 의도적으로 만든 사후 영역이다. 주평가 +107.38%를 대체하지 않고,
실제 시간 이득도 주장하지 않는다. 단순 cache hit 수를 최대화하는 것과 전체 비용을
최소화하는 것이 다름을 보여주는 설명이다.

## 해석과 다음 차례

### 지지·기각·미확인

올바른 순수 함수 계약 아래의 보존 정리와 실제 재사용 동작은 지지된다. 동결한
주평가에서 전체 P7 및 전체 로컬 시간 개선 가설은 지지되지 않았다. 사후의 조건부
이득 영역은 증명·구성됐지만 실제 대화 분포에서 그 조건이 얼마나 자주 나타나는지는 모른다.

전체 이력 hash는 질의마다 남으므로 snapshot 길이를 B_q라 하면 합계
`Σ_q Θ(B_q)` 직렬화·hash 작업이 사라지지 않는다. 방문한 원문의 exact key 생성·hash·
동등성 확인 역시 길이에 의존한다. dict/LRU lookup의 구조 조작은 평균 상수 시간이어도
원문 인코딩이 상수 시간인 것은 아니다. 충분한 용량에서는 각 고유 stage key를
최초 한 번 계산하지만, 유한 LRU의 순환 workload에서는 반복해 계산할 수 있다.
원래 파서·상태 분석 복잡도와 출처 렌더링은 miss 및 공통 경로에 그대로 남는다.

사후 라벨 수정, 주평가의 긴 입력 제외, 유리한 비교군으로 주 비교 변경은 하지 않았다.
비용 경계 진단과 그림·이 보고서는 평가 후 추가한 것으로 명시한다.

### 실행하지 않은 항목

실제 LLM 토큰·요금·응답 품질, 실제 운영 대화, 외부 작성자의 블라인드 자연어 의미
평가, 실제 작업 실행 성공, concurrency, Python 물리 메모리/RSS, 실제 parser
배포 업그레이드, incremental snapshot 검증, 최종 답 캐시, 비용 인지 admission
정책은 실행하지 않았다. 사후 probe의 실행시간도 측정하지 않았다.

### 다음 Codex가 먼저 재현하거나 반박할 것

1. freeze를 검증하고 새 경로에서 주평가를 실행해 결정적 5개 파일의 바이트 동일성을
   확인한다. timing이 다르다는 이유로 더 좋은 실행을 골라 교체하지 않는다.
2. public 입력과 gold 경계, 24건 제외, 243/267/276의 서로 다른 오류 분모를 확인한다.
3. pure-stage 함수가 원문·entities·namespace 밖의 상태를 읽는지 반박한다. 숨은
   의존성이 있으면 현재 동등성 정리의 가정부터 수정해야 한다.
4. 2기록 진단의 cold/warm/eviction/oversize 비용식을 직접 계산하고 3 bytes 경계에서
   전체 P7이 바뀌는지 재현한다. 이 proxy를 실제 CPU 하한으로 해석하지 않는다.

### 다음 한 가지 연구 제안

**의미 선택기를 고정한 비용 인지 선택적 재사용 정책**을 연구한다. 목표는 cache hit
최대화가 아니라, stage 실행비·원문 key비·payload 크기·예상 반복·동시 보관 크기를
함께 보고 전체 비용이 유리할 때만 보관·재사용하는 것이다. 단계 수를 알기 위해
이미 해석해야 하는 비용과 gate 자체 비용도 포함한다. 이번 사후 probe를 설계에
쓰면 개발 자료로 명시하고 새 stream을 동결해 fresh·현재 LRU·새 정책을 비교한다.
실제 시간과 P7의 목적이 충돌하면 둘을 분리하여 판정해야 한다.

이 정책을 이번 단계에서 이미 구현하거나 개선됐다고 주장하지 않는다.
**운영 변경: 없음. 이번 단계는 학술 연구 전용이다.**
