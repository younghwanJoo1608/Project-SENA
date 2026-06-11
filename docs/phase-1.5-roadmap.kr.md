# Phase 1.5 로드맵

Project-SENA의 Phase 1은 "Unity client -> inference-server -> desktop-agent -> 승인 -> 실행 -> 결과 반영"의 최소 제어 루프를 닫는 단계였다.  
Phase 1.5의 목표는 이 제어 루프를 더 예쁘게 만드는 것이 아니라, **실제로 계속 켜두고 써도 되는 수준의 안정성, 복구성, 확장 준비도**를 확보하는 것이다.

즉 이번 단계에서는 Live2D나 음성보다 먼저, 아래 질문에 답할 수 있어야 한다.

- 앱을 몇 번 반복해서 써도 흐름이 안정적인가?
- 입력/승인/실행/응답 과정에서 실패했을 때 회복 가능한가?
- 다음 Phase에서 툴, 음성, 화면 인식, 캐릭터 표현을 붙여도 구조를 크게 뜯지 않아도 되는가?

## Phase 1.5 목표

- Unity standalone 빌드에서 기본 채팅/승인/실행 루프가 정상 동작한다.
- 네트워크 오류, desktop-agent 미기동, 승인 취소 같은 실패 상황에서 사용자에게 자연스럽게 설명한다.
- 세션과 상태 표시가 최소한의 운영 가능 수준으로 정리된다.
- `open_app` 외에 1~2개의 desktop tool을 같은 방식으로 확장할 수 있는지 검증한다.
- 다음 Phase의 Live2D, STT/TTS, Vision 확장을 막는 구조적 부채를 정리한다.

## 이번 단계에서 하지 않을 것

이번 단계에서는 일부러 아래를 미룬다.

- Live2D 모델 임포트 및 표정/모션 연동
- TTS 음성 출력 본격 연결
- STT 마이크 입력 연결
- 화면 캡처 기반 Vision 대화 루프
- 고급 기억/RAG 시스템
- 캐릭터 페르소나 심화 튜닝

이유는 간단하다. 지금 필요한 것은 "기능 수 증가"가 아니라 "이미 만든 제어 루프를 실제 사용 가능한 수준으로 굳히는 것"이기 때문이다.

## 작업 축

Phase 1.5는 아래 다섯 축으로 나눈다.

1. standalone 검증
2. 실패 복구 UX
3. 세션/상태 운영성
4. desktop tool 확장 검증
5. 다음 Phase를 위한 구조 정리

## 1. Standalone 검증

Unity Editor 안에서의 성공과 standalone 실행 성공은 다르다.  
따라서 가장 먼저 해야 할 일은 Editor가 아닌 실제 실행 파일 기준 검증이다.

### 목표

- Windows standalone 빌드 생성
- 로컬 inference-server / desktop-agent와 연결
- 텍스트 입력 -> 승인 -> 메모장 실행 -> 후속 응답까지 재검증

### 할 일

- Windows 빌드 프로파일 점검
- 실행 파일 기준 기본 해상도 및 창 모드 확인
- 로컬 서버 주소를 설정 파일 또는 Inspector 노출값으로 분리할지 결정
- Editor 전용 동작이 없는지 확인

### 완료 기준

- standalone 실행 파일에서 `메모장 열어줘` 시나리오가 정상 동작한다
- Unity Editor를 열지 않은 상태에서도 승인 패널과 후속 응답이 보인다

### 검증 기록

- 2026-06-06: Windows standalone 빌드 `Builds/Windows/Project-SENA.exe` 생성 성공.
- 2026-06-06: 빌드된 앱에서 `메모장 열어줘` 입력 -> 승인 -> 메모장 실행 -> 후속 응답 표시까지 확인.
- 2026-06-06: 7680x2160 Game 창 기준 ChatPanel 비율 조정 확인.

## 2. 실패 복구 UX

지금 구조는 성공 경로는 확인됐지만, 실패 상황에서 사용자가 무엇을 해야 하는지 충분히 명확하지 않다.

### 다뤄야 할 실패 상황

- inference-server가 꺼져 있음
- desktop-agent가 꺼져 있음
- 서버 응답 타임아웃
- 승인 거절
- 툴 실행 실패
- 잘못된 세션 상태

### 할 일

