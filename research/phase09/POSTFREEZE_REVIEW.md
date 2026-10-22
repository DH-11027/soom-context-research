# Phase09 동결 후 별도 재현·원시 결과 감사

작성: 2026-10-22. 주 구현자와 역할을 분리한 동일 모델 에이전트.
같은 환경의 별도 프로세스 재현과 별도 집계 구현이다. 외부 독립 재현·외부 자연어
의미 검증·외부 사전 등록이라고 부르지 않는다. 동결한 core·정책·자료·gold·protocol은
수정하지 않았다.

## 1. 결론

**시간을 제외한 결정적 8개 파일이 전부 byte-identical이었다.** 새 평가 1,728행과
회귀 7,508행, 정책 state 432+1,877개를 원시 자료에서 다시 세었으며 저장값과 불일치가
없었다. 실제 시간의 주 비교는 두 실행 모두 selective_uninstrumented가 느렸다.

| 사전 고정 주추정량 | 원본 | 별도 재현 |
|---|---:|---:|
| Paired median ratio, selective_off / fresh_off | 1.179341 | 1.167817 |
| 변화 | **+17.9341%** | **+16.7817%** |
| 측정 cycle bootstrap 95% 비율 구간 | [1.151942, 1.213609] | [1.159105, 1.191448] |
| 로컬 3% 규칙 판정 | 실질 slowdown 관측 | 실질 slowdown 관측 |

계측 제거의 관찰·정책 상태 계약은 이 검사에서 통과했지만, H9의 실제 가속 조건은
두 실행 모두 만족하지 않았다. 이는 동등성을 깨뜨려 얻은 실패가 아니라 **동등한
정책을 유지한 상태에서 실제 전체 시간이 증가한 부정 성능 결과**다. 모든 환경과
모든 workload에서 selective가 반드시 느리다는 정리로 확대하지 않는다.

## 2. 실제 읽고 실행한 범위

동결 전 source 검토·개발 검사는 [EVALUATOR_REVIEW.md](EVALUATOR_REVIEW.md)에 있다.
동결 후 이 역할은 다음 자료를 실제로 읽거나 프로그램으로 검사했다.

- `results/holdout_results.json`, `results/regression_results.json`의 전체 요약.
- `holdout_rows.json.gz`, `regression_rows.json.gz`의 모든 원시 행.
- `holdout_states.json.gz`, `regression_states.json.gz`의 모든 정책 상태.
- 원본 `results/timing.json`과 별도 `reproduction_timing.json`의 전체 40-round
  표본·warmup·순서·bootstrap·각 stream 8회 전체/첫 step 진단.
- `results/receipt.json`, `reproduction_receipt.json`, 동결 hash.
- 실행기의 입력으로 새 holdout gzip을 읽었다. 모든 자연어 원문과 typed gold의
  대응을 외부 정답으로 재판정하지는 않았다.

실제 실행한 재현 명령은 다음과 같다.

```bash
python research/phase09/run_study.py --run \
  --session reproduction \
  --output /tmp/soom-phase09-reproduction \
  --compare research/phase09/results
python research/phase09/recount_results.py \
  --results research/phase09/results \
  --reproduction /tmp/soom-phase09-reproduction \
  --output research/phase09/recount_results.json
```

두 명령 모두 종료 코드 0이다. 기존 경로를 덮어쓰지 않았으며 후속 재현은 새 output
이름을 사용해야 한다. 본 workload timing은 원본 한 세션과 별도 재현 한 세션만
실행했고, 더 유리한 숫자를 얻으려 다시 실행하지 않았다.

## 3. 동결·환경·재현 증거

- 직접 기준: `efba3224dd09d5c5e2bf9d9be11734fa10b32502`.
- Phase09 로컬 freeze commit: `387b451a19d0c17abc22365b82daeb357b0d3ab3`.
- Freeze manifest SHA-256: `776b11146a962fff666ddbacbba6b07e2766d0789816de490ea441d911594fbc`.
- Python 3.12.14 / CPython / Linux 6.18.55 x86_64 / glibc 2.39.
- 보고된 CPU: AMD EPYC 9V74 80-Core Processor. 프로세스 affinity는 허용 목록
  0–8의 첫 CPU 0으로 고정됐고 오류는 없었다. 이 이름은 실행 호스트가 보고한 값이다.
