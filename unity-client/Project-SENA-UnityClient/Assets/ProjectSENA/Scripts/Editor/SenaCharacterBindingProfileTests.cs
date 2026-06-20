using NUnit.Framework;
using ProjectSENA.Character;
using UnityEngine;

namespace ProjectSENA.Editor.Tests
{
    public sealed class SenaCharacterBindingProfileTests
    {
        [Test]
        public void ResolveExpression_UsesConfiguredTarget()
        {
            SenaCharacterBindingProfile profile = CreateProfile(
                expressions: new[]
                {
                    Expression(SenaExpressionKeys.AwaitingApproval, "xx")
                },
                motions: null);

            Assert.That(
                profile.ResolveExpression(SenaExpressionKeys.AwaitingApproval),
                Is.EqualTo("xx"));
        }

        [Test]
        public void ResolveMotion_UsesConfiguredTarget()
        {
            SenaCharacterBindingProfile profile = CreateProfile(
                expressions: null,
                motions: new[]
                {
                    Motion(SenaMotionKeys.Thinking, "idle")
                });

            Assert.That(
                profile.ResolveMotion(SenaMotionKeys.Thinking),
                Is.EqualTo("idle"));
        }

        [Test]
        public void ResolveExpression_FallsBackToInputKeyWhenMissingOrEmpty()
        {
            SenaCharacterBindingProfile profile = CreateProfile(
                expressions: new[]
                {
                    Expression(SenaExpressionKeys.Error, string.Empty)
                },
                motions: null);

            Assert.That(
                profile.ResolveExpression(SenaExpressionKeys.Thinking),
                Is.EqualTo(SenaExpressionKeys.Thinking));
            Assert.That(
                profile.ResolveExpression(SenaExpressionKeys.Error),
                Is.EqualTo(SenaExpressionKeys.Error));
        }

        [Test]
        public void ResolveMotion_FallsBackToInputKeyWhenMissingOrEmpty()
        {
            SenaCharacterBindingProfile profile = CreateProfile(
                expressions: null,
                motions: new[]
                {
                    Motion(SenaMotionKeys.Error, string.Empty)
                });

            Assert.That(
                profile.ResolveMotion(SenaMotionKeys.Speaking),
                Is.EqualTo(SenaMotionKeys.Speaking));
            Assert.That(
                profile.ResolveMotion(SenaMotionKeys.Error),
                Is.EqualTo(SenaMotionKeys.Error));
        }

        private static SenaCharacterBindingProfile CreateProfile(
            SenaCharacterBindingProfile.ExpressionBinding[] expressions,
            SenaCharacterBindingProfile.MotionBinding[] motions)
        {
            SenaCharacterBindingProfile profile =
                ScriptableObject.CreateInstance<SenaCharacterBindingProfile>();
            profile.SetBindings(expressions, motions);
            return profile;
        }

        private static SenaCharacterBindingProfile.ExpressionBinding Expression(
            string expressionKey,
            string targetExpressionName)
        {
            return new SenaCharacterBindingProfile.ExpressionBinding
            {
                expressionKey = expressionKey,
                targetExpressionName = targetExpressionName
            };
        }

        private static SenaCharacterBindingProfile.MotionBinding Motion(
            string motionKey,
            string targetMotionGroup)
        {
            return new SenaCharacterBindingProfile.MotionBinding
            {
                motionKey = motionKey,
                targetMotionGroup = targetMotionGroup
            };
        }
    }
}
