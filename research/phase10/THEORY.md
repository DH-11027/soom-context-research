# Phase10 수학 계약: 실제 시간차의 오프라인 예측

직접 기준은 Phase09 공개 완료 commit
`0c08785fcee9ab146f33fa8a7d94a4b7700833aa`다. 이 문서는 새 평가의 시간 결과를
보기 전에 작성한다. 구현·정책·보관량을 개선하는 연구가 아니라, 그 구현의
실제 시간 손익을 제한된 trace 요약으로 예측할 수 있는지 검증하는 연구다.
수학적으로 증명하는 것은 보존의 승계, 추정식, 오차 경계와 정보 손실이다.
새 stream의 실제 시간차 또는 예측 성능은 실험 명제로 남긴다.

## 1. 실행 대상과 시간 추정 대상

하나의 stream을

\[
 X=((P_1,\nu_1),\ldots,(P_q,\nu_q))
\]

로 둔다. 각 \(P_t\)는 `records`, ordered `entities`, `snapshot`, `query`만
포함하고 \(\nu_t\)는 parser namespace다. 의미 결과를 산출하는 실행은
Phase09의 `fresh_uninstrumented` \(F\), `selective_uninstrumented` \(S\)를
그대로 사용한다. 각 stream 시작의 parser cache는 비어 있다. 같은 stream
안에서는 policy state를 유지한다. Phase10은 admission, replacement,
capacity, threshold, data structure, parsing, validation, rendering을 바꾸지
않는다. 실제 연결은 [bridge.py](bridge.py)와 기존
[execution.py](../phase09/execution.py)에 있다.

실제 시간은 입력만의 수학적 함수라고 가정하지 않는다. 실행 환경·시점의
상태를 \(\omega\)로 쓰면 \(T_m(X;\omega)\), \(m\in\{F,S\}\)다.
측정 session \(e\), stream \(i\), paired round \(r\)에 대해 코드가 기록한
\(t^e_{m,i,r}>0\)는 **7번 전체 stream replay를 한 외부 interval의 시간을
7로 나눈 microseconds**다. 7개 독립 시간 표본의 중앙값이 아니다.

평가 target과 정규화 분모는 다음으로 고정한다.

\[
 d_i^e=\operatorname{median}_r
       (t^e_{S,i,r}-t^e_{F,i,r}),\qquad
 f_i^e=\operatorname{median}_r t^e_{F,i,r}.
\]

\(d<0\)는 selective의 이득, \(d\ge0\)는 손해 방향이다.
\(d\)는 paired 차이의 중앙값이며, 두 marginal 중앙값의 차이가 아니다.
\(d/f\)도 paired 시간 비율의 중앙값이 아니다. 이 연구의 target은
고정 stream에 대한 위 측정·집계 절차의 값이다. 이를 임의 대화 모집단의
기대 시간이나 모든 환경에서 일정한 intrinsic cost로 바꾸어 해석하지 않는다.

측정 interval에는 cold cache 생성·소멸, 전체 snapshot 검증, 실제 파싱,
key·payload 처리, 정책 관리, 현재 demand·상태·copy 실행, 근거 render가
양쪽 모두 포함된다. import, 자료 loading, gold 평가, feature 추출,
모형 계산, interval 직전의 `gc.collect()`는 제외한다. GC는 실행 중 켜져
있다. parser cache의 cold 시작은 CPU·OS cache의 cold 상태를 뜻하지 않는다.
정확한 실행 구간은 [time_worker.py](time_worker.py)에 고정한다.

## 2. 관측 가능한 10개 feature

\(\phi(X)=x\in\mathbb{R}^{10}\)는 **완료된 전체 public stream**의 별도
untimed replay에서 얻는다. gold, family, 답의 정오, 평가 시간은 feature
함수의 인수가 아니다. 전체 stream trace를 읽으므로 미래 질문을 모르는
online prefix 예측기라는 주장도 하지 않는다. 추출 자체에 실제 실행 비용이
들며, 그 비용을 포함한 production speedup은 평가하지 않는다.

