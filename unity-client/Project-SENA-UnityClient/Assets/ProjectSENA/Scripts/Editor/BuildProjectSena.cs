using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;

namespace ProjectSENA.Editor
{
    public static class BuildProjectSena
    {
        private const string WindowsBuildPath = "Builds/Windows/Project-SENA.exe";

        [MenuItem("Project SENA/Build Windows Player")]
        public static void BuildWindowsPlayer()
        {
            BuildPlayerOptions options = new()
            {
                scenes = GetEnabledScenes(),
                locationPathName = WindowsBuildPath,
                target = BuildTarget.StandaloneWindows64,
                options = BuildOptions.None
            };

            Directory.CreateDirectory(Path.GetDirectoryName(WindowsBuildPath));
            BuildReport report = BuildPipeline.BuildPlayer(options);

            if (report.summary.result != BuildResult.Succeeded)
            {
                throw new BuildFailedException($"Project-SENA Windows build failed: {report.summary.result}");
            }
        }

        private static string[] GetEnabledScenes()
        {
            string[] scenes = EditorBuildSettings.scenes
                .Where(scene => scene.enabled)
                .Select(scene => scene.path)
                .ToArray();

            if (scenes.Length == 0)
            {
                throw new BuildFailedException("No enabled scenes are configured in Editor Build Settings.");
            }

            return scenes;
        }
    }
}
