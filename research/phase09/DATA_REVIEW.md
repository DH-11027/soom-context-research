# Phase09 동결 후 자료·분모·실제 시간의 분포 검토

작성: 2026-10-23 KST. 이 문서는 로컬 freeze
`b4a844efcaca73483f2c0d8b8339a1e352872745`와 원본·한 번의 별도 재현이 끝난 뒤
작성한 **사후 기술 분석**이다. 동결 코드·문서·자료·라벨·정책·결과를 변경하지 않았고
새 timing이나 selector 실행을 하지 않았다. 로컬 동결은 외부 사전 등록이 아니다.

검토자는 새 자료를 작성했던 동일 모델 에이전트다. 공개 문법·연구 설계를 공유했다.
자료 작성자가 자기 자료를 다시 검토하는 것이므로 외부 독립 자연어 의미 검증이 아니다.
다른 원격 Phase09/Phase10 연구 자료는 이 분석에 사용하지 않았다.

## 1. 직접 읽기와 재계산의 범위

동결 후 `data/holdout.json.gz`, `results/holdout_rows.json.gz`,
`results/holdout_results.json`, `results/timing.json`, `reproduction_timing.json`,
`PROTOCOL.md`를 읽었다. [`data_analysis.py`](data_analysis.py)는 실험의 summary
함수를 import하지 않고 입력·원시 행·timing block에서 아래 수치를 다시 계산한다.

- 2,488행의 유일성, 입력 라벨·gold 분모·지원 여부, status와 오류 분모.
- 실제 파서·검증 호출과 bytes, 출력 크기, **계측판에서만** P7/P8 장부 합계.
- 정확한 JSON 직렬화 동일성에 따른 원문·typed 배열 중복.
- 전체·cold·각 stream timing의 원시 ns/cycle로부터 중앙 시간과 paired ratio.

주 timing의 bootstrap 구간은 저장된 결과에서 읽었다. 이 스크립트는 bootstrap을
독립 재실행하지 않으며 중앙값과 비율을 직접 재계산한다. 정확성 실행의 정책 상태
직접 equality 검사는 별도 감사자의 담당이다. 이 문서는 원시 행의 오류 보고와
결정적 결과를 검토한 것이며 상태를 다른 cache 구현으로 다시 구성한 검증은 아니다.

## 2. 분모: 601과 601은 서로 다른 집합

새 자료는 **36 stream / 622 step**, 네 방법의 원시 행은 **2,488개**다. 이것이
2,488개 독립 대화 또는 622개 독립 프로그램이라는 뜻은 아니다.

| 검사 모집합 | 건수 |
|---|---:|
| 전체 step | 622 |
| 유효 snapshot | 610 |
| 유효하고 지원하는 질문 | 601 |
| Gold 적용 | 601 |
| Gold 적용·지원 질문 | 592 |
| Gold 적용 certified 결과 | 565 |
| Selected-gold projection 검사 | 601 |

Gold 601은 무효 snapshot 12와 membership 의미 투영 미정의 9를 제외한다.
유효·지원 601은 무효 12와 미지원 질문 9를 제외한다. 두 집합의 교집합은 592이고,
각각에만 들어 있는 항목은 9개씩이다. Gold 601에 포함된 미지원 9개는 전체 이력을
선택했는지 검사하며, 현재 상태의 답을 맞힌 성공 사례로 세면 안 된다.

| 각 방법의 판정 | 건수 |
|---|---:|
| `certified_model` | 565 |
| `ambiguous` | 21 |
| `opaque_fallback` | 15 |
| `integrity_failure` | 12 |
| `unsupported_query` | 9 |
| 실제 전체 이력 출력 | 24 |

네 방법 모두 false certification **0/565**, containment 위반 **0/592**,
selected-gold 공동 투영 실패 **0/601**이다. 전체 이력 출력 24는 opaque 15와
unsupported 9이며, 무결성 거절 12를 fallback에 합하지 않는다. 상태 판정은 제한된
typed 계획 모형의 판정으로 실제 사실성·실행 성공 인증을 뜻하지 않는다.

## 3. 표면형·프로그램의 중복과 입력 분포

동일성은 key를 정렬하고 배열 순서를 보존한 canonical JSON의 정확한 일치로 정의했다.
원문·숫자·entity 이름을 보존한다. Hash 충돌을 이용해 개수를 세지 않고 전체 문자열을
직접 비교했다.

