# Phase08 동결 후 자료·분모·가중치 검토

작성: 2026-10-22. 검토자: 새 holdout을 작성했던 별도 동일 모델 에이전트.
이 문서는 **동결과 첫 주평가가 끝난 뒤** 작성한 해석·재집계 기록이다.
자료·라벨·선택기·평가기·주 지표를 변경하지 않았고 새 timing 실험도 실행하지 않았다.

## 1. 검토 범위

실제로 읽은 것은 [작성기](holdout_builder.py), [작성 기록](HOLDOUT_AUTHOR.md),
[holdout](data/holdout.json)의 프로그램식 집계,
[주평가 요약](results/holdout_results.json),
[1,728개 원시 행](results/holdout_rows.json.gz), [원본 timing](results/timing.json)이다.
기존 schema·문법의 사전 읽기 범위는 작성 기록에 있다.

원시 행에서 비용 항목을 직접 더해 저장된 방법별 합계와 대조했다.
stream/step/method 키의 유일성, 원본 자료와 유효성·질문 지원·gold 적용 표기의
일치, 상태와 오류 분모를 재집계했다. 서로 다른 입력·gold 프로그램 수는 아래의
명시적 canonical JSON 정의로 계산했다. 주평가의 집계 함수를 호출하지 않았다.

**새 holdout의 모든 자연어 원문을 외부 사람이 수기 판정한 검토가 아니다.**
자료 작성자가 자기 builder와 typed 라벨을 검토한 것이므로, 독립 자연어 정답
감사라고 부르지 않는다. 캐시 정확성의 별도 재현은 다른 검토자의 담당이며
이 문서는 그것을 대신하지 않는다.

## 2. 오류 분모: 같은 411이라도 다른 집합이다

자료는 36 stream / 432 step이며 네 방법의 원시 행은 1,728개다.
각 방법에서 다음 수가 같았다.

| 모집합 또는 검사 대상 | 건수 | 구분 |
|---|---:|---|
| 전체 step | 432 | 반복·변경을 포함 |
| 유효 snapshot | 420 | 무효 12 제외 |
| 유효하고 지원하는 질문 | 411 | 무효 12와 미지원 9 제외; membership 변경 9는 포함 |
| Gold 적용 step | 411 | 무효 12와 membership 변경 9 제외; 미지원 9는 포함 |
| Gold 적용·지원 질문 | 402 | containment 대상 |
| Gold 적용 certified 결과 | 378 | false certification 대상 |
| Selected-gold projection 검사 | 411 | 미지원 9의 전체 history 선택 검사도 포함 |

따라서 “gold 411”과 “유효·지원 411”은 크기만 같고 같은 집합이 아니다.
**False certification의 분모는 378이며 402가 아니다.**

| 각 방법의 상태 | 건수 / 432 |
|---|---:|
| `certified_model` | 378 |
| `ambiguous` | 15 |
| `opaque_fallback` | 18 |
| `integrity_failure` | 12 |
| `unsupported_query` | 9 |

전체 이력 선택은 27/432로 opaque 18 + unsupported 9다. 무결성 실패는 거절이며
전체 이력 fallback에 합하지 않는다. Gold 제외 21개는 membership 변경의 opaque
9개와 integrity failure 12개다. Builder의 `entity_membership_undefined` 이유는
평가 행에서 `undefined_membership_projection`으로 표기되어 있으며 대상 9개는 같다.

원시 행에서 재집계한 오류는 방법별로 다음과 같다.

- False certification: **0/378**.
- Containment 위반: **0/402**.
- Selected-gold projection 실패: **0/411**.
- 구조·schema 오류: **0/432**.
- Fresh와 각 비교 방법 사이의 관찰적 동등성 실패: **각 0/432**.

Projection의 미지원 9건은 답을 맞혔다는 뜻이 아니다. 전체 이력을 선택했는지
검사한 것이다. Containment 역시 주변부 값의 포함 검사이며, product abstraction이
정확한 joint answer set을 반환한다는 검증으로 바꾸어 말하지 않는다.

## 3. 얼마나 다른 입력과 프로그램인가