- `PYTHONHASHSEED=0`, 정상 GC 활성화, threshold `[700,10,10]`.
- 별도 재현 전체 시작: `2026-10-22T12:11:28.406209+00:00`(한국 21:11:28).
- 별도 재현 완료: `2026-10-22T12:12:27.378031+00:00`(한국 21:12:27).
- 이 중 본 측정의 첫 round 시작은 12:11:40 UTC이며, warmup·감사·import 시각과 구분한다.

| 결정적 파일 | 원본과 비교 |
|---|---|
| `audit.json` | byte-identical |
| `holdout_results.json` | byte-identical |
| `holdout_rows.json.gz` | byte-identical |
| `holdout_states.json.gz` | byte-identical |
| `regression_results.json` | byte-identical |
| `regression_rows.json.gz` | byte-identical |
| `regression_states.json.gz` | byte-identical |
| `data_profile.json` | byte-identical |

시간·시각 receipt는 동일성 비교 대상이 아니다. 별도 증거는
[reproduction_receipt.json](reproduction_receipt.json),
[reproduction_timing.json](reproduction_timing.json),
[recount_results.py](recount_results.py), [recount_results.json](recount_results.json)에 있다.
GitHub 공개 commit과 위 로컬 freeze commit은 별개의 식별자다.

## 4. 새 평가의 보존·gold 분모

36 stream / 432 step에서 네 방법의 상태가 모두 같았다. 1,728행은 네 방법의
반복 실행 결과이며 1,728개 독립 대화가 아니다.

| 각 방법의 판정 | 건수 /432 |
|---|---:|
| `certified_model` | 372 |
| `ambiguous` | 24 |
| `opaque_fallback` | 15 |
| `integrity_failure` | 12 |
| `unsupported_query` | 9 |
| 실제 전체 이력 반환 | 24 |

전체 이력 반환 24는 opaque 15+unsupported 9다. 무결성 실패는 거절이며 여기에
합하지 않는다. Certified는 제한 모형의 단일값 판정으로 실제 사실성·실행 성공의 인증이 아니다.

| 검사 | 오류 /적용 분모 |
|---|---:|
| False certification | 0/372 |
| 지원 gold 질문의 containment 위반 | 0/405 |
| Selected-gold 공동 투영 실패 | 0/414 |
| Fresh 계측 기준과 나머지 3방법의 Obs 불일치 | 0/1,296 |
| 각 방법 on/off 실제 실행 trace 불일치 | 0/864 |
| Selective on/off prefix 정책 상태 불일치 | 0/432 |
| Selective on/off 정책 결정 trace 불일치 | 0/432 |

유효 snapshot은 420, 유효·지원 질문은 411이다. **Gold 적용은 414**로 다른 집합이다.
Gold 제외는 invalid 12와 의미 투영을 정의하지 않은 membership 변경 6이다.
414에는 unsupported 9의 전체 이력 선택 검사가 포함돼 있으므로 답변 성공 414건이 아니다.
Containment는 주변부 포함 검사이고 selected-gold 검사는 공동 투영 보존이다.
외부 reader의 독립 충분성 검증은 이들 검사와 다르며 수행하지 않았다.

## 5. 실제 실행 계수는 별도 감사에서 얻었다

| 432 step의 합계 | fresh_off | selective_off |
|---|---:|---:|
| 실제 cheap 호출 | 3,162 | 2,911 |
| 실제 scope 호출 | 885 | 634 |
| 실제 detail 호출 | 858 | 607 |
| 실제 파서 호출 합 | **4,905** | **4,152** |
| 파서 입력 UTF-8 bytes | 30,426,509 | 19,010,756 |
| Snapshot 검증 bytes | 11,452,505 | 11,452,505 |
| Snapshot hash 호출 | 426 | 426 |
| Render 호출 | 420 | 420 |
| 출력 UTF-8 bytes | 544,794 | 544,794 |

