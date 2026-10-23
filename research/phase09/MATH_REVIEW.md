# Phase09 동결 전 수학·계측 제거 검토

작성: 2026-10-23 KST. 주 구현자와 역할을 분리한 동일 모델 에이전트의 검토다.
외부 독립 검증이 아니며 새 Phase09 holdout 원문·builder·gold·결과는 읽지 않았다.
이 문서 작성까지 performance benchmark나 profiling을 실행하지 않았다.

## 1. 결론과 검토 범위

**검토한 특정 소스와 명시한 입력 영역에서는 정책·관찰을 바꾸지 않고 보고 전용
계측을 제거하는 경로를 구성할 수 있다.** 실제 구현은 정책에 도달하는 모든 계산을
보수적으로 유지한다. 새 runtime이 fresh보다 빠른지는 이 검토로 결론내리지 않는다.

직접 기준은 Phase08 공개 commit `efba3224dd09d5c5e2bf9d9be11734fa10b32502`다.
다음 자료를 읽고 증명·data-flow와 대조했다.

- Phase08 `HANDOFF_BACK.md`, `PROTOCOL.md`, `THEORY.md`,
  `POSTFREEZE_REVIEW.md`, `DATA_REVIEW.md`.
- Phase08 `runtime.py`, `frozen.py`, `evaluation.py`.
- Phase07 `baseline.py`, `cached.py`; Phase06 `scoped.py`; Phase05r2 `engine.py`.
- Phase08 기존 수학·평가기·개발 감사 문서의 관련 부분.
- Phase09 `bindings.py`, `derive_off.py`, 생성한 `runtime_off.py`, `ERASURE_MAP.json`.

Phase08 주평가를 이 역할에서 다시 실행하거나 원시 행을 재집계하지 않았다.
그 재현은 별도 감사 역할의 증거와 구별한다. 기존 Phase01–08 소스·자료·결과는
수정하지 않았다. Phase09의 수학 문서와 아래 반례 코드만 작성했다.

## 2. 중요한 발견: 계측의 이름과 실제 의존성은 다르다

Phase08의 `cost` dict, `action` event, 내부 timer, peak 보고는 실제 정책·의미의
branch를 결정하지 않는다. 이에 비해 다음은 통계처럼 보일 수 있지만 삭제할 수 없다.

1. Resident `hits`: `(h+1)×surplus`가 victim의 기회비용을 결정한다.
2. `ACTION_WEIGHT×WARM_ACTIONS=64`: P8 보고를 없애도 surplus 정의의 피연산자로 남는다.
3. Encoding으로 얻은 C·L·R: admission과 용량, exact key를 결정한다.
4. `next_order`, entries 삽입 순서, directory, `retained_bytes`: 미래 선택을 결정한다.
5. `scope_trace`와 query-local `query_events`: 관찰 또는 실제 의미 경로다.

Fresh의 방문 원문 UTF-8 encode는 source-byte 통계에만 쓰이므로 지울 수 있다.
Selective의 방문 encode는 공유 변수 `raw`를 통해 key/L에 도달하므로 유지한다.
이 비대칭을 숨기지 않는 것이 공정한 주 비교의 일부다. Snapshot과 output의 encode는
양쪽에 계속 있다.

현재 변환은 모든 selective 방문에서 raw encoding을 남긴다. 일부 short/cheap 경로의
동적 dead encode를 추가로 지우거나 뒤로 이동할 수도 있겠지만, 그것은 이번 변환이
구현·평가한 범위가 아니다. 가장 빠른 비계측 구현이라는 결론을 금지한다.

## 3. 구체 구현 검토

`derive_off.py`는 동결 소스를 AST로 읽고 특정 계측 대상만 지운다. 출력 소스는
사람이 읽을 수 있으며 다시 생성한 bytes와 manifest가 같은지 `--check`로 검사한다.
이 이름 기반 변환을 임의 소스에 안전하게 일반화할 수 있다는 주장은 없다.

확인한 사항은 다음과 같다.

- P8 상수·cache dictionary/Counter·immutable stage 구조·정수 density 비교·victim
  계획과 적용 순서가 유지된다. `hits`와 64의 surplus 공제도 유지된다.
- 계측만 남던 `if`의 body는 `pass`가 된다. 분기를 재배치하거나 branch cost를
  없애는 추가 최적화를 하지 않았다.
- Fresh는 selective-style stage helper로 다시 구현하지 않고 P6의 원래 fixed
  `text_scoped` 흐름과 직접 parser 호출을 유지한다.
- `finish(result,...)`를 지울 때 result 생성과 기존 render/UTF-8 encode는 남는다.
- 전체 snapshot 직렬화·SHA-256·seq 범위 확인과 early exit가 유지된다.
- `run_fresh`에 남아 있는 다른 legacy method는 이번 계약 밖이다. 특히
  `frozen_lazy` 분기는 원래 계측 helper를 부르므로 비계측 실험에 쓰면 안 된다.
