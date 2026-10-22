# Phase10 실행 전 계획 — 고정 정책의 시간 손익을 새 stream에서 예측할 수 있는가

직접 기준은 Phase09 공개 완료 `0c08785fcee9ab146f33fa8a7d94a4b7700833aa`다.
기존 Phase01–09 코드·자료·결과와 SOOM 운영은 변경하지 않는다. 새 정책이나 online gate를 만들지 않는다.
Phase09 자료·시간·사후 분석은 모두 이미 알려진 개발 근거다. 이 계획은 새 평가 원문·gold·builder를
주 구현자/수학/평가 검토자가 열기 전, 개발 calibration 시간 결과도 보기 전에 정한다.

## 1. 중심 가설 H10

**고정된 Phase09 off 구현에서, 개발 자료의 실제 경과시간으로 보정한 10-feature trace 모형이
새 고정 합성 stream의 selective−fresh 전체 시간차를 단순 기준보다 정확히 예측하고,
두 시간 세션에서 확인되는 실질적 손익의 부호를 구별할 수 있다.**

이것은 전체 public stream을 받아 untimed 실행 trace를 얻은 뒤 전체 시간을 예측하는 offline 분석이다.
미래를 모르는 운영 정책이 아니며 trace 추출에는 실제 실행 비용이 든다. 추출 비용을 공짜라고 하거나
이 predictor 자체가 계산·토큰·요금을 절약한다고 주장하지 않는다. 모형 계수는 예측 파라미터다.
고정 전체시간에 맞춰 학습한 계수를 부품별 인과 CPU 단가로 부르지 않는다.

Phase09의 파서 절약과 slowdown만으로 부품별 원인을 식별할 수 없으므로, 이번에는 실제 새 시간차를
예측할 만큼 이 trace 요약이 충분한가라는 반박 가능한 질문으로 좁힌다. 별도 microbenchmark의
비용이 그대로 가산된다고 가정하지 않는다. 미시 부품별 인과 실험은 이번 범위 밖이다.

## 2. 보존과 정보 계약

Fresh/selective off 함수·capacity·threshold·admission·replacement·directory·자료구조는 Phase09 그대로 import한다.
Obs와 π는 Phase09 정의 그대로다. 새 자료의 네 경로 on/off 관찰·정책 상태·실제 실행 trace를 별도 감사로 비교한다.
불일치가 하나라도 있으면 예측 성능과 무관하게 계약 실패로 기록하고 주 timing을 시작하지 않는다.

Selector에는 records/entities/snapshot/query와 namespace만 전달한다. Predictor의 수치 입력은 아래
10개 feature와 baseline의 P8 차이다. Gold/정답/family/author_design/실제 timing은 예측 함수의 입력이 아니다.
ID와 family는 join·집계·개발 group-CV metadata로만 보존한다. 전체 stream의 실현된 재사용 trace를 쓰므로
온라인 prefix 관측만으로 미래 반복을 예측했다는 주장은 금지한다.

## 3. 고정 feature와 모형

| Feature | 정의 |
|---|---|
| stream_constant | stream마다1 |
| queries | stream의 전체 step 수 |
| records_visited | fresh의 실제 cheap 호출 수 |
| raw_encode_bytes | fresh cheap 입력 UTF-8 길이 합; selective 방문별 raw encode 크기에 대응 |
| saved_stage_calls | fresh−selective cheap/contract/detail 호출 합 |
| saved_stage_characters | 별도 실제 off trace의 세 stage 입력 Unicode 문자 수 합의 차 |
| exact_probe_bytes | 계측 selective의 exact get key 길이 합 |
| encoded_context_payload_bytes | 실제 payload encode 길이 합+context를 사용한 각 step의 context encode 길이1회 |
| admission_attempts | 거절을 포함한 admission 시도 수 |
| policy_control_actions | 동등 정책 전이에서 원래 Phase08 정의의 control action 합 |

세 stage가 complete bundle로 같이 재사용되어 절약 열들이 공선성이므로 stage별 단가를 따로 식별하지 않는다.
P8 장부는 별도 untimed on 실행의 trace 요약으로만 읽는다. Off 주 timing에 재삽입하지 않는다.
문자와 bytes, 실제 방문과 전체 records 개수, 거절된 admission의 준비 비용을 구분한다.

