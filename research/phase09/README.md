# Phase09 — 계측을 제거해도 비계측 fresh 대비 속도 우위는 얻지 못했다

**완료된 부정 결과:** 새 합성 36 stream / 432 step에서 비계측 selective는 비계측 fresh보다
원본 **17.93%**, 별도 재현 **16.78%** 느렸다. 주 지표는 round별 log-ratio 중앙값을 지수화한 비율이다.
관찰·정책 상태·실제 실행 순서의 on/off 동등성은 통과했다. 계측 제거로 두 방법 모두
빨라졌으나 상대적인 속도 우위는 얻지 못했다. 고정 환경·합성 자료 범위의 결론이다.

직접 기준: Phase08 공개 완료 `efba3224dd09d5c5e2bf9d9be11734fa10b32502`.
기존 파일과 SOOM 운영 변경 없음. 추가는 이 폴더뿐이다.

## 읽기 순서

1. [HANDOFF_BACK.md](HANDOFF_BACK.md): RETURN_TEMPLATE에 따른 전체 인수인계.
2. [PROTOCOL.md](PROTOCOL.md): 새 결과 전 고정한 가설·40-round timing·실질 3% 기준.
3. [THEORY.md](THEORY.md): Obs/π, 계측 비간섭·dead-size 보조정리, prefix 귀납 증명·반례.
4. [erasure_manifest.json](erasure_manifest.json): 원본에서 지운 문장과 source/output hash.
5. [POSTFREEZE_REVIEW.md](POSTFREEZE_REVIEW.md), [DATA_REVIEW.md](DATA_REVIEW.md): 별도 재현·원시 행·분포 검토.

## 주요 증거

- [주 결과](results/holdout_results.json), [원시 행](results/holdout_rows.json.gz), [정책 상태](results/holdout_states.json.gz).
- [원본 시간 전체 표본](results/timing.json), [별도 재현 시간](reproduction_timing.json).
- [별도 재현 receipt](reproduction_receipt.json), [독립 재집계](recount_results.json).
- [가설 판정과 실행 성공의 구분](conclusion.json), [최종 동결·포장 확인](FINAL_CHECKS.json).
- [이전 단계 재현](INHERITANCE_AUDIT.md), [동결 전 개발 검사](DEVELOPMENT_AUDIT.md).
- [동결 hashes](freeze.json), [로컬 freeze commit](freeze_commit.json), [원본 로컬 Git 객체](pre_evaluation.bundle).

## 재현

Python 3.12.14 / CPython / Linux x86_64, 표준 라이브러리만 사용했다.
저장소 root에서 실행하며 새 output 경로를 사용한다. 실행기는 기존 결과를 덮어쓰지 않는다.

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
git bundle verify research/phase09/pre_evaluation.bundle
```

첫 네 명령과 bundle verify는 새 timing을 시작하지 않는다. `--run`은 별도 correctness
실행을 통과한 뒤 독립 interpreter에서 한 고정 timing session을 실행한다.
프로파일러·monkeypatch·호출 수 계측은 주 timing에 들어가지 않는다.
8개 결정적 산출물은 byte-identical이어야 하지만 시간과 receipt 시각은 같을 필요가 없다.

Source-specific 계측 제거의 동등성은 조건부 수학 명제이고, 실행시간의 대소는 실험 명제다.
실제 자연어 정확성, 미완료 요청·실행 증거의 일반적 보존, LLM 토큰·요금·품질,
물리 메모리나 다른 하드웨어의 성능은 검증하지 않았다. 로컬 동결은 외부 사전 등록이 아니다.
