using NUnit.Framework;
using ProjectSENA.Character;

namespace ProjectSENA.Editor.Tests
{
    public sealed class CharacterPresentationMapperTests
    {
        [TestCase(SenaCharacterState.Idle, SenaExpressionKeys.Neutral, SenaMotionKeys.Idle, false, false)]
        [TestCase(SenaCharacterState.Listening, SenaExpressionKeys.Focused, SenaMotionKeys.Listening, false, true)]
        [TestCase(SenaCharacterState.Thinking, SenaExpressionKeys.Thinking, SenaMotionKeys.Thinking, false, true)]
        [TestCase(SenaCharacterState.AwaitingApproval, SenaExpressionKeys.AwaitingApproval, SenaMotionKeys.AwaitingApproval, false, true)]
        [TestCase(SenaCharacterState.ToolRunning, SenaExpressionKeys.Focused, SenaMotionKeys.ToolRunning, false, true)]
        [TestCase(SenaCharacterState.Satisfied, SenaExpressionKeys.Satisfied, SenaMotionKeys.Positive, false, false)]
        [TestCase(SenaCharacterState.Concerned, SenaExpressionKeys.Concerned, SenaMotionKeys.Concerned, false, true)]
        [TestCase(SenaCharacterState.Disconnected, SenaExpressionKeys.Disconnected, SenaMotionKeys.Idle, false, false)]
        [TestCase(SenaCharacterState.Error, SenaExpressionKeys.Error, SenaMotionKeys.Error, false, true)]
        public void Map_UsesExpectedPresentationKeysForState(
            SenaCharacterState state,
            string expressionKey,
            string motionKey,
            bool isSpeaking,
            bool isAttentionActive)
        {
            SenaCharacterPresentation presentation = CharacterPresentationMapper.Map(
                Snapshot(state, personaState: "neutral", shouldSpeak: isSpeaking));

            Assert.That(presentation.ExpressionKey, Is.EqualTo(expressionKey));
            Assert.That(presentation.MotionKey, Is.EqualTo(motionKey));
            Assert.That(presentation.IsSpeaking, Is.EqualTo(isSpeaking));
            Assert.That(presentation.IsAttentionActive, Is.EqualTo(isAttentionActive));
        }

        [TestCase("neutral", SenaExpressionKeys.Speaking, 0.15f)]
        [TestCase("focused", SenaExpressionKeys.Focused, 0.15f)]
        [TestCase("satisfied", SenaExpressionKeys.Satisfied, 0.65f)]
        [TestCase("concerned", SenaExpressionKeys.Concerned, -0.25f)]
        [TestCase("playful", SenaExpressionKeys.Satisfied, 0.65f)]
        [TestCase("calm", SenaExpressionKeys.Neutral, 0.15f)]
        public void MapSpeaking_UsesPersonaStateForExpression(
            string personaState,
            string expressionKey,
            float expectedValence)
        {
            SenaCharacterPresentation presentation = CharacterPresentationMapper.Map(
                Snapshot(SenaCharacterState.Speaking, personaState, shouldSpeak: true));

            Assert.That(presentation.ExpressionKey, Is.EqualTo(expressionKey));
            Assert.That(presentation.MotionKey, Is.EqualTo(SenaMotionKeys.Speaking));
            Assert.That(presentation.IsSpeaking, Is.True);
            Assert.That(presentation.IsAttentionActive, Is.True);
            Assert.That(presentation.Valence, Is.EqualTo(expectedValence).Within(0.001f));
        }

        [Test]
        public void Map_KeepsSnapshotDataForDownstreamPresentation()
        {
            SenaCharacterSnapshot snapshot = new SenaCharacterSnapshot(
                SenaCharacterState.AwaitingApproval,
                assistantState: "awaiting_approval",
                personaState: "focused",
                detail: "Waiting for user approval.",
                shouldSpeak: false);

            SenaCharacterPresentation presentation = CharacterPresentationMapper.Map(snapshot);

            Assert.That(presentation.Snapshot.State, Is.EqualTo(SenaCharacterState.AwaitingApproval));
            Assert.That(presentation.Snapshot.AssistantState, Is.EqualTo("awaiting_approval"));
            Assert.That(presentation.Snapshot.PersonaState, Is.EqualTo("focused"));
            Assert.That(presentation.Snapshot.Detail, Is.EqualTo("Waiting for user approval."));
            Assert.That(presentation.Snapshot.ShouldSpeak, Is.False);
        }

        private static SenaCharacterSnapshot Snapshot(
            SenaCharacterState state,
            string personaState,
            bool shouldSpeak)
        {
            return new SenaCharacterSnapshot(
                state,
                assistantState: state.ToString(),
                personaState: personaState,
                detail: string.Empty,
                shouldSpeak: shouldSpeak);
        }
    }
}
