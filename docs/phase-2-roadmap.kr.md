# Phase 2 로드맵

Project-SENA Phase 2의 목표는 Phase 1.5에서 완성한 안정적인 제어 루프 위에 **캐릭터성, 음성, 화면 인식**을 붙이는 것이다. Phase 1.5가 "실제로 계속 켜둘 수 있는 제어 루프"를 만드는 단계였다면, Phase 2는 Project-SENA를 "도구가 붙은 채팅 UI"에서 "살아 있는 캐릭터 비서"로 전환하는 단계다.

## Phase 2 목표

- Unity client에 캐릭터 표현 레이어를 만든다.
- assistant state와 persona state를 캐릭터 표정/모션/발화 상태로 연결한다.
- TTS 출력과 speaking 상태를 연결한다.
- STT 입력을 붙일 수 있는 입력 파이프라인을 준비한다.
- `capture_screen` 결과를 Vision adapter로 넘기는 화면 인식 루프를 만든다.
- rule-based planner를 유지하되, 향후 LLM planner로 교체 가능한 경계를 만든다.

## 이번 단계에서 지켜야 할 원칙

- Phase 1.5의 안정 루프를 깨지 않는다.
- Live2D, TTS, STT, Vision은 각각 독립적으로 켜고 끌 수 있어야 한다.
- 모델과 자산은 repo에 직접 넣지 않고 다운로드 또는 사용자 제공 방식으로 둔다.
- 캐릭터 상태와 tool 실행 상태를 섞지 않는다.
- Unity UI/캐릭터 표현은 inference-server의 내부 구현에 직접 의존하지 않는다.
- 외부 라이브러리나 Unity/Windows/음성/Vision 관련 구현은 웹 검색과 공식/커뮤니티 자료를 확인한 뒤 표준 패턴을 우선한다.

## Phase 2에서 하지 않을 것

- 장기 기억/RAG 본격 구현
- 고급 LLM fine-tuning
- 멀티 캐릭터 지원
- 복잡한 행동 계획 시스템
- 원격 서버 배포 자동화
- 사용자 계정/권한 관리

이 항목들은 Phase 2 이후로 넘긴다. Phase 2에서는 "세나가 보이고, 말하고, 화면을 제한적으로 인식하는" 단일 사용자 로컬 MVP를 목표로 한다.

## 작업 축

Phase 2는 아래 다섯 축으로 나눈다.

1. Character Foundation
2. Voice Foundation
3. Vision Foundation
4. Planner Boundary
5. Phase 2 Integration Hardening

## 1. Character Foundation

상태: MVP 구현 및 Unity Editor 검증 완료.

### 목표

Unity client 안에 캐릭터 상태를 표현할 구조를 만든다. 실제 Live2D 모델을 바로 깊게 붙이기 전에, 캐릭터 상태/표정/모션/발화 이벤트를 받을 수 있는 중간 레이어를 만든다.

### 핵심 개념

- `assistant_state`: 시스템 동작 상태
  - `idle`
  - `thinking`
  - `awaiting_approval`
  - `tool_running`
  - `speaking`
  - `error`
  - `disconnected`
- `persona_state`: 캐릭터 감정/태도 상태
  - `neutral`
  - `focused`
  - `satisfied`
  - `concerned`
  - `playful`
  - `calm`

`assistant_state`는 "무엇을 하고 있는가"이고, `persona_state`는 "어떤 태도로 표현하는가"다.

캐릭터 표현은 아래 흐름으로 결정한다.

```text
assistant_state / persona_state / tool_result
-> SenaCharacterState
-> SenaCharacterPresentation
-> CharacterPresenterBase 구현체
```

`SenaCharacterPresentation`은 사람이 이해하기 쉬운 이산 표현 키를 중심으로 둔다.

- `expressionKey`: `neutral`, `focused`, `thinking`, `awaiting_approval`, `speaking`, `satisfied`, `concerned`, `disconnected`, `error`
- `motionKey`: `idle`, `listening`, `thinking`, `awaiting_approval`, `tool_running`, `speaking`, `positive`, `concerned`, `error`

`valence`, `arousal`, `focus`, `confidence` 같은 연속값은 표정 자체를 직접 결정하지 않는다. 이 값들은 흔들림 강도, 시선 집중도, speaking motion 강도 같은 보조 표현을 조정하는 데만 사용한다. 최종 표정/모션 선택은 매핑 테이블을 통과해야 한다.

### 할 일

