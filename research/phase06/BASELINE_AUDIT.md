# Phase 06 출발점 감사: 평가와 비용

기준 커밋: `780891f6c147cfd3c1a3b0d065792776aaa525f3`  
감사일: 2026-10-22  
범위: Phase 05 / revision02의 평가 계약과 구현 대조. 운영 적용과 분리한 연구다.

이 문서는 새 알고리즘의 실험 결과가 아니다. 기존 자료의 설명·코드를 검토하고, 평가기 결함 하나를 fault injection으로 재현했다. 기존 동결 파일은 수정하지 않았다. 다른 연구자가 수행하는 baseline 재현 및 Phase 06 실험과 이 감사의 실행 범위를 구분한다.

## 1. 결론과 증거의 강도

| 구분 | 발견 | 근거와 경계 |
|---|---|---|
| 평가기의 잠재 결함 — 실제 재현 | 요청 필드가 빠진 `certified_model` 출력을 평가기가 오류로 판정하지 않는다. `prediction={}`도 통과한다. | `phase05/study.py`의 반환 키만 순회하는 검사에 fault injection을 수행했다. 현재 정상 엔진이 빈 인증을 내놓았다는 발견은 아니다. |
| 기존 설명과 결과의 일치 | 문서의 main/stress lazy 인증 수, fallback 수, 출력 바이트 및 상세 입력 proxy 수치가 저장된 JSON과 일치한다. | 요약 JSON 교차 확인이다. 이 감사자가 전체 corpus를 다시 실행했다는 뜻은 아니다. |
| 명시된 모형 한계 | 기본 corpus의 answer containment는 필드별 marginal 포함 관계다. 필드 사이 joint 관계를 직접 검사하지 않는다. | `study.concrete()`가 joint 상태 집합을 마지막에 marginal로 바꾼다. revision02의 별도 대수적 suite에는 joint projection 검사가 있다. |
| 명시된 비용 한계 | 출력 bytes + 상세 파서 입력 bytes는 전체 비용이 아니다. | 해시·cheap parsing·순회·재파싱의 일부·DP·검증 CPU 및 실제 모델 비용을 합산하지 않는다. 기존 문서도 부분 proxy라고 한정한다. |
| 데이터 경계 | 읽은 평가 경로에서는 gold 전이·family·split을 선택기에 직접 전달하지 않는다. | 같은 연구자가 문법과 fixture를 설계한 합성 평가이며, 이 인터페이스 확인은 외부 자연어 일반화를 검증하지 않는다. |

읽은 범위에서 기존 정상 엔진의 잘못된 인증을 새로 발견하지 않았다. 평가기 결함은 검증 장치의 누락을 지적하며, 기존 보고된 오류 0 결과를 자동으로 무효화하거나 오류가 있었다고 입증하지 않는다.

## 2. 재현한 평가기 결함: 빈 인증 결과의 공허한 통과

대상은 `research/phase05/study.py:evaluate`의 91–95행이다.

```python
for fact, values in result["prediction"].items():
    if values is not None and not gold[fact] <= set(values):
        containment = False
    if result["status"] == "certified_model" and set(values) != gold[fact]:
        false_cert = True
```

이 검사는 요청된 필드 집합을 독립적으로 확인하지 않고 실제 반환된 키만 순회한다. 반환 키가 비어 있으면 두 지표가 초기값에 머문다. 다음 명령을 저장소 루트에서 실행했다. 정상 반환값을 복사해 상태와 예측만 바꾸는 메모리 monkeypatch이며, 기존 코드·결과를 쓰지 않는다.

```bash
PYTHONDONTWRITEBYTECODE=1 python - <<'PY'
import sys
sys.path.insert(0, "research/phase05")
import study
from fixtures import build_case

case = build_case("absolute_reset", 0)
query = case["queries"][1]  # 시간과 장소를 모두 요청한다.
normal = study.engine.run({**case["public"], "query": query})
study.engine.run = lambda public, mode: {
    **normal,
    "status": "certified_model",
    "prediction": {},
}
result = study.evaluate(case, query, "lazy")
print(result["status"], result["prediction"],
      result["false_certification"], result["containment_violation"])
PY
```

실제 출력:

```text
certified_model {} False False
```

현재 `revision02/engine.py:203`은 `requested` 전체를 순회해 예측을 작성한다. 따라서 이 fault injection은 정상 엔진이 이미 보인 언어 오류를 재현한 것이 아니라, 평가기가 그러한 결함을 검출할 수 없는 상태임을 입증한다.

새 평가기는 최소한 다음을 분리해 확인해야 한다.

- 평가기가 독립적으로 정의한 요청 필드와 반환 키의 완전한 일치.
- `certified_model`이면 모든 요청 필드가 존재하고 각각 singleton인지.
- 인증된 값이 gold와 같은지.
- unsupported 및 fallback이 해당 출력 계약을 지키는지.
- 빈 인증, 일부 필드 누락, 잘못된 singleton, TOP 인증 같은 mutant를 실제로 거부하는지.

