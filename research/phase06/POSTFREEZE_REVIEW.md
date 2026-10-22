# Phase 06 동결 후 독립 검토: 라벨, 집계, 비용 해석

검토일: 2026-10-22  
기존 연구 기준: `780891f6c147cfd3c1a3b0d065792776aaa525f3`  
Phase 06 사전 동결 커밋: `0da78eacc774556879fffd5429ba3333c9f05bb8`  
`freeze.json` 시각: `2026-10-22T09:35:43.730612+00:00`

## 1. 검토의 성격과 결론

이 문서는 선택기 구현 및 holdout 작성과 다른 에이전트가 수행한 **동결 후 검토**다. 검토자는 동결 전에는 holdout 작성기·원자료·작성자 문서를 읽지 않았으며 development 평가기 감사만 수행했다. 동결 및 최초 평가가 끝난 뒤 원자료와 결과를 함께 읽었으므로, 이번 라벨 감사는 결과를 모르는 블라인드 검증이 아니다. 같은 모델의 별도 검토이며 외부 전문가 판정으로 부르지 않는다.

확인한 결론은 다음과 같다.

- 읽은 한국어 템플릿과 대표 원문/gold 대응에서 **명백한 라벨 오류를 찾지 못했다.**
- family별 의미에서 직접 작성한 최종 상태 산식과 gold 전이 실행을 96이력에 대조하여 **96/96 joint 상태가 일치**했다. 이는 제한된 템플릿의 확인이며 일반 자연어 해석의 증명이 아니다.
- 원시 결과 2,304행을 재집계한 상태 수·오류 수·출력 바이트·모든 비용합이 저장된 요약과 일치했다.
- controlled의 답변 범위 및 출력 축소는 실제로 발생했다. challenge에서는 scope 최적화 발동 및 추가 축소가 0이었다.
- 두 split 모두 새 text-only 방법의 equal-byte-work proxy가 증가했다. 따라서 **정해진 표현에서의 범위 국소화 효과는 관측되었지만, 전체 작업량 이득 가설은 이 실험에서 지지되지 않았다.**

원자료, 동결 코드, 라벨, 결과를 수정하지 않았다. 이 검토에서 새로 작성한 저장소 파일은 이 문서뿐이다.

## 2. 사전 검토 지적의 최신 상태

사전 검토의 오래된 지적을 현재 결함으로 반복하지 않기 위해 동결 소스를 다시 확인했다.

| 사전 지적 | 동결 소스에서 확인한 상태 |
|---|---|
| 비용 bookkeeping과 검증을 위해 전체 JSON을 두 번 직렬화 | 해결됨. `new_cost()`는 카운터만 초기화하고, `counted_digest()`가 실제 validation의 JSON 직렬화·SHA 1회에서 바이트 수를 얻는다. frozen도 `BASE.history_digest`를 동일 의미의 계측 함수로 일시 대체한다. |
| H6-C가 의미 실패 상태에서도 비용 감소만으로 supported 가능 | 해결됨. `decisions()`는 같은 split의 실패·parity 실패를 포함해 검증 상태를 판단하며, 실패 시 비용 가설을 해석 불가로 표시한다. |
| 알 수 없는 status, 거짓 integrity failure, raw prediction, 일부 이력만 주는 fallback이 통과 | 해결됨. `assess()`의 enum·prediction 형식·독립 snapshot 유효성·전체 이력 반환 검사를 확인했고, 동결 전 확대 mutation audit의 통과도 확인했다. |

`run_study.verify_freeze()`를 이 검토에서 호출하여 동결 소스·자료 및 baseline 의존 파일의 SHA가 일치함을 확인했다. 이 일치는 의미의 진실성·외부 최신성 인증이 아니다.

## 3. 원문과 gold 라벨의 대응

[`holdout_builder.py`](holdout_builder.py) 전체와 [`HOLDOUT_AUTHOR.md`](HOLDOUT_AUTHOR.md), [`data/holdout.json`](data/holdout.json)의 대표 사례를 읽었다. 두 split의 각 family에서 첫 parameterization을 확인했고, `temporal_copy`는 시간 복사와 장소 복사의 두 분기를 따로 확인했다. 긴 후행 변경은 생성기의 반복 규칙과 최종 상태 산식으로 확인했다.

