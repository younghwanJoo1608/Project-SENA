# Live2D 통합 가이드

이 문서는 Phase 2에서 Live2D 모델을 Project-SENA Unity client에 연결하고, 이후 모델을 교체할 때 따라야 할 기준을 정리한다.

## 현재 결정

- Project-SENA의 캐릭터 표현 입력은 `SenaCharacterPresentation`으로 고정한다.
- Live2D presenter는 `expressionKey`와 `motionKey`를 받아 모델별 expression/motion으로 변환한다.
- 모델마다 expression 파일명과 motion group 이름이 다르므로, 직접 코드에 박지 않고 `SenaCharacterBindingProfile`로 매핑한다.
- Live2D 모델 파일, 다운로드한 모델 패키지, 개인 캐릭터 자산은 git에 커밋하지 않는다.
- Phase 2 Live2D MVP에서는 expression, Cubism motion clip, procedural idle 보완을 최소 단위로 연결한다.

## 현재 검증된 MVP 구조

2026-06-19 기준으로 아래 흐름을 Unity Editor에서 검증했다.

```text
SenaClientController
-> CharacterStateController
-> Live2DCharacterPresenter
-> CubismExpressionController / CubismMotionController / Live2DProceduralIdleDriver
-> model expression / motion / procedural idle
```

검증된 상태:

- `idle` 상태에서 기본 표정 적용
- 메모장 실행 요청처럼 approval이 필요한 요청에서 approval 대기 표정 적용
- inference-server 연결 실패 시 disconnected/error 계열 표정 적용
- Live2D 모델이 Game 화면에 렌더링됨
- Cubism motion clip이 `CubismMotionController`를 통해 재생됨
- 모델 기본 idle motion이 부족한 경우 `Live2DProceduralIdleDriver`로 대기 움직임을 보완함
- Unity 6.3 LTS URP 환경에서 HDR을 끄면 검은 배경 합성 문제가 사라짐

아직 연결하지 않은 것:

- audio lip-sync
- 시선 추적

따라서 현재 완료 기준은 "상태 신호가 Live2D expression/motion/procedural idle/speaking mouth까지 도달한다"이다. 실제 음성 길이와 입 움직임을 맞추는 audio lip-sync는 다음 단계에서 별도 기준으로 다룬다.

## 빠른 연결 체크리스트

새 Live2D 모델을 Project-SENA에 연결할 때는 아래 순서로 진행한다.

1. Cubism SDK for Unity를 로컬 Unity 프로젝트에 import한다.
2. 모델 파일을 `Assets/ProjectSENA/Characters/UserModels/` 아래에 둔다.
3. `.model3.json`을 Unity에서 reimport해서 prefab, expression list, motion/fade asset이 생성되는지 확인한다.
4. 모델 prefab root를 scene에 배치하고 Game 화면에서 보이는 위치/스케일로 조정한다.
5. 모델 root에 아래 컴포넌트를 둔다.
   - `CharacterStateController`
   - `Live2DCharacterPresenter`
   - `CubismExpressionController`
   - `CubismFadeController`
   - `CubismMotionController`
   - `Animator`
   - 필요 시 `Live2DProceduralIdleDriver`
   - 필요 시 `Live2DSpeakingMouthDriver`
6. `CharacterStateController.presenter`에 같은 root의 `Live2DCharacterPresenter`를 연결한다.
7. `ProjectSenaClient`의 `SenaClientController.characterState`에 모델 root의 `CharacterStateController`를 연결한다.
8. `SenaCharacterBindingProfile`을 만들어 SENA expression/motion key를 모델 실제 이름으로 매핑한다.
9. `Live2DCharacterPresenter.bindingProfile`, `expressionController`, `motionController`, `motionClips`를 연결한다.
10. `CubismFadeController.CubismFadeMotionList`에 모델별 `.fadeMotionList` asset을 연결한다.
11. `Animator.Controller`는 비워 둔다.
12. URP renderer/HDR 설정을 확인한다.
13. Play 모드에서 idle, approval, error/disconnected 상태를 테스트한다.