| 순서·식별자 | 정확한 값 | 해석 경계 |
|---|---|---|
| 0 `stream_constant` | 1 | penalized constant feature; 자유 intercept가 아니다 |
| 1 `queries` | \(q\) | stream 내 step 수 |
| 2 `records_visited` | fresh의 실제 cheap 호출 수 | 실제 방문 수의 동등성 감사 포함 |
| 3 `raw_encode_bytes` | fresh cheap 호출 원문의 UTF-8 bytes 합 | off fresh에서 이 encode가 실행된다는 뜻이 아니다 |
| 4 `saved_stage_calls` | 세 stage의 실제 호출 합 fresh − selective | stage별 CPU 비용이 같다는 가정은 하지 않는다 |
| 5 `saved_stage_characters` | 세 stage 실제 입력의 Unicode `len(text)` 합 fresh − selective | byte 수와 구별한다 |
| 6 `exact_probe_bytes` | selective instrumented의 `key_probe_bytes` 합 | exact key 길이 장부; 실제 RAM traffic이 아니다 |
| 7 `encoded_context_payload_bytes` | `value_encode_bytes` 합 + context를 사용한 각 step의 한 번의 context encoding 길이 | context는 step 안에서 memoized되므로 access 횟수를 곱하지 않는다 |
| 8 `admission_attempts` | selective의 admission 진입 수 | 거절 후보도 포함한다 |
| 9 `policy_control_actions` | P8 선언 control action 수 | off 경로의 CPU instruction 수가 아니다 |

`raw_encode_bytes`는 방문 원문의 길이 feature다. Phase09 off fresh에서는
계측만을 위한 encode가 삭제되었으나 selective에는 raw exact key와 정책
계산을 위해 남는다. 따라서 이 feature의 의미를 양쪽에 같은 encoding 비용이
발생한다고 해석하면 틀린다. 나머지 공통 검증·렌더 비용도 두 실행의 차이에서
정확히 소거된다고 가정하지 않는다.

Stage별 호출 절약을 분리하지 않고 합치는 것은 complete hit에서 생기는
공선성을 줄이는 명세 선택이다. 합계 feature 역시 충분통계라는 보장은 없다.
다른 feature 사이의 공선성도 허용한다.

실제 코드 [features.py](features.py)는 원래 P8 ledger를 untimed branch
witness로 사용하기 전에 Phase09의 exact observation·호출 trace·policy
trace·prefix state 동등성을 다시 검사한다. 이때 수행하는 gold 검사와
family 보고는 feature 값의 계산과 분리되어 있다. 주 timing process는
feature extractor나 감사 wrapper를 import하지 않는다.

## 3. 고정 ridge 추정식과 증명 가능한 성질

개발 자료 \(n=144\)개는 알려진 Phase09 36개 stream을 길이
\(1,4,12,36\)으로 잘라내거나 순환시킨 것이다. 144개의 독립 대화가 아니다.
개발 diagnostic의 leave-family-out split은 같은 base stream의 길이 변형을
분리해 train/test에 넣지 않는다. 이 diagnostic으로 feature, \(\lambda\),
threshold를 다시 선택하지 않는다.

단 한 calibration session에서 구한 \((d_i,f_i)\), \(f_i>0\)에 대해

\[
 z_{ij}=x_{ij}/f_i,\quad
 s_j=\begin{cases}
 \sqrt{n^{-1}\sum_i z_{ij}^2},&\sum_i z_{ij}^2>0,\\
 1,&\text{otherwise},
 \end{cases}\quad
 Z_{ij}=z_{ij}/s_j,\quad y_i=d_i/f_i.
\]

고정 \(\lambda=0.01\)에서

\[
 \theta=(Z^TZ/n+\lambda I)^{-1}Z^Ty/n,\qquad
 \beta_j=\theta_j/s_j,\qquad
 \widehat d(X)=\sum_{j=0}^9\phi_j(X)\beta_j.
\]

Holdout 예측에는 \(f_i\)나 다른 holdout 시간이 필요 없다. \(f_i\)는
개발 loss의 scaling과, 예측을 동결한 뒤 평가 error를 계산할 때만 사용한다.
구현은 [time_model.py](time_model.py)의 `fit`, `predict`다.

### 정리 T1 — 같은 문제의 가중 최소제곱 표현과 유일성

위 \(\beta\)는 다음 목적함수의 유일한 최소점이다.

\[
 J(\beta)=\frac1n\sum_i
 \left(\frac{d_i-x_i^T\beta}{f_i}\right)^2
 +\lambda\sum_j(s_j\beta_j)^2.
\]

