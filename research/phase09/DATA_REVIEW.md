# Phase09 동결 후 자료·분모·원시 결과 검토

작성 역할: 새 자료 작성자와 같은 별도 동일 모델 에이전트.
이 문서는 동결과 첫 주평가가 끝난 뒤 작성했다. 동결 파일·원문·gold·정책·평가기·주지표는 수정하지 않았다.
추가 selector 실행이나 timing 실험은 하지 않았다. 두 timing 세션이 끝난 뒤 저장된 산출물만 재집계했다.

**결론:** 관찰·정책 상태 보존과 파서 호출 감소가 있어도, 이번 고정 새 자료에서 비계측 selective는
비계측 fresh보다 두 전체 timing 세션에서 각각 **17.93%, 16.78% 느렸다.** 긴 입력을 포함한 가족의
작업점수 비중과 실측 실행시간 비중은 다르며, stream별 작은 시간 차이는 세션 사이에 부호가 달라진다.

## 1. 실제 읽기와 재집계 범위

실제로 확인한 것은 작성 당시의 builder·공개 문법, 동결 후 `PROTOCOL.md`,
`results/audit.json`, `results/holdout_results.json`, `results/data_profile.json`,
`results/timing.json`, 재현 세션의 `timing.json`이다. 새 corpus, 1,728개 원시 결과 행,
432개 prefix의 정책 상태 witness는 프로그램으로 해제·검사했다.

모든 긴 원문을 사람이 한 줄씩 읽거나, 원문 의미를 외부에서 재판정한 검토가 아니다.
Gold 작성자가 같은 자료를 재검토했으므로 외부 독립 의미 감사라고 부르지 않는다.
기존 공개 문법과 연구 설계를 공유하는 같은 모델의 역할 분리라는 경계가 그대로 남는다.

[`data_review_recount.py`](data_review_recount.py)는 Python 표준 라이브러리만 import한다.
Runtime·평가기·주 집계 함수를 호출하지 않고 다음을 직접 재집계해
[`data_review_recount.json`](data_review_recount.json)에 보존했다.

- 원본 자료와 각 raw row의 유효성·지원 여부·gold 적용 여부, step/method 키 유일성.
- 방법별 상태·분모·출력·audit 실제 호출·입력 bytes 및 on 경로의 비용 항목 합계.
- 같은 step의 반환 관찰 및 on/off의 저장된 호출/정책 trace hash·장부 동등성.
- 432개 상태 witness의 보관량·항목 수·길이 directory 일관성 및 동등성 검사 표식.
- 자료의 명시적 직렬화 동일성 통계와 family 비용 합계.
- 두 timing의 40개 round 원시값에서 방법별 중앙값과 paired log-median 비율.
- 별도 stream/첫 step 진단의 8개 원시값에서 중앙값·가족별 합·손익 부호.

상태 파일에는 원래 실행에서 두 live 상태를 직접 비교한 결과와 **한쪽 상태 witness**가 저장되어 있다.
본 재집계가 한쪽 상태와 hash만으로 두 실행의 exact 상태/trace를 새로 재구성했다는 뜻은 아니다.
정확한 live 비교는 별도 감사 실행의 결과다. Bootstrap 구간은 본 데이터 검토에서 재생성하지 않았고,
저장된 구간을 읽었다. 별도의 전체 [`recount_results.py`](recount_results.py)가 그 재산출을 담당한다.

## 2. 같은 분모로 보이는 항목도 구별한다

36 stream ×12 step =432 step이고, 네 방법의 1,728행은 같은 입력을 반복 비교한 행이다.
독립 대화 1,728개가 아니다.

| 집합 | 개수 | 의미 |
|---|---:|---|
| 전체 step | 432 | 반복·수정·오류 입력을 포함 |
| 유효 snapshot | 420 | 무효 12 제외 |
| 유효·지원 질문 | 411 | 무효 12와 미지원 9 제외; membership 변경 6은 포함 |
| Gold 적용 | 414 | 무효 12와 membership 변경 6 제외; 미지원 9는 포함 |
| Gold 적용·지원 질문 | 405 | Containment 분모 |
| Gold 적용 certified | 372 | False certification 분모 |
| Selected-gold 투영 검사 | 414 | 미지원 9의 전체 이력 선택 검사 포함 |

**414는 답변 성공 수가 아니다.** 411과도 다른 집합이다. Membership 제외의 작성기 이유는
`entity_membership_undefined`, 결과 행 이유는 `undefined_membership_projection`이며 대상 6개가 일치한다.

