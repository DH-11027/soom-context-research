# Phase07 동결 후 재현·평가 집계 감사

작성일: 2026-10-22. 검토자: 구현 담당자와 다른 동일 모델의 연구 에이전트.

## 1. 범위와 결론

동결된 구현을 같은 실행 환경의 별도 출력 경로에서 다시 실행했다.
**오류는 0건이며 결정적 산출물 5개가 원본과 바이트 단위로 일치했다.**
새 평가의 원시 1,200행을 직접 집계하여 저장된 분모·상태·비용 합계와 비교했고
불일치를 발견하지 못했다. 이 작업은 동일 환경에서의 별도 실행·집계 검토이며,
외부 기관의 독립 재현이나 실제 자연어 대화의 의미 정확성 인증이 아니다.

실제 파서 실행 감소는 발생했지만, 전체 P7 비용 proxy와 전체 로컬 실행시간은
증가했다. 원본과 재현 모두 이 방향을 보였다. 특정 반복 질문 family에서 원본에
있었던 시간 이득은 재현에서 부호가 바뀌었으므로 안정적인 성능 개선으로
해석하지 않는다.

동결된 코드·데이터·원본 결과를 수정하지 않았다. 재현 영수증과 시간 결과는
각각 새 파일 [reproduction_receipt.json](reproduction_receipt.json),
[reproduction_timing.json](reproduction_timing.json)에 보관했다. 이 문서 역시
동결 후 추가한 감사 기록이다. **원본 시간 결과를 재현 수치로 교체하지 않는다.**

## 2. 읽은 자료와 실행한 작업

개발 단계에서는 `baseline.py`, `cached.py`, `PROTOCOL.md`를 읽고
[audit.py](audit.py)의 개발용 반례·동등성 검사를 작성했다. 당시 새 holdout은
읽지 않았다. 동결 및 주 실행이 끝난 뒤 다음 자료를 검토했다.

- [run_study.py](run_study.py), [study.py](study.py), 최신 [cached.py](cached.py).
- [holdout_builder.py](holdout_builder.py), [HOLDOUT_AUTHOR.md](HOLDOUT_AUTHOR.md),
  [data/holdout.json](data/holdout.json)의 구조·분모·평가 제외 표기.
- [results/holdout_results.json](results/holdout_results.json),
  [results/holdout_rows.json.gz](results/holdout_rows.json.gz),
  [results/timing.json](results/timing.json).
- 별도 재현 출력의 영수증·시간 결과.

실행한 재현 명령은 다음과 같다.

```bash
PYTHONDONTWRITEBYTECODE=1 python research/phase07/run_study.py \
  --run \
  --output /tmp/soom-phase07-independent-reproduction \
  --compare research/phase07/results
```

재현 영수증 시각은 `2026-10-22T10:18:52.841698+00:00`이다. 환경은
Python 3.12.14, Linux 6.18.55 x86_64, glibc 2.39다. 검증한 `freeze.json`의
SHA-256은 다음과 같다.

```text
2c1df3467a8c9a4592c87c46d216df7c8216cc619361c009a7948479b99a58cf
```

동결 hash 검증을 포함한 실행이 통과했으며 아래 파일이 모두 byte-identical이었다.

| 파일 | 비교 결과 |
|---|---|
| `audit.json` | 동일 |
| `holdout_results.json` | 동일 |
| `holdout_rows.json.gz` | 동일 |
| `regression_results.json` | 동일 |
| `regression_rows.json.gz` | 동일 |

시간 결과는 비결정적 측정이므로 이 5개 동일성 판정의 대상이 아니다.
기존 Phase05·Phase06 자료로 실행한 결과는 회귀 검사이며 새로운 독립 평가로
세지 않는다. 후속 집계는 `study.summary()`를 호출하여 재사용하지 않고,
원시 행에서 직접 합산·비교했다. 이 감사 이후 추가 알고리즘 검사는 수행하지 않았다.

## 3. 분모와 답변 가능 범위

원시 행은 **300 step × 4방법 = 1,200행**이며, 각 방법에 30 stream이 있다.
stream 내부의 질문·이력이 반복되고 family별로 세 parameterization을 공유한다.
따라서 독립 대화 1,200개 또는 독립 대화 300개를 검증했다고 표현하지 않는다.
네 방법의 상태·선택·예측·출력은 같았다.

