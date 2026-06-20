using NUnit.Framework;
using ProjectSENA.Character;
using UnityEngine;

namespace ProjectSENA.Editor.Tests
{
    public sealed class CharacterStateControllerTests
    {
        [Test]
        public void ApplyAssistantText_WithSpeakingFlag_OverridesThinkingState()
        {
            GameObject gameObject = new GameObject(nameof(CharacterStateControllerTests));
            try
            {
                CharacterStateController controller =
                    gameObject.AddComponent<CharacterStateController>();
                SenaCharacterPresentation lastPresentation = default;
                controller.PresentationChanged += presentation => lastPresentation = presentation;

                controller.ApplyAssistantState("thinking", "Interpreting user text.");
                controller.ApplyAssistantText("neutral", shouldSpeak: true);

                Assert.That(controller.CurrentState, Is.EqualTo(SenaCharacterState.Speaking));
                Assert.That(lastPresentation.IsSpeaking, Is.True);
                Assert.That(lastPresentation.MotionKey, Is.EqualTo(SenaMotionKeys.Speaking));
            }
            finally
            {
                Object.DestroyImmediate(gameObject);
            }
        }

        [Test]
        public void ApplyAssistantText_WithoutSpeakingFlag_ReturnsSpeakingStateToPersonaState()
        {
            GameObject gameObject = new GameObject(nameof(CharacterStateControllerTests));
            try
            {
                CharacterStateController controller =
                    gameObject.AddComponent<CharacterStateController>();
                controller.ApplyAssistantText("neutral", shouldSpeak: true);
                controller.ApplyAssistantText("neutral", shouldSpeak: false);

                Assert.That(controller.CurrentState, Is.EqualTo(SenaCharacterState.Idle));
                Assert.That(controller.ShouldSpeak, Is.False);
            }
            finally
            {
                Object.DestroyImmediate(gameObject);
            }
        }
    }
}
