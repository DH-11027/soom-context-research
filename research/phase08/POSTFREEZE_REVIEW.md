# Phase08 동결 후 별도 재현·원시 행 감사

작성: 2026-10-22 KST. 구현자와 다른 동일 모델 에이전트가 수행했다.
역할은 분리했지만 외부 독립 재현이나 실제 자연어 의미 검증으로 부르지 않는다.
동결 core·protocol·theory·자료·원본 결과는 수정하지 않았다.

## 1. 결론

**결정적 산출물 5개가 별도 실행에서 모두 바이트 단위로 일치했다.**
새 주평가 원시 **1,728행(432 step ×4방법)**과 역사적 회귀 **5,424행(1,356질문 ×4방법)**을
기존 summary 함수를 호출하지 않는 별도 코드로 재집계했고 저장값과 불일치를 발견하지 못했다.
모든 요약·비교·family·민감도·stream 누적 손익분기점이 일치했다.

고정한 합계 P8 주가설은 이 인위 합성 자료에서 지지된다. 그러나 **이득은 3/12 family의
합계와 8/36 stream에 집중됐고, 전체 로컬 실행시간은 원본과 재현 모두 증가했다.**
정책의 범용 이득이나 실제 LLM 비용 개선을 주장할 근거는 없다.

## 2. 실제 읽고 실행한 범위

동결 전 범위는 [EVALUATOR_REVIEW.md](EVALUATOR_REVIEW.md)에 있다. 동결 이후 다음을 읽었다.

- `data/holdout_manifest.json`, `HOLDOUT_AUTHOR.md`, `freeze_commit.json`.
- 주평가 및 회귀의 `results/*_results.json`, `results/*_rows.json.gz` 전 행.
- 원본 `results/timing.json`, 이번 `reproduction_timing.json`의 전체·family별 중앙값과 표본.
- 새 `data/holdout.json`을 state replay 코드의 입력으로 사용했다.

432개 질문의 모든 자연어 원문과 gold 대응을 외부 정답으로 재판정한 작업은 아니다.
builder의 전체 소스를 이번 단계에서 새로 문장별 검토했다고 주장하지 않는다.

실행 명령:

```bash
python research/phase08/run_study.py --run \
  --output /tmp/soom-phase08-independent-reproduction \
  --compare research/phase08/results
python research/phase08/recount_results.py \
  --output research/phase08/recount_results.json
```

두 명령 모두 이미 존재하는 output 경로를 거절한다. 후속 실행은 새 `/tmp/...`를 사용한다.
재집계 구현은 `evaluation.summary`, `evaluation.compare`, P7의 summary 함수를 import하거나
호출하지 않는다. 별도 ablation replay에서만 동결 `runtime`을 직접 호출하며 gold를 주지 않는다.

## 3. 동결·환경·재현 증거

- freeze commit: `4a128204cad4abbf374fea7326b6c844f800812f`.
- freeze SHA-256: `885ff9ecf25c4df38410ab39a16ae922195e1ee5b7eb9da0501853f926a7c11a`.
- Python 3.12.14 / CPython / Linux 6.18.55 x86_64 / glibc 2.39.
- 재현 시작: `2026-10-22T11:19:57.607303+00:00`(한국 20:19:57).
- 재현 종료: `2026-10-22T11:20:04.865176+00:00`(한국 20:20:04).
- 별도 실행 시간 약 7.26초, 실패 0, 종료 코드 0.

| 결정적 파일 | 원본과 비교 |
|---|---|
| `audit.json` | byte-identical |
| `holdout_results.json` | byte-identical |
| `holdout_rows.json.gz` | byte-identical |
| `regression_results.json` | byte-identical |
| `regression_rows.json.gz` | byte-identical |

시간 표본과 receipt의 시각은 이 동일성 비교 대상이 아니다. 새 증거는
[reproduction_receipt.json](reproduction_receipt.json),
[reproduction_timing.json](reproduction_timing.json),
[recount_results.py](recount_results.py), [recount_results.json](recount_results.json)에 있다.