| 각 방법의 상태 | 건수 / 전체 300 | 비율 |
|---|---:|---:|
| `certified_model` | 243 | 81% |
| `opaque_fallback` | 21 | 7% |
| `ambiguous` | 15 | 5% |
| `unsupported_query` | 9 | 3% |
| `integrity_failure` | 12 | 4% |

유효 snapshot은 288건이며, 유효하고 지원하는 질문은 279건이다.
전체 이력을 실제 선택한 경우는 30건으로 opaque fallback 21건과 미지원 질문
9건에 대응한다. `certified_model`은 제한된 의미 모형 안의 단일값 판정이다.
실제 사실성이나 캘린더 변경 실행 성공을 인증하지 않는다.

### Gold 평가의 24건 제외

| 구분 | 건수 | 검증 범위 |
|---|---:|---|
| 유효하며 gold를 적용한 step | 276 | 가능한 경우 의미·선택 근거 검사 |
| entity membership 변경 | 12 | 기준 구현과 결과 동등성; 의미 정답 평가는 제외 |
| 무효 snapshot | 12 | 무결성 거절·캐시 접근 방지·결과 동등성 |

membership 변경 12건은 모두 유효 snapshot이며 `opaque_fallback`이다.
기존 gold를 새 entity universe의 정답으로 임의 해석하지 않은 것이다.
이 12건을 의미 정확성의 성공 사례에 포함해서는 안 된다.

gold를 적용한 276건에는 미지원 질문 9건도 들어 있다. 따라서 지원 질문의
containment 평가는 **267건**이며, 구체적인 오류 분모는 다음과 같다.

| 검사 | 관측 결과 |
|---|---:|
| certified 결과의 false certification | 0 / 243 |
| 지원 질문의 containment 위반 | 0 / 267 |
| 선택한 gold 사건의 projection 실패 | 0 / 276 |

마지막 행의 미지원 9건은 전체 이력을 선택했는지 검사한 것이며 답변 성공이 아니다.
이 검토는 모든 원문의 gold 의미를 외부 정답으로 다시 판정한 작업이 아니다.
gold는 동일 모델의 별도 작성자가 제한된 합성 문법에 맞춰 제공한 라벨이다.

## 4. 전체 원시 행의 비용 재집계

네 방법 각각에서 저장된 모든 summary 필드와 cost 합계를 원시 행으로
다시 계산했다. 또한 1,200행 각각에 대해 다음 관계를 확인했다.

\[
\text{stage requests}=\text{stage calls}+\text{stage reused}
\]

\[
\begin{aligned}
\text{cache overhead}={}&\text{key build}+\text{key probe}
  +\text{value encode}\\
  &+\text{cache read payload}+\text{cache write},\\
P_7={}&\text{output bytes}+\text{snapshot hash bytes}
  +\text{actual parser source bytes}+\text{cache overhead}.
\end{aligned}
\]

저장된 합계 및 행별 식과 일치했다. 이 관계는 사전에 정한 논리적 바이트 proxy의
장부 정합성이다. 실제 메모리 버스의 전송량·LLM 토큰·요금의 측정은 아니다.

| 항목 | `fresh` | `lru` |
|---|---:|---:|
| 실제 파서 실행 | 2,292 | 750 |
| 파서 입력 바이트 | 932,814 | 789,322 |
| snapshot 검증 바이트 | 1,053,198 | 1,053,198 |
| 출력 바이트 | 107,223 | 107,223 |
| 캐시 overhead proxy | 0 | 2,391,270 |
| 전체 P7 proxy | 2,093,235 | 4,341,013 |

실행 횟수 감소는 **67.28%**지만 파서 입력 바이트 감소는 **약 15.38%**다.
재사용한 짧은 호출의 개수와 긴 원문의 읽기 비용은 서로 다른 양이다.
실행 횟수의 감소율을 의미 해석 비용 전체의 절감률로 옮길 수 없다.

전체 proxy 변화는 다음과 같이 확인된다.

\[
\Delta P_7
=2{,}391{,}270-(932{,}814-789{,}322)
=2{,}247{,}778.
\]

즉 전체 P7 proxy는 **107.38% 증가**했다. 출력과 snapshot 검증 비용이 같은
상태에서 캐시 overhead가 절약한 파서 입력 바이트를 초과했다.

| 질문 단위 비교: `lru` 대 `fresh` | 건수 |
|---|---:|
| 실제 파서 실행 감소 | 228 / 300 |
| 전체 proxy 감소 | 0 / 300 |
| 전체 proxy 동일 | 21 / 300 |
| 전체 proxy 증가 | 279 / 300 |