**증명.** \(\theta_j=s_j\beta_j\)는 모든 \(s_j>0\)이므로 가역이다.
이를 \(n^{-1}\|y-Z\theta\|_2^2+\lambda\|\theta\|_2^2\)에 대입하면 위
식이 된다. 임의의 \(v\ne0\)에 대해
\(v^T(Z^TZ/n+\lambda I)v=\|Zv\|_2^2/n+\lambda\|v\|_2^2>0\).
따라서 positive definite이고 유일한 해가 normal equation으로 주어진다. □

Constant feature도 penalty를 받는다. 모든 개발 값이 0인 feature의
\(Z\)열·rhs는 0이므로 그 \(\theta_j=\beta_j=0\)이다. L2 train loss를
최적화한다고 L1 holdout error가 최소화되는 것은 아니다.

### 정리 T2 — 공선성이 있어도 정규화 행렬의 조건수는 제한된다

0이 아닌 열 수를 \(p_*\le10\)이라 두면 정확한 산술에서

\[
 \kappa_2(Z^TZ/n+0.01I)
 \le\frac{p_*+0.01}{0.01}\le1001.
\]

**증명.** \(A=Z^TZ/n\)는 positive semidefinite다. RMS 정의에 의해
활성 열의 \(A_{jj}=1\), 0인 열은 \(A_{jj}=0\)이므로
\(\operatorname{tr}(A)=p_*\). 모든 고유값은 비음수이며 최대값은
trace 이하이다. \(A+\lambda I\)의 고유값은 \([\lambda,p_*+\lambda]\)에
속한다. □

이것은 exact arithmetic의 행렬 조건수 경계다. 소수점 구현의 전체 오류
증명이나 예측 신뢰도 경계가 아니다. `fit`은 normal-equation residual을
별도로 기록한다. 완전히 같은 표준화 열 10개는 이 상한을 달성할 수 있고,
[counterexamples.py](counterexamples.py)가 그 rank-one 사례를 검사한다.

### 정리 T3 — 양의 feature 단위 변환에 대한 불변성

