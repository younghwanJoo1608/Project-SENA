namespace ProjectSENA.Character
{
    public static class SenaExpressionKeys
    {
        public const string Neutral = "neutral";
        public const string Focused = "focused";
        public const string Thinking = "thinking";
        public const string AwaitingApproval = "awaiting_approval";
        public const string Speaking = "speaking";
        public const string Satisfied = "satisfied";
        public const string Concerned = "concerned";
        public const string Disconnected = "disconnected";
        public const string Error = "error";
    }

    public static class SenaMotionKeys
    {
        public const string Idle = "idle";
        public const string Listening = "listening";
        public const string Thinking = "thinking";
        public const string AwaitingApproval = "awaiting_approval";
        public const string ToolRunning = "tool_running";
        public const string Speaking = "speaking";
        public const string Positive = "positive";
        public const string Concerned = "concerned";
        public const string Error = "error";
    }

    public readonly struct SenaCharacterPresentation
    {
        public SenaCharacterPresentation(
            SenaCharacterSnapshot snapshot,
            string expressionKey,
            string motionKey,
            float valence,
            float arousal,
            float focus,
            float confidence,
            bool isSpeaking,
            bool isAttentionActive)
        {
            Snapshot = snapshot;
            ExpressionKey = expressionKey;
            MotionKey = motionKey;
            Valence = valence;
            Arousal = arousal;
            Focus = focus;
            Confidence = confidence;
            IsSpeaking = isSpeaking;
            IsAttentionActive = isAttentionActive;
        }

        public SenaCharacterSnapshot Snapshot { get; }
        public SenaCharacterState State => Snapshot.State;
        public string ExpressionKey { get; }
        public string MotionKey { get; }
        public float Valence { get; }
        public float Arousal { get; }
        public float Focus { get; }
        public float Confidence { get; }
        public bool IsSpeaking { get; }
        public bool IsAttentionActive { get; }
    }
}