네 방법의 판정은 모두 다음과 같다.

| 판정 | 개수 /432 |
|---|---:|
| `certified_model` | 372 |
| `ambiguous` | 24 |
| `opaque_fallback` | 15 |
| `integrity_failure` | 12 |
| `unsupported_query` | 9 |
| 실제 전체 이력 선택 | 24 |

전체 이력 선택은 opaque 15+unsupported 9다. Integrity failure는 거절이므로 fallback에 합하지 않는다.
방법별 false certification **0/372**, containment 위반 **0/405**, selected-gold 공동 투영 실패 **0/414**다.
세 후보와 fresh의 관찰 비교는 **0/1,296** 불일치이며, 두 on/off의 실행 trace 비교는 864회다.
정책 상태·정책 trace의 432개 prefix 검사에도 불일치가 없다.
372의 certified 판정은 기존 제한 모형의 단일값 판정이며 실제 자연어 사실성이나 도구 실행 성공 인증이 아니다.

## 3. 표면형·typed 배열의 중복과 길이 분포

동일성은 key를 정렬한 canonical JSON의 exact equality로 정의한다. 배열 순서·entity 이름·숫자는 보존한다.

| 동일성 정의 | 전체 432 step | 유효 420 step |
|---|---:|---:|
| Exact records (`id`, `seq`, `text`) | 324 | 315 |
| Ordered raw history (`id`, `seq` 제외) | 215 | 212 |
| Raw history + ordered entities | 215 | 212 |
| 전체 public + namespace | 378 | 366 |

Gold 적용 414 step의 exact typed-event 배열은 **135개**다. 이들은 의미 동치류나 통계적 독립 프로그램 수가 아니다.
같은 template·작성 규칙·길이 구간을 공유하며, typed noop 위치 변화는 배열을 바꾸어도 최종 상태를 바꾸지 않을 수 있다.
위 두 raw 관련 행의 숫자가 같은 것은 이번 구성의 우연한 성질이며 entity context가 불필요하다는 뜻이 아니다.

총 record occurrence는 **3,678**, 각 원문의 UTF-8 길이는 **45–70,026 bytes**, 문자 수는 **19–45,642**다.
현재 snapshot에 나타난 모든 원문 길이의 합은 **11,395,141 bytes**다. 반복 snapshot의 중복을 포함하며,
실제 regex 스캔량·고유 원문 크기·cache 보관량과 다르다.

긴 quote의 사전 구간은 900–1,900 /9,000–18,000 /57,000–74,000 bytes다.
Fit은 2/3/5개 후보 원문의 합계 14–58k, pressure는 2/3/5개 합계 77–116k로 구성했다.
원문 합계 외에 context·payload·80의 metadata가 실제 정책 보관 크기에 더해진다.
이번 관찰의 최대 논리 보관량은 **65,520**, 최대 entries는 **12**로 고정 한도를 지켰다.
물리 RAM 사용량을 측정한 값은 아니다.

모든 stream은 12 step으로 고정되어 종료 분포가 다양하지 않다. Long churn의 항목당 단일 사용과
phase shift 마지막 세 step의 신규 후보를 포함했어도, 실제 대화의 수명 분포를 대표한다고 할 수 없다.

## 4. 실제 호출 감소와 새 분포의 보조 비용 결과

다음 호출·byte 값은 **별도 정확성 감사 실행**에서 직접 수집했다.
비계측 주 timing 안에 카운터·monkeypatch를 다시 넣어 얻은 값이 아니다.

| 전체 합계 | Fresh on/off | Selective on/off |
|---|---:|---:|
| 실제 cheap+scope+detail 호출 | 4,905 | 4,152 |
| 파서 입력 bytes | 30,426,509 | 19,010,756 |
| Snapshot hash 호출 | 426 | 426 |
| Snapshot 직렬화 bytes | 11,452,505 | 11,452,505 |
| 근거 렌더 호출 | 420 | 420 |
| 출력 bytes | 544,794 | 544,794 |

파서 호출은 **15.35%**, 파서 입력 bytes는 **37.52%** 감소했다. Snapshot 순서/gap 검사에서 조기 거절한
입력은 hash 단계에 도달하지 않으므로 hash 호출 수와 유효 snapshot 수가 다르다. 원래 검증 순서는 유지된다.