개발 stream i의 target은 `d_i=median_round(Ts−Tf)` μs, 기준 시간은 `f_i=median_round(Tf)` μs다.
`d_i`는 marginal 중앙값 차나 Phase09의 paired log-ratio가 아니다.
`z_ij=φ_ij/f_i`, `s_j=RMS_i(z_ij)`(0이면1), `Z_ij=z_ij/s_j`, `y_i=d_i/f_i`로 둔다.

`θ=(ZᵀZ/n+0.01I)⁻¹Zᵀy/n`, `β_j=θ_j/s_j`, `Δhat=Σφ_jβ_j`로 고정한다.
Constant도 penalty를 받는다. 부호 제약은 없고 λ/feature 선택이나 grid search는 하지 않는다.
학습의 f_i는 가중 최소제곱 정규화에만 쓰며 새 prediction에는 측정 시간이 필요하지 않다.
표준 라이브러리의 pivoted elimination으로 작은 선형계를 풀고 normal-equation 잔차를 기록한다.

단순 기준은 (a) Δhat=0, (b) 개발 median(d_i/queries_i)×queries,
(c) 개발 normalized loss로 구한 비음수 단일 계수×ΔP8다. 방향 기준에는 raw ΔP8와 always slowdown도 포함한다.
모든 방향 예측에서 정확한0은 slowdown으로 분류하는 보수적 tie 규칙이다.

## 4. 개발·새 평가와 역할

개발 calibration은 이미 공개된 Phase09 36 base stream을 horizon1/4/12/36으로 자르거나 순환한
144 stream/1908 prefix다. 독립144개 대화나 새 의미 프로그램이 아니다. 긴 horizon의 순환은
같은 public snapshot 순서의 반복이며 미래에 원문이 재출현할 수 있는 실제 고정 cache를 유지한다.
한 calibration timing session만 실행한다. 모형/단순 기준을 한 번 fit한다.
Leave-one-family-out 12fold는 사전 고정한 개발 진단이며, horizon/개별row 분할을 하지 않는다.
CV결과로 λ/feature/조건을 바꾸지 않는다. 개발 group과 holdout family 이름은 predictor feature가 아니다.

새 holdout은 별도 동일 모델 작성자, seed2026102210, 12family×4parameter=48stream,
각 family horizon2/8/24/64를1번씩 써서1176step이다. 원문·수치·순서는 새로 작성한다.
길이·Unicode 구성·working set을 순환 배치한다. Short,cheap/deep repeat/churn,fit/pressure,
phase shift,same-length miss,revision/copy/context,scope,integrity/unsupported/recovery를 포함한다.
서로 다른 horizon을 독립 반복으로 보거나 동일 family의 stream들을 독립 자연어 모집단으로 해석하지 않는다.
긴 payload는 제한 문법 noop quote다. 작성자는 구현/계수/시간을 읽지 않고 selector/timing을 실행하지 않는다.
같은 모델이 공개 설계·문법을 공유하므로 외부 블라인드 평가가 아니다.

## 5. 주 지표와 성공·실패 규칙

각 holdout timing session에서 **전체48stream 동일가중**으로
`E=mean_i |Δhat_i−d_i|/f_i`를 계산한다. 긴 stream이 합계를 독점하지 않도록 stream 단위 평균을 주지표로 쓴다.
전체 workload 시간은 별도 보조 측정이며 이 평균이나 stream 중앙값 합과 같은 추정량이 아니다.

H10의 수치 조건은 **원본과 별도 재현 모두**:
1. `E_model≤0.10`(fresh 시간 대비 평균 절대오차10percentage points 이하),
2. `E_model≤0.75×min(E_zero,E_per_query,E_P8)`(가장 좋은 고정 단순 기준보다25% 이상 작은 오차).

비교 baseline의 최소 오차가 0이면 25% 개선이 불가능하므로 수치 조건은 실패다.
모델도 0인 동률을 개선으로 세지 않는다. 수치 조건이 실패하면 방향 class 부족 여부와
별도로 결합 H10은 `not_supported_numerical_rule`로 판정한다.