실제 호출은 **15.3517%**, 입력 bytes는 **37.5191%** 줄었지만 주 시간은 증가했다.
426 hash 호출은 유효 420에 hash 단계까지 도달한 invalid 6을 더한 수다.
나머지 invalid는 순서 검사에서 hash 전에 거절된다.

Selective의 실제 admission 요청은 184, 삽입 70, 축출 1이며 entry hit는 251이다.
Capacity 거절 114에는 개별 oversize 36이 포함된다. Gain 거절은 0이다.
Step 종료와 계측 peak의 최대 논리 보관량은 65,520, 최대 항목 수는 12로 같았다.
물리 RSS를 측정하거나 상계한 숫자는 아니다.

이 표의 호출 계수는 **별도 wrapper가 붙은 correctness 감사 실행**에서 직접 측정했다.
주 timing의 비계측 경로에 counter/event를 다시 넣지 않았다. 계측판의 실제 장부와도
일치했다. Off 결과에 가상의 P7/P8를 채우지 않는다.

이번 새 자료에서 계측 경로의 P8는 fresh **42,423,808**, selective **45,724,400**으로
**+7.78%** 증가했다. 입력 분포가 달라졌으므로 Phase08의 합계 P8 이득을 이번 자료에서도
재현했다고 주장할 수 없으며, Phase08 자료에서 측정한 개선과 직접 합쳐서도 안 된다. 이 점수는
보조 계측 수치이고 Phase09 주지표인 실제 시간 판정을 대체하지 않는다.

## 6. 네 시간 경로와 계측 제거 효과

다음 표는 방법별 전체 workload 시간의 중앙값이다. 각 sample은 전체 workload를
3회 처리한 외부 구간의 시간을 3으로 나눈 값이며 질문 한 건 latency가 아니다.

| 방법 | 원본 중앙값 ms | 별도 재현 중앙값 ms |
|---|---:|---:|
| fresh_instrumented | 78.916 | 76.403 |
| fresh_uninstrumented | 67.128 | 65.550 |
| selective_instrumented | 88.124 | 85.798 |
| selective_uninstrumented | 79.719 | 78.313 |

| Paired median 변화 | 원본 | 별도 재현 |
|---|---:|---:|
| selective_off / fresh_off, **주 비교** | **+17.93%** | **+16.78%** |
| selective_on / fresh_on | +13.19% | +14.56% |
| fresh_off / fresh_on | −13.48% | −12.65% |
| selective_off / selective_on | −9.66% | −9.85% |

계측 제거는 양쪽을 모두 빠르게 만들었지만 selective가 fresh를 이기게 하지는 않았다.
두 번째·세 번째·네 번째 비교는 보조 결과다. 각 비율의 중앙값을 계산한 것이므로
이 숫자들을 곱하거나 빼서 부품별 CPU 비용을 정확하게 복원할 수 없다.
할당·GC·cache locality·분기 등 상호작용은 분해하지 않았다.

주추정량은 `exp(median(log(Ts/Tf)))`다. 위 방법별 중앙값을 나눈 비율과 다르다.
방법별 중앙값의 단순 비율은 원본 **1.187569**, 재현 **1.194708**이고,
주추정량은 **1.179341 / 1.167817**이다. 더 유리한 추정량으로 사후 바꾸지 않았다.

### 변동과 불확실성

원본 fresh_on의 최소/최대는 68.935/196.921 ms, fresh_off는 58.072/88.665 ms다.
재현 fresh_off는 55.407/114.008 ms다. 모든 표본을 보존했고 느린 이상값을 지우지 않았다.
전체 IQR·최소·최대·40회 원시값과 warmup은 두 timing 파일에서 확인할 수 있다.

Bootstrap은 연속 4-round의 순서 균형 cycle 10개를 단위로 한 20,000회 재표집이다.
이는 같은 고정 workload의 반복 측정에 대한 조건부 구간이다. 질문·stream을 독립
대화 표본으로 재표집하지 않았다. Cycle 간 충분한 교환가능성이 가정이며 장기 host drift나
플랫폼 일반화를 보장하지 않는다. 두 세션 모두 구간 하한이 1.03보다 컸다는 사실을
**고정 환경·이 합성 자료에서의 실질 slowdown 관측**으로 표현한다.

