# 게시 시 재현 기록

상태: **복사본 재현 통과**. 기록 시각: 2026-10-22 09:08:22 UTC 시작.

## 실제로 실행한 것

환경은 Windows, CPython 3.12.13이다. 다음 명령을 새 공개 연구 패키지에서 실행했다.

```bash
python tools/verify_archive.py
python tools/reproduce.py --phase all --reports
```

- 원래 연구 파일 59개, 14,076,747 bytes의 보관 SHA-256 일치.
- 기존 동결 프로토콜의 코드·데이터 binding 18개 일치.
- 실험·감사·보고서 생성 subprocess 17개 모두 exit 0.
- 재생성한 JSON 14개가 명시된 환경 필드를 제외하고 보관 결과와 정확히 일치.
- revision02와 기존 corpus의 2,688개 모드·질문 출력 비교 일치.
- HTML·노트북 5단계 재생성 성공. 원래 보관 자료는 실행 전후 동일.

기계 판독용 기록은 [reproduction-receipt.json](reproduction-receipt.json)이다. 개별 실행 시간은 한 번의 로컬 실행값이며 성능 벤치마크로 사용하지 않는다. 원시 stdout 로그와 복사본은 실행 환경의 `.reproductions/` 아래에 남고 Git에는 포함하지 않는다. 같은 재현 명령으로 새 로그를 만들 수 있다.

## 검증 범위

이 실행은 저장소의 코드와 결과가 서로 맞고 연구 과정을 다시 계산할 수 있음을 확인했다. Linux/macOS 실기동, 실제 LLM 답변·토큰·지연, 독립 자연어 benchmark, SOOM 운영 적용은 이번 게시 검증에 포함하지 않았다.

의도한 실패도 재현했다. Phase 02의 보정 정책 미채택, Phase 03의 사후 라벨 감사, Phase 05 최초 reducer의 축소 0건, 수정 reducer의 기존 corpus 추가 축소 0건은 정상적으로 보관 결과와 일치한 **부정 결과**다.