방향 검사는 각 세션에서 개별 stream의 block-bootstrap Δ 구간 전체가 `−.03 f` 아래면 speedup,
`+.03 f` 위면 slowdown, 그 밖은 unresolved로 둔다. 두 세션이 같은 material 방향으로 분류한 공통 집합만
방향 평가에 쓰되 전체48의 E에서 제외하지 않는다. 이 공통 집합은 측정으로 선택된 subset이다.
각 클래스≥4가 있어야 방향 질문을 식별 가능으로 판정한다. 부족하면 H10을 지지하지 않고
방향 미확인으로 종료한다. 임의로 자료/threshold/실험을 늘리지 않는다.

공통 집합에서 모델 balanced accuracy≥.75이고, 최선의 방향 기준(P8/항상slowdown/per-query)보다
적어도 .10 높아야 한다. 예측기가 다수 slowdown만 맞춰 성공하지 못하도록 하는 요구다.
이산 correct/count로 정의한 BA의 경계 판정은 정확한 유리수로 계산하고 float는 표시에만 쓴다.
**H10 지지는 보존 통과+두 수치 조건 양세션 통과+방향 조건 통과를 모두 요구한다.**
충족하지 못한 항목과 반례 stream을 그대로 보고한다. 이 실질 기준은 공학적 요구이며 분포무관 보증이 아니다.

## 6. 시간 구간·순서·불확실성·중단

별도 interpreter, PYTHONHASHSEED=0, 최초 허용 CPU 하나에 affinity, 정상 GC.
각 interval 전 gc.collect는 양쪽 동일하게 구간 밖. Import/로딩/gold/audit/feature/predictor는 구간 밖.
원래 off의 cache 생성/파괴,cold,전체검증,파싱,key/payload,정책,현재demand/state/copy/render가 구간 안.
Parser cache는 stream/replay마다 비지만 CPU/OS cache는 flush하지 않는다.

Calibration12round, holdout24round. 각 방법 interval은 해당 whole stream7replay를 외부타이머 한 쌍으로
측정한 뒤7로 나눈다. 각 stream의 2round block은 FS/SF를1번씩 포함하고 block순서는 고정seed로정한다.
각 round의 stream 순서도 고정seed로shuffle한다. Stream별1warmup round는제외하되원시값보존.
Seed calibration20261022100, primary20261022101, reproduction20261022102.
새 평가에는 별도로 whole-workload16round×2replay(1warmup)도 측정한다. 부품별 가산분해로 사용하지 않는다.

개별stream Δ bootstrap은 2round block 전체12개를4000회 복원추출한다(calibration은6block).
구간은 medianΔ의 percentile95%이며 분모f는점추정을고정한다. 상대시간비율 jointCI가 아니고
48stream·2session 전체를 동시에95%로보장하지 않는다. Block교환가능성·host drift 한계를명시한다.
질문·동일입력반복·method row를독립대화표본으로resample하지 않는다. E에는 모집단 CI를 붙이지 않는다.

Calibration1회, holdout primary1회, 별도role/process reproduction1회만. Reproduction은 새 시간으로 모형을 재학습하지 않는다.
저장된 원 calibration에서 계수를 재계산하는 것은 동일성 witness이며, prediction에는 저장한 frozen model을 그대로 읽어 쓴다.
동일계수로prediction과deterministic산출물을비교하고 actualtime만재측정한다. 새머신재보정일반화는미검증이다.
예외/계약실패/외부중단은원시progress와함께실패로보존한다. 유리한이상값제거·성능이유rerun없음.
각 worker의900초timeout은기술적중단한도이며측정이끝난prefix를선택해성공으로보고하지 않는다.

## 7. 동결·재현·전달

개발전계획및코드기록→calibration실행/fit→source/reviews/data/model/calibrationhash checkpoint→freeze commit→
새holdout열람/untimed감사/feature/prediction→predictionhash·시각봉인→primary timing 순서다.
원문·gold·builder를보지않은role은metadata/hash만받아동결한다. GitHub공개는평가후이며외부사전등록아님.
모형재계산은저장calibration원시시간으로동일성을확인하고,재현timing은모형선택에돌려주지않는다.

동결후정책/core/data/정답/지표변경이필요하면실패와변경을명시한다. 결과재집계·사후검토·반환문서는별도추가한다.
새branch research/phase10-time-prediction, 기존PR상태확인후적절한base로PR전달. merge하지않는다.
자연어의미정확성·미완료요청/실행증거일반보존·LLM토큰/요금/품질·RSS·운영배포·부품별인과CPU비용은검증하지않는다.

