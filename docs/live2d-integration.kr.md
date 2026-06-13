# Live2D 통합 계획

이 문서는 Phase 2에서 Live2D 모델을 Project-SENA Unity client에 연결하기 위한 기준을 정리한다.

## 현재 결정

- Project-SENA의 캐릭터 표현 입력은 `SenaCharacterPresentation`으로 고정한다.
- Live2D presenter는 `expressionKey`와 `motionKey`를 받아 모델별 expression/motion으로 변환한다.
- 모델마다 expression 파일명과 motion group 이름이 다르므로, 직접 코드에 박지 않고 `SenaCharacterBindingProfile`로 매핑한다.
- Live2D 모델 파일, 다운로드한 모델 패키지, 개인 캐릭터 자산은 git에 커밋하지 않는다.
- Phase 2 초기 MVP에서는 Live2D motion을 연결하지 않고 expression만 연결한다.

## 현재 검증된 MVP 구조

2026-06-14 기준으로 아래 흐름을 Unity Editor에서 검증했다.

```text
SenaClientController
-> CharacterStateController
-> Live2DCharacterPresenter
-> CubismExpressionController
-> model expression
```

검증된 상태:

- `idle` 상태에서 기본 표정 적용
- 메모장 실행 요청처럼 approval이 필요한 요청에서 approval 대기 표정 적용
- inference-server 연결 실패 시 disconnected/error 계열 표정 적용
- Live2D 모델이 Game 화면에 렌더링됨
- Unity 6.3 LTS URP 환경에서 HDR을 끄면 검은 배경 합성 문제가 사라짐

아직 연결하지 않은 것:

- Cubism motion playback
- idle motion
- speaking mouth/motion
- audio lip-sync
- 시선 추적

따라서 현재 완료 기준은 "표정 신호가 Live2D expression까지 도달한다"이며, "모션이 재생된다"가 아니다.

## Unity 씬 연결 기준

Live2D 모델 prefab의 root object에 아래 컴포넌트를 둔다.

- `CharacterStateController`
- `Live2DCharacterPresenter`
- `CubismExpressionController`

연결 규칙:

- `CharacterStateController.presenter`에는 같은 모델 root의 `Live2DCharacterPresenter`를 연결한다.
- `Live2DCharacterPresenter.bindingProfile`에는 모델별 `SenaCharacterBindingProfile`을 연결한다.
- `Live2DCharacterPresenter.expressionController`에는 같은 모델 root의 `CubismExpressionController`를 연결한다.
- `Live2DCharacterPresenter.motionController`는 Phase 2 초기 MVP에서는 비워 둔다.
- `Live2DCharacterPresenter.motionClips`는 Phase 2 초기 MVP에서는 비워 둔다.
- `ProjectSenaClient`의 `SenaClientController.characterState`에는 모델 root의 `CharacterStateController`를 연결한다.

`SenaClientController.characterState`가 비어 있으면 fallback placeholder가 자동 생성될 수 있다. Live2D 테스트 중 회색 placeholder가 보이면, 이 연결이 빠졌는지 먼저 확인한다.

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

## 다음 구현 순서

1. 공식 SDK `.unitypackage`를 로컬 Unity 프로젝트에 import한다. 완료
2. SDK import 후 프로젝트가 모델 없이도 깨지지 않는지 확인한다. 완료
3. 사용자 제공 모델을 `UserModels/`에 넣고 prefab 생성까지 확인한다. 완료
4. 모델의 expression 목록을 읽어 `SenaCharacterBindingProfile`을 만든다. 완료
5. `Live2DCharacterPresenter`를 Live2D prefab에 붙이고 expression을 연결한다. 완료
6. placeholder presenter와 Live2D presenter를 같은 `CharacterPresenterBase` 경계에서 교체 가능하게 유지한다. 완료
7. motion 연결 전, 현재 expression-only MVP를 standalone build에서 한 번 더 검증한다.
8. 다음 단계에서 `CubismMotionController`와 motion clip 연결을 별도 작업으로 진행한다.

## 참고 자료

- [Live2D Cubism SDK](https://www.live2d.com/en/sdk/about/)
- [Cubism SDK Manual](https://docs.live2d.com/en/cubism-sdk-manual/top/)
- [Cubism SDK for Unity Manual](https://docs.live2d.com/en/cubism-sdk-manual/cubism-sdk-for-unity/)
- [Cubism SDK for Unity Download](https://www.live2d.com/en/sdk/download/unity/)
- [Live2D CubismUnityComponents GitHub](https://github.com/Live2D/CubismUnityComponents)
- [CubismUnityComponents releases](https://github.com/Live2D/CubismUnityComponents/releases)