동일한 21건은 미지원 질문 9건과 무효 snapshot 12건이다. 30개 stream 어느 것도
누적 proxy의 strict 또는 sustained break-even에 도달하지 않았다.
따라서 검사만 통과하고 최적화가 작동하지 않은 결과는 아니다. **재사용은 실제
작동했으며, 사전에 정한 전체 비용 proxy에서는 이득을 내지 못했다.**

긴 입력을 포함한 family와 인위적인 oversize 조건의 비중이 바이트 총합에
영향을 준다는 경계는 [HOLDOUT_AUTHOR.md](HOLDOUT_AUTHOR.md)에 기록되어 있다.
이 분포를 현실 대화의 길이 분포라고 가정하지 않는다. 결과를 본 뒤 해당 입력을
제외하거나 비중을 바꾸어 주 결과를 교체하지 않았다.

## 5. 실행시간의 재현 변동

원본은 [results/timing.json](results/timing.json), 재현은
[reproduction_timing.json](reproduction_timing.json)에 각각 보존한다.

| 측정 | 원본 | 별도 재현 |
|---|---:|---:|
| 전체 `fresh` 중앙값 | 20.157 ms | 20.994 ms |
| 전체 `lru` 중앙값 | 27.126 ms | 31.427 ms |
| 전체 중앙값 변화 | **+34.57%** | **+49.69%** |
| `same_history_query_rotation` 변화 | **−10.56%** | **+2.37%** |

전체 실행에서는 두 관측 모두 캐시판의 중앙값이 더 컸다. 다만 전체 증가율의
크기는 같지 않다. 반복 질문 family의 원본 감소율 −10.56%는 재현에서 +2.37%로
부호가 바뀌었다. 따라서 이 family에서 안정적인 속도 개선을 입증했다고
주장하지 않는다.

이는 7회 반복의 짧은 로컬 계측이며 통계적 유의성 검정이나 환경변동의 원인
분해를 수행하지 않았다. 예를 들어 전체 재현에서 `lru` 표본은
27.779–81.211 ms 범위였고 중앙값은 31.427 ms였다. 원본과 재현 사이의 차이를
특정 원인으로 확정하거나 더 유리한 실행만 고를 근거가 없다.

측정 범위는 캐시 생성·snapshot 검증·파싱·불변 값 변환과 길이 계산·LRU·추론·
근거 렌더링을 포함한 **계측판 로컬 경로**다. import, 자료 로딩, 오프라인 gold
평가와 LLM 호출은 포함하지 않는다. 매 stream·반복의 cold cache는 이 연구의
파서 캐시를 새로 만든다는 뜻이며, CPU·운영체제·Python 내부 캐시 전체가
차갑다는 뜻은 아니다.

## 6. 가설 판정과 표현의 경계

| 가설 | 이번 결과에서 허용되는 결론 |
|---|---|
| H7-S | 관측한 자료의 결과 동등성 및 적용 가능한 gold 검사 통과 |
| H7-P | 실제 파서 실행 감소 발생; 의도한 재사용 동작 지지 |
| H7-C | 사전에 정한 전체 proxy의 이득은 이번 자료에서 기각 |
| H7-T | 원본과 재현 모두 전체 로컬 중앙값의 시간 이득을 관측하지 못함 |

H7-S를 임의 자연어 입력에 대한 정확성 증명으로 해석하지 않는다. H7-P를
전체 비용 절약으로 해석하지 않는다. 시간 결과에 통계적 유의성을 추가로
부여하지 않는다. 실제 LLM 토큰·비용·답변 품질은 측정하지 않았다.

README는 이 감사의 최초 확인 시점에 아직 작성되지 않아 문장 단위 검토를
하지 못했다. 후속 설명에서는 “300건 모두 의미 검증”, “전체 비용 67% 절약”,
“반복 질문에서 안정적인 속도 개선”, “시간을 포함한 모든 수치의 동일 재현”처럼
분모나 측정 대상을 확대하는 표현을 피해야 한다.

이 감사 뒤 수행하는 추가 microprobe나 새 예시는 별도의 사후 분석이다.
그 결과를 동결 전의 미열람 holdout 성과에 합치지 않는다. 이 문서는 추가
알고리즘이나 holdout 조건 변경을 제안하거나 실행하지 않는다.