## 4. 상태·gold 분모·보존

네 방법 모두 동일한 상태다. 1,728행을 1,728개 독립 대화로 해석하지 않는다.

| 각 방법의 상태 | 건수 /432 |
|---|---:|
| `certified_model` | 378 |
| `ambiguous` | 15 |
| `opaque_fallback` | 18 |
| `integrity_failure` | 12 |
| `unsupported_query` | 9 |

유효 snapshot은 420/432, 유효하고 지원하는 질문은 411/432이다.
전체 이력 반환은 27/432(opaque 18 + unsupported 9)이다. 무결성 거절은 전체 이력
반환에 넣지 않는다. 전체 기준 인증 범위는 378/432=87.5%이며 이 값은 제한 모형의
단일값 판정 비율이다. 실제 사실성 또는 작업 실행 성공의 인증이 아니다.

gold 적용도 411/432이지만 **유효·지원 411건과 같은 집합이 아니다.** gold 적용에는
unsupported 9건이 포함되고, 지원되지만 membership 의미 투영을 정의하지 않은 9건은
빠진다. gold 제외 21건은 membership 9건과 invalid snapshot 12건이다.

| 검사: 방법별 | 오류 /평가 분모 |
|---|---:|
| false certification | 0/378 |
| 지원 gold 질문 containment 위반 | 0/402 |
| 선택 gold 공동 투영 실패 | 0/411 |
| 구조 오류 | 0/432 |

411 projection 검사 중 unsupported 9건은 전체 이력 선택 확인이지 답변 성공이 아니다.
세 후보와 fresh의 관찰 비교는 **0/1,296** 불일치(432 step ×3 후보)였다.
baseline 자체를 포함한 1,728행 모두 저장된 parity failure가 없었다.

모든 행에서 단계 요청/호출/재사용 장부, key lookup=hit+miss, P7 합, control action 합,
P8 합, snapshot hash 호출·bytes의 기준 일치, 보관량 한도와 early-exit 무접근을 확인했다.
`hash_calls=424`는 유효 420건에 더해 hash까지 수행한 invalid 4건을 포함한다.
나머지 invalid 8건은 원래 순서·범위 검사에서 hash 전에 거절한다.

## 5. 전체 비용과 호출 재집계

| 432 step의 합계 | fresh | P7 LRU | selective | no_directory |
|---|---:|---:|---:|---:|
| 실제 파서 실행 | 4,768 | 2,014 | 4,171 | 4,171 |
| 파서 입력 bytes | 21,831,216 | 18,095,159 | 13,204,284 | 13,204,284 |
| snapshot bytes | 8,431,437 | 8,431,437 | 8,431,437 | 8,431,437 |
| 출력 bytes | 165,238 | 165,238 | 165,238 | 165,238 |
| cache overhead bytes | 0 | 20,625,232 | 7,269,311 | 9,199,861 |
| control actions | 0 | 27,306 | 6,741 | 6,785 |
| P7 | 30,427,891 | 47,317,066 | 29,070,270 | 31,000,820 |
| P8 | 30,427,891 | 47,535,514 | 29,124,198 | 31,055,100 |
| fresh 대비 P8 | — | +56.22% | **−4.28%** | +2.06% |

selective는 실제 실행 **12.52%**, 파서 입력 bytes **39.52%**를 줄였다.
P7은 4.46%, 고정 주지표 P8은 4.28% 감소했다. 계산은 다음과 같다.

\[
\begin{aligned}
\text{절약한 parser source}&=21{,}831{,}216-13{,}204{,}284=8{,}626{,}932,\\
\text{추가 cache+control}&=7{,}269{,}311+8\cdot6{,}741=7{,}323{,}239,\\
\Delta P8&=7{,}323{,}239-8{,}626{,}932=-1{,}303{,}693.
\end{aligned}
\]

