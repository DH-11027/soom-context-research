# Phase08 출발점: Phase07 비판적 재현과 계측 감사

작성: 2026-10-22(한국 시간). 주 구현자와 다른 동일 모델 연구 에이전트가 수행했다.
외부 독립 검증이 아니다. 직접 기준은 **`6da051c0132811184ecf39975d7ff647a1f47842`**다.
원래 Phase01–07 파일과 결과를 변경하지 않았으며 새 영수증만 이 단계에 보관했다.

## 1. 결론

**지정한 시작점은 재현됐다. Phase07의 기존 주평가 수치를 정정할 근거는 발견하지 못했다.**
결정적 결과 5개는 원본과 바이트 단위로 같았고, 비용 경계 진단 전체 JSON도 같았다.
별도 재집계 구현으로 원시 1,200행과 네 방법의 모든 저장된 요약 필드를 확인했다.
7,272개의 행·집계 assertion에서 불일치 0이었다. assertion 수는 독립 표본 수가 아니다.

이 결과는 기존 제한 문법의 해석이 실제 자연어에서 정확하다는 인증이 아니다.
사용한 주평가가 30 stream/300 step이며, 네 방법의 행을 합친 수가 1,200이라는 구분을 유지한다.

## 2. 실제로 읽고 실행한 범위

지정한 순서대로 `research/phase07/HANDOFF_BACK.md`, `PROTOCOL.md`, `THEORY.md`,
`POSTFREEZE_REVIEW.md`, `BOUNDARY_ANALYSIS.md`를 읽었다. 이어 다음을 검토했다.

- Phase07 `baseline.py`, `cached.py`, `study.py`, `audit.py`, `run_study.py` 전체.
- Phase07 `POSTHOC_PROTOCOL.md`, `cost_boundary_probe.py`, `freeze.json`,
  `reproduction_receipt.json`, 원본·이번 실행의 결과 요약 및 원시 행.
- Phase06 `scoped.py`, `evaluate.py`와 Phase05r2 `engine.py`의 구현 전체.
- 원본·재현의 `timing.json` 중 전체와 반복 질문 family의 7회 표본·중앙값.

실행한 명령은 아래와 같다. 기존 산출물 경로를 출력으로 지정하지 않았다.

```bash
python tools/verify_archive.py
python research/phase07/holdout_builder.py --check
python research/phase07/run_study.py --run \
  --output /tmp/soom-phase07-repro-for-phase08 \
  --compare research/phase07/results
python research/phase07/cost_boundary_probe.py \
  --output /tmp/soom-phase07-boundary-for-phase08.json
python research/phase08/inheritance/recount_phase07.py \
  --output research/phase08/inheritance/phase07_recount.json
```

마지막 명령도 출력이 이미 있으면 거절한다. 후속 재현에서는 새 `/tmp/...json`을 사용한다.
재집계 스크립트는 `phase07.study`나 선택기를 import하지 않는다.

Phase07 holdout builder는 `--check`로 실행했으며 모든 원문·gold를 사람이 개별 재판정하지 않았다.
Phase01–04, 모든 과거 연구 문서와 모든 실험은 다시 읽거나 실행하지 않았다.
Phase05 672질문과 Phase06 384질문은 이번 Phase07 실행기에 포함된 회귀 검사로 재실행됐다.
이 자료를 새 독립 평가로 세지 않는다. Phase08 새 holdout은 이 감사 작성까지 열지 않았다.

## 3. 재현 영수증과 환경

| 확인 | 결과 |
|---|---|
| 원래 archive | 59파일, 14,076,747 bytes, 동결 코드 결합 18개 통과 |
| Phase07 holdout builder | 30 streams/300 steps, 스키마·gold 확인 통과 |
| `audit.json` | 원본과 byte-identical |
| `holdout_results.json` | 원본과 byte-identical |
| `holdout_rows.json.gz` | 원본과 byte-identical |
| `regression_results.json` | 원본과 byte-identical |
| `regression_rows.json.gz` | 원본과 byte-identical |
| 사후 `posthoc/results.json` | 전체 파일 byte-identical, 18 cells/144 queries |
| 이번 전체 실행 실패 | 0, 실행기 종료 코드 0 |

