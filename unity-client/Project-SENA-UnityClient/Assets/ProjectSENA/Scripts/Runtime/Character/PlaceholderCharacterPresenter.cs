using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace ProjectSENA.Character
{
    public sealed class PlaceholderCharacterPresenter : CharacterPresenterBase
    {
        [Header("Placeholder Visuals")]
        [SerializeField] private Graphic stateTintTarget;
        [SerializeField] private TMP_Text stateLabel;
        [SerializeField] private Transform animatedRoot;

        [Header("Motion")]
        [SerializeField] private float idleBobAmplitude = 0.03f;
        [SerializeField] private float activeBobAmplitude = 0.06f;
        [SerializeField] private float bobSpeed = 2.4f;

        private SenaCharacterPresentation _presentation = CharacterPresentationMapper.Map(
            new SenaCharacterSnapshot(
                SenaCharacterState.Idle,
                "idle",
                "neutral",
                string.Empty,
                false));
        private Vector3 _initialLocalPosition;
        private bool _hasInitialLocalPosition;

        private void Awake()
        {
            if (animatedRoot == null)
            {
                animatedRoot = transform;
            }

            CaptureInitialPosition();
            ApplyVisuals();
        }

        private void Update()
        {
            UpdateMotion();
        }

        public void BindVisuals(Graphic tintTarget, TMP_Text label, Transform motionRoot)
        {
            stateTintTarget = tintTarget;
            stateLabel = label;
            animatedRoot = motionRoot != null ? motionRoot : transform;
            CaptureInitialPosition();
            ApplyVisuals();
        }

        public override void ApplyPresentation(SenaCharacterPresentation presentation)
        {
            _presentation = presentation;
            ApplyVisuals();
        }

        private void CaptureInitialPosition()
        {
            if (animatedRoot == null)
            {
                return;
            }

            _initialLocalPosition = animatedRoot.localPosition;
            _hasInitialLocalPosition = true;
        }

        private void ApplyVisuals()
        {
            if (stateTintTarget != null)
            {
                stateTintTarget.color = GetExpressionColor(_presentation.ExpressionKey);
            }

            if (stateLabel != null)
            {
                stateLabel.text = _presentation.ExpressionKey;
            }
        }

        private void UpdateMotion()
        {
            if (!_hasInitialLocalPosition || animatedRoot == null)
            {
                return;
            }

            float amplitude = Mathf.Lerp(idleBobAmplitude, activeBobAmplitude, _presentation.Arousal);
            float speed = bobSpeed * Mathf.Lerp(0.75f, 1.25f, _presentation.Arousal);
            float offset = Mathf.Sin(Time.time * speed) * amplitude;
            animatedRoot.localPosition = _initialLocalPosition + new Vector3(0f, offset, 0f);
        }

        private static Color GetExpressionColor(string expressionKey)
        {
            return expressionKey switch
            {
                SenaExpressionKeys.Focused => new Color(0.36f, 0.78f, 0.92f, 1f),
                SenaExpressionKeys.Thinking => new Color(0.95f, 0.78f, 0.32f, 1f),
                SenaExpressionKeys.AwaitingApproval => new Color(1f, 0.62f, 0.28f, 1f),
                SenaExpressionKeys.Speaking => new Color(0.55f, 0.84f, 0.48f, 1f),
                SenaExpressionKeys.Satisfied => new Color(0.46f, 0.82f, 0.52f, 1f),
                SenaExpressionKeys.Concerned => new Color(0.72f, 0.56f, 0.92f, 1f),
                SenaExpressionKeys.Disconnected => new Color(0.55f, 0.55f, 0.55f, 1f),
                SenaExpressionKeys.Error => new Color(0.92f, 0.35f, 0.35f, 1f),
                _ => new Color(0.78f, 0.82f, 0.86f, 1f)
            };
        }
    }
}
