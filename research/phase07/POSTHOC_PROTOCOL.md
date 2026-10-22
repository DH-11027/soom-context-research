# 사후 비용 경계 진단 — 주평가와 분리

작성: 2026-10-22, Phase07 동결 주평가 결과를 읽은 뒤, 아래 진단 실행 전.
주평가에서 실행 수는 줄었지만 P7과 전체 시간은 늘었다. 특히 긴 문장은 cheap
quote이고, 충분히 긴 deep quote의 조건부 이득은 주평가에 포함되지 않았다.
이 진단은 좋은 모집단 평균을 새로 주장하려는 독립 평가가 아니다. 고정한 구현과
사전 비용식의 조건부 경계, 초기 구축 비용, 메모리 경계를 검사한다.
기존 알고리즘·holdout·주평가 결과와 가설 판정을 변경하지 않는다.

두 기록 `[가람.time=8, quote]`와 동일한 time 질문을 8회 반복한다. quote payload는
단일 한글 `가`를 n회 반복한다. cheap quote와 deep quote 두 문법 모두 의미는 noop이며,
후자는 frozen parser의 세 단계를, 전자는 한 단계를 거친다. n은 사전에
`0,32,128,512,2048,8192,24000`으로 고정한다. deep 조건에 한해 정확 용량 산술로
둘이 함께 들어가는 최대 n, 그 다음 n, quote 하나만 들어가는 최대 n, 그 다음 n도
추가한다. 성능을 보고 길이를 고르지 않는다. 각 cell은 새 empty cache다.

C=context bytes, S=set text bytes, L=quote text bytes, r_s와 r_q=각 stage payload 길이,
R=r_s+r_q, m=quote stage 수, T=8이다. 두 항목이 함께 들어가면

\[
\Delta_{cold}=5C+3(S+L)+2R,
\qquad \Delta_{warm}=3C+S+(2-m)L+R.
\]

합계는 cold+(T−1)warm이다. m3이면 Δ8=26C+10S−4L+9R.
quote는 혼자 들어가지만 두 항목 합이 byte budget을 넘으면 이 순회에서 서로
축출되어 매번 cold다. quote가 oversized이면 set만 보관되며

\[
\Delta_{cold,os}=4C+3S+2L+2r_s+r_q,
\quad\Delta_{warm,os}=3C+S+2L+R.
\]

각 cell에서 의미/trace/output 동등, 원래 단계 수, 실제 실행수, hit/eviction/oversize,
계측 비용과 위 식의 차이 0을 검사한다. 시간은 이 진단에서 측정하지 않는다.
여기서 얻은 긍정 조건은 의도적으로 구성한 사후 조건이며 새 독립 일반화 증거가 아니다.
코드와 이 문서의 SHA를 실행 전에 `posthoc/freeze.json`으로 남긴다.