## 7. Stream과 최초 구축비 진단은 다른 실행이다

각 stream 전체와 첫 step을 별도 8회 측정한 기술 통계에서 selective_off의 시간이
낮은 stream은 원본 **5/36**, 재현 **7/36**이었다. 그 외는 각각 31/36, 29/36에서 높았다.
이 값은 stream별 8회 중앙값의 부호이며 유의성 검정 결과가 아니다.

최초 step 중앙값들의 합은 다음과 같다.

| 별도 cold 진단 | 원본 | 별도 재현 |
|---|---:|---:|
| fresh_off 합, ms | 7.245 | 7.031 |
| selective_off 합, ms | 10.411 | 9.391 |
| 변화 | +43.69% | +33.57% |

이 합은 주 workload 시간의 정확한 덧셈 분해가 아니다. 주 timing에는 stream별
타이머를 넣지 않았고 두 진단은 별도 실행됐다. Cold 구축비를 주비교에서 제외하지 않았다.

Family별 stream 중앙값 합의 비율에서 `fit_working_set`은 원본 −7.93%, 재현 −5.60%였다.
`short_churn`은 원본 −2.77%에서 재현 +8.98%로 부호가 바뀌었다. 부호가 유리한
family나 실행만 골라 주결과로 삼지 않는다. 큰 원문·중복·작업집합의 분포는
별도 자료 작성자의 `DATA_REVIEW.md`와 `results/data_profile.json`에서 확인한다.

## 8. 재집계 방법과 범위

`recount_results.py`는 evaluator/runtime/benchmark/summary 함수를 import하지 않는다.
원시 행에서 분모·상태·답·호출·byte 장부·event 합을 직접 다시 계산한다. State에서는
exact key bytes를 복원하고 stage 값·길이·size/surplus·hit·directory·용량을 검사한다.
Invalid/unsupported 뒤의 정책 상태가 바뀌지 않는지도 확인한다.

원본 timing 집계의 `log(Ts/Tf)`와 독립 구현의 `log(Ts)-log(Tf)`는 마지막 부동소수점
자리에서 약 10^-16 수준의 차이가 날 수 있다. 비율·구간은 재집계 구현의 고정 비교 tolerance
`rel_tol=1e-12, abs_tol=1e-14` 안에서 같고 판정은 정확히 같았다.
Raw artifact의 byte-identical 비교와 부동소수점 재계산의 허용오차 비교는 구분한다.

회귀 1,877 prefix는 Phase08 개발 89+이전 holdout 432+Phase05/06/07 1,356이다.
총 7,508행의 Obs 비교 5,631, on/off 실행 trace 비교 3,754, π 비교 1,877에서
불일치 0이다. 이 자료는 이미 알려진 개발·회귀이며 새 성능 평가와 합치지 않는다.

## 9. 남는 해석 한계와 종료

조건부 보존 정리와 이 입력들의 실제 검사, 계측 제거의 구현 동등성, 이 고정 환경의
실제 시간 차이는 각각 다른 주장이다. 이번 두 시간 관측은 “계측만 지우면 selective가
fresh보다 빨라진다”는 기대를 지지하지 않았다. CPU 부품별 원인은 profiling하거나
독립 요인 실험으로 분해하지 않았으므로 특정 counter/regex/encoding/GC를 원인으로
단정하지 않는다.

자연어 의미 정확성, 임의 정정·미완료 요청·실행 증거 일반 보존, LLM 토큰·요금·품질,
외부 reader 충분성, 물리 RSS, 다른 하드웨어·interpreter, 동시성은 검증하지 않았다.
수치가 부정이라는 이유로 정책·threshold·자료를 바꾸거나 실험을 더 늘리지 않는다.
**이 재현·재집계 단계는 완료했고 SOOM 운영 변경은 없다.**
