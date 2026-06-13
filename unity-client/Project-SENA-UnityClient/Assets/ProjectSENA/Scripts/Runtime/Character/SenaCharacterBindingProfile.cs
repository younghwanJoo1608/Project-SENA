using System;
using UnityEngine;

namespace ProjectSENA.Character
{
    [CreateAssetMenu(
        fileName = "SenaCharacterBindingProfile",
        menuName = "Project SENA/Character Binding Profile")]
    public sealed class SenaCharacterBindingProfile : ScriptableObject
    {
        [SerializeField] private ExpressionBinding[] expressionBindings = Array.Empty<ExpressionBinding>();
        [SerializeField] private MotionBinding[] motionBindings = Array.Empty<MotionBinding>();

        public void SetBindings(ExpressionBinding[] expressions, MotionBinding[] motions)
        {
            expressionBindings = expressions ?? Array.Empty<ExpressionBinding>();
            motionBindings = motions ?? Array.Empty<MotionBinding>();
        }

        public string ResolveExpression(string expressionKey)
        {
            return ResolveExpression(expressionKey, expressionKey);
        }

        public string ResolveExpression(string expressionKey, string fallback)
        {
            if (string.IsNullOrEmpty(expressionKey))
            {
                return fallback;
            }

            foreach (ExpressionBinding binding in expressionBindings)
            {
                if (string.Equals(binding.expressionKey, expressionKey, StringComparison.Ordinal))
                {
                    return string.IsNullOrEmpty(binding.targetExpressionName)
                        ? fallback
                        : binding.targetExpressionName;
                }
            }

            return fallback;
        }

        public string ResolveMotion(string motionKey)
        {
            return ResolveMotion(motionKey, motionKey);
        }

        public string ResolveMotion(string motionKey, string fallback)
        {
            if (string.IsNullOrEmpty(motionKey))
            {
                return fallback;
            }

            foreach (MotionBinding binding in motionBindings)
            {
                if (string.Equals(binding.motionKey, motionKey, StringComparison.Ordinal))
                {
                    return string.IsNullOrEmpty(binding.targetMotionGroup)
                        ? fallback
                        : binding.targetMotionGroup;
                }
            }

            return fallback;
        }

        [Serializable]
        public struct ExpressionBinding
        {
            public string expressionKey;
            public string targetExpressionName;
        }

        [Serializable]
        public struct MotionBinding
        {
            public string motionKey;
            public string targetMotionGroup;
        }
    }
}
