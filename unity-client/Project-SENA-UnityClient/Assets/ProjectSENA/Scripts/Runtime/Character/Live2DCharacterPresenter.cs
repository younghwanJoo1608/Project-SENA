#if PROJECT_SENA_LIVE2D
using System;
using System.IO;
using System.Text;
using Live2D.Cubism.Framework.Expression;
using Live2D.Cubism.Framework.Motion;
using UnityEngine;

namespace ProjectSENA.Character
{
    [DisallowMultipleComponent]
    public sealed class Live2DCharacterPresenter : CharacterPresenterBase
    {
        [Header("SENA Binding")]
        [SerializeField] private SenaCharacterBindingProfile bindingProfile;

        [Header("Cubism Components")]
        [SerializeField] private CubismExpressionController expressionController;
        [SerializeField] private CubismMotionController motionController;

        [Header("Motion Clips")]
        [SerializeField] private MotionClipBinding[] motionClips = Array.Empty<MotionClipBinding>();
        [SerializeField] private bool replaySameMotion;

        private string currentExpressionName;
        private string currentMotionName;
        private bool warnedMissingExpressionController;
        private bool warnedMissingExpressionList;

        private void Awake()
        {
            if (expressionController == null)
            {
                expressionController = GetComponentInChildren<CubismExpressionController>(includeInactive: true);
            }

            if (motionController == null)
            {
                motionController = GetComponentInChildren<CubismMotionController>(includeInactive: true);
            }
        }

        public override void ApplyPresentation(SenaCharacterPresentation presentation)
        {
            ApplyExpression(presentation);
            ApplyMotion(presentation);
        }

        private void ApplyExpression(SenaCharacterPresentation presentation)
        {
            if (expressionController == null)
            {
                WarnOnce(
                    ref warnedMissingExpressionController,
                    "Live2D expression controller is not assigned. Expression changes will be skipped.");
                return;
            }

            string targetExpression = bindingProfile == null
                ? presentation.ExpressionKey
                : bindingProfile.ResolveExpression(presentation.ExpressionKey, presentation.ExpressionKey);

            if (string.IsNullOrEmpty(targetExpression) ||
                NamesMatch(currentExpressionName, targetExpression))
            {
                return;
            }

            int expressionIndex = FindExpressionIndex(targetExpression);
            if (expressionIndex < 0)
            {
                Debug.LogWarning(
                    $"Live2D expression was not found: {targetExpression}. " +
                    $"Available expressions: {BuildAvailableExpressionList()}",
                    this);
                return;
            }

            expressionController.CurrentExpressionIndex = expressionIndex;
            currentExpressionName = targetExpression;
        }

        private int FindExpressionIndex(string expressionName)
        {
            var expressionObjects = expressionController.ExpressionsList?.CubismExpressionObjects;
            if (expressionObjects == null)
            {
                WarnOnce(
                    ref warnedMissingExpressionList,
                    "Live2D expression list is not assigned. Check the CubismExpressionController Expressions List field.");
                return -1;
            }

            for (int i = 0; i < expressionObjects.Length; i++)
            {
                if (expressionObjects[i] != null &&
                    NamesMatch(expressionObjects[i].name, expressionName))
                {
                    return i;
                }
            }

            return -1;
        }

        private string BuildAvailableExpressionList()
        {
            var expressionObjects = expressionController.ExpressionsList?.CubismExpressionObjects;
            if (expressionObjects == null || expressionObjects.Length == 0)
            {
                return "(none)";
            }

            StringBuilder builder = new StringBuilder();
            for (int i = 0; i < expressionObjects.Length; i++)
            {
                if (expressionObjects[i] == null)
                {
                    continue;
                }

                if (builder.Length > 0)
                {
                    builder.Append(", ");
                }

                builder.Append(expressionObjects[i].name);
            }

            return builder.Length == 0 ? "(none)" : builder.ToString();
        }

        private void WarnOnce(ref bool flag, string message)
        {
            if (flag)
            {
                return;
            }

            flag = true;
            Debug.LogWarning(message, this);
        }

        private void ApplyMotion(SenaCharacterPresentation presentation)
        {
            if (motionController == null)
            {
                return;
            }

            string targetMotion = bindingProfile == null
                ? presentation.MotionKey
                : bindingProfile.ResolveMotion(presentation.MotionKey, presentation.MotionKey);

            if (string.IsNullOrEmpty(targetMotion) ||
                (!replaySameMotion && NamesMatch(currentMotionName, targetMotion)))
            {
                return;
            }

            if (!TryFindMotionClip(targetMotion, out MotionClipBinding motionClip) ||
                motionClip.clip == null)
            {
                return;
            }

            motionController.PlayAnimation(
                motionClip.clip,
                priority: ToCubismPriority(motionClip.priority),
                isLoop: motionClip.loop);
            currentMotionName = targetMotion;
        }

        private bool TryFindMotionClip(string motionName, out MotionClipBinding motionClip)
        {
            foreach (MotionClipBinding candidate in motionClips)
            {
                if (NamesMatch(candidate.motionName, motionName))
                {
                    motionClip = candidate;
                    return true;
                }
            }

            motionClip = default;
            return false;
        }

        private static int ToCubismPriority(SenaLive2DMotionPriority priority)
        {
            return priority switch
            {
                SenaLive2DMotionPriority.Force => CubismMotionPriority.PriorityForce,
                SenaLive2DMotionPriority.Idle => CubismMotionPriority.PriorityIdle,
                _ => CubismMotionPriority.PriorityNormal
            };
        }

        private static bool NamesMatch(string left, string right)
        {
            return string.Equals(NormalizeName(left), NormalizeName(right), StringComparison.OrdinalIgnoreCase);
        }

        private static string NormalizeName(string value)
        {
            if (string.IsNullOrEmpty(value))
            {
                return string.Empty;
            }

            string normalized = value.Replace('\\', '/').Trim();
            normalized = Path.GetFileName(normalized);

            for (int i = 0; i < 3; i++)
            {
                string withoutExtension = Path.GetFileNameWithoutExtension(normalized);
                if (string.Equals(withoutExtension, normalized, StringComparison.Ordinal))
                {
                    break;
                }

                normalized = withoutExtension;
            }

            return normalized;
        }

        [Serializable]
        public struct MotionClipBinding
        {
            public string motionName;
            public AnimationClip clip;
            public bool loop;
            public SenaLive2DMotionPriority priority;
        }

        public enum SenaLive2DMotionPriority
        {
            Normal,
            Idle,
            Force
        }
    }
}
#endif