- Unity에 `CharacterStateController` 또는 유사 컴포넌트 추가
- 현재 채팅 상태를 캐릭터 상태 이벤트로 전달
- `CharacterStateController`는 상태 결정만 담당하고 실제 표현은 `CharacterPresenterBase` 구현체가 담당하도록 분리
- `CharacterPresentationMapper`로 상태와 페르소나를 표현 키/보조 강도값으로 변환
- placeholder 표현은 `PlaceholderCharacterPresenter`, 추후 Live2D 표현은 `Live2DCharacterPresenter` 같은 별도 구현체로 교체
- 임시 placeholder 캐릭터 표시
- 상태별 시각 표현 규칙 정의
- approval 대기, tool 실행, 오류 상태에서 캐릭터 반응 분리
- Live2D 모델이 없을 때도 동작하는 fallback 표현 구현

### 완료 기준

- 텍스트 응답 없이도 상태 변화가 캐릭터 레이어에 전달된다.
- `thinking`, `speaking`, `awaiting_approval`, `error` 상태가 화면에서 구분된다.
- Live2D 모델 도입 전에도 placeholder로 상태 전이가 검증된다.

현재 검증:

- `CharacterStateController`, `CharacterPresentationMapper`, `CharacterPresenterBase` 경계 구현 완료.
- fallback `PlaceholderCharacterPresenter` 구현 완료.
- Unity client의 assistant/persona/tool 상태가 캐릭터 상태로 전달됨.

## 2. Live2D Integration

상태: expression, idle/procedural idle, 기본 motion 연결, speaking mouth MVP를 Unity Editor에서 검증했다.

### 목표

사용자 제공 Live2D 모델을 Unity client에 로드하고, Phase 2 Character Foundation에서 만든 상태 이벤트와 연결한다.

세부 도입 기준은 [live2d-integration.kr.md](live2d-integration.kr.md)에 둔다.

### 전제

- Live2D Cubism SDK for Unity 사용 여부 확인
- Unity 6.3 LTS와 SDK 호환성 확인
- 모델 파일은 repo에 커밋하지 않는다
- 사용자 제공 자산 경로와 import 절차를 문서화한다

### 할 일

- Live2D SDK 도입 방식 결정. 완료
- `Assets/ProjectSENA/Characters/` 하위 구조 설계. 완료
- `.gitignore`에 사용자 제공 모델 경로 확인. 완료
- 모델 import 절차 문서화. 완료
- 상태별 expression mapping 작성. 완료
- 기본 idle 모션 연결. 완료
- 모델 기본 idle motion이 부족한 경우 procedural idle 보완. 완료
- mouth open parameter를 speaking 이벤트와 연결할 준비. 완료
- speaking 상태에서 임시 mouth opening 파형 적용. 완료

### 완료 기준

- Unity Editor에서 Live2D 모델이 표시된다.
- `idle`, `thinking`, `speaking`, `error`에 대응하는 최소 표정/모션이 동작한다.
- 모델이 없어도 프로젝트가 깨지지 않는다.

현재 검증:

- SnowBear Majo 테스트 모델을 local-only 자산으로 import했다.
- `SenaCharacterBindingProfile`을 통해 SENA expression key를 실제 Live2D expression에 매핑했다.
- `idle`, approval 대기, 서버 연결 끊김 상태에서 표정 변화가 확인됐다.
- Unity 6.3 LTS URP 환경에서 `CubismURPRenderer.asset`과 HDR off 설정으로 Game 뷰 렌더링을 확인했다.
- SnowBear Majo 테스트 모델의 idle motion 후보는 `Scene1.motion3.json` 하나로 확인했다.
- Motion은 `CubismFadeController`, `.fadeMotionList`, `CubismMotionController`, `AnimationClip` 매핑을 통해 연결한다.
- `Scene1.motion3.json`이 기본 idle로 체감되기 어려운 모델 고유 파라미터를 움직이는 것을 확인했다.
- `Live2DProceduralIdleDriver`로 `ParamAngleX/Y/Z`, `ParamBodyAngleX/Y`, `ParamBreath` 기반의 약한 대기 움직임을 보완했다.
- 기본 실행 로그와 모션 연결용 수동 디버그 메뉴를 정리했다.
- `CharacterPresentationMapper`와 `SenaCharacterBindingProfile`의 expression/motion key 계약을 EditMode 테스트로 고정했다.
- `Live2DSpeakingMouthDriver`를 추가해 `SenaCharacterPresentation.IsSpeaking`을 `CubismMouthController.MouthOpening`으로 전달하는 기초 speaking 표현을 구현했다.
- 짧은 batch 응답에서도 speaking 표현이 보이도록 Unity client에 `minimumSpeakingPresentationSeconds` 기반 캐릭터 전용 idle 복귀 지연을 추가했다.
- speaking 상태에서 입이 움직이고 idle 복귀 후 닫히는 것을 확인했다.
- lip-sync, eye tracking은 아직 완료 기준에서 제외한다. 다음 작업에서 별도 기준을 세운다.

