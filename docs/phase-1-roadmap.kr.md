# Phase 1 Roadmap

Project-SENA의 첫 개발 단계 목표는 "데스크톱 한 대에서 최소한의 캐릭터 비서 경험을 끝까지 연결하는 것"이다.

이 단계에서는 완성도보다 경계와 흐름을 먼저 고정한다.

## Phase 1 목표

- 텍스트 대화가 된다.
- 음성 입력이 텍스트로 들어온다.
- LLM 응답이 다시 화면과 음성으로 나온다.
- Live2D 캐릭터가 최소한의 상태 변화를 보여준다.
- 화면 캡처를 서버에 보낼 수 있다.
- PC 조작은 실제 실행 전 승인 흐름까지 확인한다.

## 가장 먼저 할 일

가장 먼저 해야 할 일은 `shared-protocol`의 MVP 메시지 계약을 정하는 것이다.

이유:

- Unity 클라이언트, desktop-agent, inference-server를 병렬로 만들 수 있다.
- 나중에 데스크톱 단일 실행에서 노트북 서버 분리로 넘어갈 때 구조를 덜 흔든다.
- PC 조작 안전 정책을 초기에 강제할 수 있다.

## 개발 순서

1. MVP 범위 고정
2. `shared-protocol` 초안 작성
3. `inference-server` 최소 API 골격 작성
4. `desktop-agent` 최소 도구 계층 작성
5. `unity-client` 최소 UI와 연결 작성
6. 단일 PC 흐름 검증

## 단계별 상세

### 1. MVP 범위 고정

이번 단계에서 포함할 기능:

- 텍스트 입력
- 마이크 입력
- LLM 응답 텍스트
- TTS 재생
- Live2D 기본 표정 또는 상태 변화
- 전체 화면 또는 선택 화면 캡처 1종
- 승인형 PC 조작 1~2종

이번 단계에서 미루는 기능:

- 장기 기억 고도화
- 고급 RAG
- 실시간 상시 화면 감시
- 복잡한 멀티툴 자동화
- 다중 캐릭터 지원

### 2. `shared-protocol` 초안 작성

먼저 정의할 메시지:

- `user_text`
- `speech_input`
- `screen_frame`
- `assistant_text`
- `assistant_state`
- `tts_audio`
- `tool_request`
- `tool_result`
- `approval_request`
- `approval_result`
- `error`

먼저 정할 필드:

- `session_id`
- `message_id`
- `timestamp`
- `source`
- `payload`
- `risk_level`

### 3. `inference-server` 최소 API 골격 작성

첫 단계 구현 목표:

- 메시지 수신 엔드포인트
- 세션별 대화 상태 유지
- 로컬 LLM 호출 어댑터 1종
- TTS 호출 어댑터 1종
- 화면 설명 입력 처리
- 도구 요청 생성 형식 고정

초기 구현은 실제 모델 품질보다 "입력에서 출력까지 끊기지 않는지"를 본다.

### 4. `desktop-agent` 최소 도구 계층 작성

첫 단계 도구:

- `capture_screen`
- `get_active_window`
- `open_app`
- `type_text`

규칙:

- 도구는 전부 구조화된 입력만 받는다.
- 승인 없이 destructive action을 실행하지 않는다.
- 셸 명령 직접 실행은 금지한다.

### 5. `unity-client` 최소 UI와 연결 작성

첫 단계 UI:

- 캐릭터 표시 영역
- 채팅 입력창
- 응답 텍스트 영역
- 마이크 시작/중지 버튼
- 화면 캡처 버튼
- 승인 팝업

첫 단계에서 중요한 것은 디자인보다 상태 전환이다.

### 6. 단일 PC 흐름 검증

검증 시나리오:

1. 사용자가 텍스트를 입력한다.
2. 서버가 캐릭터 응답을 만든다.
3. 응답 텍스트가 UI에 표시된다.
4. TTS가 재생된다.
5. 사용자가 화면 캡처를 보낸다.
6. 서버가 화면을 보고 응답한다.
7. 서버가 도구 요청을 만든다.
8. 사용자가 승인한다.
9. desktop-agent가 도구를 실행하고 결과를 돌려준다.

## Phase 1 완료 기준

- 데스크톱 한 대에서 위 검증 시나리오가 재현된다.
- 세 모듈이 직접 구현에 묶이지 않고 메시지 계약으로 연결된다.
- 도구 실행이 승인 흐름을 거친다.
- 추론 서버를 나중에 노트북으로 옮길 수 있는 구조가 유지된다.

## 다음 단계 준비물

Phase 1이 끝나면 바로 이어서 할 일:

- inference-server를 별도 PC로 분리
- STT/TTS/LLM 교체 가능한 어댑터 구조 강화
- Vision 입력 주기 제어
- 캐릭터 페르소나 설정 파일 분리
- 메모리와 로그 구조 정리