| 동일성 정의 | 전체 622 | 유효 610 | Gold 601 |
|---|---:|---:|---:|
| `records` 전체: id·seq·text 포함 | 270 | 264 | 255 |
| records + 전달한 expected snapshot | 276 | 264 | 255 |
| ordered raw history: id·seq 제외 | 185 | 180 | 177 |
| ordered raw history + ordered entities | 191 | 186 | 180 |
| public + namespace 전체 | 349 | 337 | 328 |

Gold 601 step의 서로 다른 **exact typed-event 배열은 144개**이며, noop 사건을
제거한 배열은 141개다. 이는 직렬화 중복 제거 개수다. 모든 초기 상태에 대한 전이
동등성이나 query별 의미 동치류를 계산한 값이 아니며 144개 독립 표본도 아니다.
같은 문법·family·생성 절차·parameter를 공유한다.

예를 들어 `same_length_churn`에는 유효한 서로 다른 raw history가 27개지만 exact
typed 배열은 3개다. 긴 quote의 내용이 바뀌어도 typed 의미는 noop이다. 반면
`revisions_copy_reorder`는 48개의 raw history와 48개의 exact typed 배열을 갖는다.
이 차이를 숨긴 채 표면형 수를 독립 의미 과제 수로 바꾸어 말하지 않는다.

Horizon은 1 / 3 / 8 / 12 / 16 / 24 / 32 step을 포함한다. 고정 반복과 step별
churn, 같은 길이의 다른 원문, 기존·단발·새 working set으로 바뀌는 구간을 포함한다.
`deep_finite_horizons`에서는 길이와 horizon이 함께 바뀌므로 둘의 독립 효과를
추정하는 완전 요인설계가 아니다. 구체 사전 분포는 동결한
[`HOLDOUT_AUTHOR.md`](HOLDOUT_AUTHOR.md)와 manifest에 있다.

### 큰 원문의 비중

중복 방문을 포함한 원문 5,137개의 bytes 합은 **16,031,353**이다. 원문당 범위는
45–68,000 UTF-8 bytes, 19–51,982 Unicode codepoint다. `len(str)`의 codepoint 수를
화면상의 글자 묶음인 grapheme 수와 같다고 가정하지 않는다.

- 256 codepoint 이상 원문은 **846/5,137개**이며 원문 bytes의 **97.51%**다.
- 사후 설명용으로 4,096 UTF-8 bytes 이상을 구분하면 **678개**, bytes의 **95.40%**다.
- 긴 입력을 배치한 일곱 family는 **370/622 step**, 원문 bytes의 **96.68%**,
  fresh P8의 **96.97%**를 차지한다.

첫 두 항목은 해당 원문의 bytes에 직접 귀속한 합이다. 마지막 P8 비중은 해당
**family 전체 비용의 비중**이며 quote 문자열에 직접 귀속한 비용 비율이 아니다.
긴 원문은 모두 제한 문법의 noop quote로, 긴 자연어의 복잡한 의미 추론을 평가하지 않는다.

| Family | Step | 입력 원문 bytes 합 | Fresh P8 비중 | Selective P8 변화 |
|---|---:|---:|---:|---:|
| `cold_terminal` | 3 | 87,760 | 0.59% | +11.25% |
| `deep_finite_horizons` | 43 | 2,136,323 | 14.29% | -21.80% |
| `integrity_unsupported_recovery` | 48 | 139,493 | 0.61% | -7.39% |
| `long_cheap_repeated` | 72 | 1,927,512 | 6.53% | +0.15% |
| `phase_shift` | 72 | 2,616,760 | 17.12% | +20.08% |
| `revisions_copy_reorder` | 48 | 53,095 | 0.37% | +7.68% |
| `same_length_churn` | 36 | 719,484 | 4.82% | +34.05% |
| `scope_context_rotation` | 48 | 112,224 | 0.80% | +19.15% |
| `short_churn` | 36 | 119,886 | 0.64% | +0.87% |
| `short_repeated` | 72 | 107,232 | 0.60% | +1.28% |
| `working_set_fit` | 72 | 2,469,744 | 16.54% | -20.22% |
| `working_set_pressure` | 72 | 5,541,840 | 37.08% | -13.54% |

Working-set 입력은 2/3/4개 큰 quote를 사용한다. Fit의 원문 합은
14,000/34,000/54,000 bytes, pressure는 73,000/75,000/82,000 bytes다.
Context·payload·metadata를 포함하지 않는 입력 설계 크기이며 cache retained
bytes를 측정한 수치가 아니다. 전체 합만으로 실제 대화의 대표성을 주장하지 않는다.

## 4. 별도 정확성 실행에서 센 실제 호출과 작업점수

