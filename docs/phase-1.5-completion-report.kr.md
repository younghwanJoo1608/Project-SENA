# Phase 1.5 완료 기록

작성일: 2026-06-11

## 요약

Phase 1.5는 Project-SENA의 최소 제어 루프를 실제 사용 가능한 수준으로 굳히는 단계였다. 이 단계에서 Unity client, inference-server, desktop-agent 사이의 메시지 흐름을 안정화하고, 실패 복구 UX, 세션 운영성, desktop tool 확장성을 검증했다.

핵심 루프:

```text
Unity client -> inference-server -> desktop-agent -> 사용자 승인 -> 실행 -> tool_result -> Unity 표시
```

## 완료된 기능

- Unity Editor와 standalone 앱에서 기본 채팅/승인/실행 루프 검증
- 7680x2160 초고해상도 환경에서 ChatPanel 비율 검증
- inference-server 미기동, desktop-agent 미기동, 승인 거절, tool 실행 실패 UX 정리
- session별 중복 message 처리와 pending approval 중복 방어
- `새 대화` 버튼을 통한 session reset 및 pending approval 취소
- `open_app` 기반 메모장 실행
- `get_active_window` 기반 활성 창 조회
- `type_text` 기반 텍스트 입력
- 직전에 연 앱 대상과 이미 열려 있는 메모장 대상 입력 지원
- `capture_screen` 기반 전체 화면, 활성 창, 특정 창 PNG 저장
- Windows DPI scaling 환경에서 창 캡처 좌표 보정
- 캡처 파일 보관 정책과 자동 정리 구현
- PC 재부팅 후 실행 절차 README 문서화
- Phase 1.5 통합 회귀 테스트 체크리스트 작성

## 검증된 desktop tools

| Tool | 승인 정책 | 현재 상태 |
| --- | --- | --- |
| `open_app` | 사용자 승인 | 메모장 실행 검증 완료 |
| `get_active_window` | 자동 실행 | 활성 창 title/process 반환 검증 완료 |
| `type_text` | 사용자 승인 | 메모장 대상 입력 검증 완료 |
| `capture_screen` | 사용자 승인 | 전체 화면/활성 창/메모장 창 캡처 검증 완료 |

## 테스트 결과

마지막 검증 기준:

```text
desktop-agent: 36 passed
inference-server: 18 passed
```

수동 검증:

- standalone 앱에서 `메모장 열어줘` 승인 후 실행 확인
- `현재 창 뭐야?` 응답 확인
- `메모장에 안녕하세요 입력해줘` 승인 후 입력 확인
- `전체 화면 캡처해줘`, `현재 창 캡처해줘`, `메모장 캡처해줘` 저장 결과 확인
- DPI 보정 후 활성 창/메모장 창 캡처 위치 정상 확인

## 운영 문서

- `README.md`
- `README.KR.md`
- `docs/phase-1.5-roadmap.kr.md`
- `docs/phase-1.5-regression-checklist.kr.md`
- `docs/capture-retention-policy.kr.md`
- `shared-protocol/protocol-v0.1.md`

## Known Limitations

- LLM, TTS, Vision은 아직 stub/rule-based 구조다.
- `type_text`와 `capture_screen`의 자연어 planning은 제한된 규칙 기반이다.
- `target_app`은 현재 메모장 중심으로 검증되어 있다.
- 창 캡처는 visible capture 기반이다. 최소화된 창이나 일부 하드웨어 가속/보안 창은 캡처하지 못할 수 있다.
- 캡처 파일 자동 정리는 로컬 파일 기준이며, UI에서 보존/삭제를 직접 관리하는 기능은 아직 없다.
- Unity client의 코드 분리는 Phase 2 이전에 더 정리할 여지가 있다.

## Phase 2로 넘길 항목

- 실제 Live2D 모델 도입
- 캐릭터 감정 상태와 표정/모션 연동
- STT 입력과 TTS 출력 연결
- `capture_screen` 결과를 Vision adapter로 전달하는 화면 인식 루프
- rule-based tool planning을 LLM 기반 planner와 안전 정책으로 확장
- 설정 파일 기반 서버 주소/포트 관리
- desktop tool 대상 앱 확장과 창 선택 UX

## 완료 판단

Phase 1.5의 목표였던 안정성, 복구성, desktop tool 확장 검증은 충족된 것으로 본다. 이후 작업은 `develop`에 병합한 뒤 Phase 2 브랜치에서 진행한다.