“서로 다른 snapshot”이나 “잠재 프로그램”은 동일성 규약 없이는 모호하다.
다음 표는 canonical JSON에서 key를 정렬하되 배열 순서는 보존하고, **내용 전체를
직접 비교**하여 계산했다. 숫자와 entity 이름도 보존한다.

| 동일성 정의 | 전체 432 step | 유효 420 step |
|---|---:|---:|
| `records` 전체: `seq`, `id`, `text` 포함 | 210 | 204 |
| 전달된 `(records, expected snapshot)` 쌍 | 216 | 204 |
| 순서 있는 원문 목록: `id`, `seq` 제외 | 173 | 168 |
| 원문 목록 + ordered entities | 182 | 177 |
| 전체 `public` + 실행 namespace | 321 | 309 |

무효 snapshot에는 같은 records에 다른 expected digest/head를 전달한 경우가
있으므로 두 첫 행의 전체 수가 다르다. 정상 snapshot에서는 record 배열로
expected snapshot이 결정되므로 수가 같다. Query와 namespace는 snapshot 자체와
다른 관찰이므로 마지막 행을 별도로 계산했다.

유효 420 step에 등장하는 서로 다른 원문 문자열은 675개다. 무효 변조 원문까지
포함하면 676개다. 같은 원문 history에 새 opaque ID를 부여한 경우가 있으므로
204개의 exact records를 204개의 의미상 새 history라고 부르면 안 된다.

Gold를 적용한 411 step의 **서로 다른 typed-event 배열은 123개**다. 이 수는
`kind`, `target`, `value`, `source`, `targets`와 사건 순서의 정확한 동일성에 따른다.
Noop 사건을 제거한 배열도 이번 자료에서는 123개다. Entity 이름을 gold에서
처음 등장한 순서의 `E0`, `E1`로 바꾸되 상수와 나머지 구조를 보존해도 123개다.
이 숫자 일치는 이번 생성 자료의 성질이며 일반 법칙이 아니다.

| Family | Gold 적용 step | 유효한 서로 다른 원문 history | 서로 다른 exact typed 프로그램 |
|---|---:|---:|---:|
| `short_repeated` | 36 | 3 | 3 |
| `short_churn` | 36 | 36 | 36 |
| `long_cheap_repeated` | 36 | 3 | 3 |
| `long_deep_repeated` | 36 | 3 | 3 |
| `long_deep_single_use` | 36 | 36 | 3 |
| `working_set_fit` | 36 | 3 | 3 |
| `working_set_pressure` | 36 | 3 | 3 |
| `phase_shift` | 36 | 18 | 6 |
| `revisions_copy_reorder` | 36 | 36 | 36 |
| `scope_and_ambiguity` | 36 | 18 | 18 |
| `entity_namespace_rotation` | 27 | 3 | 3 |
| `integrity_unsupported_recovery` | 24 | 6 | 6 |

예를 들어 `long_deep_single_use`는 36개의 서로 다른 원문 history를 갖지만
긴 quote의 typed 의미는 모두 noop이므로 3개의 typed 프로그램만 있다.
반대로 `revisions_copy_reorder`의 3개 stream에는 36개의 서로 다른 typed 배열이
들어 있다. 따라서 **36 stream = 36개의 독립 잠재 프로그램**이라고 말할 수 없다.

123도 독립 표본 수가 아니다. 동일 template, seed 절차, 공개 문법과 parameter
구성을 공유하며, 여러 프로그램은 같은 최종 상태나 같은 query 투영을 만들 수
있다. 모든 초기 상태에서의 전이 동등성 같은 의미 동치류는 계산하지 않았다.
위 숫자는 재현 가능한 중복 제거 통계일 뿐이다.

## 4. 전체 이득의 입력 분포 의존성

주 지표 `phase08_work_score`의 원시 행 합계는 다음과 같다.

| 방법 | P7 byte-work proxy | Phase08 score |
|---|---:|---:|
| `fresh` | 30,427,891 | 30,427,891 |
| `lru` | 47,317,066 | 47,535,514 |
| `selective` | 29,070,270 | 29,124,198 |
| `no_directory` | 31,000,820 | 31,055,100 |

