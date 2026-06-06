# Unity Client Phase 1 Setup

Phase 1의 목표는 Unity가 `inference-server:8000`과 통신하고,
`approval_request`를 UI로 보여준 뒤 `approval_result`를 다시 보내는 최소
클라이언트 루프를 완성하는 것이다.

## 이번 단계에서 만드는 것

- 텍스트 입력창과 전송 버튼
- 채팅 로그 표시
- 연결/상태 표시
- 승인 요청 모달
- `user_text -> assistant_text`
- `approval_request -> approval_result -> tool_result`

## 이번 단계에서 아직 안 하는 것

- Live2D SDK 통합
- TTS 재생
- STT 입력
- 화면 캡처 UX
- 데스크톱 펫 모드

## 권장 씬 구성

- `Canvas`
  - `ChatPanel`
    - `TranscriptText`
    - `StatusText`
    - `StateText`
    - `InputField`
    - `SendButton`
  - `ApprovalPanel`
    - `SummaryText`
    - `PromptText`
    - `AllowButton`
    - `DenyButton`
- `ProjectSenaClient`
  - `SenaClientController`
  - `ChatPanelController`
  - `ApprovalPanelController`

## 연결 순서

1. `SampleScene`를 `Main`으로 복제하거나 이름을 바꾼다.
2. `Assets/ProjectSENA/Scripts/Runtime` 아래 스크립트를 임포트한다.
3. `ProjectSenaClient` 빈 오브젝트를 만든다.
4. `SenaClientController`를 붙이고 서버 URL을 `http://127.0.0.1:8000`으로 둔다.
5. 채팅 패널과 승인 패널 오브젝트를 연결한다.
6. `ApprovalPanel`은 기본 비활성화 상태로 둔다.
7. Play Mode에서 텍스트 입력과 승인 요청 루프를 확인한다.

## 확인 시나리오

1. `open notepad` 입력
2. 채팅 로그에 assistant 응답 표시
3. 승인 모달 표시
4. Allow 클릭
5. 메모장 실행
6. `tool_result`와 후속 assistant 응답 표시