각 feature를 \(x'_{ij}=c_jx_{ij}\), \(c_j>0\)로 재표현하면 활성 열에서
\(s'_j=c_js_j\), \(Z'=Z\), \(\beta'_j=\beta_j/c_j\)이다. 0인 열의
계수는 양쪽 모두 0이다. 따라서 \({x'}^T\beta'=x^T\beta\).
이는 단위만 바꾸는 경우의 성질이며, 새 feature를 추가·삭제하거나 비선형
변환하면 같은 예측기가 된다는 뜻이 아니다. □

## 4. Baseline과 동결된 가설 판정

예측 baseline은 다음 세 가지다.

\[
 \widehat d_0=0,\qquad
 \widehat d_q=q\operatorname{median}_{i\in train}(d_i/q_i),\qquad
 \widehat d_P=a\,\Delta P8(X),
\]

\[
 a=\max\left(0,
 \frac{\sum_i (\Delta P8_i/f_i)(d_i/f_i)}
      {\sum_i(\Delta P8_i/f_i)^2}\right).
\]

마지막 분모가 0이면 \(a=0\)으로 둔다. 이는 intercept 없는 단일 scalar
가중 최소제곱의 비음수 제약 해다. \(P8\) 자체는 CPU 단위가 아니며,
이 scalar 보정도 CPU와 논리 장부의 관계를 증명하지 않는다.

평가 session \(e\)의 주 error는 48개 **모든** stream에 같은 가중치를 준다.

\[
 E_m^e=\frac1{48}\sum_{i=1}^{48}
 \frac{|\widehat d_{m,i}-d_i^e|}{f_i^e}.
\]

원본과 재현 session 양쪽에서

\[
 0<\min(E_0^e,E_q^e,E_P^e),\qquad
 E_{model}^e\le0.75\min(E_0^e,E_q^e,E_P^e),\qquad
 E_{model}^e\le0.10
\]

를 요구한다. 최고 baseline을 비교 시점에서 계산하는 규칙도 사전에 고정하며,
평가 결과에 따라 predictor를 선택하거나 refit하지 않는다.
최고 baseline error가 0이면 model error도 0이더라도 numerical 조건은
실패로 처리한다. 완벽한 baseline과의 동률을 25% 개선으로 인정하지 않는다.

부호 검사는 별도 조건이다. 각 session·stream의 paired 차이에 대해
2-round cycle을 단위로 4,000번 bootstrap하여 percentile 95% interval
\([L_i^e,U_i^e]\)를 계산한다. 분모 \(f_i^e\)는 관측된 값을 고정한다.

\[
 \ell_i^e=
 \begin{cases}
 \text{speedup},&U_i^e/f_i^e<-0.03,\\
 \text{slowdown},&L_i^e/f_i^e>+0.03,\\
 \text{unresolved},&\text{otherwise}.
 \end{cases}
\]

두 session 모두 같은 resolved label인 집합 \(R\)만 부호 판정에 사용한다.
그 안의 speedup/slowdown 수를 \(n_-,n_+\)라 두고, \(\widehat d<0\)이면
speedup, 0을 포함한 나머지는 slowdown으로 예측한다.

\[
 BA_m=\frac12\left(
 \frac{\text{correct speedups}_m}{n_-}+
 \frac{\text{correct slowdowns}_m}{n_+}\right).
\]

Joint H10 지지는 위 두 session의 numerical 조건에 더해
\(n_-,n_+\ge4\), \(BA_{model}\ge0.75\), 그리고
\(BA_{model}\ge\max(BA_{rawP8},BA_{always\ slowdown},BA_q)+0.10\)을
모두 요구한다. `scoring.py`가 함께 표시하는 calibrated P8의 부호는
\(a>0\)이면 raw P8, \(a=0\)이면 always slowdown과 같으므로 이 최고
baseline의 값을 바꾸지 않는다.
BA는 정수 correct counts와 class counts로 만든 정확한 유리수로 계산하고,
판정은 \(BA_{model}\ge3/4\), \(BA_{model}-BA_{best}\ge1/10\)을 정확히
비교한다. 표시용 float를 threshold 비교에 다시 사용하지 않는다. 예를 들어
class counts가 4/15이고 model correct counts가 4/10, baseline이 4/7이면
BA는 각각 \(5/6\), \(11/15\)로 차이가 정확히 \(1/10\)이어서 경계에
포함된다. Float 합산의 반올림 때문에 이를 탈락시키면 원래 수학 조건을
구현하지 못한 것이다. 이 구현 경계 정정은 calibration 명령을 시작한 뒤
그 결과를 회수·열람하기 전, 새 holdout과 시간 label을 읽지 않고 발견한
별도 구성 반례에 따른 것이며 규칙 변경이 아니다. 실제 timing worker가
발견 당시에도 실행 중이었다고 단정하지 않는다.

어느 class가 4개 미만이면 부호 질문은 이 규칙에서 `unidentified`이며,
joint H10은 성립했다고 결론내리지 않는다. 조건을 만족하지 않는 결과는
이 feature·fit·평가 규칙의 지지가 없다는 결론이다. 모든 시간 예측기의
불가능성 정리가 아니다.
Numerical 조건이 어느 session에서라도 실패하면 최상위 결론은
`not_supported_numerical_rule`로 먼저 기록한다. Sign class 부족은 그와 별도
field로 보존한다. Numerical 조건을 모두 통과했지만 class가 부족한 경우에만
`not_established_sign_classes_insufficient`를 최상위 결론으로 사용한다.

95% interval은 각 고정 stream의 반복 측정에 관한 cycle-bootstrap
interval이다. 이는 \(d/f\)의 joint ratio interval도, 48개 stream 또는
두 session 전체의 simultaneous 95% 보장도 아니다. Resampling은 cycle의
교환가능성을 근사한다. 시간 drift나 두 session의 공통 환경 효과가 이
가정을 깨뜨릴 수 있다. \(R\)은 측정으로 선택된 subset이므로 제외 수·양
class 수를 모두 보고하며, 전체 48개에 관한 부호 일반화로 바꾸지 않는다.

## 5. Feature 충돌이 부과하는 한계

### 정리 T4 — 같은 feature의 서로 다른 target을 모두 맞출 수는 없다

\(\phi(X)=\phi(Y)\), target이 \(a\ne b\)라고 가정하자. 임의의 결정적
feature-only predictor \(g\)는 공통 값 \(m\)을 출력하므로

\[
 \max(|m-a|,|m-b|)\ge|a-b|/2.
\]

정규화 분모가 양수 \(f_X,f_Y\)이면 더 직접적으로

\[
 \max\left(\frac{|m-a|}{f_X},\frac{|m-b|}{f_Y}\right)
 \ge\frac{|a-b|}{f_X+f_Y}.
\]

**증명.** 삼각부등식 \(|a-b|\le|a-m|+|m-b|\)를 사용한다.
두 정규화 오차가 모두 \(\epsilon\) 이하라면 우변은
\(\epsilon(f_X+f_Y)\) 이하이다. 따라서 위 하한이 필요하다. 절대 오차
경계는 \(f_X=f_Y=1\)인 경우다. □

\(a,b\)의 부호가 반대이면 동일한 부호 출력으로 둘을 모두 맞출 수 없다.
그러나 **실제 feature 충돌만 발견했다고 실제 elapsed-time target이 다름을
증명한 것은 아니다.** 차이가 있는 target이 존재한다는 가정이 정리의
조건이다. 실제 시간 관계를 확인하지 않고 이 조건을 채웠다고 주장하지 않는다.

### 실행 가능한 반례 C1 — 같은 10개 값, 다른 원문·regex 입력

`counterexamples.py`는 entity `aa`를 `[]`로 바꾸고 대응하는 set/query를
같은 길이로 바꾼다. 다른 entity는 `bb`, 1,600-byte deep noop quote와
4-step 반복은 같다. 실제 feature vector는 두 경우 모두 다음과 같다.

```text
[1, 4, 12, 6728, 9, 14022, 5055, 494, 1, 56]
```

하지만 parser·scope가 만드는 entity regex는 `(?:aa|bb)`와
`(?:\[\]|bb)`로 길이도 9와 11이다. 실제 raw execution trace도 다르다.
따라서 10개 aggregate 값은 실제 실행의 모든 문자열 입력을 재구성하지
못한다. 이 반례의 시간 관계는 **미측정**이다. regex source 길이 차이만으로
어느 쪽이 빠르다는 결론은 내리지 않는다.

## 6. Feature는 정책의 충분 상태도 아니다

### 실행 가능한 반례 C2 — 같은 aggregate, 다른 삽입 순서와 다음 재사용

각 public history에 두 짧은 set과 하나의 deep noop quote를 넣는다.
Quote \(A,B\)는 서로 다른 20,000-byte 원문, \(C\)는 30,000-byte 원문이다.
Entities는 `aa`,`bb`; context 길이 85, complete payload 길이 154다.
따라서 다음 값이 실제 고정 정책에서 계산된다.

| 항목 | 보관 크기 | surplus | 초기 hits |
|---|---:|---:|---:|
| A, B 각각 | 20,319 | 19,697 | 0 |
| C | 30,319 | 29,697 | 0 |

`A,B`와 `B,A`는 10개 feature가 모두 같지만 insertion order가 다르다.
둘 다 다음 \(C\)를 주면 총 70,957은 65,536 한도를 넘는다. A와 B의
density가 같으므로 오래 삽입된 한 개를 victim으로 고른다. C의 29,697
surplus가 victim의 19,697보다 커서 삽입된다. 결과는 각각 `B,C`와 `A,C`다.

`A,B,C`와 `B,A,C`의 feature도 여전히 동일하다.

```text
[1, 3, 9, 70246, 0, 0, 20085, 717, 3, 88]
```

이제 양쪽에 같은 \(A\)를 붙이면 첫 stream의 누적 saved stage calls는
0, 두 번째는 3이다. 따라서 \(\phi(prefix)\)만으로 다음 정책 전이나 호출
절약을 결정할 수 없다. 모든 prefix에서 올바른 instrumented/off 구현의
Obs·실제 trace·policy state는 서로 같았다. 이는 erasure 실패가 아니라
**시간 예측용 feature가 정책 상태를 의도적으로 압축한 결과**다.

이 반례도 elapsed time을 재지 않는다. 호출 수 차이를 CPU 시간차 부호의
증명으로 사용하지 않는다. offline predictor는 완료된 전체 stream의
feature를 받으므로 이 반례가 곧 현재 평가의 실패라는 뜻도 아니다.

## 7. 미래가 없는 prefix에서 최종 손익을 보장할 수 없는 이유

### 정리 T5 — 종료 시점과 미래 이득을 모르면 보편적 부호 보장이 없다

추상 비용 모형에서 어떤 공통 prefix 직후 selective가 양의 최초 비용
\(I>0\)을 지불했고, 앞으로 반복할 때마다 양의 순절약 \(h>0\)을 얻을 수
있다고 가정한다. 지금 종료하면 최종 차이는 \(I>0\)이다. 동일 prefix
뒤에 \(k>I/h\)회의 반복을 붙이면 차이는 \(I-kh<0\)이다. 동일 prefix만
본 결정적 predictor는 두 continuation에 같은 부호를 출력하므로 둘 중
하나를 틀린다. □

이 정리는 **양의 투자·반복 순절약을 가정한 추상 비용 정리**다. Python
실행에서 모든 warm hit의 실제 CPU 순절약이 양수라는 정리는 아니다.
실행 반례는 \(I=4,h=1,k=5\)의 유리수 산술로 4와 −1을 확인한다.

Phase08의 최초 투자 후 종료 반례, cheap를 먼저 지불한 뒤 남은 stage만
재사용하는 경계, 과거 인기 고착, 같은 길이의 다른 원문, 동시 보관 용량
제약은 Phase10에서도 그대로 남는다. D8은 no-directory 대비 작업점수
정리였으며 CPU 시간 정리가 아니었다. 현재 회귀 predictor가 이 경계를
제거하거나 online oracle을 만드는 것은 아니다.

## 8. 시간 가산성과 CPU 단가의 비식별성

\(\widehat d=x^T\beta\)는 선형 예측식이다. 다음을 가정하지 않는다.

- 각 feature가 서로 겹치지 않는 실제 CPU 작업 단위를 센다.
- 하나의 작업에 환경과 순서에 무관한 고정 단가가 있다.
- 공통 snapshot·render 작업의 시간이 두 방법에서 정확히 상쇄된다.
- allocation, GC, runtime cache, locality, 분기의 상호작용이 없다.

실제 \(d=x^T\beta+r\)라는 표현만 있으면 임의의 \(c\)에 대해
\(d=x^T(\beta+c)+(r-x^Tc)\)도 같다. Residual을 제한하는 추가 구조나
intervention 없이는 각 계수의 인과적 CPU 단가를 식별할 수 없다.
설계행렬이 rank deficient이면 loss의 선형 예측 부분도 별도 coefficient
해석을 허용하지 않는다. Ridge가 penalty로 하나의 해를 고르는 사실은
이 식별 문제를 해결하지 않는다.

### 실행 가능한 반례 C3 — 중앙값은 가산적이지 않다

동일 round의 두 추상 시간차 배열을 `(0,0,100)`, `(0,100,0)`이라고 하면
각 중앙값의 합은 0이다. round별 합 `(0,100,100)`의 중앙값은 100이다.
따라서 per-round 시간이 가산적이라는 추가 가정을 주더라도

\[
 \operatorname{median}(A+B)\ne
 \operatorname{median}(A)+\operatorname{median}(B)
\]

일 수 있다. 실제 stream별 interval과 전체 workload interval은 scheduling과
주변 상태도 다르다. 전체 workload secondary 결과를 stream target 합의
필연적 재현으로 요구하거나, 총 차이를 feature별 정확한 CPU 기여로 분해하지
않는다. \(\sum_i\widehat d_i\)를 계산할 수 있다는 것은 예측식의 대수적
성질일 뿐, 실제 중앙값의 가산성 증명이 아니다.

## 9. 부호 정확도와 수치 오차 사이의 정확한 경계

### 정리 T6 — 점별 오차 경계가 있으면 큰 예측의 부호는 보장된다

\(|\widehat d-d|\le\epsilon\)이고 \(|\widehat d|>\epsilon\)이면
\(\widehat d\)와 \(d\)의 부호가 같다. 0을 slowdown으로 분류하는
규칙에서도 \(|d|\ge\tau f>0\)인 항목을 잘못 분류했다면

\[
 e=|\widehat d-d|/f\ge|d|/f\ge\tau.
\]

**증명.** 두 수가 반대 부호이거나, 음의 \(d\)를 0으로 예측했다면 둘
사이의 거리는 \(|d|\) 이상이다. 첫 명제는 \(d\)가 반대 부호일 때
\(|\widehat d-d|\ge|\widehat d|\)여야 하므로 모순이다. □

따라서 모두 material인 집합 \(A\)의 오분류 수 \(M_A\)는

\[
 M_A\le\frac1\tau\sum_{i\in A} e_i.
\]

그러나 개발 residual의 최댓값은 새 입력에서의 점별 \(\epsilon\) 보장이
아니다. 그러한 전이에는 분포나 regularity에 대한 추가 가정이 필요하다.
또한 전체 평균 error만 작다고 소수 class의 오분류가 적은 것도 아니다.

실행 반례 C4는 정규화 target이 −0.04인 4개와 +0.04인 44개에 모두
+0.04를 예측한다. 평균 절대 error는 약 0.006667로 작지만 balanced
accuracy는 0.5다. 그래서 numerical 조건과 양 class를 요구하는 sign
조건을 별도로 둔다. 이 숫자는 **구성한 수학 반례**이며 새 timing 결과가
아니다. `counterexamples.py`는 유리수 grid 244개에서 material sign
error 경계도 직접 확인한다.

## 10. 보존 승계와 증명 범위

Phase09의 보존 관찰 \(Obs\)는 `cost`를 제외한 결과 field 전체와 정확한
rendered UTF-8 bytes다. \(\pi\)는 configuration, resident exact keys와
immutable stages·encoded lengths, hits·surplus·size·insertion order,
directory, retained bytes, next order를 포함하는 다음 결정 상태다.
Phase09의 조건부 정리는 각 입력 prefix에서

\[
 Obs(Run_{on}(prefix_t))=Obs(Run_{off}(prefix_t)),\qquad
 \pi(S_t^{on})=S_t^{off}
\]

를 주장한다. 마지막 등식의 우변은 off 경로의 policy projection과 같은
표현이며, report peaks나 통계 ledger는 포함하지 않는다. 정확한 정의와
귀납 증명은 [Phase09 THEORY](../phase09/THEORY.md)에 있다.

Phase10은 이 실행 함수를 source hash로 검증하고 그대로 호출한다.
Feature replay와 fitting은 해당 timing 실행과 다른 과정이고, predictor의
결과를 selector에 넣지 않는다. 따라서 동일 입력·초기 상태·namespace에
대해 기존 Obs·policy transition을 바꾸는 새 경로가 없다. 이 승계는
finite builtin JSON 입력, UTF-8 encodable 문자열, pure/fixed parser와
encoding, single-thread, 입력·코드·상수의 외부 변경 없음, 충분한 자원이라는
Phase09 가정을 그대로 전제한다. 자원 고갈, tracing hook, side-effect가
있는 custom object, concurrent mutation의 동등성은 주장하지 않는다.

Gold correctness는 제한된 합성 의미 모형에 관한 별도 감사다. 이 이론은
실제 자연어 의미 정확성, LLM token·요금·답변 품질, 임의 미완료 요청이나
실행 증거의 일반적 보존을 추가로 증명하지 않는다. 운영 SOOM을 바꾸지
않는다.

## 11. 재현 가능한 반박 지점

```bash
python research/phase10/counterexamples.py --output /tmp/soom-phase10-counterexamples.json
```

출력은 [counterexample_results.json](counterexample_results.json)과 비교할
수 있다. 원래 출력은 새 파일로 만들며 기존 결과를 덮어쓰지 않는다.
이 실행은 별도 구성 입력만 사용하고 Phase10 holdout을 열지 않는다.
원래 instrumented 함수의 내부 timer는 실행될 수 있으나 그 `local_seconds`를
버리며 새 timing 관측이나 비교값으로 사용하지 않는다.

반박의 우선순위는 다음과 같다.

1. `features.vector`의 실제 whitelist가 문서의 \(\phi\)와 같은지 확인한다.
2. Ridge의 `fit`·`predict`가 위 식을 따르며 holdout timing이 들어가지 않는지
   확인한다.
3. 실제 feature 충돌·policy order 반례와 추상 비용 반례의 경계를 확인한다.
4. 새 timing에서 수치·부호 조건을 각각 재집계한다. 동일 자료의 반복을
   독립 대화로 바꾸지 않는다.

Feature 충돌은 보편적 성능 보장을 위해 추가 가정이 필요하다는 근거다.
고정 합성 평가에서 이 모형이 유용한지는 이 문서의 수학만으로 결정하지 않는다.