## 3. Voice Foundation

### 목표

세나가 텍스트뿐 아니라 음성으로 응답할 수 있도록 TTS 출력 파이프라인을 만든다.

### 권장 접근

초기에는 TTS 엔진을 하나로 고정하지 않고 adapter 경계를 만든다.

후보:

- 로컬 TTS
- 서버 측 TTS
- 외부 API TTS
- 임시 파일 기반 TTS

### 할 일

- inference-server의 `tts_adapter` 인터페이스 구체화
- assistant text 중 `should_speak=true`인 메시지를 TTS 요청으로 변환
- TTS 결과를 audio file 또는 stream metadata로 반환
- Unity client가 audio file을 재생
- 재생 시작/종료를 `speaking` 상태와 연결
- TTS 실패 시 텍스트 응답은 유지하고 음성 실패만 안내

### 완료 기준

- `안녕` 입력 후 세나가 텍스트 응답과 함께 음성 재생을 수행한다.
- 음성 재생 중 캐릭터 상태가 `speaking`으로 전환된다.
- TTS 실패 시 앱이 멈추지 않는다.

## 4. STT Foundation

### 목표

마이크 입력을 텍스트 입력과 같은 user message 파이프라인으로 연결한다.

### 할 일

- Unity microphone capture UX 정리
- push-to-talk 또는 toggle-to-talk 정책 결정
- STT adapter 경계 정의
- STT 결과를 `speech_input` 또는 `user_text`로 변환
- 인식 중/인식 완료/인식 실패 상태 표시
- 사용자가 발화 내용을 보내기 전에 확인할지 결정

### 완료 기준

- 사용자가 마이크로 짧은 한국어 문장을 입력할 수 있다.
- STT 결과가 기존 typed message와 같은 orchestration path를 탄다.
- 오인식 시 사용자가 재시도할 수 있다.

## 5. Vision Foundation

### 목표

`capture_screen`으로 저장된 이미지를 Vision adapter로 넘겨 화면 context를 생성한다.

### 원칙

- 원본 캡처 이미지는 장기 기억에 자동 저장하지 않는다.
- Vision 결과는 "요약된 화면 context"로 session state에 남긴다.
- 화면 캡처와 Vision 분석은 별도 단계로 분리한다.
- 사용자가 명시적으로 요청한 화면만 분석한다.

### 할 일

- inference-server에 `vision_adapter` 인터페이스 추가
- `capture_screen` tool_result의 `output_path`를 Vision 분석 입력으로 연결
- Vision 결과 schema 정의
  - visible text summary
  - active app/window
  - UI element summary
  - uncertainty
- Unity에 "화면을 보고 있어" 상태 표시
- `지금 화면 보고 설명해줘` 요청을 `capture_screen -> vision_adapter -> assistant_text`로 연결
- Vision 실패 UX 정리

### 완료 기준

- 사용자가 `지금 화면 설명해줘`라고 요청하면 캡처 승인 후 화면 요약 응답이 나온다.
- 전체 화면과 현재 창 분석을 구분할 수 있다.
- Vision 결과가 tool execution과 대화 응답 사이에 자연스럽게 연결된다.

## 6. Planner Boundary

### 목표

현재 rule-based planner를 유지하면서도, Phase 3 이후 LLM 기반 planner로 교체할 수 있는 경계를 만든다.

### 할 일

- tool intent parsing을 별도 module로 분리
- rule-based planner test 강화
- planner output schema 고정
- LLM planner 후보 interface 정의
- safety policy는 desktop-agent에 남겨 직접 실행을 막는다

### 완료 기준

- rule-based planner와 future LLM planner가 같은 `tool_request` schema를 생성한다.
- planner 교체가 desktop-agent나 Unity client 변경을 요구하지 않는다.

## 7. Integration Hardening

### 목표

Phase 2에서 추가되는 character, voice, vision 기능이 Phase 1.5의 안정성을 해치지 않도록 통합 테스트와 fallback을 만든다.

### 할 일