중요: `SenaClientController.characterState`가 비어 있으면 fallback placeholder가 생성될 수 있다. Live2D 모델이 있는데 회색 placeholder가 보이면 이 연결을 먼저 확인한다.

## Unity 씬 연결 기준

Live2D 모델 prefab의 root object에 아래 컴포넌트를 둔다.

- `CharacterStateController`
- `Live2DCharacterPresenter`
- `CubismExpressionController`
- `CubismFadeController`
- `CubismMotionController`
- `Animator`
- `Live2DProceduralIdleDriver`는 선택 사항이다. 모델에 충분한 idle motion이 없을 때만 추가한다.
- `Live2DSpeakingMouthDriver`는 선택 사항이다. TTS/audio lip-sync 전 단계에서 speaking 상태를 입 움직임으로 표시할 때 추가한다.

연결 규칙:

- `CharacterStateController.presenter`에는 같은 모델 root의 `Live2DCharacterPresenter`를 연결한다.
- `Live2DCharacterPresenter.bindingProfile`에는 모델별 `SenaCharacterBindingProfile`을 연결한다.
- `Live2DCharacterPresenter.expressionController`에는 같은 모델 root의 `CubismExpressionController`를 연결한다.
- `Live2DCharacterPresenter.motionController`에는 같은 모델 root의 `CubismMotionController`를 연결한다.
- `Live2DCharacterPresenter.motionClips`에는 SENA motion key와 Unity `AnimationClip`의 매핑을 넣는다.
- `CubismFadeController.CubismFadeMotionList`에는 모델에서 생성된 `.fadeMotionList` asset을 연결한다.
- `Animator.Controller`는 CubismMotionController로 직접 모션을 재생할 때 비워 둔다. Animator Controller를 사용하면 Mecanim 쪽 애니메이션이 우선될 수 있다.
- `ProjectSenaClient`의 `SenaClientController.characterState`에는 모델 root의 `CharacterStateController`를 연결한다.

## Motion 연결 기준

Live2D SDK의 표준 흐름을 따른다.

```text
SenaCharacterPresentation.motionKey
-> SenaCharacterBindingProfile.ResolveMotion()
-> Live2DCharacterPresenter.MotionClipBinding
-> CubismMotionController.PlayAnimation(AnimationClip)
```

`Live2DCharacterPresenter`는 모션을 직접 구현하지 않는다. Unity/Cubism SDK가 생성한 `AnimationClip`을 찾아 `CubismMotionController.PlayAnimation()`에 넘기는 얇은 어댑터 역할만 한다.

모션 재생에 필요한 Cubism 구성:

- `CubismMotionController`
- `CubismFadeController`
- 모델별 `.fadeMotionList` asset
- `Animator`

주의:

- `CubismMotionController`는 `CubismFadeController`를 요구한다.
- `CubismFadeController.CubismFadeMotionList`가 비어 있으면 `CubismMotionController : CubismFadeMotionList doesn't set in CubismFadeController.` 오류가 발생한다.
- `CubismMotionController.PlayAnimation(..., isLoop: true)`는 반복 재생은 해 주지만, 루프 경계에서의 fade 처리는 별도 callback/replay 방식이 필요할 수 있다. Phase 2에서는 먼저 반복 idle motion을 안정화하고, 루프 경계가 눈에 띄면 후속 작업으로 개선한다.

SnowBear Majo 테스트 모델 기준:

- `魔女.model3.json`의 `Motions.Idle`은 `Scene1.motion3.json` 하나를 가리킨다.
- Unity import 후 `Scene1.motion3.json`에서 생성된 `AnimationClip`을 idle 후보로 사용한다.
- `Live2DCharacterPresenter.motionClips` 초기 테스트 값:
  - `motionName`: `idle`
  - `clip`: `Scene1` 또는 Unity가 `Scene1.motion3.json`에서 생성한 animation clip
  - `loop`: `true`
  - `priority`: `Idle`

