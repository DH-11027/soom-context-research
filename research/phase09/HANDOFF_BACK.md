# Phase09 반환 — 정책을 보존하는 계측 제거와 실제 시간의 부정 결과

작성: 2026-10-23. 주 구현·통합 연구자와 수학 검토자, 평가기·재현 감사자,
자료 작성자를 나눈 **동일 모델 연구**다. 외부 독립 검증이 아니다.

**완료 결론:** 계측판과 비계측판의 매-prefix 의미 관찰·정책 상태를 보존하는 보수적
계측 제거를 정의·구현·검사했다. 그러나 새 고정 합성 workload에서 주 비교
`fresh_uninstrumented → selective_uninstrumented`의 전체 실행시간은
원본 **+23.5945%**, 한 번의 별도 재현 **+15.8004%**였다. 사전 5% 실질 개선 가설은
두 실행 모두 기각됐다. 실제 파서 호출과 입력 bytes를 줄였다는 사실은 실제 시간
개선의 증명이 아니었다. **SOOM 운영 변경 없음.**

**GitHub 전달:** [PR #6](https://github.com/DH-11027/soom-context-research/pull/6),
open / unmerged. 연구 payload 공개 commit은
`68bec47a04850c19a1abea0425113cb0955ddd81`이며 로컬 payload
`77b441d2be35721d62373ccb1fcc982c5f8f413d`와 전체 Git tree
`9eb8c6d731ea97d4a34fb3d93953654f54090f10`이 정확히 같음을 원격 fetch 후 확인했다.
이 문단과 [DELIVERY_RECEIPT.json](DELIVERY_RECEIPT.json)은 그 확인 뒤 추가한 전달 기록이다.
PR의 최신 head에는 이 전달 기록도 포함된다. 연구 코드·자료·실험 결과는 바꾸지 않았다.

## 출발 상태

### 기준 commit과 현재 원격 상태

- 저장소: <https://github.com/DH-11027/soom-context-research>
- 직접 읽기·재현 기준: **`efba3224dd09d5c5e2bf9d9be11734fa10b32502`**.
- Archive 기준: `780891f6c147cfd3c1a3b0d065792776aaa525f3`.
- Phase07 완료: `6da051c0132811184ecf39975d7ff647a1f47842`.
- Phase08 로컬 freeze: `4a128204cad4abbf374fea7326b6c844f800812f`.
  공개 완료 commit과 다르며 원본 bundle의 Git 객체를 확인했다. 외부 사전 등록이 아니다.

처음 PR #1–#3의 상태를 확인했고, 최종 전달 시 전체 PR 목록을 다시 확인했다.
확인 당시 #1–#5는 모두 **open / unmerged**였다.

| PR | Head branch | Base branch |
|---|---|---|
| #1 | `research/phase06-scoped-opaque` | `main` |
| #2 | `research/phase07-parse-reuse` | `research/phase06-scoped-opaque` |
| #3 | `research/phase08-cost-aware-reuse` | `research/phase07-parse-reuse` |
| 기존 #4 | `research/phase09-instrumentation-erasure` | `research/phase08-cost-aware-reuse` |
| 기존 #5 | `research/phase10-time-prediction` | `research/phase09-instrumentation-erasure` |

**전달 중 발견한 충돌:** 이번 원본 실험과 별도 재현이 모두 끝난 뒤에야 기존 다른
Phase09/Phase10 branch와 PR #4/#5를 발견했다. 그때 주 연구자가 PR 메타데이터·본문
일부와 기존 Phase09 반환 문서의 첫 부분을 확인했다. 이번 동결 설계·코드·자료·임계값은
그 결과를 읽기 전에 정해졌다. 기존 연구의 구현·실험은 재현하거나 합치지 않았다.
이번 작업을 저장소 최초 Phase09라고 부르지 않는다.

기존 branch를 보존하기 위해 이번 전달 branch는
**`research/phase09-instrumentation-erasure-20261023`**, base는 지정된 Phase08의
**`research/phase08-cost-aware-reuse`**로 정했다. 별도 sibling 연구다. 기존 연구 branch
덮어쓰기·강제 push·PR merge·main 변경은 하지 않는다. 상세 확인 기록은
[DELIVERY_CONTEXT.json](DELIVERY_CONTEXT.json)에 있다. 공개 완료 commit/PR 번호는
그 PR의 head와 전달 영수증에서 확인하며, 아래 로컬 freeze와 혼동하지 않는다.

### 읽기와 검사의 경계

주 연구자는 지정 순서로 Phase08 `HANDOFF_BACK.md`, `PROTOCOL.md`, `THEORY.md`,
`POSTFREEZE_REVIEW.md`, `DATA_REVIEW.md`를 인수했다. 직접 구현 검토의 중심은
Phase08 `frozen.py`, `runtime.py`, `evaluation.py`, `run_study.py`와 Phase06의
`text_scoped` 경로다. 반환 형식은 `docs/RETURN_TEMPLATE.md`를 따랐다.

| 구분 | 실제 범위와 증거 |
|---|---|
| 주 연구자 직접 읽기·작성 | 위 Phase08 인수 문서·핵심 경로, Phase09 변환기·runtime·benchmark·protocol·반환 문서, 동결 후 새 자료 작성 기록·분포·요약·재현 검토 |
| 수학 역할의 소스·증명 검토 | P6 scoped/P7 fresh wrapper/P8 cache·evaluation의 의존성, Phase09 erasure map·생성 소스, 두 작은 반례. 새 holdout·성능 결과는 읽지 않음. [MATH_REVIEW.md](MATH_REVIEW.md) |
| 평가기·재현 역할 | Phase08 run/evaluation/runtime/frozen, P7 baseline/cached, P6 scoped, archive·hash·결정적 재현, Phase09 상태·호출 감사와 원시 재집계. [INHERITANCE_AUDIT.md](INHERITANCE_AUDIT.md), [EVALUATOR_REVIEW.md](EVALUATOR_REVIEW.md) |
| 자료 작성 역할 | 공개 문법·설계를 공유하되 구현자가 동결 전 열지 않은 새 자료·builder·typed gold 작성. 동결 후 자기 자료의 분모·중복·분포 재검토. [HOLDOUT_AUTHOR.md](HOLDOUT_AUTHOR.md), [DATA_REVIEW.md](DATA_REVIEW.md) |
| 프로그램으로 검사 | Phase08/09 hash·builder 재생성·원시 행·gold 적용 집합·정책 상태·실제 호출 trace·timing 재집계. 모든 원시 행을 사람이 수기로 읽었다는 뜻이 아님 |
| 확인하지 않은 것 | 저장소 전체의 모든 과거 실험 재실행, 기존 별도 Phase09/10 재현, 외부 reader의 자연어 의미 판정, 실제 SOOM·LLM 평가 |

### Phase08 출발점 재현과 새로운 관찰

[INHERITANCE_AUDIT.md](INHERITANCE_AUDIT.md)의 명령을 새 `/tmp` 출력 경로에서 실행했다.
Archive 59개 파일·18개 동결 소스 결합, Phase08 freeze, builder와 bundle 검증이 통과했다.
결정적 결과 **5파일 byte-identical**, 원시 주평가 1,728행과 회귀 5,424행의 재집계
불일치 0이었다. 기존 수치를 정정할 근거를 발견하지 않았다.

Phase08의 이번 계측 경로 재현은 fresh **61.835218 ms**, selective **70.742949 ms**
(+14.4056%), no_directory **75.594985 ms**였다. Directory의 상대 시간 순서는
Phase08의 기존 두 관측과 뒤집혔다. 새 관측을 남기되 기존 결과를 교체하지 않는다.
이는 directory의 CPU 우월성이나 열등성을 증명하지 않는다. Phase08의 P8 합계 이득,
다수 stream의 손해, 긴 noop family 지배, gain 거절 0이라는 해석 경계도 그대로다.

## 이번 가설과 계약

### 하나의 중심 가설과 선택 이유

**H9:** Phase08 정책·용량·임계값을 고정하고 의미 관찰·전체 검증·정책 상태를 보존하는
계측 제거를 수행하면, 새 고정 합성 workload에서 selective가 fresh보다 cold 포함
전체 실제 실행시간을 실질적으로 줄인다.

Phase08에서 작업점수와 시간이 어긋났기 때문에 정책 재튜닝 전에 실행 경로의 보고
작업을 분리하는 것이 직접적인 다음 질문이었다. 자연어 의미 일반화도 미해결이지만
동시에 추진하지 않았다. H9의 **5%** 실질 개선선과 판정 규칙은 새 결과 전에 동결했다.

입력은 현재 `records`, ordered `entities`, `query`, `snapshot`, `parser_namespace`다.
미래 반복·gold·family·정답·종료 시점은 selector에 전달하지 않는다.

### Obs와 π: 답 하나보다 강한 보존

\[
Obs(x,r)=\bigl(r\setminus\{cost\},\;RenderUTF8(x,r)\bigr).
\]

`cost`를 제외한 모든 결과 필드의 **존재 여부와 값**, 실제 근거 렌더 bytes를 보존한다.
`status`, `reason`, `prediction`, `selected`, `remaining_input_facts`, `scope_trace`,
`output_bytes`를 포함한다. 무결성 거절의 렌더 관찰은 빈 bytes다.

Fresh의 persistent policy state는 `()`다. Selective 상태의 투영 π는 보고 전용
cost/event/timer/peak만 지우고 다음을 모두 남긴다.

- Exact context/raw keys와 resident 순회·삽입 순서.
- Immutable cheap/scope/detail 값, 실제 payload 길이, entry 크기·문자 수.
- `hits`, `surplus`, `order`, `next_order`.
- 문자 길이 directory의 내용과 순서, retained bytes, 용량·directory 설정.
- Admission·victim·tie-breaking에 필요한 모든 상태.

각 유한 입력열의 매 prefix에서 요구하는 계약은

\[
Obs(Run_I(x_{1:t}))=Obs(Run_U(x_{1:t})),\qquad
\pi(S_t^I)=S_t^U.
\]

첫 식은 prefix가 낸 **관찰열**의 동일성이다. 최종 답만 같고 cache가 달라지는 구현은
계약을 만족하지 않는다. 감사에서는 실제 구조·bytes를 직접 비교했고 digest는 영수증이다.

### 지운 계산과 남긴 계산

| 계산 | 결정과 데이터 의존성 |
|---|---|
| 보고용 counter·control event·내부 timer·보고 합계·peak | 결과·정책의 소비자가 없어 제거 |
| Fresh 방문 원문의 `len(text.encode('utf-8'))` | source-byte 장부만 공급하므로 제거 |
| Selective 원문 UTF-8·context encoding·exact key 비교 | key와 실제 L/C 공급자이므로 유지 |
| 실제 payload encoding·immutable stage·R | 크기·surplus·보관 metadata에 필요하므로 유지 |
| L/C/R, surplus·victim 계산·정렬, hits 갱신, directory, 용량·삽입·삭제 | 정책의 일부이므로 유지 |
| Snapshot 전체 직렬화·hash·검증 | 실제 거절/진행 분기이므로 유지 |
| 현재 demand·query 내부 memo·상태 실행·copy·근거 렌더 | 의미 관찰의 일부이므로 유지 |

같은 UTF-8 연산도 데이터 의존성이 다르다. Fresh에서 없어진 것은 방문 원문 크기의
**통계용 encode**이며 전체 snapshot·출력 encode는 남는다. Selective의 `raw`는 key와
L을 공급하므로 남는다. 현재 구현은 일부 bypass 경로에서 동적으로 불필요한 raw까지
지연 제거하지 않은 **보수적 source erasure**다. 가능한 가장 빠른 동등 구현을 찾은 것이 아니다.

고정 상수는 `MIN_CHARS=256`, `MAX_BYTES=65536`, `MAX_ENTRIES=64`, `HIT_CAP=255`,
`META_BYTES=80`, `ACTION_WEIGHT=8`, `WARM_ACTIONS=8`이다. 특히

\[
b=L-C-R-8\times8=L-C-R-64
\]

는 그대로 남는다. 실제 action counter를 지워도 이 상수는 admission의 피연산자다.
자료구조·정책·replacement를 함께 변경하지 않았다.

### 보조정리에서 prefix 정리까지

[THEORY.md](THEORY.md)는 다음 증명 구조를 제공한다.

1. **보고 비간섭 E1:** 지운 문장은 보존 상태·분기·명시적 오류의 피연산자를 공급하지 않는다.
2. **Cache 연산 보존 E2:** 동일 exact key와 stage·L/C/R·hits·순서에서 동일 admission과
   victim 집합을 얻고, 동일 resident/directory/용량 상태로 전이한다.
3. **질문 보존 E3:** 전체 검증과 원래 요청한 parser 단계, 현재 실행·렌더가 동일하다.
4. **Prefix 귀납 E9:** 빈 cache에서 시작해 E2/E3를 반복하면 두 계약식이 모든 prefix에 성립한다.

가정은 유한 native JSON형 입력, UTF-8 가능 일반 문자열, 고정 순수 semantic code,
immutable 값, 호출 중 외부 변조 없음, 단일 스레드, 충분한 자원이다. 명시적 snapshot·query
거절과 음수 용량 오류는 유지한다. `MemoryError`, 비동기 중단, 사용자 정의 객체 부작용,
GC callback·객체 주소·CPU/OS 상태까지의 관찰 동등성은 주장하지 않는다.
이는 특정 소스의 조건부 증명이며 Python 전체의 기계 검증이나 파서의 자연어 의미 증명이 아니다.
시간 관계는 이 정리에서 따라오지 않는다.

### 먼저 찾은 작은 반례와 유지한 이전 경계

[counterexamples.py](counterexamples.py)의 실행 가능한 잘못된 삭제 mutant 두 개:

| 잘못된 삭제 | 반례와 결과 |
|---|---|
| 계측을 지웠으니 `ACTION_WEIGHT=0` | 문자 수 278, L=320, C=103, R=154인 한 quote. 원래 b=−1로 거절, mutant b=63으로 보관. 첫 답은 같지만 상태가 즉시 다름 |
| `hits`를 통계라고 지움 | 고정 용량 65,536에서 A,A,B. A 크기33,408·surplus32,750, B 크기34,408·surplus33,750. 정상 A의 hit가 1이면 가중값65,500으로 B를 거절; mutant는 A를 축출하고 B를 보관. 세 관찰은 같지만 prefix2부터 정책 상태가 다름 |

원래 정책의 결함을 발견했다는 뜻이 아니라, 잘못된 계측 제거가 더 약한 답 비교를
통과할 수 있다는 반례다. 상태 mutant 8개와 관찰 mutant 3개도 감사기가 검출했다.

Phase08의 경계도 유지했다. 양의 최초 투자 직후 stream이 끝나면 회수 보장은 없다.
Cheap를 이미 지불했다면 남은 단계의 절약만 세어야 한다. 과거 hit가 미래 인기를 보장하지
않으며, 같은 길이는 exact hit가 아니다. 개별 항목이 들어가도 동시 합은 용량을 넘을 수 있다.
D8은 같은 정책 상태에서 no_directory 대비 작업점수의 정리이며 CPU 시간 정리가 아니다.

## 변경과 재현

### 파일과 구현 경계

변경은 `research/phase09/`에만 있다. 원래 동결 코드·자료·결과를 고치지 않았다.

| 파일 묶음 | 역할 |
|---|---|
| `bindings.py`, `derive_off.py`, `runtime_off.py`, `ERASURE_MAP.json` | 정확한 이전 소스 binding, 명시적 AST erasure, 생성 소스와 삭제 목록 |
| `benchmark.py`, `run_study.py` | 네 경로 외부 timing, 동결·검증·실패 중단·저장 |
| `audit_equivalence.py`, `counterexamples.py`, `recount_results.py` | 직접 Obs/state/trace 감사, 반례, 별도 원시 재집계 |
| `PROTOCOL.md`, `THEORY.md`, `MATH_REVIEW.md`, `EVALUATOR_REVIEW.md` | 실행 전 동결한 계약·증명·평가 규칙 |
| `holdout_builder.py`, `HOLDOUT_AUTHOR.md`, `data/` | 미열람 새 자료·작성 경계·분포·hash |
| `freeze.json`, `freeze_commit.json`, `pre_evaluation.bundle` | 로컬 동결과 원본 Git 객체 |
| `inheritance/`, `development_results/`, `development_results_v2/` | 출발점 재현과 동결 전 개발 감사 원본 |
| `results/`, `reproduction_*.json`, `recount_results.json` | 주 결과·원시 행·시간, 별도 재현·재집계 |
| `POSTFREEZE_REVIEW.md`, `DATA_REVIEW.md`, `data_analysis.py/json` | 동결 후 해석·분모·중복·분포 검토 |

On 경로는 수정하지 않은 Phase08 `evaluation.run`을 직접 호출한다. Off fresh는 P6
default `text_scoped`에서 보고만 지웠다. 생성 파일에 남은 다른 legacy method는 이번
계약·시간 평가 범위 밖이다. `frozen_lazy`까지 비계측이라고 주장하지 않는다.
Off selective는 P8의 원래 stage 요청·cache 연산을 보존한다.

개발 감사는 P8 주평가432 + P8개발89 + 이전1,356 = **1,877 prefix / 7,508행**이다.
필드 존재 여부까지 Obs를 강화하고 fresh scope alias도 실제 호출 감사에 포함한 최종
개발 결과가 `development_results_v2/`이며 이전 개발 결과도 보존했다. 최종 실패 0,
11 mutant 검출, 예외 후 6개 monkeypatch binding 복원 확인을 마친 뒤 동결했다.

### 개발·새 평가 구분, 동결 시간과 hash

P8의 결과와 자료는 방향 선택에 썼으므로 **개발·회귀**다. 새 자료는 12 family×3의
**36 stream /622 step**이며 주 구현자는 동결 전에 raw/gold/builder를 열지 않았다.
동일 모델의 자료 작성자는 공개 설계·문법을 공유했다. 외부 blind 자연어 평가는 아니다.
자료 작성 중 722로 잘못 합한 합계를 쓰기 전 assertion이 잡아 622로 정정했다.
Horizon이나 gold를 성능 결과에 맞춰 변경하지 않았다.

- Seed: 자료·순서 `2026102309`, bootstrap `2026102310`.
- Local checkpoint: `0e62476d4ce4eedb48ec419a557537deae8e50b0`.
- Local freeze: **`b4a844efcaca73483f2c0d8b8339a1e352872745`**.
- Freeze tree: `eb51eca40e0231222cd47ca4a50ae9dd69f79be0`.
- 동결 시각: **2026-10-23 00:00:28.677080 UTC / 09:00:28.677080 KST**.
- 최초 평가: 00:00:58.655200–00:01:58.708859 UTC.
- 별도 재현: 00:02:35.114169–00:03:36.050339 UTC.

| Artifact | SHA-256 |
|---|---|
| `freeze.json` | `89713911799d7dc6e583d3aaf062bdfa24e3eba98cc7572ed53510adf941b3e8` |
| `runtime_off.py` | `da687991cdfc75beb70b3413a9c884ed30c231e4af59c3081aaa72d2258b664a` |
| `data/holdout.json.gz` | `bc56abfc5be274cd8ae6e0d574ad314bc3ddcff94999eac71d1cd6de81aafaad` |
| 압축 해제 JSON | `f24d7e73550ee87d03442b660f93f0cd234b409f516db3c983d8ca3ef080a732` |
| 원본 `results/timing.json` | `cedf9eade4c5a84a16ecaca829747cc7de7dc078e089ba819f8229b36abff340` |
| `reproduction_timing.json` | `714487b7a0307982879f658b5527e1d323f0efec8194840cb4c63e7fbf5bf2e5` |

모든 동결 소스·자료·baseline hash는 `freeze.json`, 산출물 hash는 각 receipt에 있다.
`pre_evaluation.bundle`은 원본 checkpoint/freeze 객체를 보존한다. Bundle 내부 ref명은
원격 이름 충돌을 알기 전 로컬 이름이며 객체는 그대로다. 다른 새 local ref로 fetch하면 된다.
**로컬 동결이며 외부 사전 등록이 아니다. GitHub 공개는 평가 이후다.**

### 실행 환경과 동일한 시간 구간

Python **3.12.14 / CPython / Linux 6.18.55 x86_64 / glibc 2.39**, 핵심 실험은 표준
라이브러리만 쓴다. `PYTHONHASHSEED=0`, GC enabled, threshold `(700,10,10)`이다.
허용 CPU 중 첫 CPU에 affinity를 고정했지만 독점 host·주파수 고정은 아니다.

네 방법 순열 24개를 각각 한 번씩 쓴 **24 complete block**이다. 각 timing 구간은
전체 workload 3회, 표시 시간은 1회로 정규화한다. 방법당 warm-up 1회는 제외한다.
매 stream/cycle마다 cache를 새로 만들어 생성·파괴와 cold 구축을 포함한다.
전체 검증·실제 파싱·key/payload·정책·현재 실행·동일 렌더를 외부 `perf_counter_ns`로 잰다.
Import·자료 로딩·public 입력 준비·gold 평가·감사·보고는 네 방법 모두 제외한다.

Off 주 timing에는 호출 counter·monkeypatch·event 기록을 다시 넣지 않았다. 실제 호출·
검증 bytes는 **별도 정확성 감사 실행**에서 관찰한 수치다. Profiler는 사용하지 않았다.
Parser cache cold를 CPU/OS cache cold라고 부르지 않는다. 이상치 삭제·유리한 재실행
선택·결과에 따른 반복 추가는 없고, 원본 뒤 별도 재현은 정확히 한 번이다.

### 재현 명령

저장소 root에서 실행한다. 출력 경로가 이미 있으면 **새 이름**을 쓴다.
`--freeze`는 새로 실행해 기존 freeze를 교체하지 않는다.

```bash
python tools/verify_archive.py
python research/phase08/run_study.py --verify
python research/phase08/holdout_builder.py --check
git bundle verify research/phase08/pre_evaluation.bundle

python research/phase09/run_study.py --verify
python research/phase09/derive_off.py --check
python research/phase09/holdout_builder.py --check
git bundle verify research/phase09/pre_evaluation.bundle

PYTHONHASHSEED=0 python research/phase09/run_study.py --run \
  --output /tmp/soom-phase09-next-reproduction \
  --compare research/phase09/results
python research/phase09/recount_results.py \
  --results /tmp/soom-phase09-next-reproduction \
  --output /tmp/soom-phase09-next-recount.json
python research/phase09/data_analysis.py --check
```

Bundle의 원본 freeze 객체를 별도 ref에 읽는 예:

```bash
git fetch research/phase09/pre_evaluation.bundle \
  research/phase09-instrumentation-erasure:refs/heads/phase09-local-freeze-evidence
```

원본/재현의 결정적 결과 **6개**가 byte-identical이었다: audit mutants, counterexamples,
holdout summary/rows, regression summary/rows. 시간과 날짜 영수증은 동일성 대상이 아니다.
재집계기는 runtime·평가기·benchmark summary를 import하지 않고 각 실행의 원시 자료에서
**306,537 assertion, mismatch 0**을 확인했다. Assertion 수는 독립 표본 수가 아니다.

## 실제 결과

### 공정한 네 경로 비교

다음은 **622 step 전체 workload**의 방법별 중앙 시간이다. 질문 한 건의 latency가 아니다.

| 방법 | 원본 ms | 별도 재현 ms |
|---|---:|---:|
| `fresh_instrumented` | 138.316 | 137.396 |
| `fresh_uninstrumented` | 109.357 | 110.859 |
| `selective_instrumented` | 146.225 | 147.029 |
| `selective_uninstrumented` | 134.894 | 131.813 |

주 추정량은 위 중앙값끼리 나눈 값이 아니라

\[
\widehat\rho=\operatorname{median}_{b=1}^{24}
\frac{T_{b,selective\_off}}{T_{b,fresh\_off}}
\]

이다. 10,000회 complete-block bootstrap의 조건부 95% 구간과 전·후반 일관성을
사전에 고정했다. 구간 상단<0.95이고 두 절반도<0.95일 때 실질 개선 지지,
하단>0.95이면 해당 가설 기각, 나머지는 미확인이다.

| 주 비교 | 원본 | 별도 재현 |
|---|---:|---:|
| Paired 중앙 비율 | 1.235945 | 1.158004 |
| 변화율 | **+23.5945%** | **+15.8004%** |
| 조건부 95% ratio 구간 | [1.145990, 1.312707] | [1.135810, 1.239072] |
| 전반 12 block 중앙 비율 | 1.235945 | 1.159013 |
| 후반 12 block 중앙 비율 | 1.255426 | 1.147986 |
| Selective가 빠른 block | 0/24 | 0/24 |
| 사전 5% 개선 판정 | **기각** | **기각** |

두 구간 하단은 1도 넘는다. 이 관측 범위에서 작은 전체 speedup도 보이지 않았다.
다만 slowdown 크기는 두 세션에서 상당히 다르다. 구간은 고정 corpus·세션의 block
교환가능성을 가정한 근사치이며 시간적 상관·공유 CPU 변동을 배제하지 않는다.
새 대화 모집단·하드웨어 모집단의 신뢰구간이나 독립 대화 24개의 검정으로 표현하지 않는다.

동일 방법의 on→off paired 변화는 fresh **−19.60% / −19.28%**, selective
**−7.42% / −9.15%**다. Selective 자체의 5% 개선은 원본에서는 구간 상단 때문에
미확인, 재현에서는 해당 기준을 충족한다. 주 off/off는 모두 손해다.
`T_on−T_off`를 특정 counter·encode의 정확한 CPU 비용으로 귀속하지 않는다.
할당·GC·분기·cache locality·wrapper 제거의 상호작용은 분해하지 않았다.

### 보존, gold, 실제 호출

새 **622 prefix /2,488 raw rows**, 회귀 **1,788 prefix /7,152 rows**에서 계약·gold
실패 0이다. 회귀는 P8 432 + 이전1,356이며 새 독립 평가 분모에 합치지 않는다.
새 자료에서 다른 세 경로 대 fresh의 Obs 불일치 **0/1,866**, selective on/off의 직접
정책 상태 불일치 **0/622**, 두 on/off 실제 호출 trace 비교 불일치 **0/1,244**였다.

| 각 방법의 판정/검사 | 수치 |
|---|---:|
| `certified_model` | 565 |
| `ambiguous` | 21 |
| `opaque_fallback` | 15 |
| `integrity_failure` | 12 |
| `unsupported_query` | 9 |
| 실제 전체 이력 출력 | 24 |
| False certification | 0/565 |
| Containment 위반 | 0/592 |
| Selected-gold 공동 투영 실패 | 0/601 |

Gold 601은 invalid12와 membership 투영 미정의9를 제외한다. 유효·지원 질문도601이지만
invalid12와 unsupported9를 제외한 **다른 집합**이다. 교집합은592다. Gold의 unsupported9는
전체 이력 선택 검사이며 답변 성공이 아니다. 주변 답 포함과 공동 답집합 투영도 구별한다.
`certified_model`은 제한 typed 모형의 판정이다.

| 별도 호출 감사의 합계 | Fresh | Selective |
|---|---:|---:|
| 실제 cheap/scope/detail 실행 | 7,221 | 5,631 |
| 실제 parser 입력 bytes | 43,264,845 | 15,694,905 |
| 전체 snapshot hash 호출 | 614 | 614 |
| 전체 snapshot hash 입력 bytes | 16,314,040 | 16,314,040 |
| 출력 UTF-8 bytes | 282,813 | 282,813 |

호출 **−22.0191%**, parser 입력 bytes **−63.7237%**여도 시간은 늘었다. Hash614에는
유효610뿐 아니라 hash까지 수행하고 거절된 invalid도 포함된다. Parser 입력 bytes는
정규식이 실제로 훑은 bytes나 CPU instruction·물리 RAM traffic이 아니다.

계측판의 사후 장부는 fresh P8 **59,861,698**, selective **56,165,363**(−6.1748%)다.
P7는 **59,861,698→56,060,715**(−6.3496%), control actions는 **0→13,081**이다.
P8 감소/동일/증가는291/21/310 step, 최종 감소 stream은12/36이다. Gain admission
거절은0건이라 surplus gate 하나의 독립 기여를 식별하지 못했다. P8는 이번 주 시간
지표를 대체하지 않으며 LLM 토큰·요금·품질도 아니다.

### 새 자료 분포·중복·cold·stream 손익

Horizon은1/3/8/12/16/24/32를 포함한다. 원문은45–68,000 UTF-8 bytes,
19–51,982 codepoint다. 짧은 반복·churn, 긴 cheap/deep noop, 같은 길이 miss,
2/3/4항목 working set, phase shift, 정정·copy·reorder, namespace/entities 변화,
invalid/unsupported/recovery를 포함한다. `deep_finite_horizons`의 길이와 horizon은
함께 변하므로 두 요인의 독립 효과를 추정하는 완전 요인설계가 아니다.

유효 입력의 서로 다른 exact records 배열은 **264**, id/seq를 제외한 ordered raw
history는 **180**, gold601의 exact typed-event 배열은 **144**다. Noop 제거 후141이다.
직렬화 중복 통계이며 독립 프로그램 수나 의미 동치류 수가 아니다.

중복 방문을 포함한5,137개 원문 중256 codepoint 이상846개가 원문 bytes의 **97.51%**다.
긴 원문을 넣은7 family의370/622 step이 fresh P8의 **96.97%**를 차지한다.
마지막 비율은 해당 family **전체 비용**의 비중이다. 긴 원문은 제한 문법의 noop quote이며
복잡한 자연어 의미 추론 자료가 아니다. Working-set 원문 합은 fit14,000/34,000/54,000,
pressure73,000/75,000/82,000 bytes이며 context/payload/metadata를 제외한 설계 크기다.

별도 stream timing은8회 AB/BA, 구간당5cycle의 기술 통계다. 원본 **2/36**, 재현 **1/36**만
selective가 빨랐다. `working_set_fit-00`은 **−1.66%→+4.13%**로 부호가 뒤집혔다.
원본의 가장 좋은 stream도5% 개선선에는 못 미쳤다. 모든36개 시간표를
[DATA_REVIEW.md](DATA_REVIEW.md)에 남겼고 유리한 family만 새 주평가로 고르지 않았다.

36 stream 최초 step을 모은 별도 cold workload(8pair×10cycle)는 **+47.04% /+44.02%**였다.
주 timing도 이미 cold 구축을 포함하므로 이를 추가 비용처럼 다시 더하면 안 된다.
이 숫자도 질문 한 건의 latency가 아니다. Stream별 다중비교나 별도 독립성 추론은 하지 않았다.

## 해석과 다음 차례

### 지지·기각·미확인

| 판정 | 주장과 범위 |
|---|---|
| 조건부 증명 및 실행 증거로 지지 | 명시한 소스 erasure는 가정 아래 Obs와 정책 projection을 보존한다. 새/회귀 자료의 직접 state·trace 감사와 재현이 일치했다 |
| 고정 자료·환경에서 기각 | 비계측 selective가 비계측 fresh보다5% 이상 전체 시간을 줄인다는 H9. 두 실행 모두24block 전부 느렸다 |
| 관측으로 확인 | 계측 제거 자체의 중앙 시간 감소, parser 호출·입력 bytes 절약, 동일 snapshot·출력. 각각의 실행·분모를 구별한다 |
| 미확인 | Slowdown의 정확한 원인별 CPU 분해, 가장 빠른 동등 selective 구현, 다른 입력분포·Python·하드웨어의 성능, selective 재사용 일반의 가능/불가능 |
| 미실행 | 외부 자연어 의미 정확성, LLM 토큰·요금·답변 품질, 미완료 요청·실제 실행 증거의 일반적 보존, 외부 reader 독립 검증, concurrency·물리 RSS·운영 적용 |

동결 뒤 정책·자료·gold·라벨·threshold·반복 수를 바꾸지 않았다. 새로운 성능 실험을
늘려 부정 결과를 대체하지 않았다. 결과를 설명하는 사후 분석은 별도 문서로 표시했다.

### 다음 연구자가 먼저 재현하거나 반박할 부분

먼저 `--verify`, builder `--check`, bundle 검증과 원시 재집계를 수행하고, 새 경로에서
한 번의 전체 재현으로 결정적6파일을 비교한다. 그다음 final answer만 보는 약한 검사가
아닌 π의 완전성, fresh UTF-8 encode의 보고 전용 의존성, selective의64·hits·순서 유지,
명시적 early exit와 current copy 실행을 반박해 보는 것이 우선이다.
새 플랫폼 시간 차이는 기존 raw 결과를 교체하지 말고 별도 세션으로 보고한다.

### 다음 한 가지 가설

**동일 정책과 prefix 계약을 유지하면서 selective raw UTF-8 생성만 경로별로 지연하면,
이번 보수적 erasure보다 실제 시간을 줄일 수 있는가?**

좁은 후보 조건은 문자 gate 통과 E, exact probe 필요 Q, 실제 miss에서 complete/global
bundle을 얻어 admission을 계산해야 하는 B에 대해 `E ∧ (Q ∨ B)`다. 짧은 bypass와
directory 음성·불완전 bundle에서는 raw/L을 쓰지 않을 수 있다. Directory 양성에서는
parse 전에 exact key가 반드시 필요하고, complete bundle이면 admission 성공 여부와
무관하게 정확 L을 계산해야 한다. `64`, payload, hit, victim·capacity는 그대로 둔다.
지연 분기의 추가 비용이 절약보다 클 수도 있으므로 이득은 미확인이다.

이번 결과에 맞춰 admission·replacement까지 바꾸지 말고, 새 계약·새 미열람 자료·동결을
갖춘 별도 한 단계로 검증한다. 현재 자료는 그때 개발 자료다. **SOOM 운영 변경 없음.**