- Instrumented fresh는 Phase07의 별도 P6 모듈 객체를 사용하고 off fresh는 Phase08이
  로드한 P6 객체를 사용한다. 원천 bytes는 같지만 호출 감사에서는 이 모듈 객체들을
  혼동하지 않아야 한다. 주 timing에는 어느 monkey patch도 넣지 않는다.

보존 논증은 [THEORY.md](THEORY.md)의 E1(보고 비간섭), E2(cache 연산),
E3(질문), E9(prefix 귀납)으로 분리했다. 원문·context·stage의 구조적 값과
정책 상태를 보존하며 Python 객체 주소나 자원 고갈 실패까지 보존하지는 않는다.

## 4. 직접 실행한 두 반례

```bash
python research/phase09/counterexamples.py
python research/phase09/derive_off.py --check
```

두 명령은 통과했다. 반례는 사전 구성한 개발 진단이며 holdout 성과 또는 속도 자료가 아니다.

| 잘못된 제거 | 가장 이른 정책 불일치 | 이후 구체 결과 | 의미 관찰 |
|---|---:|---|---|
| resident hit 갱신 삭제 | `A,A`의 prefix 2 | prefix 3의 B를 정상판은 거절, mutant는 받아 A 축출 | 3/3질문 동일 |
| 계측 제거와 함께 `ACTION_WEIGHT=0` | prefix 1 | b가 −1→63으로 바뀌어 거절→admit | 1/1질문 동일 |

첫 반례는 고정 65,536 용량 아래 A의 e=33,408, B의 e=34,408로 개별 보관은
가능하지만 함께 보관할 수 없는 구성이다. A hit 하나가 weight를 32,750→65,500으로
바꾸고 B의 b=33,750와의 비교를 뒤집는다. 두 번째는 길이 gate도 통과하는 문자 수
278, L=320, C=103, R=154의 단일 quote다.

두 경우 모두 답만 같으면 통과시키는 감사는 잘못된 정책 변경을 놓친다.
이것은 정상 Phase08의 결함 보고가 아니라 Phase09의 계약을 약하게 정의하면 생기는
반례다. 잘못된 mutant의 변경은 그 Python 프로세스에만 있고, 상수는 `finally`로
복구하며 동결 원본 파일에 쓰지 않는다.

## 5. 검토 artifact 결합

아래는 이 검토에서 실제 확인한 bytes다. 최종 동결 manifest가 최종 실행 결합의 기준이며,
나중에 관련 소스가 바뀌면 이 표만으로 같은 검토를 받았다고 표현하면 안 된다.

| 파일 | SHA-256 |
|---|---|
| `derive_off.py` | `abb61d348a5cb12e5bf09dd77fa3879e8d5f733693bc82e0242a28a592635dba` |
| `runtime_off.py` | `da687991cdfc75beb70b3413a9c884ed30c231e4af59c3081aaa72d2258b664a` |
| `bindings.py` | `6eee70b72b66114c9451fce849948edda7768a9b12a5ac0e0d43183e6fec7c3a` |
| `ERASURE_MAP.json` | `997aa528c1c96260d6dcb3c0bd6ce5be0ae20b64173f7d89bfc8c5129ba09e73` |
| `counterexamples.py` | `2f24c13701cfc325f77743da661d639f7a38178ccf00d95c1dd54c7cfbfd4783` |

Manifest는 채택한 함수 안에서 P6 14개, P8 48개의 제거 위치를 기록한다.
이 수는 제거한 CPU 명령 수·표본 수가 아니다. 별도로 아예 채택하지 않은 cost/action/
finish helper와 wrapper 전체까지 포함한 총 삭제 문장 수라고도 부르지 않는다.

## 6. 동결 전에 남은 실행 gate와 주장 경계

새 실험 전에 별도 감사에서 개발 입력의 매-prefix Obs/π, 실제 stage call과 전체
snapshot 검증의 동등성, 원래 Phase08 계측 경로 결합, immutable/early-exit/capacity를
확인해야 한다. 수학 검토만으로 실행 gate를 통과했다고 대체하지 않는다.

시간의 주 비교는 반드시 off fresh→off selective다. 네 경로를 함께 측정하더라도
`T_on−T_off`는 독립 CPU 부품의 정확한 비용 분해가 아니다. 보존 정리는 속도 부등식을
함의하지 않는다. 현재 자료로도 모든 유한 stream의 무손해, 과거 인기 고착 해결,
대부분의 실제 대화 개선을 증명할 수 없다.

외부 자연어 의미·일반적 미완료 요청·실행 증거·LLM 요금/품질·외부 reader·동시 실행·
운영 성능은 검증하지 않았다. 새 평가의 결과를 보지 않은 상태에서 이 검토를 마친다.
**SOOM 운영 변경 없음.**
