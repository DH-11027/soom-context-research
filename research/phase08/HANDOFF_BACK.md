# Phase08 연구 반환 — 선택적 순수 해석 재사용의 조건부 이득과 시간 한계

작성: 2026-10-22. `docs/RETURN_TEMPLATE.md`의 항목을 따라 작성했다.

**이번 단계의 결론:** 의미 선택기를 고정한 선택적 재사용은 새 합성 자료에서 실제 파서 실행을
12.52%, 사전 고정한 전체 P8 작업점수를 4.28% 줄였다. 그러나 이득은 36 stream 중
8개에 집중됐고, 전체 로컬 실행시간은 원본 +12.37%, 별도 재현 +15.21%로 늘었다.
따라서 제한된 비용 모형의 조건부 이득은 지지되지만 실제 속도 개선이나 범용 비용 우월성은
입증되지 않았다. 출력과 답변 범위는 그대로다. **SOOM 운영 변경 없음.**

## 1. 출발 상태

### 기준과 GitHub 상태

- 저장소: <https://github.com/DH-11027/soom-context-research>.
- 최초 archive 기준: `780891f6c147cfd3c1a3b0d065792776aaa525f3`.
- 직접 읽기·재현 기준: **`6da051c0132811184ecf39975d7ff647a1f47842`**, Phase07 완료 commit.
- 2026-10-22 전달 직전 다시 확인한 [Phase06 PR #1](https://github.com/DH-11027/soom-context-research/pull/1)은
  open/unmerged, base `main`, head `research/phase06-scoped-opaque`다.
- [Phase07 PR #2](https://github.com/DH-11027/soom-context-research/pull/2)도 open/unmerged이며,
  base는 Phase06 branch, head는 `research/phase07-parse-reuse`, head commit은 위 직접 기준과 같다.
- 새 branch는 `research/phase08-cost-aware-reuse`, PR base는 **`research/phase07-parse-reuse`**다.
  기존 branch를 덮어쓰거나 PR을 merge하지 않는다. 추가 파일은 모두 `research/phase08/` 아래다.

### 실제 읽은 자료와 역할

주 구현자는 Phase07 완료 commit의 `HANDOFF_BACK.md`, `PROTOCOL.md`, `THEORY.md`,
`POSTFREEZE_REVIEW.md`, `BOUNDARY_ANALYSIS.md`를 지정 순서로 읽었다. 이후
`baseline.py`, `cached.py`, `study.py`, `run_study.py`, 결과·동결 자료를 필요한 범위에서 확인했다.
별도 감사 역할은 `audit.py`, `POSTHOC_PROTOCOL.md`, `cost_boundary_probe.py`,
주평가·사후·재현 JSON까지 확인하고 원시 행을 재집계했다. 상세 읽기 범위와 실행 증거는
[INHERITANCE_AUDIT.md](INHERITANCE_AUDIT.md)에 있다.

의미·평가 계약 확인에는 Phase06 `scoped.py`, `evaluate.py`, `THEORY.md`,
`POSTFREEZE_LIMITS.md`와 Phase05 revision02 `engine.py`의 관련 구현을 사용했다.
새 자료 작성자는 기존 schema와 동결 문법을 읽되, 새 정책 구현·실행 결과를 보지 않고
원문과 typed gold를 작성했다. 수학 검토, 평가기·재현 검토, 자료 작성을 역할별로 분리했다.
**모두 같은 모델의 에이전트이며 공개 설계를 공유했다. 외부 독립 검증·외부 블라인드 자연어
평가라고 부르지 않는다.** 저장소 전체나 모든 과거 실험을 읽고 실행했다고 주장하지 않는다.

### Phase07에 대한 비판적 확인

다음 명령을 원본을 덮어쓰지 않는 새 경로에서 실제 실행했다.

```bash
python tools/verify_archive.py
python research/phase07/holdout_builder.py --check
python research/phase07/run_study.py --run \
  --output /tmp/soom-phase07-repro-for-phase08 \
  --compare research/phase07/results
python research/phase07/cost_boundary_probe.py \
  --output /tmp/soom-phase07-boundary-for-phase08.json
```

archive 59개 파일·18개 코드 결합 검증이 통과했다. Phase07의 결정적 결과 5개와 사후
경계 JSON이 원본과 바이트 단위로 일치했다. 1,200 raw row의 별도 재집계 7,272개
assertion도 통과했다. Assertion 개수는 평가 표본 수가 아니다.

Phase07의 fresh→LRU 결과인 실제 호출 2,292→750, P7 2,093,235→4,341,013
(+107.38%)를 재확인했다. 이번 환경의 시간은 18.779→25.758 ms(+37.17%)였다.
원본 +34.57%, 이전 별도 재현 +49.69%를 정정하거나 대체하지 않는다. 반복 질문 family의
시간 부호가 실행마다 바뀌는 문제도 남는다. **이전 수치의 정정은 필요하지 않았다.**

새로 명확히 한 계측 경계는 다음과 같다. P7의 `key_probe`는 get 시 논리적 전체 key를
한 번 계상하며 Python dict 내부의 모든 hash/equality 작업을 세지 않는다. 파서 입력 길이도
각 regex가 실제 읽은 바이트 수가 아니다. payload·metadata의 논리 크기는 실제 RSS가 아니다.
이는 원래 P7 정의를 바꾼 정정이 아니라, CPU·물리 메모리로 일반화할 수 없는 이유의 구체화다.

## 2. 이번 가설과 수학적 계약

### 하나의 주가설과 병목 선택

**H8:** 원래 의미 선택기와 검증을 유지하면서, 이미 관측한 순수 해석 결과의 단계·크기와
과거 재사용 정보만 사용하는 선택적 보관 정책이 새 합성 stream의 cold 비용을 포함한
전체 `P8` 합계를 frozen fresh보다 줄이고, 실제 파서 실행도 줄이며, 관찰을 보존한다.

세 조건 중 하나라도 실패하면 이 자료에서 H8을 지지하지 않도록
[PROTOCOL.md](PROTOCOL.md)에 고정했다. Phase07의 호출 감소만으로는 총비용이 늘었고,
사후 수식에서 1·2단계 재사용은 key 비용을 이길 수 없었다. 따라서 모든 hit를 늘리기보다
값비싼 complete bundle만 보관하는 방향을 한 단계 검증했다. 원래 자연어 의미 추출의
일반화 문제를 해결하는 연구로 바꾸지 않았다. 이번 시간 결과는 이제 실제 실행비 측정을
다음 우선 병목으로 삼아야 한다는 근거다.

### 입력·출력·허용 정보

입력은 현재 public의 records, ordered entities, query, expected snapshot과 실행 namespace다.
raw-only 경로에는 그 네 public 필드와 namespace만 복사한다. Gold AST, 정답,
family label, 미래 step, 미래 반복 횟수, gold 적용 여부는 전달하지 않는다.

보존 관찰은 현재 질문에 대한 상태, 선택 기록, 예측, 불확실성, snapshot 판정과 근거 렌더다.
파서 실행 횟수·시간·cache 장부는 개선 여부를 측정하므로 동등성 관찰에서 제외한다.
과거 상태는 exact key에 결합된 immutable cheap/scope/detail 값, payload 크기,
포화 hit 수와 보관 순서·크기뿐이다. 질문의 TOP, 최종 답, 선택 인덱스, copy 당시 값은 저장하지 않는다.

정확 key는 `(semantic fingerprint, namespace, ordered entities)`의 canonical bytes와
원문 UTF-8 전체다. 순수성, 의미 버전의 완전성, key 완전성, immutable 값, 동일 단계 요청 경로,
단일 실행 중 외부 변조 없음 아래 귀납적으로 원래 해석 값과 같다. Snapshot 검증, 현재 demand,
현재 상태 실행·copy, 렌더는 질문마다 유지된다. 이 조건부 관찰 동등성은 기존 파서의
자연어 이해 정확성이나 실제 실행 성공을 증명하지 않는다.

### 구현한 온라인 정책

1. 원래 검증 후 방문한 원문마다 유료 길이 gate를 적용한다. 256 Unicode 문자 미만이면 bypass한다.
2. 보관 후보의 문자 길이 directory에 같은 길이가 없으면 exact lookup을 건너뛴다.
   같은 길이는 hit 판정이 아니다. 양성인 경우 exact context와 원문 전체를 비교한다.
3. miss에서는 원래 경로가 요청하는 단계만 실제 실행한다. cheap가 `havoc`, scope가
   `(None, global)`이고 detail까지 실제 요청된 complete bundle만 후보로 삼는다.
   단계 수·payload 크기를 미리 공짜로 알지 않는다.
4. 실제 encode로 payload 길이 `R`을 얻은 뒤, 원문 길이 `L`, context 길이 `C`에 대해
   `b = L - C - R - 64 > 0`인 후보를 고려한다. 이는 query 전체의 이득 보장이 아니다.
5. 논리 보관 크기 `e=C+L+R+80`, 총 65,536·최대 64항목 한도를 지킨다. 부족하면
   기존 항목의 `w=(min(h,255)+1)b`와 `w/e`로 victim 계획을 만들고, 새 `b`가
   victim들의 `w` 합보다 클 때만 교체한다. 미래 빈도는 사용하지 않는다.

256·255·80·64·65,536과 가중치 8은 새 자료를 열기 전에 고정했다. 최적값이라고
주장하지 않는다. 길이 필터의 양성 결과가 exact equality를 대신하지 않으며, rejected 후보의
반복 횟수까지 추적하지 않는 정책이라 오래된 인기 항목이 새 항목을 막는 반례가 있다.

### 비용식과 증명 범위

P7은 그대로 유지했다.

\[
P7=\text{output}+\text{hash}+\text{parser\_source}+\text{key\_build}
+\text{key\_probe}+\text{value\_encode}+\text{payload\_read}+\text{cache\_write}.
\]

정책 판단·관리의 명시적 event 수를 `A`라 두고 주지표를 다음으로 동결했다.

\[
P8(\lambda)=P7+\lambda A,\qquad \lambda=8.
\]

P7은 논리 바이트 작업량, P8은 **가중 작업점수**다. 8은 CPU 또는 바이트로 보정한 환산율이
아니다. gate, lookup, stage 관측·읽기, payload 준비, 크기·점수·용량 검사, density 비교,
victim 계획, 삽입·삭제를 event로 센다. 이 장부가 모든 Python 명령·할당·GC·dict 충돌·
big-int bit 연산을 정확히 센다는 주장은 하지 않는다. 모든 실측 시간에는 계측도 포함된다.

원문 UTF-8 encode는 원래 fresh도 크기 관측을 위해 수행한다. 새 경로는 그 bytes를
key로 재사용하되 기존 P7 정의의 `L` key-build charge를 유지했다. 길이 directory가
피하는 것은 불필요한 exact key 준비·probe이며, 전체 원문 읽기·encode·snapshot 검증이
사라지는 것은 아니다. 검증 공유나 incremental snapshot은 구현하지 않았다.

이하 `Δ`는 `selective − fresh`의 비용 차이다. 완전 warm인 complete bundle 한 항목에서
query당 context 생성비를 제외하면

\[
\Delta P8=-L+C+R+8\lambda.
\]

따라서 `b`는 이 국소 warm surplus를 기준으로 삼지만 cold 구축비와 다른 항목은 별도다.
빈 cache에서 시작하고 한 short set과 한 deep global noop을 매 질문 모두 방문하며,
첫 directory 조회가 음성이고 문자 gate와 `b>0`을 만족한다고 하자. Query/context가 고정되고
최초 보관 후 계속 hit하며 eviction이 없는 두 기록 사례에서는 전체 차이가 다음과 같다.

\[
\Delta_T=(3-T)L+2TC+(T+1)R+(9T+16)\lambda.
\]

`T≤3`이면 길이만 늘려 전체 이득을 만들 수 없다. `T>3`에서 위 식이 음수여야 하며
동시에 용량 `C+L+R+80≤65,536`을 충족해야 한다. 현재 비용 모형·반복 구조의 식이지
실제 CPU의 정보이론적 하한이 아니다. 개발 감사에서 cold/warm 식의 잔차 0을 확인했다.

길이 필터의 별도 정리 D8은 `no_directory`와 비교한다. Exact text가 같으면 문자 길이도
같으므로 생략되는 조회는 확실한 miss다. Admission이 실제 장부 합에 의존하지 않는 고정
정책에서 resident 상태·stage·hit·파서 호출은 같고, 모든 `λ≥0`에 대해
`P8(selective)≤P8(no_directory)`다. **이는 fresh 또는 wall time에 대한 우월성 정리가 아니다.**

공통 snapshot 작업 `Σq Θ(Bq)`, 실제 miss 파서 계산비 `Σ p_s`, key와 payload의
길이 의존 작업은 남는다. 충돌 시 victim 정렬은 `O(N log N)` 비교이며 비교마다 계상했다.
`N≤64`는 물리 메모리나 무한 stream의 bit complexity 상한이 아니다. 자세한 가정·증명·
반례·선행 연구 구분은 [THEORY.md](THEORY.md), [MATH_REVIEW.md](MATH_REVIEW.md)에 있다.

## 3. 변경과 재현

### 파일 구성

| 역할 | 파일 |
|---|---|
| 고정 의미 로드와 새 정책 | `frozen.py`, `runtime.py` |
| 비교·평가·실행 | `evaluation.py`, `audit.py`, `run_study.py` |
| 개발 | `development.py`, `data/development.json`, `development_results/`, `DEVELOPMENT_AUDIT.md` |
| 새 자료와 작성 경계 | `holdout_builder.py`, `HOLDOUT_AUTHOR.md`, `data/holdout.json`, `data/holdout_manifest.json` |
| 동결 계획·수학·검토 | `PROTOCOL.md`, `THEORY.md`, `MATH_REVIEW.md`, `EVALUATOR_REVIEW.md`, `freeze.json`, `freeze_commit.json` |
| Phase07 재현·감사 | `INHERITANCE_AUDIT.md`, `inheritance/` |
| 주평가·회귀·시간 원본 | `results/` |
| 별도 재현·재집계 | `reproduction_receipt.json`, `reproduction_timing.json`, `recount_results.py`, `recount_results.json` |
| 사후 해석 | `POSTFREEZE_REVIEW.md`, `DATA_REVIEW.md` |
| 진입점·인수인계·동결 Git 증거 | `README.md`, `HANDOFF_BACK.md`, `pre_evaluation.bundle` |

모든 추가 파일은 Phase08 안에 있다. 기존 동결 파일과 결과는 변경하지 않았다.

### 데이터 구분과 동결

개발은 9 stream/89 step이다. Phase07 holdout 300 step와 사후 18 cell/144질문은 정책을
생각하는 데 사용한 개발 정보이며 새 독립 평가로 세지 않는다. Phase05 672질문과
Phase06 384질문도 역사적 회귀다. 주평가와 합쳐 성과 평균을 만들지 않는다.

새 자료는 seed **2026102208**, **12 family ×3 parameterization ×12 step =36 stream/432 step**다.
정책 구현자와 수학·평가 검토자는 동결 전 새 원문·라벨·builder를 열지 않았다. 작성자는 공개
문법·연구 설계를 공유했다. 새 자료가 운영 대화 분포를 대표하거나 외부 독립 표본이라는 뜻은 아니다.

- 로컬 checkpoint commit: `55714fd4e9b690309805767d17b48b22b4630891`.
- 로컬 freeze commit: **`4a128204cad4abbf374fea7326b6c844f800812f`**.
- Freeze 시각: **2026-10-22 11:19:06.451193 UTC / 20:19:06.451193 KST**.
- 첫 주평가 실행: 11:19:20.688 UTC부터. `freeze_commit.json`에 실행 직전 경계를 기록했다.
- GitHub 공개는 평가 후다. **외부 사전 등록이 아니다.**

| 파일 | SHA-256 |
|---|---|
| `freeze.json` | `885ff9ecf25c4df38410ab39a16ae922195e1ee5b7eb9da0501853f926a7c11a` |
| `runtime.py` | `d923f5f1a0012b5f70348ed4cfdd376791ac6e12b1af3ed7b663e4aab674de13` |
| `data/holdout.json` | `9f8c46a60d23eea8bea3f6dc7626908d4f74885a52b05d93d83c714ad6dc6613` |
| `results/holdout_results.json` | `73fa06ea9088847925a5d316d356d4fdafa717eb8bbe3606663876c2734787ce` |
| `results/holdout_rows.json.gz` | `fd0181c632e5692c8bdfd63516abffa87749dea80fff756cc3b74a5df78137ea` |
| `pre_evaluation.bundle` | `36c1c6eec57100cc79b005bbe2734566a71f2577bea328f5ced6c7a274528744` |

전체 source·자료·기준 결합 hash는 [freeze.json](freeze.json), 산출물 hash는 원본·재현 receipt에 있다.
직접 Git push의 HTTPS credential이 없어 GitHub connector의 Git object 전달을 사용한다.
그 API의 공개 commit SHA와 로컬 동결 commit SHA는 구별한다. 로컬 checkpoint/freeze 두 commit의
원본 Git 객체는 `pre_evaluation.bundle`에 보존했다. 이 bundle은 Phase07 기준 commit을
prerequisite로 요구하며 `git bundle verify`를 통과했다. 외부 공개 시각을 동결 시각으로 소급하지 않는다.

### 실행 환경과 재현 명령

Python **3.12.14**, CPython, Linux **6.18.55 x86_64**, glibc **2.39**.
핵심 코드·평가·재현은 Python 표준 라이브러리만 사용한다. LLM 호출은 없다.
저장소 root에서 존재하지 않는 새 output 경로를 사용한다.

```bash
python tools/verify_archive.py
python research/phase08/run_study.py --verify
python research/phase08/holdout_builder.py --check
python research/phase08/run_study.py --run \
  --output /tmp/soom-phase08-repro-new \
  --compare research/phase08/results
python research/phase08/recount_results.py \
  --output /tmp/soom-phase08-recount-new.json
```

로컬 동결 Git 객체를 확인하려면 다음을 추가로 실행할 수 있다. 새로운 ref만 만든다.

```bash
git bundle verify research/phase08/pre_evaluation.bundle
git fetch research/phase08/pre_evaluation.bundle \
  refs/heads/research/phase08-cost-aware-reuse:refs/heads/phase08-local-freeze-evidence
git show --stat 4a128204cad4abbf374fea7326b6c844f800812f
```

원본 후 별도 역할의 새 실행에서 결정적 **5개 파일이 모두 byte-identical**이었다.
시간과 시각 receipt는 동일성 비교에서 제외했다. 별도 summary 함수를 사용하지 않는
재집계는 새 1,728행·회귀 5,424행의 합계·분모·family·민감도·누적 손익분기점을 확인했다.
새 timing을 더 유리하게 얻으려고 반복 실행을 늘리지 않았다.

개발 감사에는 보존 50방문, 원본 P7 LRU와 새 계측 adapter의 10방문 동등성,
잘못된 출력 mutant 9개 검출, exact key·불변 값·현재 copy·무효 snapshot·용량·비용식
검사가 포함된다. 세부 분모는 `DEVELOPMENT_AUDIT.md`를 따른다. 회귀는 1,356질문이며
새 정확성·성능 표본으로 합치지 않는다.

## 4. 실제 결과

### 주 비교와 전체 비용

모든 방법이 같은 432 step, 매 stream 비어 있는 cache, 같은 원래 선택기·검증 경로를 사용했다.
주 비교는 항상 **fresh→selective**다. LRU는 더 비싼 비교군이며 그에 대한 개선을 주 성과로 대체하지 않는다.

| 합계 | fresh | Phase07 LRU | selective | no_directory |
|---|---:|---:|---:|---:|
| 실제 파서 실행 | 4,768 | 2,014 | **4,171** | 4,171 |
| 파서 입력 bytes | 21,831,216 | 18,095,159 | **13,204,284** | 13,204,284 |
| Snapshot 검증 bytes | 8,431,437 | 8,431,437 | 8,431,437 | 8,431,437 |
| 출력 UTF-8 bytes | 165,238 | 165,238 | 165,238 | 165,238 |
| Cache overhead proxy | 0 | 20,625,232 | 7,269,311 | 9,199,861 |
| Control actions | 0 | 27,306 | 6,741 | 6,785 |
| P7 | 30,427,891 | 47,317,066 | 29,070,270 | 31,000,820 |
| **P8, λ=8** | **30,427,891** | **47,535,514** | **29,124,198** | **31,055,100** |
| Fresh 대비 P8 | — | +56.22% | **−4.28%** | +2.06% |

Selective는 실제 호출 **12.52%**, 파서 입력 bytes **39.52%**, P7 **4.46%**를 줄였다.
추가 cache/control 7,323,239보다 절약한 parser source 8,626,932가 커서
P8가 **1,303,693** 줄었다. LRU는 호출을 더 많이 줄이지만 총비용은 더 크다.
이 차이를 LLM 토큰·요금·답변 품질이나 물리 RAM traffic의 변화라고 부르지 않는다.

Selective의 실제 complete bundle hit는 199건이며 각 3단계를 재사용해 597회를 줄였다.
Admission 시도 119, write 45, capacity 거절 74(개별 oversize 34 포함), eviction 3,
최대 논리 보관량 65,500, 최대 entries 12다. **Gain 거절은 0건**이므로 주평가에서
수치 surplus gate 하나의 독립 효과가 입증됐다고 해석하지 않는다.

### 이득의 분포와 실패

- 질문별 P8 감소 **100/432**, 동일 **21/432**, 증가 **311/432**다.
- Stream 최종 누적 감소 **8/36**, 증가 **28/36**다. 한 번이라도 이득을 지난 것은 10개이나
  `phase_shift` 2개는 다시 손해로 돌아갔다.
- Family 합계 감소는 **3/12**다. `long_deep_repeated` −3.09%, `working_set_fit` −16.22%,
  `working_set_pressure` −10.68%이며 나머지 9 family는 손해다.
- 첫 step 36개의 합은 **2,568,437→3,360,578(+30.84%)**다. Cold 구축비를 제외하지 않았다.
- `long_deep_single_use`는 실제 파서 실행을 줄이지 못하면서 P8 **+11.98%**다.
  `phase_shift`의 family 합도 **+3.87%**다.

긴 원문 여섯 family는 질문 절반이나 fresh byte proxy의 **97.50%**다. 두 working-set
family의 차이 **−1,839,957**과 나머지 열 family의 **+536,264**가 전체 이득을 만든다.
긴 원문은 모두 제한 문법의 noop quote다. 길이가 긴 자연어 의미 추론을 해결했다는 실험이 아니다.

432 step 중 유효 records 배열의 서로 다른 exact 값은 204개, id·seq를 제외한 ordered
원문 history는 168개, gold 적용 411 step의 exact typed-event 배열은 123개다.
이들은 명시적 직렬화 동일성 통계이며 의미 동치류·독립 프로그램 수가 아니다.
1,728 raw row는 **432 step ×4방법**이다. 1,728개 독립 대화로 세지 않는다.
자세한 중복·분포·family별 표는 [DATA_REVIEW.md](DATA_REVIEW.md)에 있다.

### 답변 범위와 정확성 분모

네 방법은 모두 다음과 같다.

| 판정 | 건수 /432 |
|---|---:|
| `certified_model` | 378 |
| `ambiguous` | 15 |
| `opaque_fallback` | 18 |
| `integrity_failure` | 12 |
| `unsupported_query` | 9 |
| 실제 전체 이력 출력 | 27 |

378/432=87.5%는 제한 모형의 단일값 판정 범위다. 실제 사실성·실행 성공 인증이 아니다.
전체 이력 출력은 opaque 18+unsupported 9이며 무결성 거절을 합하지 않는다.

- 후보 세 방법과 fresh의 관찰 불일치: **0/1,296** 비교.
- 방법별 false certification: **0/378**.
- 방법별 containment 위반: **0/402** 지원 gold 질문.
- 방법별 selected-gold 공동 투영 실패: **0/411**.
- Gold 제외: invalid snapshot 12와 의미 투영 미정의 membership 변경 9, 총 **21/432**.

Gold 적용 411건에는 unsupported 9의 전체 이력 선택 검사가 포함되므로 411건의 답변 성공이
아니다. 유효·지원 질문도 411건이지만 **다른 집합**이다. 주변부 답 포함과 selected-gold의
공동 투영 보존은 서로 다른 검사이며, 반환 product abstraction이 정확한 joint answer set이라는
주장도 아니다. Raw/digest만 받은 외부 reader의 독립 충분성 검증은 하지 않았다.

### Ablation과 가중치

`no_directory`는 같은 보관 정책에서 길이 음성 필터만 끈다. 두 방법의 resident exact
keys·순서·stage 값·payload·점수·hit·directory·용량을 432 step마다 replay하여 **0/432**
차이를 확인했다. Parser 호출은 둘 다 4,171이다. Directory는 exact lookup **276→234**로
42회를 피하고 P8를 **1,930,902(6.22%)** 줄였다. Filter 없는 방법은 fresh보다 P8가
2.06% 높고, filter가 있는 방법은 4.28% 낮다. 이 비교로 구별한 효과는 불필요한 key 작업이다.

고정 정책을 사전에 정한 가중치 0/8/32/128로 재채점하면 fresh 대비 **−4.46/−4.28/−3.75/−1.63%**다.
각 가중치에 맞춰 정책을 다시 최적화하지 않았다. 모든 가중치나 실제 CPU 비용에 대한 강건성은 아니다.

### 실제 시간과 역사적 회귀

| 전체 로컬 중앙값, ms | 원본 | 별도 재현 |
|---|---:|---:|
| fresh | 61.849 | 56.930 |
| LRU | 84.566 | 76.754 |
| selective | 69.497 | 65.590 |
| no_directory | 68.202 | 63.903 |
| selective 대 fresh | **+12.37%** | **+15.21%** |

두 실행 모두 전체 속도 개선을 관측하지 못했다. Directory는 논리 비용을 줄였지만
두 관측에서 `no_directory`보다 오히려 느렸다. 따라서 논리 key-work 감소를 CPU 가속으로
옮길 수 없다. 계측 event를 포함한 연구 경로의 시간이며, counters를 제거한 운영 경로의
성능이나 slowdown의 원인 분해는 측정하지 않았다.

7회 로컬 반복, 방법 순서 회전, 폐기 warm-up, 매 stream·반복 새 cache를 사용했다.
Cache 생성·검증·파서·정책·현재 추론·렌더 포함, import·자료 로딩·gold·LLM 제외다.
통계적 유의성 검정·하드웨어 일반화·CPU/OS cache 완전 초기화는 하지 않았다.

역사적 1,356질문(Phase07 300+Phase06 384+Phase05 672)은 보존 회귀다.
실제 호출 **7,153→7,153**, P8 **4,433,717→4,474,349(+0.9164%)**이며 새로운 호출·
비용 감소 질문은 0/1,356이다. 주평가의 긍정 수치와 합치지 않는다.

## 5. 실패·반례·남은 경계

작은 반례는 주평가 전에 만들고 [DEVELOPMENT_AUDIT.md](DEVELOPMENT_AUDIT.md)에 보존했다.

| 조건 | 결론 |
|---|---|
| 양의 최초 cache 투자 직후 stream 종료 | 미래 절약이 없어 fresh 이하의 보편 유한-stream 보장 불가 |
| Cheap를 먼저 지불한 뒤 남은 2stage lookup | 동일 P7 key 비용 계약에서 최대 절약 2L보다 key 2L+C와 payload·관리비가 커 warm 이득 불가 |
| C=99, L=1,271, R=154의 최초 방문 | P8 +3,248 |
| 같은 항목 두 방문 | 실제 호출 8→5지만 누적 P8 +2,401 |
| 같은 문자 길이인 다른 긴 cheap 원문 | 불필요한 exact miss 비용 +2,804 |
| 더 큰 이전 항목이 작은 새 반복 후보를 막음 | 새 후보 반복에도 재사용되지 않는 고착; 개발 4방문 +1,588 |
| 3byte 한글 한 글자로 동시 보관 경계 통과 | eviction 변화, 용량은 지킴; 보관 결정의 불연속성 |

첫 반례는 이전 절약 credit 없이 현재 공통 경로를 유지하고 양의 투자를 미래 재사용으로
회수하는 정책에 대한 명제다. 요청 내부의 이미 확정된 중복이나 별도 공통 비용 최적화까지
불가능하다는 주장은 아니다. 인기 고착은 정책의 실제 한계이며 사후 decay 등을 추가하지 않았다.

미실행·미확인 항목은 다음과 같다.

- 외부 자연어 의미·표현 일반화, 암묵적 정정, 미완료 요청 수명, 자유로운 참조 관계,
  실제 도구 실행 성공·증거 보존. 현재 합성 모형 밖의 능력이다.
- 실제 LLM 토큰·요금·응답 품질, 원문/digest reader의 독립 검증.
- 비계측 production path의 속도, counters/regex/key/정렬의 CPU 기여 분해, 물리 RSS,
  concurrency·멀티 프로세스·장기 운영·배포.
- 모든 자연어 원문에 대한 외부 수기 gold 재판정, 모든 의미 동치류 계산, 통계적 유의성.

## 6. 해석과 다음 차례

### 지지·기각·미확인

**지지:** 명시한 순수성·key·경로 가정 아래의 관찰 보존 정리, directory의 한쪽 비용 우월성
(비교군은 no_directory), 이번 고정 합성 분포에서 보존·실제 호출 감소·전체 P8 감소의 동시 성립.
동결 후 결과의 별도 실행 재현과 원시 행 재집계도 일치했다.

**반박되거나 관측과 맞지 않음:** 모든 유한 stream에서 fresh 이하라는 보장, hit/호출 감소를
총비용 감소로 보는 주장, 대부분의 stream에서 이득이라는 주장. 전체 로컬 속도 개선은 두 실행에서
관측되지 않았고 오히려 느렸다. 이것을 모든 환경에서 반드시 느리다는 정리로 확대하지 않는다.

**미확인:** 자연 대화 분포에서 합계 이득, 실제 CPU·LLM 비용·응답 품질 개선, 수치 gain gate
단독의 효과, 임의 원문 의미 정확성. H8을 지지한다는 말은 이 범위까지 지지한다는 뜻이 아니다.

동결 후 정책·자료·gold·비교군·주지표·threshold를 바꾸지 않았다. `POSTFREEZE_REVIEW.md`와
`DATA_REVIEW.md`는 사후 재현·분모·분포 해석이다. 유리한 새 benchmark를 추가하거나
family를 제외해 주결과를 재정의하지 않았다. 추가 수치 실험은 더 하지 않고 이 단계를 종료한다.

### 다음 Codex가 먼저 재현하거나 반박할 부분

1. `--verify`, builder `--check`, 새 경로 재현을 실행하고 결정적 5개 파일과 freeze hashes를 확인한다.
2. `recount_results.py`로 P8의 항목 합·gold 제외·3후보 관찰 비교·stream 손익분기점을 다시 센다.
   서로 다른 두 411 분모를 합치지 않는다.
3. [THEORY.md](THEORY.md)의 순수성/정확 key 가정과 D8에서 admission이 장부 합에 의존하지
   않는 전제를 검토한다. Length 양성만으로 hit 처리하는 반례를 먼저 대입한다.
4. 8/36 stream만 이득인 분포, 긴 noop quote를 포함한 여섯 family가 fresh P7 합계의 97.50%를 차지하는 구성,
   directory의 proxy·시간 반대 방향이 일반화를 막는 충분한 이유인지 반박한다.
5. 원본과 재현 timing을 모두 읽고, 부호가 유리한 family나 실행 하나만 택하지 않는다.

### 다음 한 가지 연구 제안

**다음 가설은 “동일 의미·검증을 유지한 비계측 선택적 경로가 fresh의 실제 전체 시간을 줄이는가”다.**
우선 fresh와 selective 양쪽에서 계측 event 기록과 실제 계산을 분리해, 시간 측정용 비계측
경로와 장부 산출 경로의 관찰·resident 결정을 각각 검증해야 한다. 정책 결정에 실제 필요한
key·payload encoding과 크기 계산은 유지한다. Phase08 자료는 그때 개발 자료로 전환하고, 새 조건을
동결한 뒤 새 stream에서 cold 포함 end-to-end 시간을 주지표로 비교한다. 전체 검증을
생략하지 않으며, 실제 parser/key/policy 비용의 원인 분해를 보조 증거로 둔다.

이번에는 이 후속 구현이나 성과를 만들지 않았다. 반복·aging 정책을 더 복잡하게 만드는 일보다
현재의 proxy 이득이 실제 계산비와 왜 갈라지는지 먼저 확인하는 것이 다음 한 단계다.

**운영 변경 없음. 기존 SOOM 운영, Phase01–07 동결 코드·자료·결과를 보존했다.**
