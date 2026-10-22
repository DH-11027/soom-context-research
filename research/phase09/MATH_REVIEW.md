# Phase09 동결 전 수학·의존성 검토

검토자: 주 구현자와 역할을 분리한 동일 모델 에이전트.
최초 문서화: 2026-10-22 11:56 UTC / 20:56 KST 이후.
외부 독립 검증이 아니다. 새 Phase09 holdout 원문·builder·gold·결과는 읽지 않았다.

## 읽기 범위

직접 기준은 Phase08 공개 완료 commit
`efba3224dd09d5c5e2bf9d9be11734fa10b32502`다.
Phase08 `HANDOFF_BACK.md`, `PROTOCOL.md`, `THEORY.md`,
`POSTFREEZE_REVIEW.md`, `DATA_REVIEW.md`를 지정 순서로 열었으며, 도구 출력이
잘린 문서는 개별로 다시 읽었다. 이어 `runtime.py`, `frozen.py`, `evaluation.py`,
`development.py`, `MATH_REVIEW.md`, Phase07 `baseline.py`, `cached.py`,
Phase06 `scoped.py`, Phase05 revision02 `engine.py` 전체를 읽었다.
Phase07 `study.py`에서는 PARITY와 public/render 함수 위치를 확인했다.

저장소 전체나 과거 모든 실험을 검토했다는 주장은 하지 않는다. Phase08 전체
재현·원시 행 재집계는 별도 감사 담당자의 작업이며 이 문서의 직접 실행과 구분한다.
기존 동결 파일은 수정하지 않았다. 이 역할이 작성한 새 파일은 THEORY와 이 문서다.

## 1. 핵심 발견

Selective의 `cost`는 정책과 의미로 되먹임되지 않는다. 장부를 읽는 곳은 다시
장부 또는 보고를 만드는 곳이다. 삭제 가능한 `peak_*`와 삭제할 수 없는
`retained_bytes`를 구별해야 한다. `hits`는 계수이지만 victim weight의 입력이므로
삭제할 수 없다. `ACTION_WEIGHT*WARM_ACTIONS`도 실제 surplus 상수로 남아야 한다.

Fresh의 방문별 UTF-8 encode는 size 관측만을 위한 것이므로 source-byte 장부와
함께 삭제 가능하다. Snapshot 직렬화·UTF-8·SHA256, evidence 렌더는 별개의
실제 검증·출력 계산이며 삭제할 수 없다. Selective에는 exact raw key와 L,C,R이
정책 입력이므로 대응 encoding이 살아 있다. 이 비대칭 자체가 새로운 성능
결과를 필요로 하는 이유다.

조건부 prefix 보존 정리, Obs·π, 입력·자원·예외의 가정, 시간 산술과
유지해야 할 이전 반례는 [THEORY.md](THEORY.md)에 기술했다.

## 2. 직접 실행한 작은 hit-count 반례

2026-10-22 개발 중 아래 코드를 고정 Phase08 runtime에 실행했다. 새 holdout을
열거나 timing을 측정하지 않았다. 이 코드는 source를 수정하지 않고 mutant의
hit만 의도적으로 지워 final-answer-only 검사의 허점을 보인다.

```python
import sys
sys.path.insert(0, 'research/phase08')
import runtime as r
import development as d

prefix = '표현 연습:「'
suffix = '」라는 문장을 써봤어. 약속은 그대로야.'

def quote(n, letter):
    return prefix + letter * (n-len((prefix+suffix).encode())) + suffix

def public(n, letter, i):
    texts, gold = d.initialized()
    return d.step(texts+[quote(n,letter)], gold+[d.event('noop')], i)['public']

original, mutant = r.SelectiveCache(), r.SelectiveCache()
observations_equal = []
for i,(n,letter) in enumerate([(20000,'a'),(30000,'b'),(20000,'a'),(21000,'c')]):
    if i == 3:
        for entry in mutant.entries.values():
            entry['hits'] = 0
    a = r.run(public(n,letter,i), original)
    b = r.run(public(n,letter,i), mutant)
    observations_equal.append(
        {k:v for k,v in a.items() if k != 'cost'} ==
        {k:v for k,v in b.items() if k != 'cost'})
assert observations_equal == [True]*4
assert [len(k[1]) for k in original.entries] == [20000,30000]
assert [len(k[1]) for k in mutant.entries] == [30000,21000]
assert original.next_order == 2
assert mutant.next_order == 3
```