P7 LRU가 더 많은 호출을 줄여도 전체 비용이 더 큰 것은 모순이 아니다.
호출 횟수, 입력 바이트, key/payload 작업은 다른 양이다. 실제 LLM 토큰·요금·품질의
개선으로 옮겨 해석하지 않는다. 출력과 전체 snapshot 검증은 그대로다.

selective의 admission attempts 119건은 writes 45와 capacity rejection 74로 나뉜다.
74건에는 개별 oversize 34건이 포함된다. eviction은 3, 최대 entries 12,
최대 논리 보관량 65,500 bytes다. Python RSS 상한은 측정하지 않았다.

`admission_reject_gain=0`이다. 따라서 주평가 자체에서는 음의 surplus 후보를 거절하는
수치 gate가 작동하는 사례가 없었다. selective-vs-LRU의 차이 전체를 그 임계값 하나의
인과효과로 주장할 수 없다.

## 6. 합계 이득의 분포와 cold 비용

| family | selective 대 fresh P8 |
|---|---:|
| entity_namespace_rotation | +0.89% |
| integrity_unsupported_recovery | +1.48% |
| long_cheap_repeated | +0.14% |
| long_deep_repeated | **−3.09%** |
| long_deep_single_use | **+11.98%** |
| phase_shift | **+3.87%** |
| revisions_copy_reorder | +2.15% |
| scope_and_ambiguity | +2.69% |
| short_churn | +1.02% |
| short_repeated | +1.33% |
| working_set_fit | **−16.22%** |
| working_set_pressure | **−10.68%** |

전체 12 family 중 합계가 좋아진 것은 3개다. 36 stream 중 최종 누적 이득은 **8개**,
손실은 **28개**, 동일은 0개다. 이득 stream의 합 −1,974,957과 손실 stream의 합
+671,264가 합쳐져 주결과 −1,303,693이 된다.

누적 P8가 한 번이라도 fresh보다 낮아진 stream은 10개지만, 끝까지 이득으로 마친
stream은 8개다. `phase_shift`의 2개 stream은 4번째 질문에서 일시적 손익분기점을
지났다가 끝에는 손해가 됐다. 일시적 break-even을 지속 이득으로 부르지 않는다.

100/432질문에서 실제 실행과 P8가 모두 감소했고, P8 동일은 21/432,
증가는 311/432였다. 동일 21건은 invalid 12와 unsupported 9의 기존 early exit다.

모든 stream의 첫 step 36개를 합치면 fresh P8 **2,568,437**, selective
**3,360,578**로 **+792,141(+30.84%)**다. cold 구축비를 warm 결과에서 빼지 않았다.
후속 반복 이득이 이 비용을 회수한 조건이 있었을 뿐, 최초 방문 자체가 저렴해진 것은 아니다.

이 자료는 긴 raw와 반복·working-set 조건을 의도적으로 배치한 인위 분포다.
byte 합계에서 긴 입력이 더 큰 비중을 차지한다. 8/36 stream의 이득이 전체 합계에서
28/36 stream의 손실을 넘었다고 대부분의 실제 대화가 개선된다고 결론낼 수 없다.

## 7. 길이 필터 ablation: 실제 resident 상태도 확인

`selective`와 `no_directory`는 실제 호출 4,171, stage별 재사용 각 199,
writes 45, eviction 3, capacity 거절 74로 같았다. raw 행의 aggregate가 같다는
관찰에 그치지 않고, 동결 runtime을 같은 36 stream에 다시 실행했다.

**432 step 각각이 끝날 때 다음 상태가 완전히 같았다.**

- resident exact keys와 insertion order.
- 순수 stage 값과 payload 길이.
- size, characters, surplus, hits, order 등 모든 entry metadata.
- length directory, retained/peak bytes, peak entries, next_order.

resident 상태 불일치 0/432이며 이 replay의 864개 결과·비시간 장부도 원본 행과 같았다.
이는 동결 구현의 replay이지 별도 구현된 cache나 외부 의미 검증이 아니다. timing은 측정하지 않았다.