아래 호출은 **주 timing에 counter를 끼워 넣어 센 것이 아니다**. 별도의 비시간 감사
실행에서 monkeypatch로 관찰한 원시 행을 합한 것이다. On/off 각각의 실제 파서·검증
호출과 source bytes는 같은 방법 안에서 동일했다.

| 합계 | Fresh | Selective | 변화 |
|---|---:|---:|---:|
| 실제 cheap/scope/detail 호출 | 7,221 | 5,631 | -22.02% |
| 실제 파서 입력 bytes | 43,264,845 | 15,694,905 | -63.72% |
| Snapshot hash 호출 | 614 | 614 | 동일 |
| Snapshot hash 입력 bytes | 16,314,040 | 16,314,040 | 동일 |
| 출력 UTF-8 bytes | 282,813 | 282,813 | 동일 |
| P7: 계측판 장부 | 59,861,698 | 56,060,715 | -6.35% |
| Control actions: 계측판 장부 | 0 | 13,081 | — |
| P8: 계측판 장부 | 59,861,698 | 56,165,363 | -6.17% |

Invalid 12건 중 seq/head에서 일찍 거절되는 경우에는 hash까지 가지 않으므로
hash 호출 614를 유효 snapshot 610과 같다고 생각하면 안 된다. 거절 전 실제 hash를
수행한 invalid도 있다. 모든 방법의 같은 검증 경로가 유지됐다는 측정이다.

P8가 감소한 step은 291/622, 동일 21/622, 증가 310/622다. Stream 전체 P8 감소는
12/36이고 나머지 24개는 증가했다. P8는 동결한 가중 작업점수이며 실제 CPU 시간,
물리 RAM traffic, LLM 토큰·요금이 아니다. 이 수치는 사후 기술 통계이고 Phase09의
주 성능 지표를 대체하지 않는다.

Selective의 entry hit는 530, write 80, eviction 2, admission 시도 214,
capacity 거절 134, gain 거절 0이었다. 따라서 이 자료에서도 수치 surplus gate
하나의 독립 효과는 식별하지 못한다. 이 정책의 성능을 개별 gate의 공로로
분해하는 실험은 수행하지 않았다.

## 5. 주 실행시간: 개선 가설은 두 실행 모두 기각

주 비교는 **fresh_uninstrumented → selective_uninstrumented**다. 각 complete
block의 `T(selective_off)/T(fresh_off)`를 먼저 계산한 뒤 24개의 중앙값을 취한다.
아래 방법별 중앙값끼리 나눈 비율과 수치가 조금 다를 수 있으며 두 집계식을 혼용하지 않는다.

| 전체 workload 중앙 시간 | 원본 | 별도 재현 |
|---|---:|---:|
| fresh_instrumented | 138.316 ms | 137.396 ms |
| fresh_uninstrumented | 109.357 ms | 110.859 ms |
| selective_instrumented | 146.225 ms | 147.029 ms |
| selective_uninstrumented | 134.894 ms | 131.813 ms |
| **주 paired 변화** | **+23.59%** | **+15.80%** |
| 조건부 95% 구간: 변화로 표시 | +14.60% … +31.27% | +13.58% … +23.91% |
| Selective가 더 빠른 complete block | 0/24 | 0/24 |

사전 실질적 개선선은 비율 0.95다. 두 실행의 구간 하단은 0.95와 1.00을 모두
넘으므로 이 고정 자료·환경에서 5% 개선 가설은 기각된다. 전·후반 12 block도 같은
방향이다. 원본 +23.59%와 재현 +15.80%의 크기 차이는 남아 있으며 유리한 것만
선택하지 않는다. 24개 block은 독립 대화 표본이 아니다. Bootstrap은 complete
block의 교환가능성을 가정한 고정 corpus·timing session의 조건부 근사 구간이며
시간적 상관·공유 CPU 변동을 배제하지 않는다.

계측 제거 자체의 paired 변화는 fresh에서 원본 **-19.60%**, 재현 **-19.28%**이고,
selective에서는 **-7.42%**, **-9.15%**다. Selective의 원본 5% 개선 판정은
구간 상단이 0.95보다 커 미확인이며, 재현은 해당 기준을 충족한다. 주 off/off 비교는
둘 다 손해다. `T_on-T_off`를 counter 하나의 정확한 CPU 비용이라고 해석하지 않는다.
할당·GC·분기·cache locality와 코드 경로의 상호작용을 이 자료만으로 분해하지 못한다.

### Cold 구축비와 stream별 손익

