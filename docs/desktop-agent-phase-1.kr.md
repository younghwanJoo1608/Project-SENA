# Desktop Agent Phase 1

이번 단계의 목표는 `tool_request`를 실제 Windows 로컬 동작으로 연결할 수 있는 최소 실행면을 만드는 것이다.

## 목표

- 추론 서버가 만든 `tool_request`를 데스크톱 측에서 수신할 수 있다.
- 도구별 허용 여부를 정책으로 판정할 수 있다.
- 승인 필요 작업은 즉시 실행하지 않고 대기 상태로 둘 수 있다.
- 실행 가능한 작업은 실제 Windows API 또는 안전한 로컬 라이브러리 호출로 수행할 수 있다.
- 실행 결과를 `tool_result` 메시지로 되돌려줄 수 있다.

## MVP 도구 범위

- `get_active_window`
- `open_app`
- `capture_screen`
- `type_text`

## 구현 순서

1. Python 패키지 골격 생성
2. 공통 프로토콜 DTO 정의 또는 공유 계층 연결
3. 도구 정책 엔진 구현
4. 도구 실행기 구현
5. 로컬 테스트용 CLI 또는 HTTP 엔드포인트 구현
6. `tool_request -> tool_result` 검증 테스트 작성

## 설계 원칙

- 추론 서버는 절대 로컬 OS를 직접 건드리지 않는다.
- `desktop-agent`만 실행 권한을 가진다.
- 실행 전 정책 판정과 승인 필요 여부가 먼저 나온다.
- unknown tool은 기본 거부한다.
- destructive action은 이번 단계에 포함하지 않는다.

## 권장 모듈 구조

- `desktop-agent/pyproject.toml`
- `desktop-agent/src/project_sena_desktop_agent/main.py`
- `desktop-agent/src/project_sena_desktop_agent/policy.py`
- `desktop-agent/src/project_sena_desktop_agent/executor.py`
- `desktop-agent/src/project_sena_desktop_agent/tools/`
- `desktop-agent/tests/`

## 기술 선택 초안

- 활성 창 조회: `pygetwindow` 또는 Win32 API 래퍼
- 앱 실행: `subprocess` 또는 `os.startfile`
- 화면 캡처: `mss` 또는 `PIL.ImageGrab`
- 텍스트 입력: `pyautogui` 또는 향후 더 정밀한 Win32 입력 경로

## 이번 단계 완료 기준

- `open_app(notepad)` 요청을 받아 정책 판정 결과를 낼 수 있다.
- 승인 필요 요청을 실행하지 않고 대기 상태로 표현할 수 있다.
- 승인된 요청을 실행하고 `tool_result(success|denied|error)`를 만들 수 있다.
- 최소 1개 이상의 자동 테스트가 통과한다.