이 파일은 새 평가기의 구현 또는 검사를 수행했다고 주장하지 않는다.

## 3. answer containment와 답변 가능 범위는 다르다

`study.py:91–95`에서 `None`은 TOP이므로 모든 gold를 포함하는 것으로 간주한다. 이것은 보수적 근사의 soundness 검사에는 맞지만, 모든 답을 TOP으로 돌려도 포함 위반은 0이다. unsupported의 빈 예측도 기존 루프에서 포함 위반 0이다. 오류 수와 답변 범위는 함께 읽어야 한다.

다음 지표를 구분하는 것이 적절하다.

| 지표 | 해석 |
|---|---|
| `false_certification / certified` | 실제 단정의 오류 비율 |
| `containment_violation / supported` | 모형의 정답 가능성을 제거한 비율 |
| `certified / all` | 전체 질문에 대한 인증 범위 |
| `certified / gold_singleton_supported` | 모형에서 답이 유일한 지원 질문을 실제로 해결하는 범위 |
| `ambiguous / all` | 모호성 반환 비율 |
| `opaque_fallback / all` | 미해석 때문에 전체 이력으로 돌아간 비율 |
| `unsupported / all` | 질문 계약을 지원하지 않는 비율 |
| `selected == all` | 실제 전체 원문 출력 비율 |
| `strictly fewer records/bytes` | 출력 축소가 실제 발생한 질문 수 |

`ambiguous`에는 실제 의미의 모호성과 분석 정밀도 부족이 섞일 수 있다. gold가 singleton인 지원 질문에 대한 인증 범위를 함께 보면 두 원인을 더 잘 구분할 수 있다. `selected == all`과 fallback status도 같은 지표가 아니다. unsupported도 전체 이력을 출력하며, 짧은 이력에서는 인증된 출력이 모든 기록을 포함할 수도 있다.

## 4. marginal 포함 검사와 joint 보존 검사

`study.py:52–82`의 구체 실행기는 branch별 joint 상태를 실행하지만 마지막에 필드별 가능한 값 집합으로 바꾼다.

```python
return {f"{f[0]}.{f[1]}": {s[i] for s in states}
        for i, f in enumerate(facts)}
```

따라서 기본 corpus 평가는 필드별 답 포함을 확인한다. 여러 필드의 값이 함께 가능한지에 대한 관계 보존을 직접 확인하지 않는다. 기존 문서는 product domain의 상관관계 손실을 인정하므로 그 설명과 충돌하지 않는다. 다만 이 수치를 자유로운 복합 질문의 전체 의미 보존으로 확대할 수 없다.

별도 `revision02/reduction_study.py:70–76`은 full gold stream과 선택된 gold stream을 구체 실행한 뒤 질문 필드의 **joint projection equality**를 검사한다. 이것은 원문 선택에 대한 더 강한 검사지만 범위가 제한된다.

- 두 모임의 초기 시간은 0과 1로 고정되어 있다.
- 정의된 11개 연산으로 길이 4 프로그램을 만든다.
- 세 질문은 모두 시간에 관한 질문이다.
- 장소 질문, unknown/havoc의 구체 전이, 자유 언어 해석, 실제 실행·권한은 포함하지 않는다.

새 실험에서도 typed 의미가 정확히 정의된 경우의 joint projection, text-only 분석의 포함 관계, 최종 인증 형태를 별도 검사로 유지할 가치가 있다. 골드가 존재하지 않거나 무한 TOP인 경우 임의의 유한 값 몇 개만 골라 검사하고 일반 보존을 증명했다고 부르면 안 된다.

## 5. 비용 지표 대조

읽은 코드의 비용 경로는 다음과 같다.

| 경로 | 측정 또는 작업 |
|---|---|
| `revision02/engine.py:164–166` | cheap parser 호출 수 |
| `revision02/engine.py:167–170` | detailed parser 호출 수와 원문 UTF-8 bytes |
| `revision02/engine.py:127–140` | 전체 snapshot JSON 직렬화와 SHA 검사 |
| `revision02/engine.py:144–147` | receipt·질문·출처 원문 렌더링 |
| `phase05/study.py:123–125` | 출력 bytes + detail 원문 bytes proxy 및 호출 고정비의 손익분기 값 |
| `revision02/reducer.py:82–88` | 선택된 원문의 cheap/detail 재파싱; detail 재파싱만 별도 count/bytes |

부분 proxy에서 빠진 비용에는 cheap parsing의 원문 처리량, 정규식 구성, 역방향 순회, JSON 직렬화·해시 읽기, reducer의 cheap 재파싱, DP 및 검증 CPU가 있다. 실제 LLM prompt·토큰·고정 호출비·응답 생성도 측정하지 않는다. 기존 문서가 부분 proxy라고 명시하는 것은 타당하다.

