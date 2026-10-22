# Phase09 연구 반환 — 필요한 상태를 남기고 계측을 지웠지만 실제 속도 우위는 얻지 못했다

작성: 2026-10-22 KST. `docs/RETURN_TEMPLATE.md`의 출발·계약·변경/재현·결과·다음 차례를 따른다.

**결론:** 동일 의미·전체 검증·정책 상태를 보존하는 비계측판을 구현하고 검증했다.
하지만 새 합성 36 stream / 432 step에서 **fresh_uninstrumented → selective_uninstrumented**의
주 시간 비율은 원본 **+17.93%**, 별도 재현 **+16.78%**였다. 사전 고정한 실질 3% 기준에서
두 실행 모두 slowdown이었다. 따라서 **H9의 속도 개선 가설은 이번 고정 자료·환경에서 지지되지 않는다.**
두 방법 모두 계측 제거 자체로는 빨라졌다. 그것이 selective의 상대적 우위를 뜻하지 않았다.
기존 코드·자료·결과와 SOOM 운영은 변경하지 않았다.

## 1. 출발 상태

### 저장소와 정확한 기준

- 저장소: <https://github.com/DH-11027/soom-context-research>.
- 최초 archive: `780891f6c147cfd3c1a3b0d065792776aaa525f3`.
- Phase07 완료: `6da051c0132811184ecf39975d7ff647a1f47842`.
- 직접 읽기·재현 기준은 **Phase08 공개 완료 `efba3224dd09d5c5e2bf9d9be11734fa10b32502`**다.
  Phase08 로컬 freeze `4a128204cad4abbf374fea7326b6c844f800812f`와 혼동하지 않는다.
- 착수 때 GitHub API로 PR #1/#2/#3이 모두 open/unmerged임을 확인했다.
  Base는 각각 main / research/phase06-scoped-opaque / research/phase07-parse-reuse였다.
- 새 branch는 `research/phase09-instrumentation-erasure`이며 Phase08 완료에서 분기했다.
  전달 직전에도 #1/#2/#3의 open/unmerged 상태와 #3 head `efba3224…`를 다시 확인했다.
  열린 Phase08 branch를 base로 사용한다. 기존 branch를 덮어쓰거나 PR을 merge하지 않는다.