실행 환경은 **Python 3.12.14 / Linux 6.18.55 x86_64 / glibc 2.39**다.
재현 영수증 시각은 `2026-10-22T11:03:16.876607+00:00`(한국 20:03:16)이다.
Phase07 freeze SHA-256은
`2c1df3467a8c9a4592c87c46d216df7c8216cc619361c009a7948479b99a58cf`다.

새 증거는 [inheritance/verification_summary.json](inheritance/verification_summary.json),
[phase07_reproduction_receipt.json](inheritance/phase07_reproduction_receipt.json),
[phase07_recount.json](inheritance/phase07_recount.json),
[phase07_boundary_reproduction.json](inheritance/phase07_boundary_reproduction.json)에 있다.

## 4. 원시 행에서 다시 확인한 주평가

| 합계: 300 step 각각 | fresh | lru |
|---|---:|---:|
| 실제 순수 파서 실행 | 2,292 | 750 |
| 실제 파서 입력 bytes | 932,814 | 789,322 |
| snapshot hash bytes | 1,053,198 | 1,053,198 |
| 출력 UTF-8 bytes | 107,223 | 107,223 |
| cache overhead proxy | 0 | 2,391,270 |
| P7 | 2,093,235 | 4,341,013 |

각 행에서 stage requests = calls + reused, 그리고 P7의 모든 정의된 항의 합이
저장값과 일치했다. 실제 실행 감소는 228/300, P7 감소/동일/증가는 0/21/279였다.
P7 증가는 107.382974%, 실제 파서 실행 감소는 67.277487%다.

네 방법 각각 상태는 `certified_model` 243, `opaque_fallback` 21,
`ambiguous` 15, `unsupported_query` 9, `integrity_failure` 12다.
전체 이력 반환은 30/300이다. gold 적용 276건에서 false certification **0/243**,
지원 질문 containment 위반 **0/267**, selected-gold joint projection 실패 **0/276**를
확인했다. gold 제외 24건은 invalid snapshot 12건과 entity membership 변경 12건이다.
마지막 projection 분모의 unsupported 9건은 전체 이력을 선택했는지 확인한 것이다.

`E6.assess`의 containment는 가능한 공동 답의 각 좌표가 예측 범위에 포함되는지 확인한다.
주변부 범위의 직곱이 실제 공동 답집합과 정확히 같다는 검사는 아니다.
별도 `selected_gold_projection_equal`는 선택된 gold 사건을 실행한 공동 투영과
전체 gold 사건의 공동 투영을 직접 비교한다. 선택기 내부 결과 보존과 원문·digest만
받은 별도 reader의 독립 의미 검증 가능성 역시 다른 주장이다.

## 5. 코드·설명·비용식의 일치와 남는 경계

### 의미 보존 경로

`cached.run`은 cache 접근 전에 Phase06의 `validate`를 호출한다. 순서 오류는
hash 이전에 거절하고, 순서가 맞으면 전체 canonical records를 직렬화·hash한다.
지원하지 않는 질문도 기존처럼 전체 이력을 반환하며 파서 cache를 예열하지 않는다.

정확한 UTF-8 원문과 ordered entities/fingerprint/namespace context를 pair key로
쓴다. stage별 슬롯에는 같은 frozen 순수 함수의 결과만 들어간다. immutable 변환,
현재 demand의 재계산, query-local TOP 생성, 현재 copy 실행, 현재 인덱스의 trace와
렌더를 확인했다. 명시된 단일 스레드·순수성·의미 버전 고정 가정 아래, 보존 증명의
귀납 구조와 구현이 어긋나는 곳은 찾지 못했다. 숨은 외부 의존성이 생기는 미래 파서에는
이 결론을 그대로 적용할 수 없다. namespace rotation은 실제 parser 의미 업그레이드가 아니다.

