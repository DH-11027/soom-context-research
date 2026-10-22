# 문헌과 이 연구에서 사용한 범위

논문은 개념적 근거와 비교 대상이다. 이 저장소는 아래 논문의 모델·벤치마크를 재현한 저장소가 아니며 그 성과를 본 연구의 측정 결과로 사용하지 않는다. 외부 논문 본문·데이터는 포함하지 않고 원 출처로 연결한다.

| 문헌 | 연결되는 질문 | 본 연구의 사용 범위 |
|---|---|---|
| Lin & Bilmes, 2011, [A Class of Submodular Functions for Document Summarization](https://aclanthology.org/P11-1052/) | coverage와 중복 감소 | Phase 01 max-coverage의 구조를 이해하는 배경. 실제 LLM 답변 효용의 부분모듈러성을 가정하지 않음 |
| Krause & Guestrin, UAI 2005, [Near-optimal Nonmyopic Value of Information in Graphical Models](https://www.cs.cmu.edu/~guestrin/Publications/UAI2005/uai2005.pdf) | 정보 이익의 조건과 보완성 | XOR 반례와 정보 획득에 필요한 가정 구분 |
| [RECOMP](https://arxiv.org/abs/2310.04408) | 질문에 맞춘 검색 맥락 압축 | 질문 조건부 압축과 선택적 추가라는 관련 방향. 학습 압축기 미실행 |
| [LongMemEval](https://arxiv.org/abs/2410.10813) | 장기 대화에서 추출·시간·갱신·보류 | 실제 장기 대화 평가가 필요하다는 배경. 벤치마크 미실행 |
| Angelopoulos et al., [Learn then Test](https://arxiv.org/abs/2110.01052) | 후보 정책 선택과 위험 제어 | Phase 02의 보정·다중검정 관점. 합성 표본을 실세계 보장으로 확장하지 않음 |
| [CODI-CRAC 2021 논문](https://aclanthology.org/2021.codi-sharedtask.8/) | 참조 대상·담화 지시 해석 | Phase 03이 단순 유사도보다 어려운 관계 추출 문제임을 구분. 해당 시스템·데이터 미실행 |
| [GAP, 2018](https://aclanthology.org/Q18-1042/) | 모호한 참조와 평가 | 관련 평가 방향. GAP 데이터 미실행·미포함 |
| [Sufficient Context](https://arxiv.org/abs/2411.06037) | 관련성과 답변에 충분함의 차이 | Phase 04의 질문 충분성 관점. 논문의 자동 평가기를 구현한 것은 아님 |
| [CompAct, EMNLP 2024](https://aclanthology.org/2024.emnlp-main.1194/) | 질의응답을 위한 능동 맥락 압축 | 질문 중심 압축이라는 관련성. 해당 파이프라인 미재현 |
| Cousot & Cousot, 1977, [Abstract Interpretation](https://cs.nyu.edu/~pcousot/COUSOTpapers/POPL77.shtml) | 가능한 상태를 보수적으로 근사하기 | Phase 05의 추상 의미·포함 관계 개념. 자연어 parser soundness를 이 논문이 보증하는 것은 아님 |
| Clarke et al., 2000, [Counterexample-guided Abstraction Refinement](https://www.cs.cmu.edu/~emc/papers/Conference%20Papers/Counterexample-guided%20Abstraction%20Refinement.pdf) | 필요한 부분의 의미 정밀화 | 영감과 비교 개념. 여기의 고정 패턴 상세 파서는 완전한 CEGAR 시스템이 아님 |
| Weiser, [Program Slicing](https://faculty.cc.gatech.edu/~harrold/6340/cs6340_fall2009/Readings/Weiser.Slicing.TSE.pdf) | 질문의 출력에서 거꾸로 의존성 추적 | Phase 05를 해석하는 프로그램 분석 배경. 원 논문의 알고리즘을 그대로 재현하지 않음 |

새 연구에서 특정 논문의 정리나 성과를 사용한다면 원문과 가정을 다시 확인하고 해당 실험의 출처를 구체적으로 적는다. 이 목록은 선행연구 전체를 망라하거나 본 알고리즘의 신규성을 입증하는 문헌조사가 아니다.