보조로 읽은 **계측판 장부**에서는 P7가 **42,423,808→45,654,960(+7.62%)**,
P8가 **42,423,808→45,724,400(+7.78%)**다. 이는 새로운 자료 분포에서 고정 정책을 재평가한 결과다.
**Phase08의 다른 자료에서 P8 −4.28%였던 결과를 정정하거나 덮어쓰는 값이 아니다.**
비계측판에 P8 장부가 있다고 주장하지 않으며, Phase09 주지표를 보조 P8로 바꾸지도 않는다.

Selective의 실제 hit는 251개이고 각각 세 단계 재사용으로 753호출을 줄였다. Admission 시도184,
삽입70, capacity 거절114(개별 oversize36 포함), eviction1이다. Gain 거절은 이번에도0이므로
surplus 수치 gate 하나의 독립 효과를 입증했다는 주장은 할 수 없다.

## 5. 긴 원문 합계의 지배와 시간의 지배는 다르다

사후 설명용으로 `short_repeated`, `short_churn`, `scope_ambiguity`를 제외한 **긴 quote 포함9family**를
묶었다. 이들은 27stream/324step이며 fresh P7의 **99.0435%**를 차지한다.
이는 해당 가족 전체 비용 비중이지 quote 원문 자체에 직접 귀속한 비용 비율이 아니다.

그런데 별도 stream 진단에서 각 stream의 fresh_off 중앙값을 합했을 때 이9family의 비중은
원본 **84.9018%**, 재현 **84.2658%**다. 논리 bytes 비중을 실측 실행시간 비중으로 곧바로 읽을 수 없다.
또한 아래 시간은 별도로 측정한 stream 중앙값의 합이므로 주 timing의 정확한 부품별 덧셈 분해가 아니다.

| Family | Fresh P8 | Selective−fresh P8 | 별도 stream 시간 변화: 원본 | 재현 |
|---|---:|---:|---:|---:|
| `short_repeated` | 115,218 | +2,304 | +19.61% | +1.85% |
| `short_churn` | 219,545 | +3,264 | −2.77% | +8.98% |
| `long_cheap` | 1,917,714 | +3,168 | +12.38% | +16.92% |
| `long_deep_repeat` | 4,023,738 | −95,439 | +10.60% | +17.99% |
| `long_deep_churn` | 3,569,562 | +1,849,378 | +32.00% | +40.62% |
| `fit_working_set` | 5,179,695 | −861,587 | −7.93% | −5.60% |
| `pressure_working_set` | 13,788,507 | +947,232 | +20.79% | +16.35% |
| `phase_shift` | 3,919,563 | +107,526 | +24.23% | +20.54% |
| `same_length_misses` | 3,777,282 | +184,051 | +34.89% | +27.33% |
| `revisions_copy_context` | 3,722,497 | +1,299,581 | +18.44% | +30.95% |
| `scope_ambiguity` | 71,001 | +1,800 | +3.93% | +2.76% |
| `integrity_unsupported_recovery` | 2,119,486 | −140,686 | +8.19% | +8.36% |

여기서 시간 비율은 각 family에 속한 세 stream의 off 중앙값 합의 비율이다. 주 paired 비율과 추정량이 다르다.
큰 입력이 포함된 가족에서 손해가 관찰되지만, 이것이 원문 길이만의 인과효과라는 결론은 낼 수 없다.
반복·문법 단계·working-set·context 변경·cold 구축이 함께 달라진다. 예컨대 fit은 두 세션에서 이득이지만
pressure는 손해이고, long_deep_repeat는 P8가 감소해도 시간이 증가했다. 큰 원문이면 항상 이득이거나
항상 손해라는 단일 길이 법칙은 이번 결과로 성립하지 않는다.

## 6. 네 경로의 전체 시간: 중앙값과 paired 비율을 구별

| 전체 workload 중앙값, ms | 원본 | 별도 재현 |
|---|---:|---:|
| `fresh_instrumented` | 78.916 | 76.403 |
| `fresh_uninstrumented` | 67.128 | 65.550 |
| `selective_instrumented` | 88.124 | 85.798 |
| `selective_uninstrumented` | 79.719 | 78.313 |

주추정량은 round마다 같은 workload의 `log(T_candidate/T_reference)`를 구하고 중앙값을 지수화한 비율이다.
위 방법별 중앙값끼리 나눈 비율이 아니다.