| family | 확인한 의미 대응 | 주의할 경계 |
|---|---|---|
| `place_only_late` | A의 장소만 새 장소로 지정 | 시간 유지 문구 및 단일 장소 변경이라는 제한 언어 가정 |
| `other_entity_late` | B의 시간만 변경 | A 질문에 대한 무관함은 공개 엔터티 구분에 의존 |
| `time_only_late` | A의 명시적 시간 지정 후 상대 음수 이동 | `앞으로`를 더 이른 시간으로 해석; 일반 정수 시간 모형 |
| `overwritten_unknown` | A의 첫 시간 지정을 후속 절대 지정이 덮음 | 과거 변경 이력이 아니라 현재 값 질문 |
| `temporal_copy` | 복사 당시 source 값을 target으로 이동한 뒤 source를 다시 변경 | 마지막 source 값을 소급 복사하지 않음; 시간/장소 분기 모두 확인 |
| `weak_choice` | 두 대상 중 정확히 하나를 지정하는 두 joint 분기 | 임의로 한 target을 gold로 확정하지 않음 |
| `quoted_update` | 명시적인 인용·예시로 상태 유지 | 실제 변경하지 않는다는 문구가 있음 |
| `compound_change` | 한 원문 안의 장소·시간 지정을 모두 적용 | `sequence`에 두 전이를 모두 저장 |
| `negation` | 변경 요청 자체가 없거나 변경하지 말라는 문장으로 상태 유지 | 이전 실행을 소급 취소하는 의미로 라벨링하지 않음 |
| `late_correction` | 최종 명시 시간으로 현재 값을 교체 | 현재 상태 계약이며 잘못된 과거 기록 자체를 삭제하는 모형이 아님 |
| `unsupported_query` | 장소 변경 gold는 유지하고 과정·실제 실행 질문은 미지원 | 이 family에도 지원되는 현재 시간 대조 질문이 들어 있음 |
| `long_suffix` | 4/8/12/16개의 실제 장소 변경을 순서대로 적용 | 인위적 반복 구조이므로 pooled 효과에 대한 가중치 영향이 있음 |

값이 지정되지 않은 문장을 임의의 단일 값으로 gold 라벨링한 경우는 이 자료에서 발견하지 못했다. 작성자는 “장소만 다시 정해줘” 같은 문장을 자료에서 제외했다고 명시하며, 생성기에서도 사용하지 않는다.

초기화 문구의 `도서관로`, `공원로`처럼 한국어 조사 사용이 부자연스러운 표현이 있다. 이는 뜻을 반대로 라벨링한 오류는 아니지만 자연 대화의 대표성을 낮춘다. 일부 시각은 24를 넘는다. 모형이 일반 정수 시간을 명시하므로 모형 내부 오류로 보지는 않지만 실제 달력 상태의 평가로 확장해서는 안 된다.

### 중복된 구조와 독립성

controlled의 `overwritten_unknown`과 `late_correction`은 모두 “A 시간 절대 지정 → A 시간 절대 지정”이라는 동일한 의존성 구조다. 두 family가 다른 값을 갖는다고 해서 독립적인 두 추론 능력을 검증한 것은 아니다. split 사이에도 같은 48개 잠재 프로그램·gold·질문을 두 표현으로 쓴 짝 구조가 있다.

따라서 384질문을 384개의 독립 자연 대화로 세거나 12 family를 완전히 독립적인 12개 능력 시험으로 해석하지 않는다. 새로운 parameterization과 표현에 대한 합성 holdout이라는 기존 한정이 필요하다.

## 4. 최종 joint 상태의 별도 산식 검사

이 감사자는 생성기의 gold 이벤트를 실행해 정답을 다시 만드는 대신, family의 의도된 의미에서 최종 네 좌표를 직접 계산하는 짧은 산식을 따로 작성했다. 그 결과와 `evaluate.exact_states()`가 gold를 실행한 결과를 비교했다.

실행 결과:

```json
{"analytic_final_joint_checks": 96, "failures": 0,
 "source": "posthoc family formulas; no selector calls"}
```

재현 명령은 저장소 루트에서 다음과 같다. 코드를 생성기에 추가하거나 원자료를 다시 쓰지 않는다.