Phase08 score에는 정책 control action의 사전 가중치가 들어가므로 이를 실제
전송 byte나 CPU instruction 수라고 부르지 않는다. Fresh에는 추가 control action이
없어 P7와 score가 같다. 아래 비중은 이 fresh 합계에 대한 비중이다.

| Family | Fresh 합 | Fresh 전체 비중 | Selective − fresh score |
|---|---:|---:|---:|
| `short_repeated` | 119,331 | 0.39% | +1,584 |
| `short_churn` | 325,032 | 1.07% | +3,312 |
| `long_cheap_repeated` | 2,128,851 | 7.00% | +2,880 |
| `long_deep_repeated` | 4,204,803 | 13.82% | −130,080 |
| `long_deep_single_use` | 4,204,803 | 13.82% | +503,824 |
| `working_set_fit` | 3,764,559 | 12.37% | −610,644 |
| `working_set_pressure` | 11,513,355 | 37.84% | −1,229,313 |
| `phase_shift` | 3,852,248 | 12.66% | +149,224 |
| `revisions_copy_reorder` | 94,719 | 0.31% | +2,040 |
| `scope_and_ambiguity` | 65,061 | 0.21% | +1,752 |
| `entity_namespace_rotation` | 96,555 | 0.32% | +864 |
| `integrity_unsupported_recovery` | 58,574 | 0.19% | +864 |

긴 입력을 넣은 여섯 family는 전체 step의 절반인 216/432를 차지하지만,
fresh byte proxy 합에서는 **29,668,619 / 30,427,891 = 97.50%**를 차지한다.
특히 fit와 pressure 두 family가 fresh 합의 **50.21%**다.

두 working-set family에서 합계 차이는 −1,839,957이고, 나머지 열 family의
합계 차이는 +536,264다. 따라서 전체 차이가

\[
-1{,}839{,}957+536{,}264=-1{,}303{,}693
\quad(-4.2845\%)
\]

인 것은 맞지만, **대부분의 조건에서 이득이라는 뜻은 아니다.** Stream 최종 합계는
8/36에서 줄고 28/36에서 늘었다. 질문별 score는 100/432에서 줄고, 21/432에서
같고, 311/432에서 늘었다. 위 family 분해는 사후 설명이며, 유리한 family만
남겨 주평가를 다시 정의하는 조작을 하지 않는다.

`long_deep_single_use`는 실제 파서 실행을 하나도 줄이지 못하면서 전체 score가
11.98% 늘었다. `phase_shift`는 일부 warm 질문에서 절약했지만 stream 전체에서는
구축·교체 비용을 회수하지 못해 family 합이 3.87% 늘었다. 관측된 반복을 이용해도
미래 반복을 보장할 수 없다는 한계가 자료에서 실제로 나타난다.

## 5. 표면형과 의미 검증의 경계

큰 원문은 모두 제한 문법의 **noop quote**다. payload가 길어져도 gold 상태는
바뀌지 않는다. 긴 cheap와 deep quote는 서로 다른 고정 표면형이 유도하는 파서
단계 수를 비교하기 위한 것이다. 따라서 이 결과는 일반적인 긴 자연어 대화의
의미 추론 비용이나 관계·정정·실행 증거 이해 능력의 개선을 입증하지 않는다.

짧은 부분에는 set/add/copy/maybe-set, frame과 query 변경을 넣었다. 이는 기존
제한 모형의 보존 경계를 검사하며, 새 어휘·자유로운 표현·대명사·암묵적 정정·
실제 실행 여부의 외부 자연어 의미 평가는 아니다. 표현 일반화는 Phase06에서
남은 문제이며 이번 자료로 해결됐다고 말할 수 없다.

출력 UTF-8 bytes는 네 방법 모두 165,238로 동일하다. 답변 범위와 fallback 상태도
동일하다. 비용 정책이 맥락을 더 잘 선택하거나 답을 더 많이 인증한 성과로
보고하면 안 된다. 이 평가에서 달라진 것은 동일 선택 경로의 계산 재사용 비용이다.

