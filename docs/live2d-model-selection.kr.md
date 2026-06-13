# Live2D 모델 선정 체크리스트

Project-SENA에 넣을 무료 Live2D 모델을 고를 때 확인할 항목이다.

## 라이선스

무료 모델이라도 아래 조건은 별도로 확인한다.

- 개인 사용 가능 여부
- 비상업 사용만 가능한지
- 상업 사용 가능 여부
- 앱/프로그램에 포함해서 배포 가능한지
- 수정 가능 여부
- 저작자 표시 필요 여부
- 재배포 금지 여부
- AI assistant, chatbot, VTuber 용도 제한 여부

Project-SENA repo에는 모델 파일을 커밋하지 않는다. 모델은 사용자가 로컬에 넣는 방식으로 둔다.

## 기술 조건

확인할 파일:

- `.model3.json`
- `.moc3`
- `textures/`
- `motions/`
- `expressions/`
- `physics3.json`
- `pose3.json`

우선순위:

1. Cubism 4 또는 Cubism 5 계열 모델
2. expression 파일이 여러 개 있는 모델
3. idle motion이 있는 모델
4. mouth open / eye blink parameter가 정상 구성된 모델
5. Unity Cubism SDK에서 import 사례가 있는 모델

## 표현 매핑 확인

모델을 가져오면 먼저 expression/motion 목록을 확인한 뒤 `SenaCharacterBindingProfile`에 매핑한다.

초기 SENA expression key:

- `neutral`
- `focused`
- `thinking`
- `awaiting_approval`
- `speaking`
- `satisfied`
- `concerned`
- `disconnected`
- `error`

모델에 해당 표정이 없으면 가까운 표현으로 연결한다.

예:

```text
SENA satisfied -> model expression smile
SENA concerned -> model expression sad
SENA error -> model expression worried
SENA awaiting_approval -> model expression focused 또는 neutral
```

초기 SENA motion key:

- `idle`
- `listening`
- `thinking`
- `awaiting_approval`
- `tool_running`
- `speaking`
- `positive`
- `concerned`
- `error`

모델에 motion이 적다면 대부분을 `idle`로 연결해도 된다. 표정 매핑이 먼저고, motion은 나중에 정교화한다.

## 후보 평가 메모 양식

```text
모델 이름:
출처 URL:
라이선스:
상업/비상업:
재배포 가능 여부:
수정 가능 여부:
Cubism 버전:
model3.json 존재:
expression 개수:
motion 개수:
Unity import 사례:
주의사항:
```

## 추천 판단

처음에는 표현이 풍부한 모델보다 **라이선스가 명확하고 Unity import가 잘 되는 모델**이 좋다. Phase 2의 목적은 최종 캐릭터 선정이 아니라 Project-SENA의 Live2D presenter 경계를 검증하는 것이다.

## 현재 테스트 후보

모델 이름: SnowBear Project `魔女`

출처 URL: <https://snowbearpro.booth.pm/items/6499774>

판단:

- 무료 모델이며 개인 사용 테스트에는 적합해 보인다.
- BOOTH 설명 기준으로 재배포/재판매는 금지이며, 모델 및 원본 그림 수정도 금지다.
- Project-SENA repo에는 포함하지 않고 `UserModels/` 아래 로컬 전용 자산으로만 둔다.
- `model3.json`, `moc3`, `physics3`, `cdi3`, texture, expression 파일, motion 파일이 있다.
- `model3.json`의 EyeBlink/LipSync 그룹은 구성되어 있다.
- 원본 `model3.json`에는 expression/motion 목록이 비어 있었으므로, 로컬 테스트 사본에서만 `FileReferences.Expressions`와 `Motions`를 보강했다.

초기 매핑 방향:

- `neutral`, `speaking`: expression을 강하게 걸지 않거나 기본 표정에 가까운 표현
- `focused`, `thinking`, `awaiting_approval`: 집중/기본 계열 표현
- `satisfied`: 밝은 표정 계열
- `concerned`, `error`, `disconnected`: 우는 표정 또는 어두운 표정 계열
- motion은 우선 `idle` 하나로 묶고, 표정 매핑을 먼저 검증한다.
