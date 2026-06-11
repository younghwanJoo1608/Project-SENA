# Phase 1.5 통합 회귀 테스트 체크리스트

이 문서는 Project-SENA Phase 1.5 기능이 PC 재부팅 후에도 같은 방식으로 동작하는지 확인하기 위한 수동 회귀 테스트 절차다.

## 목적

- `unity-client -> inference-server -> desktop-agent -> 승인 -> 실행 -> 결과 반영` 루프를 재검증한다.
- 실패 복구 UX와 세션 초기화가 깨지지 않았는지 확인한다.
- Phase 2에서 Live2D, 음성, Vision을 붙이기 전 안정 기준선을 남긴다.

## 사전 준비

PowerShell 7 창을 두 개 연다.

첫 번째 창에서 desktop-agent 실행:

```powershell
cd "G:\Repos\LLM Vtuber Agent\desktop-agent"
.\.venv\Scripts\python -m uvicorn project_sena_desktop_agent.api:app --reload --port 8010
```

두 번째 창에서 inference-server 실행:

```powershell
cd "G:\Repos\LLM Vtuber Agent\inference-server"
$env:PROJECT_SENA_DESKTOP_AGENT_URL = "http://127.0.0.1:8010"
.\.venv\Scripts\python -m uvicorn project_sena_inference.main:app --reload --port 8000
```

서버 상태 확인:

```powershell
Invoke-RestMethod http://127.0.0.1:8010/health
Invoke-RestMethod http://127.0.0.1:8000/health
```

Unity Editor 또는 standalone 앱을 실행한다.

## 기본 연결

- [ ] Unity 화면에 `연결됨`이 표시된다.
- [ ] 입력창과 보내기 버튼이 활성화되어 있다.
- [ ] `안녕`을 입력하면 규칙 기반 응답이 표시된다.
- [ ] `새 대화` 버튼을 누르면 채팅 로그와 세션 상태가 초기화된다.

## open_app

입력:

```text
메모장 열어줘
```

기대 결과:

- [ ] 승인 패널이 열린다.
- [ ] 대상 작업이 메모장 실행으로 표시된다.
- [ ] `허용`을 누르면 메모장이 열린다.
- [ ] Unity 채팅에 앱 실행 완료 안내가 표시된다.

거절 경로:

- [ ] 같은 요청에서 `거절`을 누르면 메모장이 열리지 않는다.
- [ ] Unity 채팅에 작업 취소 안내가 표시된다.
- [ ] 앱이 다시 입력 가능한 상태로 돌아온다.

## get_active_window

입력:

```text
현재 창 뭐야?
```

기대 결과:

- [ ] 별도 승인 없이 바로 실행된다.
- [ ] 현재 활성 창 제목과 process 이름이 세나 응답으로 표시된다.
- [ ] 상태가 `대기 중`으로 복구된다.

## type_text

### 직전에 연 앱 대상

절차:

1. `메모장 열어줘`를 승인해서 메모장을 연다.
2. Unity로 돌아와 아래를 입력한다.

```text
안녕하세요 입력해줘
```

기대 결과:

- [ ] 승인 패널에 대상 창이 메모장으로 표시된다.
- [ ] `허용`을 누르면 메모장에 `안녕하세요`가 입력된다.
- [ ] Unity 채팅에 텍스트 입력 완료 안내가 표시된다.

### 이미 열려 있는 특정 앱 대상

절차:

1. 메모장을 수동으로 미리 열어 둔다.
2. Unity에서 아래를 입력한다.

```text
메모장에 안녕하세요 입력해줘
```

기대 결과:

- [ ] 승인 패널에 대상 창이 메모장으로 표시된다.
- [ ] `허용`을 누르면 이미 열려 있던 메모장에 텍스트가 입력된다.
- [ ] Unity 창이 foreground여도 메모장 대상 선택이 유지된다.

실패 경로:

- [ ] 메모장이 열려 있지 않은 상태에서 `메모장에 안녕하세요 입력해줘`를 보내면 대상 앱 창을 찾지 못했다는 안내가 표시된다.

## capture_screen

캡처 파일 기본 위치:

```text
%LOCALAPPDATA%\ProjectSENA\captures
```