이렇게 두면 SENA의 내부 `motionKey = idle`이 모델의 idle animation clip으로 연결된다. 모델을 교체할 때는 같은 SENA 키를 유지하고, binding profile과 motion clip 연결만 모델별로 바꾼다.

## Procedural idle 보완 기준

모델에 포함된 idle motion이 없거나, 실제로는 특정 표정/손동작 파라미터만 움직여 기본 대기 움직임으로 쓰기 어려운 경우가 있다. 이때는 Cubism motion clip을 억지로 수정하지 않고 `Live2DProceduralIdleDriver`를 모델 root에 추가한다.

`Live2DProceduralIdleDriver`는 Cubism SDK의 `ICubismUpdatable` 흐름에 맞춰 표준 파라미터에 약한 additive 값을 더한다.

기본 대상 파라미터:

- `ParamAngleX`
- `ParamAngleY`
- `ParamAngleZ`
- `ParamBodyAngleX`
- `ParamBodyAngleY`
- `ParamBreath`

이 컴포넌트는 기존 `CubismMotionController`를 대체하지 않는다. 모델에 원본 idle clip이 있으면 그대로 재생하고, procedural idle은 아주 약한 호흡/고개 흔들림 레이어로만 사용한다. 모델에 해당 파라미터가 없으면 자동으로 스킵한다.

권장 설정:

- 처음에는 `globalWeight = 1`
- 움직임이 과하면 `globalWeight` 또는 각 파라미터의 `amplitude`를 낮춘다.
- 모델 고유 motion이 충분히 자연스럽다면 `playOnStart`를 끄거나 컴포넌트를 제거한다.

SnowBear Majo 테스트 모델에서는 `Scene1.motion3.json`이 일반적인 기본 idle이라기보다 `哭哭`, `招手` 같은 모델 고유 파라미터를 움직였다. 그래서 `Live2DProceduralIdleDriver`를 추가해 `ParamAngleX/Y/Z`, `ParamBodyAngleX/Y`, `ParamBreath` 기반의 약한 대기 움직임을 보완했다.

## Speaking mouth 기초 표현 기준

TTS와 오디오 기반 lip-sync가 붙기 전에는 `Live2DSpeakingMouthDriver`로 speaking 상태를 최소 표현한다.

역할:

- 같은 모델 root의 `CharacterStateController.PresentationChanged`를 구독한다.
- `SenaCharacterPresentation.IsSpeaking == true`일 때 `CubismMouthController.MouthOpening`을 주기적으로 변조한다.
- speaking이 끝나면 입을 `closedOpening`으로 부드럽게 닫는다.

이 드라이버는 Live2D 공식 MouthMovement 구조를 따른다. 모델에는 `CubismMouthController`가 있어야 하고, 입 열림 파라미터에는 `CubismMouthParameter`가 있어야 한다. SnowBear Majo 테스트 모델은 `ParamMouthOpenY`가 mouth parameter로 import되어 있다.

Unity client의 `/v1/messages` 응답은 `assistant_text` 직후 `assistant_state: idle`이 같은 batch 안에 들어올 수 있다. 이 경우 speaking 표현이 한 프레임만 켜졌다가 바로 꺼질 수 있으므로, `SenaClientController.minimumSpeakingPresentationSeconds` 동안 캐릭터 레이어의 idle 복귀만 짧게 지연한다. UI의 assistant state text는 서버 응답 그대로 갱신한다. 승인 요청, tool result, error, disconnected 같은 더 중요한 상태가 오면 speaking hold는 즉시 취소한다.

`CubismMouthController.BlendMode`는 speaking 기초 표현에서는 `Override`를 사용한다. `Multiply`는 현재 mouth parameter 값에 `MouthOpening`을 곱하기 때문에, 모델/표정/모션이 입 파라미터를 0으로 두고 있으면 `MouthOpening`을 올려도 실제 입이 열리지 않을 수 있다.

초기 권장 설정:

- `closedOpening = 0`
- `mouthBlendMode = Override`
- `minimumSpeakingOpening = 0.15`
- `maximumSpeakingOpening = 0.75`
- `syllableFrequencyHz = 4.5`
- `smoothingSpeed = 18`

나중에 TTS 오디오가 들어오면 `syllableFrequencyHz` 기반 임시 파형 대신 오디오 envelope 또는 음소/viseme adapter가 `MouthOpening` 값을 공급하도록 교체한다. 이때도 `CharacterStateController`와 `SenaCharacterPresentation` 계약은 유지한다.

## URP 렌더링 기준

Live2D Cubism SDK for Unity R5 계열은 URP용 renderer pass를 요구한다.

현재 검증된 설정:

- `PC_RPAsset`의 Renderer List에 `CubismURPRenderer.asset` 연결
- `Main Camera`가 해당 renderer index를 사용
- `PC_RPAsset`에서 HDR 비활성화
- `Main Camera` 배경색 alpha는 1로 설정

주의:

- Scene 뷰에서 보이는 것과 Game 뷰에서 보이는 것은 다를 수 있다. 최종 판단은 Game 뷰와 standalone build에서 한다.
- Live2D 모델은 UI `RectTransform`이 아니라 월드 오브젝트다. `Position X = 7000` 같은 UI 픽셀 좌표식 배치는 카메라 밖으로 나갈 수 있다.
- 모델이 Scene 뷰에는 보이지만 Game 뷰에는 보이지 않으면, 먼저 모델 root의 world position과 `Main Camera` 기준 전방 위치를 확인한다.
- URP + Cubism에서 배경이 검게 보이면 HDR 설정을 먼저 확인한다.

## 모델별 binding profile 기준

SENA 내부 표현 키는 모델이 바뀌어도 유지한다.

예:

- `neutral`
- `focused`
- `thinking`
- `awaiting_approval`
- `speaking`
- `satisfied`
- `concerned`
- `disconnected`
- `error`

모델별로 바뀌는 것은 `targetExpressionName`뿐이다. 예를 들어 SnowBear Majo 테스트 모델에서는 내부 키를 `x`, `yj`, `xx`, `ku`, `h`, `sq` 같은 실제 expression 이름에 매핑했다.

`Live2DCharacterPresenter`는 expression 이름을 비교할 때 경로와 확장자를 제거한다. 따라서 `x`, `x.exp3`, `expressions/x.exp3.json`처럼 들어와도 같은 이름으로 비교할 수 있다.

motion도 같은 방식으로 내부 key와 모델별 clip 이름을 분리한다. 현재 테스트 모델처럼 사용할 수 있는 motion clip이 하나뿐이면 여러 SENA motion key를 같은 모델 motion으로 매핑하고, 표정과 procedural idle로 상태 차이를 보완할 수 있다.

## SENA 내부 상태 매핑 기준

`CharacterPresentationMapper`는 아래 SENA 내부 키를 생성한다. 이 표는 모델별 expression/motion 이름이 아니라 Project-SENA 내부 계약이다.

| Character state | Expression key | Motion key | Speaking | Attention |
| --- | --- | --- | --- | --- |
| `Idle` | `neutral` | `idle` | false | false |
| `Listening` | `focused` | `listening` | false | true |
| `Thinking` | `thinking` | `thinking` | false | true |
| `AwaitingApproval` | `awaiting_approval` | `awaiting_approval` | false | true |
| `ToolRunning` | `focused` | `tool_running` | false | true |
| `Speaking` | persona 기반 | `speaking` | true | true |
| `Satisfied` | `satisfied` | `positive` | false | false |
| `Concerned` | `concerned` | `concerned` | false | true |
| `Disconnected` | `disconnected` | `idle` | false | false |
| `Error` | `error` | `error` | false | true |

`Speaking` 상태는 `persona_state`에 따라 expression을 고른다.

| Persona state | Speaking expression |
| --- | --- |
| `focused` | `focused` |
| `satisfied` | `satisfied` |
| `concerned` | `concerned` |
| `playful` | `satisfied` |
| `calm` | `neutral` |
| 기타/없음 | `speaking` |

