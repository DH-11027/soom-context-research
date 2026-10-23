# Phase09 — 2026-10-23 별도 계측 제거 연구

**보존은 유지됐고, 전체 속도 개선 가설은 기각됐다.** Phase08 공개 완료
`efba3224dd09d5c5e2bf9d9be11734fa10b32502`를 정확한 기준으로 삼은 연구다.
SOOM 운영 변경은 없다.

새 36 stream /622 step에서 공정한 `fresh_uninstrumented → selective_uninstrumented`
전체 시간의 paired 중앙 변화는 원본 **+23.59%**, 한 번의 별도 재현 **+15.80%**였다.
실제 parser 호출은22.02%, parser 입력 bytes는63.72% 줄었지만 실제 시간 개선으로
이어지지 않았다. 원본·재현의 결정적6파일은 byte-identical이었다.

## 먼저 읽을 문서

1. [HANDOFF_BACK.md](HANDOFF_BACK.md): 결과·수학·재현·한계·다음 한 가지 질문.
2. [PROTOCOL.md](PROTOCOL.md): 결과 전에 동결한 비교·timing·판정 규칙.
3. [THEORY.md](THEORY.md): 관찰/정책 상태의 prefix 보존과 작은 반례.
4. [POSTFREEZE_REVIEW.md](POSTFREEZE_REVIEW.md): 별도 재현과 독립 원시 재집계.
5. [DATA_REVIEW.md](DATA_REVIEW.md): 분모·중복·긴 입력 비중·모든36 stream의 시간.

`results/`에 원시 행과 원시 timing, `freeze.json`과 `pre_evaluation.bundle`에
로컬 동결 증거가 있다. 로컬 동결은 외부 사전 등록이 아니다. 같은 모델의 역할 분리는
외부 독립 자연어 검증이 아니다. 긴 원문은 제한 문법의 noop quote다.

## 빠른 재현

```bash
python research/phase09/run_study.py --verify
python research/phase09/holdout_builder.py --check
PYTHONHASHSEED=0 python research/phase09/run_study.py --run \
  --output /tmp/soom-phase09-new-reproduction \
  --compare research/phase09/results
python research/phase09/recount_results.py \
  --results /tmp/soom-phase09-new-reproduction \
  --output /tmp/soom-phase09-new-recount.json
```

기존 출력 경로는 새 이름을 사용한다. 시간은 동일성 비교 대상이 아니다.
표준 라이브러리·Python3.12.14 환경이며 자세한 측정 범위는 protocol에 있다.

## 기존 다른 Phase09와의 관계

이번 원본/재현 뒤 전달 과정에서 기존 PR #4의 Phase09와 PR #5의 Phase10을 발견했다.
그 구현·결과를 이번 동결 설계에 사용하거나 합치지 않았다. 기존 연구를 보존하는
별도 branch `research/phase09-instrumentation-erasure-20261023`이며 base는 Phase08이다.
상세 경계는 [DELIVERY_CONTEXT.json](DELIVERY_CONTEXT.json)에 기록했다.