### P7 장부는 실제 CPU·메모리 작업의 완전 계측이 아니다

비용식 `(2−m)L+C+R`은 `get`에서 한 번의 exact-key 논리 probe를 부과하는
**정의된 P7 장부**와 일치한다. 다음 한계를 더 구체적으로 기록한다.

1. `ParseCache.get`은 방문마다 전체 key 길이를 한 번 `key_probe_bytes`에 더한다.
   `put`의 `key in entries`, `pop`, dict insertion과 hit의 `move_to_end`에 대해
   내부 hash/equality 비용을 바이트 항으로 각각 추가 계상하지는 않는다.
   쓰기는 key+payload의 논리 길이로 부과하고 CPU 관리 비용은 실제 시간에 들어간다.
   따라서 P7를 모든 내부 key 연산 또는 실제 RAM traffic의 총량으로 부를 수 없다.
2. 파서 입력 bytes는 요청된 단계마다 전체 원문 길이를 부과한다. 실제 정규식은
   접두사 불일치로 조기 종료할 수 있으므로 3단계면 CPU가 원문을 정확히 3회 끝까지
   읽었다는 뜻이 아니다. 짧은 파서 호출의 CPU 비용과 긴 입력 바이트 비용도 다르다.
3. `retained_bytes`는 key와 stage payload의 canonical 길이 합이다. dict/tuple/object
   header, stage 슬롯 이름, allocator, 일시적 객체를 포함한 RSS는 아니다.
4. timing도 `cached.run`의 계측판 경로다. fresh는 변경하지 않은 `P6.run`을 호출한 뒤
   공통 계측을 덧붙인다. 실제 SOOM 배포나 LLM 호출 성능을 측정하지 않는다.

이는 기존 수치를 다시 계산할 이유가 아니라 **그 수치를 해석할 수 있는 범위**다.
Phase08에서는 정책 판단·메타데이터·새 key 연산을 정의에 명시하고 별도로 계상해야 한다.

## 6. 이번 실행시간 — 원본은 보존

[phase07_reproduction_timing.json](inheritance/phase07_reproduction_timing.json)에 7회
표본을 그대로 보관했다. 시간은 결정적 5개 파일의 동일성 대상이 아니다.

| 전체 중앙값 | Phase07 원본 | Phase07 당시 재현 | 이번 Phase08 출발점 재현 |
|---|---:|---:|---:|
| fresh ms | 20.157 | 20.994 | 18.779 |
| lru ms | 27.126 | 31.427 | 25.758 |
| 변화 | +34.57% | +49.69% | +37.17% |

반복 질문 family는 이번 실행에서 1.562→1.341 ms(−14.12%)였다. 이전 실행은
−10.56%와 +2.37%로 부호가 바뀌었다. 세 관측 중 유리한 값을 골라 안정적인 이득으로
주장하지 않는다. 유의성 검정·플랫폼 일반화·변동 원인 분해는 하지 않았다.

## 7. Phase08으로 넘기는 판단

전체 snapshot 검증은 사라지지 않는다. 기존 캐시는 실제 파싱을 줄였지만 원래 fresh보다
비쌌고, 수학적 이득 영역은 길고 3단계를 거치며 충분히 반복되고 함께 보관되는 특정 조건이다.
따라서 admission을 결정하는 데 필요한 정보를 얻는 비용, 미래 반복을 알 수 없다는 경계,
정책 자체의 관리 비용을 포함하는 한 단계는 타당하다. 성공 판정은 원래 fresh와의 전체
비용 비교여야 하며, 어려운 자료를 제외하거나 비싼 ablation만 이겼다는 이유로 바꿀 수 없다.

외부 자연어 평가, 실제 LLM 토큰·요금·품질, 운영 적용, 병렬 cache, 물리 메모리 상한,
reader의 독립 의미 검증은 이번 출발점 감사에서 수행하지 않았다. **SOOM 운영 변경 없음.**