- Phase 2 회귀 체크리스트 작성
- Live2D 자산 없음 상태 검증
- TTS 엔진 없음 상태 검증
- STT 엔진 없음 상태 검증
- Vision adapter 없음 상태 검증
- standalone 빌드 재검증
- 7680x2160 환경 재검증

### 완료 기준

- 선택 기능이 꺼져 있어도 기본 채팅/tool 루프가 정상 동작한다.
- 음성/캐릭터/Vision 실패가 전체 앱 실패로 전파되지 않는다.

## 권장 구현 순서

1. Phase 2 브랜치와 로드맵 작성. 완료
2. Character Foundation placeholder 구현. 완료
3. Character state와 기존 assistant/persona state 연결. 완료
4. Live2D SDK/모델 도입 방식 조사. 완료
5. Live2D fallback-safe import 구조 작성. 완료
6. Live2D expression-only MVP 검증. 완료
7. Live2D motion 연결 기준 설계. 완료
8. Live2D idle motion/procedural idle 검증. 완료
9. 상태별 expression/motion 매핑 안정화. 완료
10. speaking 상태와 mouth/표정 연결. 완료
11. TTS adapter 구체화와 Unity audio playback
12. STT 입력 UX 설계 및 최소 구현
13. Vision adapter interface 추가
14. `capture_screen -> vision summary -> response` 루프 구현
15. Planner boundary 정리
16. Phase 2 통합 회귀 테스트

## 첫 번째 구현 과제

Phase 2의 첫 구현 과제는 **Character Foundation placeholder**로 한다.

구체 작업:

- Unity에 캐릭터 표시 영역을 만든다.
- 실제 Live2D 모델 없이도 동작하는 placeholder 캐릭터를 둔다.
- `assistant_state`와 `persona_state`를 캐릭터 상태 이벤트로 연결한다.
- 상태별 색/표정/간단한 움직임을 정의한다.
- 기존 ChatPanel과 approval UX를 깨지 않는다.

이 작업이 끝나면 Live2D 모델을 도입할 때 "모델을 어디에 꽂을지"가 명확해진다.

## Known Risks

- Unity UI와 캐릭터 레이어가 뒤섞이면 이후 Live2D 도입 때 다시 뜯어고치게 된다.
- TTS를 먼저 붙이면 캐릭터 speaking 상태 없이 음성만 나와서 표현 구조가 어색해질 수 있다.
- Vision을 먼저 붙이면 이미지/개인정보/지연시간 문제가 커져 캐릭터 경험보다 시스템 복잡도가 먼저 증가할 수 있다.
- Live2D SDK 버전과 Unity 6.3 LTS 호환성은 반드시 확인해야 한다.
- 음성/화면 인식 기능은 하드웨어 부하와 지연시간을 따로 측정해야 한다.

## 완료 기준

Phase 2는 아래가 충족되면 완료로 본다.

- Unity 화면에 세나 캐릭터 또는 fallback placeholder가 표시된다.
- assistant/persona state가 캐릭터 표현과 연결된다.
- TTS 응답이 Unity에서 재생되고 speaking 상태와 연결된다.
- STT 또는 Vision 중 최소 하나가 기존 message pipeline과 연결된다.
- Vision을 선택한 경우, 캡처 기반 화면 요약 응답이 동작한다.
- 기능 실패 시 기본 채팅/tool 루프는 유지된다.
- standalone 빌드에서 Phase 1.5 회귀 테스트가 여전히 통과한다.

## 다음 Phase 후보

Phase 2 이후에는 아래 중 하나로 이어진다.

1. Phase 3A: Memory and Persona
   - 장기 기억
   - 캐릭터 프로필
   - 대화 스타일 강화

2. Phase 3B: Advanced Desktop Autonomy
   - 더 많은 desktop tools
   - app별 target selection
   - 안전한 multi-step task execution

3. Phase 3C: Inference Server Upgrade
   - 로컬 LLM 연결
   - GPU 서버 분리
   - Vision/TTS/STT 최적화

## Phase 3 이후로 넘길 아이디어

- Character telemetry feedback loop
  - Phase 2에서는 character state를 단방향 표현 레이어로 제한한다.
  - Phase 3 이후에는 `speaking_duration`, `animation_finished`, `user_interrupted`, `attention_target` 같은 캐릭터 런타임 telemetry를 inference/assistant UX policy에 참고 신호로 올릴 수 있다.
  - 단, character telemetry가 tool 실행 권한이나 desktop-agent policy를 직접 결정하지 않도록 한다.