실측 deterministic 값: context C=93, payload R=154,
A=(b=19,689,e=20,327,h=1), B=(b=29,689,e=30,327,h=0),
C=(b=20,689,e=21,327). 네 번째 질문 정상 writes/evictions는 0/0,
mutant는 1/1이었다. 의미 반환 필드가 모두 같아도 정책 상태와 미래 전이는
달라질 수 있음을 4-step에서 확인했다. 비교한 의미 필드는 반환 필드의 `cost`
제거본이며, 이 반례에서 각 방법의 selected와 원문이 같으므로 렌더도 같다.

## 3. 동결 전 최종 구현 검토

초안 후 `erase.py`, `bindings.py`, `execution.py`, `off_fresh.py`,
`off_selective.py`, `erasure_manifest.json` 전체를 직접 읽고 원본과 대조했다.
`python research/phase09/erase.py --check`를 직접 실행해 통과했다.

- Transformer는 source-specific 삭제이며 일반 dead-code optimizer가 아니다.
  삭제된 Assign/AugAssign/action은 보존값에 데이터를 돌려주지 않는다.
- Chained init에서 peak 두 target만 지우고 `retained_bytes=0`을 보존한다.
  `next_order`, hits saturation, lengths, exact keys, stage 값과 payload 길이를 유지한다.
- Surplus의 64와 metadata allowance 80, 용량·entry 수, victim 정렬의 정수
  교차곱·tie·전체 계획 후 mutation 순서가 그대로다.
- Fresh `size` 삭제 뒤 남아 있는 의미 경로에는 size 참조가 없다.
  Snapshot JSON 직렬화·UTF-8·SHA256과 seq 우선 검증 순서는 남는다.
- Selective의 raw encode는 짧은 bypass를 포함한 기존 모든 방문에서 남는다.
  Lazy encode, 새 parser, admission, replacement, 자료구조 최적화는 추가하지 않았다.
- Generated off 함수에 cost, action, perf_counter, new_cost, finish 이름이
  남지 않는 AST 확인이 있다. 내부 timer와 보고 경로는 호출하지 않는다.
- 주 timing 호출은 static off 함수다. AST 생성·gold 평가·관찰 재렌더 감사는
  timed workload 함수의 내용이 아니다.
- On은 원래 P8 `evaluation.run`을 직접 호출하므로 재구현 계측판이 아니다.
  Off fresh는 P6의 `text_scoped`만 사용한다. 다른 method가 파일에 남아 있다는
  이유로 그 경로도 비계측·검증됐다고 주장하지 않는다.

| 검토한 파일 | SHA-256 |
|---|---|
| `erase.py` | `249c89f909658c8d6bdb4d6d4e8118034c30e79517453eae96f91b0f76394971` |
| `off_fresh.py` | `6e15bec049362c5d5c3464331337987770882d70baf4b82b8fe321ff85771ea9` |
| `off_selective.py` | `f3b8e770335d2866b2bdb88bdc34ed6cb6f04ad1f62e31ba77794a8985879e84` |
| `erasure_manifest.json` | `b6c97eb68dd49ba453aa0cf45160e2e9d9163596b1971bbfcf318936a839e29b` |
| `execution.py` | `da222c2511c5b033aa4d7b640e0e59c6a2bef657ddeeda637ae75b88272b6dab` |
| `bindings.py` | `8c238b3e536c8bbbd6e38dd85e8d0eb701d6c39916b32fab2ca66af970b6ccd6` |

검토 범위에서 E9의 데이터 의존성 계약을 깨는 삭제를 찾지 못했다. 전체
Python 의미의 자동 정형 검증·임의 예외 동등성·CPU 가속 증명은 하지 않았다.

## 4. 보존한 반례 실행기

[counterexamples.py](counterexamples.py)는 새 자료를 읽지 않고 두 잘못된
변환을 검사한다. `counterexample_results.json`은 동결 전 실행 결과다.

```bash
python research/phase09/counterexamples.py --output /tmp/phase09-counterexamples-new.json
```

첫 mutant는 `get`에서 hit 갱신을 생략한다. §2의 초기 직접 실험과 최종
resident 결과는 같지만, 실제 누락 시점인 3번째 질문부터 π 불일치를 검출한다.
네 의미 결과는 여전히 같고 4번째에서 resident 집합이 갈라진다. 실제 생성된
비계측판과 원본은 네 prefix 모두 Obs·π가 같다.

두 번째 mutant는 같은 문자 길이만으로 resident 값을 돌려준다. 긴 deep noop을
먼저 보관하고 같은 길이의 해석 불능 원문을 넣으면 정상은 `opaque_fallback`,
mutant는 `certified_model`로 갈라졌다. 길이 필터 양성을 exact equality로 대체하면
의미 관찰까지 실패한다. 이는 Phase08의 기존 경계가 계측 제거 중에도 필요함을
보인다. 실제 on/off erasure 실패는 0이었다.

