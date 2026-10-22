# Phase 06 — 영향 범위만 아는 미해석 사건

**결론:** 올바른 may-write 상한을 얻으면 그 밖의 질문에 답하는 범위를 넓힐 수 있다.
이번 원문 분석기는 정해진 문법에 가까운 새 192질문에서 86건을 실제로 더 줄였지만,
표현을 바꾼 192질문에서는 추가 축소가 0건이었다. 두 조건의 출력+전체 원문 처리
바이트 proxy는 각각 **4.99%, 5.96% 증가**했다. 실제 LLM 토큰·비용·품질은 미측정이다.

## 읽기 순서

1. [다음 연구자 반환 문서](HANDOFF_BACK.md): 결론, 정확한 수치, 재현, 한계, 다음 한 가지 제안.
2. [기존 연구 감사](BASELINE_AUDIT.md): 빈 인증 결과를 놓치는 평가기 공백과 실제 재현.
3. [수학적 계약](THEORY.md): frame condition, scoped TOP, 보존 증명과 반례.
4. [실행 전 계획](PROTOCOL.md), [동결 기록](freeze.json), [평가 자료 작성 경계](HOLDOUT_AUTHOR.md).
5. [새 평가 결과](results/holdout_results.json), [기존 자료 회귀](results/regression_results.json),
   [유한 모형·평가기 검사](results/audit.json), [로컬 시간](results/timing.json).
6. [동결 후 별도 검토](POSTFREEZE_REVIEW.md): 96개 gold 상태의 별도 산식과 원시 결과 재집계.
7. [사후 수학적 경계](POSTFREEZE_LIMITS.md): scoped TOP의 조건부 최소성, 정확 생략의
   필요충분조건, 원문 의미의 모호성 경계, 정확 인증의 최악 경우 읽기 하한.

## 재현

저장소 루트, Python 3.12 표준 라이브러리만 사용한다. 기존 동결 자료를 덮어쓰지 않는다.

```bash
python tools/verify_archive.py
python tools/reproduce.py --phase 05r2
python research/phase06/holdout_builder.py --check
python research/phase06/run_study.py --run \
  --output /tmp/phase06-reproduction-new \
  --compare research/phase06/results
```

출력 경로는 존재하지 않는 새 디렉터리여야 한다. Windows에서는 `/tmp/...` 대신
`.reproductions/phase06-new` 같은 새 경로를 사용한다. 이미 동결한 `--freeze`는 다시 실행하지 않는다.
development를 별도로 확인하려면 `--dev --output <새 경로>`를 사용한다.

`--compare`는 3개 JSON과 2개 gzip 원시 행 파일을 정확히 비교한다. 시간과 실행
영수증은 환경에 따라 달라진다. 같은 환경의 별도 에이전트 재현 결과는
[reproduction_receipt.json](reproduction_receipt.json)에 있다. 외부 독립 재현은 아니다.

원시 결과는 gzip으로 저장했다. 정답 라벨을 포함한 입력은 `data/holdout.json`,
선택 결과·비용·contract trace는 `results/holdout_rows.json.gz`와
`results/regression_rows.json.gz`에 있다.

```python
import gzip, json
with gzip.open("research/phase06/results/holdout_rows.json.gz", "rt", encoding="utf-8") as f:
    rows = json.load(f)
print(rows[0])
```

## 구현 경계

- `scoped.py`: 원문 분석, scoped TOP, 역방향 선택. gold를 import하지 않는다.
- `evaluate.py`: 별도 gold joint-state 실행, 독립 질문 계약, 엄격한 결과 검사.
- `audit.py`: 반례, 16,128개 유한 모형 비교, 12개 잘못된 출력 mutation,
  6개 범위 문법의 긍정 사례와 18개 부정 최소쌍, 무결성/입력 경계 검사.
- `run_study.py`: 사전 동결, 결과/비용 기록, 비공허성 판정, 반복 재현.
- `development.py`, `holdout_builder.py`: 각각 개발용 작성과 별도 평가 자료 작성.

현재 SOOM 운영 변경은 없다. `certified_model`은 이 작은 계획 상태 모형 안의
singleton 판정이다. 원문 선택과 digest만으로 생략 정당성을 검증하는 reader는
구현하지 않았으며, 원문을 읽는 실제 LLM의 답변 품질을 인증하지 않는다.