새 실험은 서로 다른 단위를 임의로 실비에 합산하기보다 다음 cost vector를 분리해서 기록하는 편이 낫다.

```text
output_utf8_bytes
snapshot_serialized_bytes
records_visited
cheap_calls / cheap_source_bytes
contract_calls / contract_source_bytes
detail_calls / detail_source_bytes
reparse_calls / reparse_source_bytes
local_wall_time
```

전체 이력 기준과 비교할 때 해시·검증 비용을 양쪽에 동일하게 부과했는지도 명시해야 한다. 로컬 wall time은 Python·OS·시스템 부하에 의존하므로 결정적인 작업량과 별도로 해석한다.

## 6. 기존 수치 교차 확인

`research/phase05/results.json`의 `summary.main.lazy`와 `summary.stress.lazy`를 읽어 문서의 설명과 대조했다.

| 항목 | main | stress |
|---|---:|---:|
| 질문 수 | 384 | 288 |
| `certified_model` | 288 | 36 |
| `opaque_fallback` | 48 | 240 |
| `ambiguous` | 32 | 0 |
| `unsupported_query` | 16 | 12 |
| false certification | 0 | 0 |
| answer containment 위반 | 0 | 0 |
| 출력 bytes 감소 | 63.1294676% | 9.2071410% |
| detailed 호출 | 224 | 240 |
| detailed 원문 bytes | 15,920 | 18,687 |
| 출력 + detail 입력 proxy 감소 | 59.7745549% | 4.3111805% |

이 표는 저장된 결과와 설명의 일치 확인이다. 이 감사자가 전체 실험을 다시 실행해 얻은 수치가 아니다. main의 유리한 수치와 stress의 낮은 인증 범위·절감률을 함께 보고해야 한다.

## 7. 입력 누출과 독립성

`study.py:85–88`은 `{**case["public"], "query": query}`만 선택기에 전달하고 gold를 그 후 평가에 사용한다. `fixtures.py`는 public과 gold를 별도로 저장한다. 읽은 경로에서 gold 전이·family·split을 선택기에 직접 넘기는 것을 발견하지 않았다.

그러나 이것만으로 데이터의 독립성이 생기지는 않는다.

- fixture는 엔진의 `event`, `snapshot` helper를 공유한다.
- 문법과 fixture를 같은 연구자가 설계했다.
- stress의 추가 표현은 네 가지 suffix 패턴을 반복한다(`fixtures.py:70–79`).
- 672질문은 336개 이력에 질문 두 개씩 적용한 짝지어진 사례다.
- 대수적 suite는 정의된 연산의 표면 표현을 생성한다.

따라서 기존 corpus는 새 단계의 회귀 검사로 사용해야 한다. 새 독립 자연어 평가라고 부르면 안 된다. 별도 에이전트가 새 holdout을 작성하더라도 공통 지시와 의미 모형을 공유한 합성 평가라는 한계를 밝혀야 하며, 외부 인간의 블라인드 평가와 동일시할 수 없다.

## 8. 읽은 자료, 실행한 것, 미확인 부분

읽은 자료:

- `HANDOFF.md`
- `docs/RESEARCH_LOG.md`
- `docs/MATHEMATICS.md`
- `docs/NEXT_EXPERIMENT.md`
- `docs/ARTIFACT_GUIDE.md`
- `docs/REPRODUCIBILITY.md`
- `research/phase05/revision02/engine.py`
- `research/phase05/revision02/reducer.py`
- `research/phase05/revision02/reduction_study.py`
- `research/phase05/revision02/audit.py`
- `research/phase05/study.py`
- `research/phase05/fixtures.py`
- `research/phase05/results.json`의 main/stress lazy 요약

실행한 것:

- 위 빈 인증 fault injection. `PYTHONDONTWRITEBYTECODE=1`로 Python을 실행했고, 저장소의 기존 파일을 수정하지 않았다.
- 기존 JSON의 두 lazy 요약을 출력해 문서와 대조했다.

이 감사에서 실행·검증하지 않은 것:

- Phase 01–04 코드 및 결과의 독립 재검산.
- 전체 raw 결과 row와 corpus 개별 사례의 전수 수동 검토.
- baseline 전체 재현. 별도 연구 실행 기록을 확인해야 한다.
- Phase 06 선택기·평가기의 구현, 새 실험 또는 새 수치 산출.
- 실제 자연어 외부 평가, 실제 LLM·토큰·API 비용 실험.

새 연구 결과는 별도 프로토콜과 실행 산출물에 근거해 기록해야 한다. 이 감사의 제안을 구현 전에 성공 결과로 간주하지 않는다.
