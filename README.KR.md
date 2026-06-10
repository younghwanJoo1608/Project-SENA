# Project-SENA

**Screen-aware Emotional Native Assistant**

Project-SENA는 한국어 기반 Windows 데스크톱 Live2D 캐릭터 비서 프로젝트입니다. 사용자의 데스크톱 화면을 이해하고, 텍스트와 음성으로 대화하며, 캐릭터 페르소나를 유지한 채 응답하고, 사용자가 승인한 경우 안전하게 PC 조작을 수행하는 것을 목표로 합니다.

이 프로젝트는 ProjectLucia에서 영감을 받았지만, 장기적으로는 데스크톱 환경과 추론 백엔드를 더 명확하게 분리한 구조를 지향합니다.

## 목표

- 한국어 텍스트 및 음성 대화
- 안정적인 페르소나를 가진 Live2D 캐릭터 렌더링
- 데스크톱 스크린샷과 활성 창 정보를 기반으로 한 화면 인식 대화
- 명시적인 도구 요청과 사용자 승인을 거치는 안전한 PC 조작
- 로컬 우선 추론 구조와 별도 서버 PC로 확장 가능한 아키텍처

## 아키텍처

Project-SENA는 네 가지 주요 영역으로 구성됩니다.

- `unity-client`: Live2D UI, 채팅, 마이크 입력, 스피커 출력, 승인 대화상자
- `desktop-agent`: Windows 로컬 화면 캡처, 활성 창 확인, 안전한 PC 자동화
- `inference-server`: 한국어 LLM, TTS, 비전 분석, 감정 분석, RAG, 메모리
- `shared-protocol`: 데스크톱 측과 추론 서버 사이의 메시지 규격

데스크톱 PC는 비서의 눈, 귀, 목소리, 손 역할을 맡습니다. 추론 서버는 비서의 두뇌 역할을 맡습니다.

## 개발 로드맵

1. RTX 3060 Ti 데스크톱에서 단일 PC MVP를 먼저 실행합니다.
2. 이후 추론 작업을 게이밍 노트북으로 분리합니다.
3. 장기적으로 노트북 서버를 고급 추론 전용 PC로 교체합니다.

## 실행 방법

PC를 껐다 켠 뒤에는 PowerShell 7 창을 두 개 열고, `desktop-agent`와 `inference-server`를 각각 실행합니다.

### 1. desktop-agent 실행

첫 번째 PowerShell 7 창:

```powershell
cd "G:\Repos\LLM Vtuber Agent\desktop-agent"
.\.venv\Scripts\python -m uvicorn project_sena_desktop_agent.api:app --reload --port 8010
```

정상 실행 확인:

```powershell
Invoke-RestMethod http://127.0.0.1:8010/health
```

### 2. inference-server 실행

두 번째 PowerShell 7 창:

```powershell
cd "G:\Repos\LLM Vtuber Agent\inference-server"
$env:PROJECT_SENA_DESKTOP_AGENT_URL = "http://127.0.0.1:8010"
.\.venv\Scripts\python -m uvicorn project_sena_inference.main:app --reload --port 8000
```

정상 실행 확인:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

### 3. Unity client 실행

두 서버가 모두 켜진 뒤 Unity Editor에서 `Project-SENA-UnityClient`를 열고 Play 버튼을 누릅니다. 빌드된 standalone 앱을 사용할 때도 서버 두 개를 먼저 실행한 뒤 앱을 실행합니다.

### 처음 설정하거나 의존성이 바뀐 경우

`.venv`가 없거나 `pyproject.toml` 의존성이 바뀐 경우에만 각 폴더에서 아래 명령을 실행합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .[dev]
```

## 참고 프로젝트

ProjectLucia 저장소들은 분석과 선택적 재사용을 위해 `references/` 아래에 보관합니다. 이 폴더는 이 저장소의 커밋 대상에서 제외됩니다.

현재 참고 저장소:

- `references/ProjectLucia_Client_HiyoriEdition`
- `references/ProjectLucia_Server_HiyoriEdition`
- `references/ProjectLucia_Finetuning_Server`

## 안전 원칙

추론 서버는 PC 조작을 직접 실행하지 않습니다. 추론 서버는 구조화된 도구 요청만 만들고, 실제 실행 여부는 데스크톱 에이전트가 판단합니다.

위험하거나 민감한 작업은 기본적으로 차단하거나 사용자 승인을 요구합니다.

## 라이선스

Project-SENA의 소스 코드는 MIT License로 배포합니다. 외부 모델, Live2D 자산, 음성 자산, 생성 미디어, 기타 외부 리소스는 다운로드 또는 사용자 제공 방식으로 사용하며, 각 리소스의 별도 라이선스를 따릅니다. 자세한 내용은 `THIRD_PARTY_NOTICES.md`를 참고하세요.