길이 필터는 exact lookup 276→234로 **42회**를 피했다. key-build bytes
884,954와 key-probe bytes 1,045,596을 줄여 합계 1,930,550 bytes를 피했고,
control actions 44개 차이 352를 더하면 P8 차이는 **1,930,902**다.
따라서 no_directory 대비 P8 −6.22%는 이 자료에서 동일 재사용을 더 적은 논리
lookup 작업으로 수행한 효과와 연결된다. 호출 감소나 답변 범위 변화는 아니다.

## 8. 실제 시간은 다른 결론

| 전체 중앙값 ms | 원본 | 별도 재현 |
|---|---:|---:|
| fresh | 61.849 | 56.930 |
| P7 LRU | 84.566 | 76.754 |
| selective | 69.497 | 65.590 |
| no_directory | 68.202 | 63.903 |
| selective 대 fresh 변화 | **+12.37%** | **+15.21%** |

P8 합계는 개선됐지만 두 전체 시간 관측은 모두 느렸다. 게다가 길이 필터는
no_directory보다 P8가 낮아도 실제 중앙값은 원본·재현 모두 더 컸다.
**논리 key-work 절약을 실제 CPU 가속으로 옮길 수 없다는 직접 관측**이다.

`working_set_fit` family는 원본 −1.40%, 재현 −2.06%였으나, 이 두 로컬 관측만으로
통계적·플랫폼 일반화를 주장하지 않는다. `entity_namespace_rotation`은 원본
+10.58%에서 재현 −1.12%로 부호가 바뀌었다. 더 유리한 실행을 골라 보고하지 않는다.
7회 반복·중앙값 실험이며 유의성 검정·모집단 추정·변동 원인 분해는 하지 않았다.

## 9. 가중치 민감도와 역사 회귀

고정 λ=8 정책의 같은 실행을 재채점한 결과다. 각 가중치로 admission을 다시
설계하거나 정책을 재실행한 결과가 아니다.

| control action 가중치 | selective 대 fresh 합계 변화 |
|---|---:|
| 0 | −4.46% |
| **8, 주지표** | **−4.28%** |
| 32 | −3.75% |
| 128 | −1.63% |

이 사전 민감도 범위에서 합계 부호는 같지만, 모든 가중치에 대한 강건성이나
실제 CPU 환산율을 추정한 것이 아니다. 주지표를 더 유리한 값으로 바꾸지 않는다.

역사 자료 1,356질문(Phase07 300 + Phase06 384 + Phase05 672)에서는 관찰 오류 0이고,
파서 실행은 **7,153→7,153**, P8는 **4,433,717→4,474,349(+0.9164%)**였다.
새 호출 감소는 0/1,356, P8 감소도 0/1,356이다. 이 검사는 기존 자료의 회귀이며,
새 미열람 평가의 긍정 수치와 합쳐 평균내지 않는다.

## 10. 최종 해석과 남는 한계

주가설의 세 조건인 관측 보존, 실제 실행 감소, 전체 P8 감소는 이번 고정 합성 평가에서
함께 성립했다. 모든 입력에서 이득이라는 주장은 이미 개발 반례로 배제됐고,
이번 대부분의 stream 손해·single-use 손해·phase-shift 역전이 그 경계를 재확인한다.
실제 전체 시간 개선은 원본과 별도 재현 모두 관측하지 못했다.

실제 자연어 의미, 정정 일반화, 미완료 요청의 수명주기, 실제 실행 성공의 증거,
독립 reader의 충분성 검증, LLM 토큰·요금·응답 품질, concurrency, 물리 메모리,
운영 배포는 평가하지 않았다. 기존 제한 모형이 검증하지 않은 능력을 추가 보존한다고
주장하지 않는다. **SOOM 운영 변경 없음.**

이번 감사 이후 유리한 새 조건·새 benchmark를 추가하지 않았다. 재현과 원시 행 검토의
미해결 수치 불일치는 없어 이 연구 단계를 인수인계할 수 있다.