```bash
PYTHONDONTWRITEBYTECODE=1 python - <<'PY'
import json, sys
sys.path.insert(0, "research/phase06")
import evaluate

corpus = json.load(open("research/phase06/data/holdout.json"))
places = ("도서관", "공원", "카페")
checked = 0
for case in corpus:
    i = int(case["id"].rsplit("-", 1)[1])
    family = case["family"]
    at, bt = (3, 7, 14, 21)[i], (11, 16, 5, 9)[i]
    ap, bp = places[i % 3], places[(i + 1) % 3]
    new_place, changed = places[(i + 2) % 3], at + 4 + i
    expected = [at, ap, bt, bp]
    if family in ("place_only_late", "unsupported_query"):
        expected[1] = new_place
    elif family == "other_entity_late":
        expected[2] = bt + 6
    elif family == "time_only_late":
        expected[0] = changed - (1 + i % 2)
    elif family == "overwritten_unknown":
        expected[0] = at + 2
    elif family == "temporal_copy":
        if i % 2 == 0:
            expected[0], expected[2] = bt + 2, bt + 7
        else:
            expected[1], expected[3] = new_place, places[i % 3]
    elif family == "weak_choice":
        expected[1] = new_place
    elif family == "compound_change":
        expected[0], expected[1] = changed, new_place
    elif family == "late_correction":
        expected[0] = at + 1
    elif family == "long_suffix":
        expected[1] = places[(i + 4 * (i + 1)) % 3]
    elif family not in ("quoted_update", "negation"):
        raise AssertionError(family)
    if family == "weak_choice":
        left, right = expected.copy(), expected.copy()
        left[0], right[2] = at + bt + 1, at + bt + 1
        analytic = {tuple(left), tuple(right)}
    else:
        analytic = {tuple(expected)}
    actual = evaluate.exact_states(case["gold"], case["public"]["entities"])
    assert actual == analytic, (case["id"], actual, analytic)
    checked += 1
print({"analytic_final_joint_checks": checked, "failures": 0})
PY
```

이 검사는 template/gold/구체 실행기의 대응을 보강한다. 템플릿 작성 의도가 자유 한국어의 유일한 해석이라는 독립적인 증명은 아니다. 새 라벨 선택이나 알고리즘 튜닝에는 사용하지 않았다.

별도로 다음 읽기 전용 재생성 검사도 실행했다.

```bash
python research/phase06/holdout_builder.py --check
```

96이력/384질문/48잠재 프로그램, 269,310 bytes 및 SHA-256
`ee2640474780954514f3018e971701c49e273bf6b4e6f5d156bcd2428035a830`이 기존 자료와 일치했다.

## 5. 저장된 결과의 독립 재집계

[`results/holdout_rows.json.gz`](results/holdout_rows.json.gz)의 2,304행을 읽어 split·method별 상태 `Counter`, 오류 수, 출력 바이트 및 비용 키의 합을 직접 계산했다. `evaluate.summarize()`를 다시 호출해 같은 구현을 재실행한 것이 아니다.

다음 항목이 [`results/holdout_results.json`](results/holdout_results.json)과 모두 일치했다.

- 두 split × 여섯 method의 상태 수.
- schema 오류, false certification, containment 위반, selected gold projection 실패 수.
- output/full-output bytes와 모든 비용 벡터 합.
- raw row 수 2,304, 해제 후 UTF-8 크기 2,509,175 bytes.
- gzip SHA-256 `cb1539adfc27f89ab525cabbcf68bda869fca4d0c0a8395c46885662450681aa`.

요약의 핵심 비교는 다음과 같다. 각 split은 192질문이며, 이 중 지원 질문은 184개, gold의 joint 답이 유일한 지원 질문은 168개다.

| 항목 | controlled frozen → text | challenge frozen → text |
|---|---:|---:|
| `certified_model` | 26 → 100 | 6 → 6 |
| `opaque_fallback` | 158 → 72 | 178 → 178 |
| `ambiguous` | 0 → 12 | 0 → 0 |
| `unsupported_query` | 8 → 8 | 8 → 8 |
| 실제 전체 이력 출력 | 166 → 80 | 186 → 186 |
| 추가로 기록/출력이 줄어든 질문 | 86 | 0 |
| 새로운 인증 | 74 | 0 |
| text의 proper scope 사건 처리 | 278 | 0 |
| 출력 bytes | 107,661 → 76,944 | 121,479 → 121,479 |
| frozen 대비 출력 감소 | 28.5312% | 0% |
| equal-byte-work proxy | 267,407 → 280,758 | 297,685 → 315,417 |
| proxy 비용 증가 | 4.9928% | 5.9566% |

지원하지 않는 실제 캘린더 반영 질문을 해결한 것으로 해석할 근거는 없다. `unsupported_query` family의 일부 개선은 그 family에 함께 넣은 **지원되는 현재 시간 질문**에서 나온 것이다.

oracle는 controlled에서 120개, challenge에서 108개를 인증했다. 이 결과는 gold may-write를 외부에서 받은 조건부 결과다. 원문 분석기가 이를 추출했다고 해석할 수 없고 annotation 생성·검증 비용도 측정하지 않았다.

## 6. 출력 감소에도 작업량이 증가한 이유

controlled에서 text-only 방법과 frozen의 차이를 원시 비용합으로 분해하면 다음과 같다.

| 비용 성분 | text − frozen |
|---|---:|
| 출력 bytes | −30,717 |
| 해시 입력 bytes | 0 |
| cheap parsing 입력 bytes | +28,953 |
| contract parsing 입력 bytes | +20,843 |
| detailed parsing 입력 bytes | −5,728 |
| source-work bytes 합 | +44,068 |
| 출력 + source-work proxy | **+13,351** |

