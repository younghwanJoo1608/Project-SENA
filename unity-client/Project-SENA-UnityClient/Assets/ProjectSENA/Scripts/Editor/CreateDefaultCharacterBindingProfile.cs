using ProjectSENA.Character;
using UnityEditor;
using UnityEngine;

namespace ProjectSENA.Editor
{
    public static class CreateDefaultCharacterBindingProfile
    {
        private const string CharacterFolderPath = "Assets/ProjectSENA/Characters";
        private const string AssetPath = CharacterFolderPath + "/SenaDefaultCharacterBindingProfile.asset";

        [MenuItem("Project SENA/Create Default Character Binding Profile")]
        public static void Run()
        {
            EnsureFolder(CharacterFolderPath);

            SenaCharacterBindingProfile profile =
                AssetDatabase.LoadAssetAtPath<SenaCharacterBindingProfile>(AssetPath);

            if (profile == null)
            {
                profile = ScriptableObject.CreateInstance<SenaCharacterBindingProfile>();
                AssetDatabase.CreateAsset(profile, AssetPath);
            }
            else if (!EditorUtility.DisplayDialog(
                         "Overwrite character binding profile?",
                         "SenaDefaultCharacterBindingProfile already exists. Overwrite its expression and motion bindings with the generic SENA defaults?",
                         "Overwrite",
                         "Cancel"))
            {
                Selection.activeObject = profile;
                EditorGUIUtility.PingObject(profile);
                return;
            }

            profile.SetBindings(CreateExpressionBindings(), CreateMotionBindings());
            EditorUtility.SetDirty(profile);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();

            Selection.activeObject = profile;
            EditorGUIUtility.PingObject(profile);
        }

        private static SenaCharacterBindingProfile.ExpressionBinding[] CreateExpressionBindings()
        {
            return new[]
            {
                Expression(SenaExpressionKeys.Neutral, SenaExpressionKeys.Neutral),
                Expression(SenaExpressionKeys.Focused, SenaExpressionKeys.Focused),
                Expression(SenaExpressionKeys.Thinking, SenaExpressionKeys.Thinking),
                Expression(SenaExpressionKeys.AwaitingApproval, SenaExpressionKeys.AwaitingApproval),
                Expression(SenaExpressionKeys.Speaking, SenaExpressionKeys.Speaking),
                Expression(SenaExpressionKeys.Satisfied, SenaExpressionKeys.Satisfied),
                Expression(SenaExpressionKeys.Concerned, SenaExpressionKeys.Concerned),
                Expression(SenaExpressionKeys.Disconnected, SenaExpressionKeys.Disconnected),
                Expression(SenaExpressionKeys.Error, SenaExpressionKeys.Error)
            };
        }

        private static SenaCharacterBindingProfile.MotionBinding[] CreateMotionBindings()
        {
            return new[]
            {
                Motion(SenaMotionKeys.Idle, SenaMotionKeys.Idle),
                Motion(SenaMotionKeys.Listening, SenaMotionKeys.Listening),
                Motion(SenaMotionKeys.Thinking, SenaMotionKeys.Thinking),
                Motion(SenaMotionKeys.AwaitingApproval, SenaMotionKeys.AwaitingApproval),
                Motion(SenaMotionKeys.ToolRunning, SenaMotionKeys.ToolRunning),
                Motion(SenaMotionKeys.Speaking, SenaMotionKeys.Speaking),
                Motion(SenaMotionKeys.Positive, SenaMotionKeys.Positive),
                Motion(SenaMotionKeys.Concerned, SenaMotionKeys.Concerned),
                Motion(SenaMotionKeys.Error, SenaMotionKeys.Error)
            };
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

        private static void EnsureFolder(string assetPath)
        {
            if (AssetDatabase.IsValidFolder(assetPath))
            {
                return;
            }

            string[] parts = assetPath.Split('/');
            string current = parts[0];

            for (int i = 1; i < parts.Length; i++)
            {
                string next = current + "/" + parts[i];
                if (!AssetDatabase.IsValidFolder(next))
                {
                    AssetDatabase.CreateFolder(current, parts[i]);
                }

                current = next;
            }
        }
    }
}