| Paired 비교 | 원본 변화 | 재현 변화 |
|---|---:|---:|
| **Fresh off→selective off, 주 비교** | **+17.9341%** | **+16.7817%** |
| Fresh on→selective on | +13.1870% | +14.5640% |
| Fresh on→fresh off | −13.4777% | −12.6471% |
| Selective on→selective off | −9.6574% | −9.8528% |

주 비교의 ratio-of-marginal-medians는 원본 **1.187569**, 재현 **1.194708**이다.
이를 위 paired 비율1.179341/1.167817과 섞지 않는다.
양쪽 계측 제거는 각각의 기존 경로보다 빨랐지만 selective_off가 fresh_off를 이기지는 못했다.
한쪽만 계측을 제거한 혼합 비교를 주 성과로 삼으면 안 된다.

주 비교의 저장된95% cycle-bootstrap 구간은 원본 **[1.151942,1.213609]**,
재현 **[1.159105,1.191448]**다. 사전3% 실질차이 기준의 slowdown 쪽에 두 구간 전체가 놓인다.
Resampling 단위는 네 연속 round로 구성한10개 cycle이며, 질문이나 대화를 resampling한 구간이 아니다.
같은 고정 workload의 측정 세션을 대상으로 하고 cycle의 충분한 교환가능성을 가정한다.
임의 host drift·긴 자기상관·하드웨어 변경에 대한 보장은 없다.

모든40개 round와 제외한 warmup 원시값은 보존했다. 예컨대 원본 fresh_on 범위는68.935–196.921ms였고,
재현 fresh_off 범위는55.407–114.008ms였다. 잡음이 없었던 실험이 아니다.
온오프 시간 차이를 카운터·encoding·GC 중 한 부품의 정확한 CPU 비용으로 분해하지 않는다.

## 7. Stream별 손익과 cold 비용

별도8회 진단에서 whole-stream off 중앙값이 낮은 stream은 원본 **5/36**, 재현 **7/36**이었다.
두 세션 모두 낮은 것은 **3/36**이고, 여섯 stream에서 손익 부호가 바뀌었다.
두 세션에서 공통으로 낮은 stream은 `fit_working_set-01`, `fit_working_set-02`, `scope_ambiguity-01`이다.
이것은 per-stream 검정을 통과한 안정적 속도 개선이나 다중비교 보정 결과가 아니다.
특히 짧은 stream의 작은 차이를 일반화하면 안 된다.

| 별도 진단 중앙값의 합 | 원본 fresh→selective | 변화 | 재현 fresh→selective | 변화 |
|---|---:|---:|---:|---:|
| 36개 whole stream | 71.116→82.068ms | +15.40% | 65.389→76.229ms | +16.58% |
| 36개 첫 step, cold | 7.245→10.411ms | +43.69% | 7.031→9.391ms | +33.57% |

Cold 첫 step이 더 빠른 stream은 원본1/36, 재현2/36이었으며 공통 이득 stream은 없었다.
이는 parser cache가 비어 있는 시작의 진단이다. CPU·OS cache까지 cold로 만들지 않았다.
이 표의 합을 주 workload 시간에서 빼서 정확한 warm 비용을 계산할 수 없다. 서로 다른 실행이다.

## 8. 해석과 재현

H9의 속도 개선 기대는 이번 고정 환경·합성 workload에서 지지되지 않았고,
사전 규칙은 두 세션 모두 실질 slowdown으로 판정했다. 이는 모든 환경에서 느리다는 정리가 아니다.
보존 계약은 통과했다. 따라서 부정 성능 결과를 숨기기 위해 semantic 실패로 돌리거나,
유리한 가족만 새 주평가로 재정의할 이유가 없다.

자연어 의미 정확성, 자유로운 참조·정정, 미완료 요청, 실제 실행 성공과 근거의 일반 보존,
외부 reader 충분성, LLM token·요금·답변 품질, 물리 RAM, 동시성·운영 배포는 검증하지 않았다.
SOOM 운영 변경은 없다.

본 검토의 재집계는 다음과 같이 새 출력 경로로 실행한다.

```bash
python research/phase09/data_review_recount.py \
  --reproduction-timing research/phase09/reproduction_timing.json \
  --output /tmp/soom-phase09-data-review-recount-new.json
```

`data_review_recount.json`에는 읽은 corpus/원시 행/상태/profile/summary/두 timing의 SHA-256을 보존했다.
이 코드·문서는 동결 후 분석 추가이며, 사전 동결된 정책이나 주평가 설계로 소급하지 않는다.