모델별 `SenaCharacterBindingProfile`은 위 내부 키를 모델의 실제 expression/motion 이름으로 변환한다.

예를 들어 SnowBear Majo 테스트 모델은 실제 expression 이름이 SENA 내부 키와 다르므로 아래처럼 매핑했다.

| SENA expression key | SnowBear Majo target |
| --- | --- |
| `neutral` | `x` |
| `focused` | `yj` |
| `thinking` | `yj` |
| `awaiting_approval` | `xx` |
| `speaking` | `x` |
| `satisfied` | `x` |
| `concerned` | `ku` |
| `disconnected` | `h` |
| `error` | `sq` |

SnowBear Majo 테스트 모델은 usable motion clip이 사실상 `Scene1` 하나였기 때문에 모든 SENA motion key를 `idle` target으로 연결했다. 상태별 차이는 expression과 `Live2DProceduralIdleDriver`로 보완한다.

이 매핑 계약은 Unity EditMode 테스트로 검증한다.

Unity Editor에서 실행:

1. `Window > General > Test Runner`를 연다.
2. `EditMode` 탭을 선택한다.
3. `ProjectSENA.Editor.Tests` 아래의 character 관련 테스트를 실행한다.

현재 포함된 테스트:

- `CharacterPresentationMapperTests`
- `SenaCharacterBindingProfileTests`

## 표현 흐름

```text
assistant_state / persona_state / tool_result
-> SenaCharacterState
-> SenaCharacterPresentation
-> SenaCharacterBindingProfile
-> Live2D expression / motion
```

`expressionKey`는 최종 표정 선택용 키다.

예:

- `neutral`
- `focused`
- `thinking`
- `awaiting_approval`
- `speaking`
- `satisfied`
- `concerned`
- `disconnected`
- `error`

`motionKey`는 모션 그룹 선택용 키다.

예:

- `idle`
- `listening`
- `thinking`
- `awaiting_approval`
- `tool_running`
- `speaking`
- `positive`
- `concerned`
- `error`

`valence`, `arousal`, `focus`, `confidence` 같은 연속값은 표정을 직접 결정하지 않는다. Live2D presenter에서는 흔들림, 시선, idle 강도, speaking motion 강도 같은 보조 표현에만 사용한다.

## 자산 배치 정책

커밋 가능:

- character binding profile
- import 절차 문서
- 예제용 빈 폴더 또는 README
- SENA 쪽 presenter 코드

커밋 금지:

- 사용자 제공 Live2D 모델
- 다운로드한 모델 패키지
- 생성된 텍스처/캐시
- 유료 또는 라이선스 제한이 있는 캐릭터 자산

로컬 전용 추천 경로:

```text
unity-client/Project-SENA-UnityClient/Assets/ProjectSENA/Characters/UserModels/
unity-client/Project-SENA-UnityClient/Assets/ProjectSENA/Characters/DownloadedModels/
```

위 경로는 `.gitignore`에 포함한다.

모델 후보를 고를 때는 [live2d-model-selection.kr.md](live2d-model-selection.kr.md)의 라이선스/기술 체크리스트를 먼저 확인한다.

## 검증 시나리오

Live2D 연결 후 최소한 아래 시나리오를 확인한다.

- Unity Play 직후 캐릭터가 Game 화면에 보인다.
- Console에 Live2D error가 반복 발생하지 않는다.
- 기본 상태에서 idle 표정과 대기 움직임이 보인다.
- assistant text 수신 중 `should_speak=true`일 때 입이 움직인다.
- assistant text 처리 후 idle로 돌아가면 입이 닫힌다.
- `메모장 열어줘` 같은 승인 요청에서 approval 표정으로 바뀐다.
- 승인/거절 후 다시 idle 또는 결과 상태로 돌아온다.
- inference-server 또는 desktop-agent 연결 실패 시 error/disconnected 표정으로 바뀐다.

## Troubleshooting