- `ConnectionStatusText`와 상태 텍스트를 사용자 친화적으로 정리
- 실패 시 채팅창에 기술 로그가 아니라 자연어 안내 표시
- 재시도 버튼 또는 최소한 "다시 보내기" 가능한 상태 복구
- 승인 패널이 열린 상태에서 실패하면 패널을 어떻게 닫고 어떤 메시지를 남길지 정리

### 완료 기준

- 위 실패 상황 각각에서 앱이 멈추지 않는다
- 사용자가 "무슨 일이 났는지"와 "다음에 뭘 하면 되는지"를 알 수 있다

### 검증 기록

- 2026-06-06: inference-server 미기동 시 Unity가 한국어 안내를 표시하고 입력 가능 상태로 복구됨을 확인.
- 2026-06-06: desktop-agent 미기동 시 inference-server 연결은 유지하면서 desktop-agent 연결 실패만 분리 표시함을 확인.
- 2026-06-06: 승인 거절 시 툴이 실행되지 않고 idle 상태로 복구됨을 확인.
- 2026-06-06: 테스트 전용 failure injection으로 tool 실행 실패 UX를 검증함. 테스트 경로는 `PROJECT_SENA_ENABLE_FAILURE_INJECTION=1`일 때만 활성화된다.

## 3. 세션/상태 운영성

지금은 세션이 살아 있고 단일 사용자 흐름이 유지되는 한 문제없지만, 실사용성 측면에서는 최소한의 세션 운영 규칙이 필요하다.

### 할 일

- 새 대화 시작 / 대화 로그 지우기 동작 정의
- 세션 ID 재생성 시점 정리
- 승인 대기 중 입력 가능 여부 정책 고정
- 상태값(`idle`, `thinking`, `awaiting_approval`)의 UI 표현 정리
- 같은 `message_id` 재전송 시 중복 tool dispatch가 발생하지 않도록 방어
- 이미 pending approval이 있는 session에서 새 tool 요청이 겹치지 않도록 방어
- 이미 처리된 approval 결과가 다시 들어왔을 때 stale 응답으로 정리

### 권장 방향

- "새 대화" 버튼 하나 추가
- 대화 리셋 시 채팅 로그와 세션 ID를 동시에 초기화
- 승인 대기 중에는 입력창과 보내기 버튼을 비활성화 유지
- 세션 ID 영구 저장은 pending approval 복구 정책과 함께 다룬다. 단순히 Unity `PlayerPrefs`에 저장하면 앱 재시작 후 이전 pending 상태와 충돌할 수 있으므로, 먼저 "새 대화"와 "대기 작업 폐기" UX를 정한다.

### 완료 기준

- 사용자가 여러 턴을 주고받다가도 대화를 명시적으로 초기화할 수 있다
- 상태 전이가 UI 상에서 일관되게 보인다
- 네트워크 재시도나 중복 클릭으로 같은 tool이 두 번 실행되지 않는다

### 진행 기록

- 2026-06-06: inference-server에 session별 `message_id` 응답 캐시를 추가해 같은 inbound message 재전송 시 이전 응답을 반환하도록 함.
- 2026-06-06: inference-server가 pending approval 중 새 user_text/tool planning을 막고 먼저 승인/거절을 요구하도록 함.
- 2026-06-06: inference-server가 pending approval이 없는 approval_result를 stale approval로 처리하고 desktop-agent로 내려보내지 않도록 함.
- 2026-06-06: desktop-agent도 `message_id` 응답 캐시와 session별 pending tool 중복 방어를 추가함.
- 2026-06-06: Unity Hierarchy에 정적 "새 대화" 버튼을 추가함. 버튼은 새 session_id를 만들고 채팅 로그, 승인 패널, 입력창 상태를 초기화한다.
- 2026-06-06: pending approval 중 "새 대화"를 누르면 이전 session_id로 `approval_result(approved=false)`를 보내 서버/desktop-agent의 pending tool을 취소하도록 함.

## 4. Desktop tool 확장 검증

Phase 1은 `open_app` 하나로 루프를 닫았다.  
Phase 1.5에서는 최소 1~2개의 tool을 더 붙여서 구조가 일반화되는지 확인해야 한다.

### 우선순위 후보

- `get_active_window`
- `capture_screen`
- `type_text`

### 추천 순서

1. `get_active_window`
2. `type_text`
3. `capture_screen`