모든 stream의 첫 step 36개만 모은 별도 보조 timing은 원본 **+47.04%**, 재현
**+44.02%**다. 각각 8회 paired block 모두 selective가 느렸다. 이 숫자는 36개
첫 step 전체의 묶음이며 질문 한 건의 latency가 아니다. 본 실험의 모든 stream은
처음부터 cold 구축비를 포함했다. Parser cache cold를 CPU/OS cache cold라고 부르지 않는다.

Stream별 별도 8회 측정에서는 원본 **2/36**, 재현 **1/36**만 중앙 비율이 1보다
작다. 원본에는 5% 이상 빠른 stream이 없고, 재현에는 1개가 있다. 이 보조 검사는
기술 통계이며 stream별 독립 성능 검정으로 발표하지 않는다.

아래 각 cell은 **원본 / 재현**의 off/off paired 변화다. 모든 stream을 남겨
유리한 working set만 따로 주평가로 만들지 않았다.

| Family | Parameter 0 | Parameter 1 | Parameter 2 |
|---|---:|---:|---:|
| `cold_terminal` | +56.65% / +47.58% | +54.72% / +37.31% | +49.10% / +28.20% |
| `deep_finite_horizons` | +55.67% / +19.73% | +18.97% / +11.41% | +15.77% / +18.70% |
| `integrity_unsupported_recovery` | +5.01% / +17.73% | +12.83% / +9.78% | +19.36% / +5.07% |
| `long_cheap_repeated` | +13.45% / +9.26% | +15.60% / +11.84% | +14.07% / +26.45% |
| `phase_shift` | +6.54% / +9.46% | +29.76% / +38.41% | +32.19% / +40.80% |
| `revisions_copy_reorder` | +3.09% / +11.56% | +17.36% / +7.78% | +18.00% / +20.35% |
| `same_length_churn` | +48.30% / +59.48% | +42.76% / +52.06% | +35.69% / +34.73% |
| `scope_context_rotation` | +18.62% / +23.75% | +28.00% / +30.17% | +26.87% / +29.52% |
| `short_churn` | +19.52% / +2.50% | +13.18% / +4.37% | +14.10% / +6.22% |
| `short_repeated` | +12.40% / +7.99% | +7.22% / +12.97% | +14.67% / +10.42% |
| `working_set_fit` | -1.66% / +4.13% | -3.75% / -9.50% | +10.62% / +8.94% |
| `working_set_pressure` | +21.58% / +16.42% | +17.37% / +18.32% | +28.68% / +22.20% |

`working_set_fit-00`은 -1.66%에서 +4.13%로 부호가 바뀌었다. 작은 로컬 개선을
안정적 속도 우월성으로 일반화하지 않아야 하는 직접적인 사례다.

별도로 잰 fresh stream 중앙값을 합하면 위 일곱 긴 입력 family의 비중은 원본
**80.44%**, 재현 **80.69%**다. 이는 독립적으로 잰 stream 시간의 기술적 합이며
주 whole-workload 시간의 정확한 원인별 분해나 대체 추정량이 아니다. P8 family
비중 96.97%와 실제 시간 비중이 같지 않다는 점도 proxy의 한계를 보여준다.

## 6. 재현 명령과 남는 주장 경계

```bash
python research/phase09/data_analysis.py --check
```

새 위치에 같은 결과를 쓰려면 `--output /tmp/phase09-data-analysis-new.json`을
사용한다. 기존 다른 bytes를 덮어쓰지 않는다. 이 명령은 자료와 저장 결과만 읽고
파서·정책·timing을 실행하지 않는다. 상세 재계산 결과는
[`data_analysis.json`](data_analysis.json)에 있다.

이 검토가 지지하는 결론은 **고정한 정책의 보수적 계측 제거 후에도 새 합성 자료의
전체 실행시간 개선이 관측되지 않았고, 두 사전 규칙의 실행에서 더 느렸다는 것**이다.
선택적 재사용 일반의 불가능성, 다른 구현·환경의 CPU 하한, 완전한 최소 실행 구현의
실패를 증명하지 않는다. 반대로 파서 호출·입력 bytes·P8 개선을 실제 CPU 가속으로
바꾸어 말할 수도 없다.

자유로운 자연어 의미 정확성, LLM 토큰·요금·답변 품질, 미완료 요청·실제 실행 증거의
일반적 보존, 외부 reader의 독립 검증, concurrency와 물리 RSS는 평가하지 않았다.
이번 부정 결과를 개선하기 위한 사후 정책 조정·새 성능 실험은 수행하지 않았다.
**SOOM 운영 변경 없음.**