반례 실행기의 SHA-256은
`cdb7dbcefe476dd24a3005f3a980e8e70b8af5c0571c9a889db68e6b1df6ba1a`다.
새 holdout/builder/gold/결과는 이 문서 완료까지 읽지 않았다.

## 5. 동결 전 timing·통계 계약 추가 검토

새 성능 결과를 보기 전에 `benchmark.py`, `PROTOCOL.md`, `run_study.py`를
읽고 실제 시간 구간·반복·집계와 문서가 일치하는지 확인했다.

- 주 구간은 external `perf_counter_ns` 한 쌍 사이의 전체 workload 3회다.
  Cache는 매 stream마다 생성·파괴되고 이 작업은 구간 안에 있다.
  정적 코드 생성, import, 자료 로딩, gold 평가, 정확성·상태 감사는 밖이다.
- 각 interval 전 GC collection은 밖에 있고 정상 GC는 안에서도 켜진다.
  이 구분은 protocol에 기록되어 있다. Parser cache cold와 CPU/OS cold를
  구분한다. Primary timing에 monkeypatch/profiler를 넣지 않는다.
- 두 full-workload warmup의 값을 보존하되 추정량에서는 제외한다.
  본 측정은 40 round ×4 방법 ×3 replay이며, 결과가 유리해질 때까지
  반복하는 중단 규칙이 없다. 별도 재현은 정해진 다른 order seed 1회다.
- 주추정량 `exp(median(log(S_off/F_off)))`와 marginal method 시간 중앙값의
  비율은 다를 수 있다. 두 값을 따로 기록하므로 최종 주 퍼센트도 주추정량을
  사용해야 한다. Stream/cold 8회 기술 통계는 다른 실행이며 주시간의 정확한
  additive decomposition으로 해석하면 안 된다.
- Four-round order-balanced cycle 전체 10개를 단위로 복원 추출하는
  bootstrap 20,000회는 고정 workload의 반복측정 불확실성이다.
  질문·대화·stream의 모집단 표본 불확실성이 아니다. Cycle 교환가능성,
  장기 host drift 미포함, 10 cycle의 작은 수라는 한계가 명시돼 있다.
- 3% practical margin과 원본·별도 재현 모두의 상한<0.97 조건은 실제 코드·
  protocol과 맞는다. 이 판정은 distribution-free 성능 보증이나 실제 대화
  모집단의 동등성 검정이 아니다. Secondary 비교에 독립적인 다중가설 유의성을
  주장하지 않는다.

자료를 열거나 시간을 재지 않고 Williams order를 직접 검산했다. 각 위치마다
네 방법이 1회씩 나오고, **round 내부** ordered adjacency 12쌍은 각 1회다.
Round 경계를 넘는 adjacency까지 완전 균형이라는 뜻은 아니다.
또 인위적인 40개 paired ratio가 모두 0.9 / 1.0 / 1.1인 세 산술 입력을
`paired_summary`에 넣어 각 bootstrap 구간이 그 ratio에 수렴하고 각각
speedup / within-margin / slowdown 판정이 되는지 확인했다. 실제 workload
timing이나 추가 성능 표본을 만든 검사가 아니다.

검토 중 두 설명·증거 보존 문제를 전달했고 동결 전에 반영된 것을 확인했다.
첫째, 원래 docstring의 "evaluator import 없음"은 실제 bindings가 원본 P8
evaluation wrapper를 import한다는 사실과 맞지 않았다. 최종 문구는 import는
timing 전에 있고 gold assessor 실행은 timed workload에 없다고 구분한다.
둘째, main raw samples가 종료까지 메모리에만 있던 것을 수정해 각 완료 round
뒤 progress 파일에 warmups·seed·원시 rounds를 저장한다. 따라서 후속 diagnostics
중 중단되어도 완료된 주측정은 남는다. 중단 순간의 미완료 interval까지
보존한다는 주장은 하지 않는다.

| 검토한 timing 파일 | SHA-256 |
|---|---|
| `benchmark.py` | `8b681bdc43e16b7a6829e3c44a86943051e659086f337917c20315dd9b074742` |
| `PROTOCOL.md` | `afbb5ca7fe0d35d44584a2b351cb5d873f1bfb778d7728b73e15e1b14cd5adad` |
| `run_study.py` | `46b415384651ef1c445c10018799ad8cd4e0ed9427d471d558e160f7c8c43a9d` |

검토 범위에서 주시간 계산의 치명적인 오류나 문서와 다른 유리한 표본 선택을
발견하지 못했다. 새로운 Phase09 corpus와 성능 결과는 열지 않았다.
