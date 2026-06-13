namespace ProjectSENA.Character
{
    public static class CharacterPresentationMapper
    {
        public static SenaCharacterPresentation Map(SenaCharacterSnapshot snapshot)
        {
            return snapshot.State switch
            {
                SenaCharacterState.Listening => Create(
                    snapshot,
                    SenaExpressionKeys.Focused,
                    SenaMotionKeys.Listening,
                    valence: 0.15f,
                    arousal: 0.35f,
                    focus: 0.75f,
                    confidence: 0.8f,
                    isAttentionActive: true),
                SenaCharacterState.Thinking => Create(
                    snapshot,
                    SenaExpressionKeys.Thinking,
                    SenaMotionKeys.Thinking,
                    valence: 0.05f,
                    arousal: 0.55f,
                    focus: 0.85f,
                    confidence: 0.75f,
                    isAttentionActive: true),
                SenaCharacterState.AwaitingApproval => Create(
                    snapshot,
                    SenaExpressionKeys.AwaitingApproval,
                    SenaMotionKeys.AwaitingApproval,
                    valence: 0.05f,
                    arousal: 0.5f,
                    focus: 0.9f,
                    confidence: 0.9f,
                    isAttentionActive: true),
                SenaCharacterState.ToolRunning => Create(
                    snapshot,
                    SenaExpressionKeys.Focused,
                    SenaMotionKeys.ToolRunning,
                    valence: 0.05f,
                    arousal: 0.65f,
                    focus: 0.95f,
                    confidence: 0.85f,
                    isAttentionActive: true),
                SenaCharacterState.Speaking => MapSpeaking(snapshot),
                SenaCharacterState.Satisfied => Create(
                    snapshot,
                    SenaExpressionKeys.Satisfied,
                    SenaMotionKeys.Positive,
                    valence: 0.75f,
                    arousal: 0.45f,
                    focus: 0.45f,
                    confidence: 0.9f),
                SenaCharacterState.Concerned => Create(
                    snapshot,
                    SenaExpressionKeys.Concerned,
                    SenaMotionKeys.Concerned,
                    valence: -0.35f,
                    arousal: 0.45f,
                    focus: 0.65f,
                    confidence: 0.75f,
                    isAttentionActive: true),
                SenaCharacterState.Disconnected => Create(
                    snapshot,
                    SenaExpressionKeys.Disconnected,
                    SenaMotionKeys.Idle,
                    valence: -0.25f,
                    arousal: 0.2f,
                    focus: 0.2f,
                    confidence: 0.65f),
                SenaCharacterState.Error => Create(
                    snapshot,
                    SenaExpressionKeys.Error,
                    SenaMotionKeys.Error,
                    valence: -0.7f,
                    arousal: 0.65f,
                    focus: 0.75f,
                    confidence: 0.85f,
                    isAttentionActive: true),
                _ => Create(
                    snapshot,
                    SenaExpressionKeys.Neutral,
                    SenaMotionKeys.Idle,
                    valence: 0.1f,
                    arousal: 0.15f,
                    focus: 0.25f,
                    confidence: 0.85f)
            };
        }

        private static SenaCharacterPresentation MapSpeaking(SenaCharacterSnapshot snapshot)
        {
            string expressionKey = snapshot.PersonaState switch
            {
                "focused" => SenaExpressionKeys.Focused,
                "satisfied" => SenaExpressionKeys.Satisfied,
                "concerned" => SenaExpressionKeys.Concerned,
                "playful" => SenaExpressionKeys.Satisfied,
                "calm" => SenaExpressionKeys.Neutral,
                _ => SenaExpressionKeys.Speaking
            };

            float valence = expressionKey switch
            {
                SenaExpressionKeys.Satisfied => 0.65f,
                SenaExpressionKeys.Concerned => -0.25f,
                _ => 0.15f
            };

            return Create(
                snapshot,
                expressionKey,
                SenaMotionKeys.Speaking,
                valence,
                arousal: 0.55f,
                focus: 0.55f,
                confidence: 0.8f,
                isSpeaking: true,
                isAttentionActive: true);
        }

        private static SenaCharacterPresentation Create(
            SenaCharacterSnapshot snapshot,
            string expressionKey,
            string motionKey,
            float valence,
            float arousal,
            float focus,
            float confidence,
            bool isSpeaking = false,
            bool isAttentionActive = false)
        {
            return new SenaCharacterPresentation(
                snapshot,
                expressionKey,
                motionKey,
                valence,
                arousal,
                focus,
                confidence,
                isSpeaking,
                isAttentionActive);
        }
    }
}