`capture_screen`은 Vision과 이어지므로 가치가 크지만, 상태와 데이터량이 늘어나기 때문에 `get_active_window`나 `type_text`보다 약간 뒤에 붙이는 편이 좋다.

### 검증 포인트

- inference-server의 tool planning 구조가 `open_app` 전용으로 굳지 않았는가
- desktop-agent policy / executor가 tool별로 무리 없이 확장되는가
- Unity client가 새로운 `tool_result`를 자연스럽게 표시할 수 있는가

### 완료 기준

- `open_app` 외 1개 이상 tool이 같은 승인/실행/결과 루프로 동작한다

### 진행 기록

- 2026-06-07: `get_active_window`를 observation-only `auto_allowed` tool로 검증함. desktop-agent는 foreground window title, handle, process id/name/path를 반환하고, inference-server와 Unity가 approval 없이 결과를 표시한다.
- 2026-06-07: `type_text` foreground 기반 1차 구현을 추가함. desktop-agent는 approval request 생성 시 foreground window를 기록하고, 승인 후 window가 바뀌었으면 입력하지 않도록 한다. inference-server는 `입력해줘`, `써줘`, `type ...` 요청을 `type_text`로 planning한다.
- 2026-06-09: `type_text`가 `target_app: notepad`를 통해 이미 열려 있는 메모장 창을 찾아 입력할 수 있도록 확장함. 명시 대상이 있으면 마지막 `open_app` 대상이나 Unity foreground보다 우선한다.
- 2026-06-09: `capture_screen`을 파일 저장 기반 visible capture로 확장함. `all_screens`, `active_window`, `target_window` 모드를 지원하고, 캡처 파일은 기본적으로 로컬 Project-SENA capture directory에 PNG로 저장한다.

## 5. 다음 Phase를 위한 구조 정리

Phase 2에서 Live2D, 음성, Vision을 붙일 생각이라면 지금 구조를 한 번 다듬어두는 것이 좋다.

### 정리 대상

- Unity client의 입력/네트워크/승인/UI 상태 코드 경계
- desktop-agent의 policy / executor / transport 경계
- inference-server의 rule-based planning과 후속 model adapter 경계
- 설정값의 외부화

### 추천 방향

- Unity:
  - `UI Controller`
  - `Session/App Controller`
  - `Network Client`
  로 책임 분리

- desktop-agent:
  - `transport`
  - `policy`
  - `executor`
  유지

- inference-server:
  - `orchestrator`
  - `desktop_agent_adapter`
  - 향후 `llm_adapter`
  분리 유지

### 완료 기준

- 다음 단계에서 Live2D나 STT/TTS를 붙일 때 기존 파일을 크게 뒤엎지 않아도 된다

## 우선순위 제안

실제 작업 순서는 아래를 권장한다.

1. standalone 빌드 검증
2. 실패 복구 UX 정리
3. 세션 초기화 / 상태 운영성 보강
4. `get_active_window` 추가
5. 구조 정리 리팩터링

이 순서가 좋은 이유는, 먼저 "실제로 쓸 수 있는가"를 확인한 뒤, 그 위에 툴 확장과 구조 정리를 올릴 수 있기 때문이다.

## 완료 기준

Phase 1.5는 아래가 되면 완료로 본다.

- standalone 앱에서 기본 채팅/승인/실행 루프가 동작한다
- 대표 실패 상황에서 앱이 멈추지 않고 복구 가능하다
- 세션 초기화와 상태 표시가 일관된다
- `open_app` 외 최소 1개 tool이 추가로 검증된다
- 다음 Phase의 캐릭터/음성/화면 인식 확장을 막는 큰 구조 문제가 없다

통합 회귀 테스트 절차는 `docs/phase-1.5-regression-checklist.kr.md`를 기준으로 한다.
캡처 파일 보관과 자동 정리 기준은 `docs/capture-retention-policy.kr.md`를 기준으로 한다.

## 다음 Phase 연결

Phase 1.5가 끝나면 다음 후보는 두 갈래다.

1. 캐릭터성 확장
   - Live2D
   - 감정 상태 반영
   - 캐릭터 표현 강화

2. 감각 확장
   - STT/TTS
   - 화면 캡처/Vision
   - 멀티모달 입력

권장 순서는 **Live2D placeholder -> 실제 Live2D 도입**과 **standalone 검증 완료 후 STT/TTS 연결**이다.