원본 timing은 fresh 61.849 ms, selective 69.497 ms의 전체 중앙값으로
selective가 약 12.37% 더 컸다. 이 문서에서는 저장된 값을 읽었으며 재측정하지
않았다. Proxy 합의 감소를 실제 로컬 속도 개선으로 바꾸어 표현할 수 없다.
7회 로컬 반복이며 통계적 유의성이나 플랫폼 일반화도 입증하지 않았다.

## 6. 이 검토의 결론

주평가의 합계 개선은 저장된 원시 행과 일치하며, 사후 분모 변경이 필요할 오류를
발견하지 않았다. 다만 지지되는 주장은 **사전에 구성한 이 합성 분포에서, 같은
관찰을 유지하면서 사전 score의 전체 합이 줄었다**는 범위다. 일반 비용 우월성,
대다수 stream의 개선, 실제 시간·LLM 요금·답변 품질 개선으로 확대할 수 없다.

다음 연구자가 우선 확인할 데이터 관련 반박점은 긴 noop quote 및 working-set
압력의 비중이다. 이 비중이 다른 새 자료에서 합계 이득이 유지되는지는 미확인이다.
현재 자료를 다시 가중하거나 정책을 조정해 얻은 결과는 새로운 독립 평가가 아니다.

## 7. 집계 재현의 핵심 명령

아래는 원시 행과 입력 파일만 읽는다. 정책·선택기·timing을 실행하지 않는다.

```bash
python - <<'PY'
import gzip, json
from pathlib import Path
from collections import Counter
p = Path('research/phase08')
corpus = json.loads((p / 'data/holdout.json').read_text())
rows = json.loads(gzip.decompress((p / 'results/holdout_rows.json.gz').read_bytes()))
summary = json.loads((p / 'results/holdout_results.json').read_text())
steps = {(s['id'], i): q for s in corpus for i, q in enumerate(s['steps'])}
key = lambda x: json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
valid = [q for q in steps.values() if q['expected_integrity'] == 'valid']
gold = [q for q in steps.values() if q['gold_applicable']]
print('valid exact records:', len({key(q['public']['records']) for q in valid}))
print('valid raw histories:', len({key([r['text'] for r in q['public']['records']]) for q in valid}))
print('exact typed programs:', len({key(q['gold']) for q in gold}))
assert len(rows) == len({(r['stream_id'], r['step_index'], r['method']) for r in rows}) == 1728
for r in rows:
    q = steps[r['stream_id'], r['step_index']]
    assert r['valid_snapshot'] == (q['expected_integrity'] == 'valid')
    assert r['supported'] == q['question_contract']['supported']
    assert r['gold_evaluated'] == q['gold_applicable']
for method, stored in summary['summary'].items():
    rr = [r for r in rows if r['method'] == method]
    for field, value in stored['cost'].items():
        assert sum(r['cost'][field] for r in rr) == value
    print(method, len(rr), Counter(r['status'] for r in rr))
    print('gold/cert/containment/projection:',
          sum(r['gold_evaluated'] for r in rr),
          sum(r['gold_evaluated'] and r['status'] == 'certified_model' for r in rr),
          sum(r['containment_violation'] is not None for r in rr),
          sum(r['selected_gold_projection_equal'] is not None for r in rr))
for family in summary['families']:
    totals = {m: sum(r['cost']['phase08_work_score'] for r in rows
                    if r['family'] == family and r['method'] == m)
              for m in ('fresh', 'selective')}
    print(family, totals['fresh'], totals['selective'] - totals['fresh'])
PY
```

검토한 자료·원본 결과의 SHA-256은 다음과 같다.

| 파일 | SHA-256 |
|---|---|
| `data/holdout.json` | `9f8c46a60d23eea8bea3f6dc7626908d4f74885a52b05d93d83c714ad6dc6613` |
| `results/holdout_results.json` | `73fa06ea9088847925a5d316d356d4fdafa717eb8bbe3606663876c2734787ce` |
| `results/holdout_rows.json.gz` | `fd0181c632e5692c8bdfd63516abffa87749dea80fff756cc3b74a5df78137ea` |
| `results/timing.json` | `9c15e6d6b4c38c484000f132470c9421b156abdd79aa168ac880a20e276eb416` |
