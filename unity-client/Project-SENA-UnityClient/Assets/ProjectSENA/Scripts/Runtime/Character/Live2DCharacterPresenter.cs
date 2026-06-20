#if PROJECT_SENA_LIVE2D
using System;
using System.Collections;
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
        [SerializeField] private bool warnOnSkippedMotion = true;
        [SerializeField] private bool rebindAnimatorBeforeFirstMotion = true;

        private string currentExpressionName;
        private string currentMotionName;
        private bool warnedMissingExpressionController;
        private bool warnedMissingExpressionList;
        private bool warnedMissingMotionController;
        private bool warnedEmptyMotionClips;
        private bool warnedAnimatorController;
        private bool warnedMissingAnimator;
        private bool animatorReboundForMotion;
        private bool canPlayMotions;
        private bool hasLatestPresentation;
        private SenaCharacterPresentation latestPresentation;

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

        private void Start()
        {
            StartCoroutine(EnableMotionPlaybackAfterFirstFrame());
        }

        public override void ApplyPresentation(SenaCharacterPresentation presentation)
        {
            latestPresentation = presentation;
            hasLatestPresentation = true;

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
            ApplyMotion(presentation, forceReplay: false);
        }

        private void ApplyMotion(SenaCharacterPresentation presentation, bool forceReplay)
        {
            string targetMotion = bindingProfile == null
                ? presentation.MotionKey
                : bindingProfile.ResolveMotion(presentation.MotionKey, presentation.MotionKey);

            if (string.IsNullOrEmpty(targetMotion) ||
                (!forceReplay && !replaySameMotion && NamesMatch(currentMotionName, targetMotion)))
            {
                return;
            }

            if (!canPlayMotions)
            {
                return;
            }

            if (motionController == null)
            {
                if (warnOnSkippedMotion)
                {
                    WarnOnce(
                        ref warnedMissingMotionController,
                        $"Live2D motion controller is not assigned. Motion '{targetMotion}' will be skipped.");
                }

                return;
            }

            if (motionClips == null || motionClips.Length == 0)
            {
                if (warnOnSkippedMotion)
                {
                    WarnOnce(
                        ref warnedEmptyMotionClips,
                        $"Live2D motion clips are not configured. Motion '{targetMotion}' will be skipped.");
                }

                return;
            }

            if (!TryFindMotionClip(targetMotion, out MotionClipBinding motionClip))
            {
                if (warnOnSkippedMotion)
                {
                    Debug.LogWarning(
                        $"Live2D motion was not found: {targetMotion}. " +
                        $"Available motions: {BuildAvailableMotionList()}",
                        this);
                }

                return;
            }

            if (motionClip.clip == null)
            {
                if (warnOnSkippedMotion)
                {
                    Debug.LogWarning(
                        $"Live2D motion clip is not assigned for motion: {targetMotion}.",
                        this);
                }

                return;
            }

            PrepareMotionPlayback();

            motionController.PlayAnimation(
                motionClip.clip,
                priority: ToCubismPriority(motionClip.priority),
                isLoop: motionClip.loop);
            currentMotionName = targetMotion;
        }

        private IEnumerator EnableMotionPlaybackAfterFirstFrame()
        {
            yield return null;

            canPlayMotions = true;

            if (hasLatestPresentation)
            {
                ApplyMotion(latestPresentation, forceReplay: true);
            }
        }

        private void PrepareMotionPlayback()
        {
            Animator animator = ResolveAnimator();
            if (animator == null)
            {
                WarnOnce(
                    ref warnedMissingAnimator,
                    "Live2D Animator is not found. CubismMotionController requires an Animator on the model root.");
                return;
            }

            if (animator.runtimeAnimatorController != null)
            {
                WarnOnce(
                    ref warnedAnimatorController,
                    "Live2D Animator has an AnimatorController assigned. CubismMotionController playback expects the Animator Controller field to be empty.");
            }

            if (!rebindAnimatorBeforeFirstMotion || animatorReboundForMotion)
            {
                return;
            }

            animator.Rebind();
            animator.Update(0f);
            animatorReboundForMotion = true;
        }

        private Animator ResolveAnimator()
        {
            if (motionController != null)
            {
                Animator animator = motionController.GetComponent<Animator>();
                if (animator != null)
                {
                    return animator;
                }
            }

            return GetComponentInChildren<Animator>(includeInactive: true);
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

        private string BuildAvailableMotionList()
        {
            if (motionClips == null || motionClips.Length == 0)
            {
                return "(none)";
            }

            StringBuilder builder = new StringBuilder();
            foreach (MotionClipBinding candidate in motionClips)
            {
                if (string.IsNullOrWhiteSpace(candidate.motionName))
                {
                    continue;
                }

                if (builder.Length > 0)
                {
                    builder.Append(", ");
                }

                builder.Append(candidate.motionName);
            }

            return builder.Length == 0 ? "(none)" : builder.ToString();
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