**GitHub 전달:** [PR #4](https://github.com/DH-11027/soom-context-research/pull/4)를 open/unmerged 상태로 열었다.
연구 내용의 최초 공개 commit은 `218b1ad042cf2a2f8ec260420e13f6af9b729e7b`이고,
로컬 연구 완료 commit `f8649c3196dd289cb53325920fbbff7d0e87641b`와 전체 Git tree
`1a020e0813a03e1a399bc84cd558e94f3ee2ef0e`가 정확히 같았다. 공개 branch를 다시 fetch한
`git diff`가 비어 있었으며, 기존 기준 대비 75파일 추가가 모두 이 폴더 아래임을 확인했다.
[DELIVERY.json](DELIVERY.json)에 그 검증을 기록했다. 이어진 문서 commit은 이 receipt와
README/HANDOFF의 전달 링크만 추가한다. 최종 공개 head와 tree 대조도 PR 본문에 남긴다.
로컬 freeze 객체는 bundle에 보존했다. 로컬 동결 시각을 외부 공개 시각으로 소급하지 않는다.

### 실제 읽기와 역할 구분

주 구현자는 Phase08 `HANDOFF_BACK.md`, `PROTOCOL.md`, `THEORY.md`, `POSTFREEZE_REVIEW.md`,
`DATA_REVIEW.md` 순서로 인수인계하고, 필요한 이론 부분을 다시 확인했다.
이후 `runtime.py`, `frozen.py`, `evaluation.py`, `run_study.py`, Phase06 `scoped.py`,
Phase07 `baseline.py`, `cached.py`, `study.py`, 반환 template을 직접 읽었다.

수학 역할은 앞의 문서와 Phase05/06/07의 관련 의미·의존성 코드를 검토하고
THEORY/MATH_REVIEW 및 실행 가능한 반례를 작성했다. 평가·재현 역할은 Phase08
`audit.py`, 평가기·개발·재현·재집계 자료를 확인하고 Phase09 evaluator/audit를 작성했다.
주 구현자가 그 평가기 전체를 별도로 읽었다. 새 자료 작성자는 기존 schema·문법을 읽고
자료를 만들되 Phase09 구현·개발 결과를 읽지 않았다.

프로그램으로 확인한 자료는 기존 archive hash 결합, Phase08 1,728 새 행·5,424 회귀 행,
새 Phase09 1,728행·7,508 회귀 행·각 prefix 정책 상태, source/data hashes, timing 원시값이다.
저장소 전체를 읽거나 모든 과거 실험을 다시 수행했다고 주장하지 않는다.
새 corpus 모든 자연어 문장을 외부 의미 정답으로 수기 판정한 작업도 아니다.
역할을 나눴지만 **모두 같은 모델이며 공개 설계·문법을 공유했다. 외부 독립 검증이 아니다.**

### Phase08 재현과 새 발견

다음 요구 명령을 원본을 덮어쓰지 않는 경로에서 실제 실행했다.

```bash
python tools/verify_archive.py
python research/phase08/run_study.py --verify
python research/phase08/holdout_builder.py --check
python research/phase08/run_study.py --run \
  --output /tmp/soom-phase08-repro-for-phase09 \
  --compare research/phase08/results
python research/phase08/recount_results.py \
  --output /tmp/soom-phase08-recount-for-phase09.json
git bundle verify research/phase08/pre_evaluation.bundle
```

6개 명령 모두 통과했다. Archive 59파일/18결합, 결정적 결과 5파일과 기존 recount 결과의
byte identity를 확인했다. **Phase08 기존 수치를 정정할 오류는 발견하지 않았다.**

이번 새 관측의 Phase08 전체 중앙값은 fresh 60.488ms, selective 66.014ms로 **+9.14%**다.
No-directory는 68.138ms여서 이번에는 selective가 더 빨랐다. 과거 두 실행에서
directory가 더 느렸다는 기록을 고치지 않는다. 이 부호 역전은 directory의 CPU 효과가
기존 7회 관측만으로 안정적으로 정해지지 않았다는 추가 증거다. D8의 작업점수 정리는 그대로다.
원문 명령/환경/결과는 [INHERITANCE_AUDIT.md](INHERITANCE_AUDIT.md)와 `inheritance/`에 있다.

## 2. 이번 가설과 계약

### 하나의 중심 가설

**H9:** Phase08 정책·의미·전체 snapshot 검증을 유지하면서 계측 전용 작업을 제거하면,
새 고정 합성 workload의 cold 포함 전체 실행시간이 비계측 fresh보다 실질적으로 줄어든다.

Phase08에서 proxy와 시간의 방향이 달랐으므로, 새 보관 정책을 설계하기 전에 실제 비용과
계측의 경계를 확인하는 것이 적절한 다음 단계였다. 계측이 기존 slowdown의 원인이라는
결론을 전제하지 않았다. MIN_CHARS=256, 용량65,536, entries64, metadata80, hit cap255,
surplus의 8×8 상수, directory·admission·replacement·자료구조를 고정했다.

### 입력, Obs, π

입력 `x_t=(records, ordered_entities, query, snapshot, namespace)`는 builtin JSON형의
유한 값이며 문자열은 UTF-8 encodable이다. 실행 중 불변, 동결 순수 함수, 단일 스레드,
정상 자원 가용성을 가정한다. Invalid snapshot과 unsupported query는 정상 반환 사례로 포함한다.
Gold, 정답, family, 미래 step·반복 수는 실행기의 입력이 아니다.

`Obs`는 반환 dict에서 `cost`만 뺀 정확한 내용과 근거 렌더의 실제 UTF-8 bytes다.
status/reason/prediction/selected/remaining_input_facts/scope_trace/output_bytes의 값·존재 여부를
비교한다. 출력 길이나 hash만 같다는 조건으로 대체하지 않는다.

Selective 정책 상태 `π(S)`에는 다음이 남는다.

- Resident `(context bytes, raw bytes)` exact key와 dict 삽입 순서.
- Immutable stage 값과 payload 길이, size/characters/surplus/hits/order.
- Length directory의 개수, retained_bytes, next_order, capacity와 directory 설정.
- 의미 fingerprint와 고정 정책 상수는 source hash 불변 전제로 묶는다.

보고용 peak와 ledger만 지운다. Fresh의 persistent 상태는 빈 상태다.
각 입력 prefix에 대한 계약은 다음 두 등식이다.

\[
Obs(Run_{on}(x_{1:t}))=Obs(Run_{off}(x_{1:t})),\qquad
\pi(S^{on}_t)=S^{off}_t.
\]

Fresh와 selective 사이에는 관찰 동등성을 요구하며 서로 다른 cache 상태의 동일성은 요구하지 않는다.
최종 답이 같아도 on/off cache 상태가 다르면 동일 정책의 계측 제거 계약 실패다.

### 실제 삭제와 유지

| 계산 | 처리와 데이터 의존성 |
|---|---|
| 비용 카운터·control event dict·내부 timer·보고 합계 | 정책·의미로 흘러가지 않아 제거 |
| 보고용 peak_bytes/peak_entries | 다음 결정에 사용하지 않아 제거 |
| Fresh read의 `len(text.encode('utf-8'))` | size가 source-byte 장부에만 흘러 encode와 함께 제거 |
| Fresh의 Phase07/08 wrapper | 비용 장부·timer를 더하는 층이어서 off는 의미 run으로 직접 연결 |
| Selective raw/context/payload encode 및 L/C/R | exact key, surplus, size, admission/victim 입력이어서 유지 |
| Hits·surplus·보관량·order·directory | 미래 결정에 사용하므로 유지 |
| 정렬·victim 계획·삽입·삭제·immutable 변환 | 동일 정책 전이이므로 유지 |
| 전체 snapshot JSON/UTF-8/SHA256 | 무결성 판정에 필요하여 유지 |
| 현재 demand·copy·상태 실행·scope trace·근거 렌더 | 현재 관찰에 필요하여 유지 |

Selective는 짧은 bypass 방문에서도 원래 위치의 eager raw encode를 유지했다.
그 경로에서 사용하지 않을 변환까지 lazy하게 옮기는 별도 최적화는 하지 않았다.
그러므로 이번은 **source-specific한 보수적 계측 삭제**이며, 가능한 모든 dead-code 제거의
최솟값이나 최고속 구현이라고 주장하지 않는다. 이 남은 비대칭은 숨기지 않는다.

구현은 `erase.py`가 원본 AST의 명시된 문장을 제거하여 정적 `off_fresh.py`와
`off_selective.py`를 생성하는 방식이다. `erasure_manifest.json`에 삭제 문장·원본 위치·
source/output hash를 남겼다. 생성은 timing 이전이며 런타임에 AST를 바꾸지 않는다.
Fresh 보존 범위는 `method='text_scoped'`다. 다른 보존된 method branch의 성능은 연구하지 않았다.

### 증명과 작은 반례

**E1 장부 비간섭:** cost와 peak의 읽기는 보고·다른 장부 갱신에만 흐르고, 의미/정책 상태로
되돌아가는 의존성이 없다. 충분한 자원 아래 지운 문장은 상태 투영을 바꾸지 않는 단계다.
**E2 Fresh dead size:** 장부를 지우면 방문별 UTF-8 크기의 사용처가 사라지므로 함께 지울 수 있다.
**E3 정책 결정성:** 같은 π와 입력이면 exact key hit/miss, stage 값, C/L/R,
`b=L−C−R−64`, `e=C+L+R+80`, `w=(h+1)b`, density·동점 순서·victim 계획이 같다.
이를 빈 cache에서 시작하는 prefix 귀납으로 연결하면 E9의 두 동등식을 얻는다.
상세 증명은 [THEORY.md](THEORY.md)와 [MATH_REVIEW.md](MATH_REVIEW.md)에 있다.

수학적 검토는 Python 전체의 정형 검증이 아니며, OOM·kill·외부 mutation·임의 사용자 객체의
부작용·exception traceback·시간·GC 행태까지 동등하다고 하지 않는다. 의미 parser 자체의
자연어 정확성을 새로 증명하는 것도 아니다.

작은 **세 요청 반례 A,A,B**에서는 A의 surplus=32,146, size=32,812,
B의 surplus=33,346, size=34,012다. 각각은 들어가지만 합66,824는 용량65,536을 넘는다.
정상은 두 번째 A에서 hit=1, weight=64,292가 되어 B를 거절한다.
Hit 갱신을 통계로 오인해 지우면 weight=32,146에 머물러 B가 A를 축출한다.
**세 답은 같지만 두 번째부터 정책 상태가 다르고 세 번째에는 보관 결정도 다르다.**

별도 `counterexamples.py`의 네 요청 A,B,A,C 반례는 복수 resident의 victim 순서까지
갈라짐을 보인다. 같은 문자 길이를 exact identity로 쓰는 mutant도 원래 opaque 판정을
잘못 certified로 바꾼다. 실제 공개 off 구현은 이 mutants와 달리 모든 개발 prefix를 보존했다.
15개 상태 mutant와 9개 잘못된 출력 mutant의 검출을 일반적인 무오류 증명으로 확대하지 않는다.

Phase08의 최초 투자 직후 종료, late lookup의 P7 경계, 과거 인기 고착, 같은 길이의 다른 원문,
동시 용량 경계는 그대로다. D8은 no_directory 대비 논리 점수 정리이며 CPU 시간 정리가 아니다.

## 3. 변경과 재현

### 파일과 자료 구분

| 역할 | 파일 |
|---|---|
| 원본 연결·기계적 삭제·네 실행 경로 | bindings.py, erase.py, erasure_manifest.json, off_fresh.py, off_selective.py, execution.py |
| 별도 관찰/상태/호출 감사 | evaluator.py, audit.py, EVALUATOR_REVIEW.md |
| 이론·반례 | THEORY.md, MATH_REVIEW.md, counterexamples.py, counterexample_results.json |
| 주 timing·실행·분포 | benchmark.py, run_study.py, data_profile.py |
| 동결·자료 | PROTOCOL.md, freeze.json, freeze_commit.json, pre_evaluation.bundle, holdout_builder.py, HOLDOUT_AUTHOR.md, data/ |
| 이전 단계/개발 | INHERITANCE_AUDIT.md, inheritance/, DEVELOPMENT_AUDIT.md, development_final/, 초기 development_results/ |
| 원본·재현·재집계 | results/, reproduction_receipt.json, reproduction_timing.json, recount_results.py/json |
| 사후 검토·전달 | POSTFREEZE_REVIEW.md, DATA_REVIEW.md, README.md, HANDOFF_BACK.md |

개발은 Phase08 개발89 + 이전 주평가432 + Phase05–07 회귀1356 =1877 prefix다.
507 stream container, 7508 method rows이며 새 독립 평가로 합치지 않는다.
개발 중 상태 occupancy를 비용처럼 합산하던 보고 표현을 최대값으로 분리하고
고의 오류 fixture의 문법 전제를 수정했다. 이 변경과 두 개발 산출물은 DEVELOPMENT_AUDIT에 남겼다.

새 자료는 **seed2026102209, 12 family ×3 parameterization ×12 step=36 stream/432 step**이다.
긴 quote 구간은 UTF-8 약900–1900 /9000–18000 /57000–74000 bytes로 작성했고,
실제 record 범위45–70,026 bytes다. Fit/pressure, 반복/매회변경, 종료 직전 cold 후보,
같은 길이 exact miss, context/copy/revision, invalid·unsupported·회복을 포함한다.
상세 working-set/분포는 작성 manifest와 DATA_REVIEW를 따른다.

유효420 step의 서로 다른 exact records는315, id/seq를 뺀 ordered raw history는212다.
Gold 적용414 step의 exact typed-event 배열은135개다. 이는 canonical serialization의
동일성 통계이며 독립 잠재 프로그램 수나 의미 동치류 수가 아니다.
긴 payload는 제한 문법의 noop quote이며 복잡한 자연어 추론 자료가 아니다.

### 로컬 동결

- Checkpoint: **`c2759e0dcb669cec2dd59b75115f88d45a93af4f`**.
- Local freeze: **`387b451a19d0c17abc22365b82daeb357b0d3ab3`**.
- Freeze 시각: **2026-10-22 12:09:12.962258 UTC / 21:09:12.962258 KST**.
- 첫 실행 경계 기록: **12:09:38.665290 UTC /21:09:38.665290 KST**, 새 평가 실행 직전.
- GitHub 공개는 평가 이후다. **외부 사전 등록이 아니다.**

주 구현자·수학·평가 검토자는 freeze까지 새 원문·gold·builder를 열지 않았다.
작성자가 공유 설계·문법을 알았다는 한계는 남는다. Source·자료 hash는 freeze.json에 결합했다.

| 주요 파일 | SHA-256 |
|---|---|
| off_fresh.py | `6e15bec049362c5d5c3464331337987770882d70baf4b82b8fe321ff85771ea9` |
| off_selective.py | `f3b8e770335d2866b2bdb88bdc34ed6cb6f04ad1f62e31ba77794a8985879e84` |
| benchmark.py | `8b681bdc43e16b7a6829e3c44a86943051e659086f337917c20315dd9b074742` |
| data/holdout.json.gz | `1a36ee60f57c7e0ad7f6f91f098e9803db212d4de2e00920510740e5b5ee20e6` |
| 해제된 JSON | `c659d9c89126d5184ddc4a59102050ec50a8e6a8bfb2a3306d04fe4f526c6740` |

압축은 동결 전 저장 형식만 바꾼 것이며 해제 bytes13,030,700의 동일성을 확인했다.
pre_evaluation.bundle에는 로컬 checkpoint/freeze 객체가 보존되어 있고,
Phase08 공개 완료 commit을 prerequisite로 `git bundle verify`를 통과했다.

### 환경과 명령

Python3.12.14/CPython, Linux6.18.55 x86_64, glibc2.39,
AMD EPYC9V74 80-Core Processor. 주 timing process는 허용 CPU0 하나에 affinity를 고정했고
PYTHONHASHSEED=0, 정상 GC를 사용했다. 호스트 부하의 완전 격리나 CPU/OS cache cold는 아니다.
표준 라이브러리만 사용했고 LLM/API 호출은 없다.

```bash
python tools/verify_archive.py
python research/phase09/erase.py --check
python research/phase09/run_study.py --verify
python research/phase09/holdout_builder.py --check
python research/phase09/run_study.py --run \
  --session reproduction \
  --output /tmp/soom-phase09-repro-new \
  --compare research/phase09/results
python research/phase09/recount_results.py \
  --results research/phase09/results \
  --reproduction /tmp/soom-phase09-repro-new \
  --output /tmp/soom-phase09-recount-new.json
python research/phase09/data_review_recount.py \
  --reproduction-timing research/phase09/reproduction_timing.json \
  --output /tmp/soom-phase09-data-review-recount-new.json
python research/phase09/counterexamples.py \
  --output /tmp/soom-phase09-counterexamples-new.json
git bundle verify research/phase09/pre_evaluation.bundle
```

별도 재현에서 audit, holdout summary/rows/states, regression summary/rows/states,
data profile의 **8개 결정적 산출물이 byte-identical**이었다. 시간·시각 receipt는 비교 대상이 아니다.
독립 recount는 evaluator.summary/benchmark 집계 함수를 import하지 않고 원시 값에서 다시 계산했다.
주 timing은 원본1회·재현1회로 종료했으며 유리한 결과를 얻기 위한 추가 session은 없다.

## 4. 실제 결과

### 주 비교: 계측을 양쪽에서 제거한 전체 시간

각 session은 40 paired round, 4방법, interval마다 전체 workload3 replay다.
Cache는 매 stream/replay 새로 만들고 생성·파괴·cold 비용을 포함한다.
전체 검증·실제 파싱·key/payload·정책·현재 상태/copy·동일 렌더가 외부 timer 안에 있다.
Import/자료 로딩/gold/별도 감사/GC 사전 collection은 제외했다.
2 warmup은 주집계에서 제외하되 원시값을 보존했다.

| 전체 workload 시간 중앙값, ms | 원본 | 별도 재현 |
|---|---:|---:|
| fresh_instrumented | 78.916 | 76.403 |
| fresh_uninstrumented | **67.128** | **65.550** |
| selective_instrumented | 88.124 | 85.798 |
| selective_uninstrumented | **79.719** | **78.313** |

이는 질문 한 건의 latency가 아니다. 표는 각 방법의 marginal 중앙값이며, 주 추정량은
round별 비율의 log 중앙값이므로 표의 두 중앙값을 나눈 값과 다를 수 있다.

\[
\rho=\exp\left(\operatorname{median}_r\log
\frac{T_{selective\_off,r}}{T_{fresh\_off,r}}\right).
\]

| 주 추정량 | 원본 | 별도 재현 |
|---|---:|---:|
| ρ | 1.179341 | 1.167817 |
| 시간 변화 | **+17.93%** | **+16.78%** |
| Cycle bootstrap95% 구간: 변화율 | +15.19% ~ +21.36% | +15.91% ~ +19.14% |
| 사전 실질3% 판정 | slowdown | slowdown |

Bootstrap은 같은 고정 workload를 재는 연속4 round의 cycle10개를 단위로20,000회 수행했다.
질문·대화·method row를 독립 표본으로 resampling하지 않았다. Cycle 간 충분한 교환가능성을
가정하며, 10개 cycle은 작고 임의 host drift나 다른 머신·실제 대화 분포에 대한 구간이 아니다.
유리한 표본을 골라 버리지 않았고 원본·재현의 모든 raw/warmup/순서를 남겼다.

변동은 있었다. Fresh_off 원본 최소58.072ms–최대88.665ms,
재현55.407ms–114.008ms였다. Selective_off는 각각69.912–96.509ms,
64.171–105.847ms였다. 이 변동을 감안한 사전 판정에서도 두 세션 방향은 같았다.

### 계측 제거 자체의 효과와 주 가설을 구분

| 동일 방법 on→off, paired 변화 | 원본 | 별도 재현 |
|---|---:|---:|
| Fresh | −13.48% | −12.65% |
| Selective | −9.66% | −9.85% |

두 방법 모두 빨라졌으나 fresh의 감소율이 더 컸다. 계측이 비용을 더한다는 관측과
계측을 없애면 selective가 fresh보다 빠르다는 주장은 서로 다르다.
계측판 간 비교도 원본+13.19%, 재현+14.56%로 selective가 느렸다.
이 숫자들은 각각 paired 추정량이며 서로 곱하거나 빼서 다른 paired 추정량의
정확한 분해라고 해석하지 않는다.

같은 집계 규약의 네 관측시간에서는 다음 산술 항등식이 성립한다.

\[
S_{off}-F_{off}
=(S_{on}-F_{on})-[(S_{on}-S_{off})-(F_{on}-F_{off})].
\]

Selective의 절약만 볼 수 없고 fresh에서도 없어지는 비용을 포함해야 한다.
On−off는 변경 전체의 효과이며 event append/encoding/GC 등 한 부품의 정확한 CPU 비용이 아니다.
이번 단계에서 profiler 또는 부품별 인과 분해는 하지 않았다.

### 정확성·정책 상태·판정 범위

네 방법의 판정은 모두 다음과 같다.

| 판정 | 각 방법 /432 |
|---|---:|
| certified_model | 372 |
| ambiguous | 24 |
| opaque_fallback | 15 |
| integrity_failure | 12 |
| unsupported_query | 9 |
| 실제 전체 이력 출력 | 24 |

전체 이력24는 opaque15+unsupported9이며 integrity 거절을 더하지 않는다.
Certified_model은 제한 모형의 singleton 판정이며 실제 사실성·도구 실행 성공 인증이 아니다.

- Fresh 계측판과 나머지3경로의 exact Obs 불일치: **0/1296**.
- 방법 내부 on/off 실제 parse/scope/snapshot/render trace 불일치: **0/864**.
- Selective 정책 상태 π 및 실제 get/admit 결정 trace 불일치: 각각 **0/432**.
- False certification: 방법별 **0/372**.
- 주변부 containment 위반: 방법별 **0/405**.
- Selected-gold 공동 투영 실패: 방법별 **0/414**.

Gold 적용414는 invalid12+membership 의미투영 미정의6을 제외한 집합이고,
유효·지원411은 invalid12+unsupported9를 제외한 다른 집합이다.
Gold414에는 unsupported9의 전체 이력 선택 확인이 포함되므로 답변 성공414가 아니다.
외부 reader가 raw/digest만 받아 독립적으로 충분성을 확인하는 검증은 하지 않았다.

### 실제 호출·bytes와 점수: 별도 감사 실행의 수치

아래 호출 계수는 주 timing 밖의 wrapper 감사에서 직접 측정했다.
On/off 사이의 정확한 실행 trace 일치도 확인했다. 비계측 timing 실행 내부에 장부를 다시 넣지 않았다.

| 합계 | Fresh on/off | Selective on/off |
|---|---:|---:|
| 실제 cheap+scope+detail 실행 | 4,905 | 4,152 (−15.35%) |
| 파서에 전달한 UTF-8 길이 합 | 30,426,509 | 19,010,756 (−37.52%) |
| 전체 snapshot 직렬화 bytes | 11,452,505 | 11,452,505 |
| Snapshot hash 호출 | 426 | 426 |
| 출력 UTF-8 bytes | 544,794 | 544,794 |

길이 합은 regex가 물리적으로 읽은 bytes나 CPU instruction 수가 아니다.
426회 hash는 유효420에 hash까지 수행한 invalid6을 포함하며, 나머지 invalid6은 순서 검사에서 멈춘다.
출력과 snapshot 비용은 같은 자료의 네 방법 사이에서 동일하다는 의미다.

Selective는 complete hit251로 stage753회를 절약했다. Admission184, write70,
capacity reject114(oversize36 포함), eviction1, 최대 논리 보관65,520/65,536,
최대 resident12다. Gain 거절은0이어서 수치 surplus gate 단독 효과를 주장하지 않는다.

보조 계측 점수는 fresh P8=42,423,808 → selective45,724,400으로 **+7.78%**였다.
Phase08의 −4.28%를 정정한 것이 아니다. 새 구성에서는 score 이득도 유지되지 않았다.
Off 결과에는 가짜 P7/P8 장부를 붙이지 않는다. 실제 시간의 주 결과를 이 보조 점수로 대체하지 않는다.

### Cold와 이득 분포

별도8회 stream 진단에서 전체 stream 중앙값이 줄어든 것은 원본 **5/36**,
재현 **7/36**이었다. 단지 양의/음의 점추정 수이며 stream마다 유의성 검정을 한 것이 아니다.
두 세션 공통 이득은 **3/36**이고 **6 stream**에서 손익 부호가 바뀌었다.
첫 step을 매번 새 cache로 재는 별도 cold 진단의 중앙값 합은 **+43.69% /+33.57%**였다.
이 합은 다른 실행에서 얻은 진단이고 주 전체시간의 정확한 가산 분해가 아니다.

큰 원문·working-set·surface/typed 중복과 family별 손익은 [DATA_REVIEW.md](DATA_REVIEW.md)에
원시 행 기반으로 기록했다. 큰 입력의 비용 비중을 원문 quote 그 자체의 CPU 비용으로 직접 귀속하지 않는다.
긴 quote를 포함한 9 family는 fresh P7의 **99.0435%**를 차지했지만, 별도 stream 진단의
fresh 실행시간 중앙값 합에서 차지한 비중은 **84.9018% /84.2658%**였다. 이 비중도 주 timing의
정확한 가산 분해가 아니다. `fit_working_set` family는 두 진단에서 **−7.93% /−5.60%**,
`pressure_working_set`은 **+20.79% /+16.35%**였다. `long_deep_repeat`는 P8가 감소해도
시간은 **+10.60% /+17.99%** 증가했다. 길이만의 단일 손익 법칙이나 인과효과를 주장하지 않는다.
유리한 family만 고르거나 이득 stream만 묶어 주 비교를 다시 정의하지 않았다.

## 5. 해석과 다음 차례

### 지지·기각·미확인

**지지:** 명시한 가정 아래 source-specific 계측 제거의 prefix Obs/π 보존 정리;
새 자료와 기존 회귀에서 그 구현 계약 통과; 같은 자료에서 실제 파서 호출 감소;
각 방법의 on→off 시간 감소; 원본/재현 모두의 selective_off slowdown.

**이번 자료·환경에서 지지되지 않음:** H9의 전체 시간 개선 가설.
"계측을 제거하면 자동으로 selective가 fresh보다 빨라진다"는 설명은 이 구현·분포에서
관측과 맞지 않는다. 모든 환경에서 selective가 반드시 느리다는 정리는 아니다.
P8의 기존 합계 개선을 새 자료/대다수 stream의 개선으로 일반화할 근거도 없다.

**미확인:** 어느 코드 부품이 초과시간을 얼마나 만들었는지, 더 완전한 path-sensitive
계측/죽은 계산 제거의 성능, 다른 interpreter/CPU·실제 대화 분포에서의 효과,
실제 자연어 의미 정확성·암묵적 정정·미완료 요청·자유 참조·실행 증거의 일반 보존,
LLM 토큰·요금·답변 품질, 물리 RSS, 동시성, 운영 배포.

동결 후 정책·source core·새 데이터·gold·주지표·threshold 변경은 없다.
사후 추가는 원시 결과 재집계·분포 해석·반환 문서다. 성능 세션을 늘리거나 새 유리한
benchmark를 추가하지 않았다. 느린 결과를 미완료로 취급하지 않고 한 연구 단계로 종료한다.

### 다음 Codex가 먼저 재현·반박할 부분

1. 지정 Phase08 기준과 `freeze.json` source hashes, AST 재생성, bundle의 로컬 commit을 확인한다.
2. 새 경로 `--run --compare`로 8개 결정적 파일을 비교하고 시간은 별도 관측으로 남긴다.
3. Hit 삭제의 세 요청 반례부터 실행해 답 비교만으로는 π 계약을 검증할 수 없음을 확인한다.
4. Fresh source-size encode의 dead dependency와 selective C/L/R→b/e→victim 의존성을 다시 추적한다.
5. 실제 비교가 fresh_off→selective_off인지, 전부 cold 비용을 포함하는지, 주 timing에
   감사 wrapper가 없는지, paired 비율과 marginal 중앙값을 혼동하지 않았는지 확인한다.
6. Bootstrap10 cycle·host drift·single CPU·같은 모델 합성자료라는 한계, gold414와 유효지원411,
   unsupported9의 검사 의미를 먼저 반박한다. 1728행을 독립 대화로 재해석하지 않는다.

### 다음 한 가지 연구 제안

**고정 의미·정책에서 실제 파서 절약과 key/payload 처리의 시간 손익분기점을 실측으로
예측할 수 있는가**를 다음 가설로 제안한다. 이번은 계측 삭제 전체의 효과만 식별했고,
호출15.35% 감소가 시간 이득으로 이어지지 않는 부품별 이유는 분해하지 않았다.
다음에는 Phase09를 개발 자료로 전환하고, 별도 진단에서 순수 stage와 key/payload/정책의
실제 길이·반복별 비용을 관찰해 시간 모형을 세운 뒤 새 stream의 부호를 예측해야 한다.
Profiling 값은 보조 진단으로 두고 새 비계측 전체시간으로 검증하며, 부품 비용의 완전한
가산성을 전제하지 않는다. 이 후속 구현·모형·실험은 이번에는 수행하지 않았다.

**SOOM 운영 변경 없음. 기존 Phase01–08 동결 코드·자료·결과 보존. Phase09 한 단계 완료.**