### 모델 대신 회색 placeholder가 보임

- `ProjectSenaClient`의 `SenaClientController.characterState`가 모델 root의 `CharacterStateController`를 가리키는지 확인한다.
- `CharacterStateController.presenter`가 같은 root의 `Live2DCharacterPresenter`를 가리키는지 확인한다.

### Expression was not found 경고가 발생함

- `CubismExpressionController.ExpressionsList`에 expression object가 들어 있는지 확인한다.
- `.model3.json`을 reimport했는지 확인한다.
- `SenaCharacterBindingProfile`의 target expression 이름이 실제 expression asset 이름과 맞는지 확인한다.

### Motion was not found 경고가 발생함

- `SenaCharacterBindingProfile`의 target motion 이름과 `Live2DCharacterPresenter.motionClips.motionName`이 같은지 확인한다.
- motion clip이 `Live2DCharacterPresenter.motionClips.clip`에 연결되어 있는지 확인한다.

### Not found motion from CubismFadeMotionList 오류가 발생함

- `CubismFadeController.CubismFadeMotionList`가 연결되어 있는지 확인한다.
- `AnimationClip`이 같은 모델 import에서 생성된 `.fadeMotionList`와 함께 쓰이고 있는지 확인한다.
- model/motion reimport 후 fade list가 갱신됐는지 확인한다.

### Scene 뷰에는 보이지만 Game 뷰에는 안 보임

- 모델 root의 world position이 `Main Camera`가 보는 영역 안인지 확인한다.
- UI 픽셀 좌표처럼 `Position X = 7000` 등을 넣지 않았는지 확인한다.
- Game 뷰와 standalone build를 기준으로 판단한다.

### Game 뷰 배경이 검게 보임

- `PC_RPAsset`에 `CubismURPRenderer.asset`이 연결되어 있는지 확인한다.
- `PC_RPAsset`에서 HDR을 끈다.
- `Main Camera`가 올바른 URP renderer index를 사용하는지 확인한다.

### Motion이 재생되지만 움직임이 체감되지 않음

- AnimationClip의 curve binding target이 현재 모델 hierarchy에 존재하는지 확인한다.
- 모델 motion이 `ParamAngleX`, `ParamBodyAngleX`, `ParamBreath`가 아니라 모델 고유 파라미터만 움직이는지 확인한다.
- 기본 idle로 쓰기 어렵다면 `Live2DProceduralIdleDriver`를 추가한다.

### Speaking 상태인데 입이 움직이지 않음

- 모델 root에 `Live2DSpeakingMouthDriver`가 있는지 확인한다.
- `Live2DSpeakingMouthDriver.characterState`가 같은 root의 `CharacterStateController`를 가리키는지 확인한다.
- `Live2DSpeakingMouthDriver.mouthController`가 모델 root의 `CubismMouthController`를 가리키는지 확인한다.
- `ParamMouthOpenY` 또는 모델의 입 열림 파라미터에 `CubismMouthParameter`가 붙어 있는지 확인한다.
- `assistant_text.payload.should_speak`가 `true`로 들어오는지 확인한다.

## SDK 도입 메모

Live2D 공식 자료 기준으로 Cubism SDK for Unity는 Unity용 SDK와 GitHub components를 제공한다. 2026년 현재 다운로드 페이지에는 Unity용 `.unitypackage`가 제공되고, 최신 Cubism Unity Components 계열은 URP 중심이며 Built-in/HDRP 지원에는 제한이 있다는 내용이 있다.

우리 Unity 프로젝트는 URP 템플릿이므로 방향은 맞지만, 실제 SDK import 전에 아래를 확인한다.

- Unity 6.3 LTS와 SDK 버전 호환성
- URP render pass 요구사항
- 모델이 Cubism 5.3+ 기능을 사용하는지
- Windows x64 standalone build 동작 여부
- 모델 자산 라이선스

URP 관련 검증에는 Live2D 공식 URP import 문서와 Built-in to URP migration 문서를 우선 참고한다. 특히 `CubismURPRenderer.asset`, HDR precision, Camera renderer 지정 여부는 문제 발생 시 첫 번째로 확인한다.

