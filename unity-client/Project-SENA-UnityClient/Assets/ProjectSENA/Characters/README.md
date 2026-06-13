# Project-SENA Character Assets

This folder stores Project-SENA character configuration that can be committed.

Do not commit user-supplied Live2D models, downloaded model packages, generated textures, or private character assets.

Recommended local-only folders:

- `UserModels/`
- `DownloadedModels/`

Use `SenaCharacterBindingProfile` assets to map Project-SENA expression and motion keys to each model's actual Live2D expression names and motion groups.

## Commit Boundary

Commit:

- Binding profiles
- Character presenter code
- Documentation
- Empty folder metadata needed by Unity

Do not commit:

- Cubism SDK files
- User-provided Live2D model folders
- Generated model prefabs, textures, motions, and expression assets under local-only model folders
- Paid or license-restricted character assets

## Scene Wiring

For a Live2D model scene instance:

- Add `CharacterStateController` to the model root.
- Add `Live2DCharacterPresenter` to the model root.
- Assign the model's `CubismExpressionController` to `Live2DCharacterPresenter`.
- Assign a model-specific `SenaCharacterBindingProfile`.
- Assign the model root's `CharacterStateController` to `SenaClientController.characterState`.

If `SenaClientController.characterState` is empty, the runtime fallback placeholder can appear instead of the Live2D character.

Phase 2 initial Live2D MVP uses expression only. Leave Cubism motion fields empty until motion playback is implemented as a separate task.