detail 호출은 158 → 72로 줄지만 방문 기록은 554개 늘었다. 전역 미해석을 만나면 곧 전체 이력 fallback으로 끝나는 baseline과 달리, 좁은 scope는 다른 필드의 답을 찾기 위해 더 오래된 기록까지 탐색할 수 있다. 출력 축소를 가능하게 하는 탐색 자체에도 비용이 든다.

challenge는 실제 scope 국소화가 한 번도 발동하지 않았다. cheap/detail 호출, 선택, 출력은 baseline과 같고 contract 분석 178회/17,732 bytes만 추가된다. 오류 0이나 의미 동등성만으로 이 split을 개선 성공으로 보고하면 안 된다. 동결 결과의 `not_supported_no_effect` 및 비용 미지지 판정은 관측과 맞다.

### 사후 가중치 민감도 확인 — 주평가를 대체하지 않음

인위적 반복 구조인 `long_suffix`의 영향을 알아보기 위해, 결과를 본 뒤 해당 family만 제외하고 기존 row를 재집계했다. 알고리즘·라벨을 바꾸지 않았고, 원래 주결과도 그대로 보존했다.

| controlled의 집계 범위 | 질문 수 | 출력 감소 | proxy 비용 증가 |
|---|---:|---:|---:|
| 사전에 정한 전체 | 192 | 28.5312% | 4.9928% |
| 사후 `long_suffix` 제외 | 176 | 22.3502% | 1.4745% |

출력 축소는 긴 후행 변경 family 하나에만 의존하지 않는다. 동시에 그 family를 제외해도 이 proxy에서 총이득은 확인되지 않는다. 이는 분포 가중치의 영향을 보는 사후 진단이며 유리한 새 평가조건의 결과로 교체하면 안 된다.

## 7. 로컬 시간 통계 확인

[`results/timing.json`](results/timing.json)의 모든 method·split에 대해 저장된 다섯 값에서 median/min/max를 다시 계산하여 일치를 확인했다. 최초 기록된 실행의 text-scoped 대 frozen 중앙값은 다음과 같다.

| 범위 | 질문 수 | frozen 중앙값 | text 중앙값 | 상대 변화 |
|---|---:|---:|---:|---:|
| controlled | 192 | 5.992 ms | 8.492 ms | +41.72% |
| challenge | 192 | 5.956 ms | 6.217 ms | +4.38% |
| 기존 corpus 회귀 | 672 | 27.021 ms | 29.963 ms | +10.89% |

위 값은 corpus 전체를 한 번 순회하는 **계측된 로컬 Python 경로**의 시간이다. 한 질문의 시간이나 LLM latency가 아니다. challenge의 관측 범위는 frozen 5.279–6.856 ms, text 5.761–8.282 ms로 겹친다. 작은 중앙값 차이를 안정적인 일반 성능 차이 또는 통계적 유의성으로 해석하지 않는다. 이번 표의 목적은 실제 측정에서 총 시간 이득이 뒷받침되지 않았다는 사실을 기록하는 것이다.

현재 `output_bytes`는 reader에게 줄 원문·질문·receipt의 렌더링 크기다. prediction/scope-trace/cost dict의 직렬화는 여기에 포함되지 않는다. trace는 offline diagnostics이며, downstream에서 독립 검증 가능한 proof-carrying certificate를 전달한 비용이라고 주장할 수 없다. 전체 LLM·서비스 비용은 미측정이다.

## 8. 이번 검토가 확인하지 않은 것

- 외부 인간의 라벨 검증 또는 실제 자연 대화의 평가.
- 질문 생성과 학습 분포의 독립성에 대한 통계적 보장.
- 실제 LLM 답변 품질, 토큰, API 고정비, 검색 서비스 비용.
- 계획 상태를 넘는 미완료 요청 생명주기, 실행 증거, 권한 또는 관계 맥락의 보존.
- 임의의 source sentence에서 may-write를 안전하게 추출한다는 보장.
- 새 선택기의 전역 최소 비용 또는 full history 대비 서비스 전체 비용 최적성.

이 검토에서는 holdout 전체 selector 실험을 새로 실행하지 않았다. 원자료 재생성 확인, 별도 최종 상태 산식 비교, 저장된 원시 결과의 재집계, timing 통계 확인 및 freeze SHA 검증을 실행했다. 최초 실험과 별도 전체 재현의 실행 사실은 각 receipt를 따른다.

다음 연구에서는 이 자료를 이미 본 데이터로 취급해야 한다. challenge 표현을 문법에 추가한 뒤 같은 challenge에서 성능이 좋아져도 그것은 사후 회귀 개선이며 새로운 holdout 일반화 성과가 아니다.