## 로컬 SDK 설치 정책

Cubism SDK와 Cubism Core는 Live2D 라이선스 동의가 필요한 외부 SDK이므로 repo에 커밋하지 않는다.

로컬 설치 절차:

1. Live2D 공식 다운로드 페이지에서 Cubism SDK for Unity `.unitypackage`를 받는다.
2. Unity Editor에서 `Assets > Import Package > Custom Package...`로 import한다.
3. 또는 Unity batchmode에서 `-importPackage`로 import한다.
4. import 결과로 생기는 `Assets/Live2D/`, `Assets/csc.rsp`, `Assets/mcs.rsp`는 local-only로 유지한다.
5. Live2D presenter를 실제로 컴파일할 개발 PC에서만 `PROJECT_SENA_LIVE2D` scripting define을 켠다.

SENA repo에 커밋되는 코드는 `CharacterPresenterBase`까지만 공통 계약으로 삼는다. `Live2DCharacterPresenter`는 `PROJECT_SENA_LIVE2D` define이 있을 때만 Cubism SDK 타입을 참조한다. 따라서 SDK가 없는 환경에서도 placeholder 캐릭터와 일반 Unity client는 계속 컴파일되어야 한다.

## 모델 교체 기준

모델을 바꾸더라도 아래 항목만 교체한다.

- `UserModels/` 아래의 실제 모델 폴더
- Unity가 생성한 Live2D prefab
- 해당 모델용 `SenaCharacterBindingProfile`
- `Live2DCharacterPresenter`의 expression/motion clip 연결

바꾸지 않는 항목:

- `SenaCharacterState`
- `SenaCharacterPresentation`
- `CharacterPresentationMapper`
- `CharacterPresenterBase`
- inference-server와 shared protocol

즉, 모델 교체는 표현 어댑터 영역의 작업이어야 하며 대화/추론/승인 흐름을 건드리지 않는다.

## Phase 2 구현 순서

1. 공식 SDK `.unitypackage`를 로컬 Unity 프로젝트에 import한다. 완료
2. SDK import 후 프로젝트가 모델 없이도 깨지지 않는지 확인한다. 완료
3. 사용자 제공 모델을 `UserModels/`에 넣고 prefab 생성까지 확인한다. 완료
4. 모델의 expression 목록을 읽어 `SenaCharacterBindingProfile`을 만든다. 완료
5. `Live2DCharacterPresenter`를 Live2D prefab에 붙이고 expression을 연결한다. 완료
6. placeholder presenter와 Live2D presenter를 같은 `CharacterPresenterBase` 경계에서 교체 가능하게 유지한다. 완료
7. `CubismMotionController`와 motion clip을 연결한다. 완료
8. 필요 시 `Live2DProceduralIdleDriver`로 idle 움직임을 보완한다. 완료
9. `Live2DSpeakingMouthDriver`로 speaking mouth 기초 표현을 연결한다. 완료
10. Unity client의 `minimumSpeakingPresentationSeconds`로 짧은 응답에서도 speaking 표현이 보이도록 한다. 완료
11. TTS 오디오 기반 lip-sync로 교체할 경계를 정리한다.
12. Live2D 모델 교체 절차를 한 번 더 검증한다.

## 참고 자료

- [Live2D Cubism SDK](https://www.live2d.com/en/sdk/about/)
- [Cubism SDK Manual](https://docs.live2d.com/en/cubism-sdk-manual/top/)
- [Cubism SDK for Unity Manual](https://docs.live2d.com/en/cubism-sdk-manual/cubism-sdk-for-unity/)
- [Cubism SDK for Unity Download](https://www.live2d.com/en/sdk/download/unity/)
- [Live2D CubismUnityComponents GitHub](https://github.com/Live2D/CubismUnityComponents)
- [CubismUnityComponents releases](https://github.com/Live2D/CubismUnityComponents/releases)