캡처 파일 보관 정책은 `docs/capture-retention-policy.kr.md`를 따른다.

자동 정리는 `capture_screen` 저장 직후 실행된다. 기본 정책은 7일, 1GB, 500개 제한이며 `keep/` 하위 폴더와 `.keep` marker 파일은 삭제하지 않는다.

### 전체 화면

입력:

```text
전체 화면 캡처해줘
```

기대 결과:

- [ ] 승인 패널이 열린다.
- [ ] `허용`을 누르면 전체 화면 PNG가 저장된다.
- [ ] 7680x2160 환경에서는 저장된 이미지 크기가 7680x2160이다.

### 현재 활성 창

입력:

```text
현재 창 캡처해줘
```

기대 결과:

- [ ] 승인 패널에 대상 창 정보가 표시된다.
- [ ] `허용`을 누르면 현재 활성 창 영역만 PNG로 저장된다.
- [ ] 캡처 위치가 실제 창 위치와 어긋나지 않는다.

### 이미 열려 있는 특정 창

입력:

```text
메모장 캡처해줘
```

기대 결과:

- [ ] 승인 패널에 대상 창이 메모장으로 표시된다.
- [ ] `허용`을 누르면 메모장 창 영역만 PNG로 저장된다.
- [ ] 캡처 위치가 실제 메모장 위치와 어긋나지 않는다.

실패 경로:

- [ ] 메모장이 열려 있지 않으면 캡처 대상 창을 찾지 못했다는 안내가 표시된다.
- [ ] 대상 창이 최소화되어 있으면 캡처할 수 없다는 안내가 표시된다.

## 실패 복구

### inference-server 꺼짐

절차:

1. inference-server PowerShell 창에서 `Ctrl+C`로 서버를 끈다.
2. Unity에서 메시지를 보낸다.

기대 결과:

- [ ] Unity가 서버 연결 실패를 한국어로 표시한다.
- [ ] 입력창과 보내기 버튼이 다시 사용 가능한 상태로 돌아온다.

### desktop-agent 꺼짐

절차:

1. inference-server는 켜 둔다.
2. desktop-agent PowerShell 창에서 `Ctrl+C`로 서버를 끈다.
3. Unity에서 `메모장 열어줘`를 보낸다.

기대 결과:

- [ ] Unity가 desktop-agent와 통신하지 못했다는 안내를 표시한다.
- [ ] inference-server 연결 자체는 유지된다.
- [ ] 입력 가능한 상태로 복구된다.

### 승인 대기 중 새 대화

절차:

1. `메모장 열어줘`를 보내 승인 패널을 띄운다.
2. 승인하지 않고 `새 대화` 버튼을 누른다.

기대 결과:

- [ ] 승인 패널이 닫힌다.
- [ ] 이전 pending tool이 취소된다.
- [ ] 새 session_id로 대화가 시작된다.
- [ ] 이후 `메모장 열어줘`를 다시 보내도 중복 실행 문제가 없다.

## 자동 테스트

Python 테스트:

```powershell
cd "G:\Repos\LLM Vtuber Agent\desktop-agent"
.\.venv\Scripts\python -m pytest

cd "G:\Repos\LLM Vtuber Agent\inference-server"
.\.venv\Scripts\python -m pytest
```

기대 결과:

- [ ] desktop-agent 테스트가 모두 통과한다.
- [ ] inference-server 테스트가 모두 통과한다.

## 완료 기준

아래가 모두 만족되면 Phase 1.5 기능 회귀 테스트를 통과한 것으로 본다.

- [ ] 기본 연결과 새 대화가 정상이다.
- [ ] `open_app`, `get_active_window`, `type_text`, `capture_screen`이 정상이다.
- [ ] 승인 거절, 서버 미기동, desktop-agent 미기동, pending 취소가 복구 가능하다.
- [ ] 캡처 파일이 올바른 위치와 크기로 저장된다.
- [ ] 캡처 파일 보관 정책과 자동 정리 기준이 문서화되어 있다.
- [ ] `capture_screen` 결과에 `cleanup.deleted_files`, `cleanup.deleted_bytes`, `cleanup.error_message` 요약이 포함된다.
- [ ] 자동 테스트가 모두 통과한다.
