using System.IO;
using TMPro;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TextCore.LowLevel;

namespace ProjectSENA.Editor
{
    public static class SetupKoreanTmpFonts
    {
        private const string FontFolderPath = "Assets/ProjectSENA/Fonts";
        private const string SourceFontFolderPath = FontFolderPath + "/Source";
        private const string FontAssetPath = FontFolderPath + "/ProjectSenaKoreanTMP.asset";
        private const string ImportedSourceFontPath = SourceFontFolderPath + "/MalgunGothic.ttf";
        private const string FontAssetName = "ProjectSenaKoreanTMP";
        private const int SamplingPointSize = 90;
        private const int AtlasPadding = 9;
        private const int AtlasWidth = 1024;
        private const int AtlasHeight = 1024;

        private const string InitialCharacters =
            "\uBA54\uC2DC\uC9C0\uB97C \uC785\uB825\uD574 \uC918 \uBCF4\uB0B4\uAE30 \uC5F0\uACB0\uB428 \uC5F0\uACB0 \uB04A\uAE40 \uC2B9\uC778 \uB300\uAE30 \uC911 \uC785\uB825\uC744 \uAE30\uB2E4\uB9AC\uACE0 \uC788\uC5B4 \uB098 \uC138\uB098 \uC548\uB0B4 \uBA54\uBAA8\uC7A5 \uC5F4\uC5B4\uC918 \uC571 \uC2E4\uD589\uC774 \uC644\uB8CC\uB410\uC5B4 \uC694\uCCAD\uD55C \uC791\uC5C5\uC744 \uC900\uBE44\uD588\uC5B4 \uC2E4\uD589 \uC804\uC5D0 \uD655\uC778\uC744 \uBC1B\uC744\uAC8C \uD5C8\uC6A9 \uAC70\uC808";

        [MenuItem("Project SENA/Setup Korean TMP Fonts")]
        public static void Run()
        {
            Font sourceFont = FindSourceFont();
            if (sourceFont == null)
            {
                EditorUtility.DisplayDialog(
                    "Project-SENA",
                    "\uD55C\uAE00\uC744 \uC9C0\uC6D0\uD558\uB294 \uD3F0\uD2B8 \uD30C\uC77C\uC744 \uCC3E\uC9C0 \uBABB\uD588\uC5B4. Windows Fonts \uD3F4\uB354\uC5D0 Malgun Gothic \uB610\uB294 Noto Sans KR \uACC4\uC5F4 \uD3F0\uD2B8\uAC00 \uC788\uB294\uC9C0 \uD655\uC778\uD574 \uC918.",
                    "\uD655\uC778");
                return;
            }

            TMP_FontAsset generatedAsset = TMP_FontAsset.CreateFontAsset(
                sourceFont,
                SamplingPointSize,
                AtlasPadding,
                GlyphRenderMode.SDFAA,
                AtlasWidth,
                AtlasHeight,
                AtlasPopulationMode.Dynamic,
                true);

            if (generatedAsset == null)
            {
                EditorUtility.DisplayDialog(
                    "Project-SENA",
                    "TMP \uD3F0\uD2B8 \uC5D0\uC14B\uC744 \uB9CC\uB4DC\uB294 \uB3C4\uC911 \uC2E4\uD328\uD588\uC5B4. \uD3F0\uD2B8 \uC18C\uC2A4\uAC00 \uC81C\uB300\uB85C \uC784\uD3EC\uD2B8\uB410\uB294\uC9C0 \uD655\uC778\uD574 \uC918.",
                    "\uD655\uC778");
                return;
            }

            EnsureFolder(FontFolderPath);

            TMP_FontAsset fontAsset = AssetDatabase.LoadAssetAtPath<TMP_FontAsset>(FontAssetPath);
            if (fontAsset == null)
            {
                generatedAsset.name = FontAssetName;
                AssetDatabase.CreateAsset(generatedAsset, FontAssetPath);
                fontAsset = generatedAsset;
            }
            else
            {
                RemoveSubAssets(FontAssetPath, fontAsset);
                EditorUtility.CopySerialized(generatedAsset, fontAsset);
                fontAsset.name = FontAssetName;
            }

            EnsureSubAssets(fontAsset);
            SaveAndReloadFontAsset();
            fontAsset = AssetDatabase.LoadAssetAtPath<TMP_FontAsset>(FontAssetPath);
            if (fontAsset == null)
            {
                EditorUtility.DisplayDialog(
                    "Project-SENA",
                    "TMP 폰트 에셋을 다시 불러오지 못했어. 에셋이 정상적으로 저장됐는지 확인해 줘.",
                    "확인");
                return;
            }

            ConfigureFontAsset(fontAsset);
            SaveAndReloadFontAsset();
            fontAsset = AssetDatabase.LoadAssetAtPath<TMP_FontAsset>(FontAssetPath);
            if (fontAsset == null || fontAsset.material == null || fontAsset.atlasTextures == null || fontAsset.atlasTextures.Length == 0 || fontAsset.atlasTextures[0] == null)
            {
                EditorUtility.DisplayDialog(
                    "Project-SENA",
                    "TMP 폰트의 atlas 또는 material이 아직 비어 있어. 현재 폰트 에셋 생성이 완전히 끝나지 않았어.",
                    "확인");
                return;
            }

            ApplyFontToActiveScene(fontAsset);

            TMP_Settings settings = GetTmpSettingsAsset();
            if (settings != null)
            {
                TMP_Settings.defaultFontAsset = fontAsset;
                EditorUtility.SetDirty(settings);
            }

            EditorUtility.SetDirty(fontAsset);
            SaveAndReloadFontAsset();

            EditorUtility.DisplayDialog(
                "Project-SENA",
                "\uD55C\uAE00 TMP \uD3F0\uD2B8\uB97C \uC0C8\uB85C \uC815\uB9AC\uD588\uC5B4. \uC52C\uC744 \uC800\uC7A5\uD55C \uB4A4 Placeholder\uC640 Text\uAC00 \uC815\uC0C1 \uD45C\uC2DC\uB418\uB294\uC9C0 \uD655\uC778\uD574 \uC918.",
                "\uD655\uC778");
        }

        private static void ConfigureFontAsset(TMP_FontAsset fontAsset)
        {
            fontAsset.atlasPopulationMode = AtlasPopulationMode.Dynamic;
            fontAsset.isMultiAtlasTexturesEnabled = true;
            fontAsset.TryAddCharacters(InitialCharacters, out _);
            fontAsset.ReadFontAssetDefinition();

            if (fontAsset.material != null)
            {
                fontAsset.material.hideFlags = HideFlags.None;
                fontAsset.material.name = FontAssetName + " Material";
                EditorUtility.SetDirty(fontAsset.material);
            }

            if (fontAsset.atlasTextures != null)
            {
                for (int i = 0; i < fontAsset.atlasTextures.Length; i++)
                {
                    Texture2D atlas = fontAsset.atlasTextures[i];
                    if (atlas == null)
                    {
                        continue;
                    }

                    atlas.hideFlags = HideFlags.None;
                    atlas.name = i == 0 ? FontAssetName + " Atlas" : FontAssetName + " Atlas " + i;
                    EditorUtility.SetDirty(atlas);
                }
            }
        }

        private static void EnsureSubAssets(TMP_FontAsset fontAsset)
        {
            if (fontAsset.atlasTextures != null)
            {
                foreach (Texture2D atlasTexture in fontAsset.atlasTextures)
                {
                    if (atlasTexture == null)
                    {
                        continue;
                    }

                    AssetDatabase.AddObjectToAsset(atlasTexture, fontAsset);
                }
            }

            if (fontAsset.material != null)
            {
                AssetDatabase.AddObjectToAsset(fontAsset.material, fontAsset);
            }
        }

        private static void SaveAndReloadFontAsset()
        {
            AssetDatabase.SaveAssets();
            AssetDatabase.ImportAsset(FontAssetPath, ImportAssetOptions.ForceUpdate);
            AssetDatabase.Refresh();
        }

        private static void RemoveSubAssets(string assetPath, TMP_FontAsset mainAsset)
        {
            Object[] assets = AssetDatabase.LoadAllAssetsAtPath(assetPath);
            foreach (Object asset in assets)
            {
                if (asset == null || asset == mainAsset)
                {
                    continue;
                }

                Object.DestroyImmediate(asset, true);
            }
        }

        private static Font FindSourceFont()
        {
            EnsureFolder(SourceFontFolderPath);
            EnsureImportedFontExists();
            EnsureIncludeFontData(ImportedSourceFontPath);
            return AssetDatabase.LoadAssetAtPath<Font>(ImportedSourceFontPath);
        }

        private static void EnsureImportedFontExists()
        {
            if (File.Exists(ImportedSourceFontPath))
            {
                return;
            }

            string windowsFontDirectory = Path.Combine(
                System.Environment.GetFolderPath(System.Environment.SpecialFolder.Windows),
                "Fonts");

            string[] candidateFiles =
            {
                Path.Combine(windowsFontDirectory, "malgun.ttf"),
                Path.Combine(windowsFontDirectory, "malgunbd.ttf"),
                Path.Combine(windowsFontDirectory, "malgunsl.ttf")
            };

            foreach (string sourceFilePath in candidateFiles)
            {
                if (!File.Exists(sourceFilePath))
                {
                    continue;
                }

                File.Copy(sourceFilePath, ImportedSourceFontPath, true);
                AssetDatabase.ImportAsset(ImportedSourceFontPath, ImportAssetOptions.ForceSynchronousImport);
                return;
            }
        }

        private static void EnsureIncludeFontData(string assetPath)
        {
            if (AssetImporter.GetAtPath(assetPath) is not TrueTypeFontImporter fontImporter)
            {
                return;
            }

            if (fontImporter.includeFontData)
            {
                return;
            }

            fontImporter.includeFontData = true;
            fontImporter.SaveAndReimport();
        }

        private static void ApplyFontToActiveScene(TMP_FontAsset fontAsset)
        {
            Scene scene = SceneManager.GetActiveScene();
            if (!scene.IsValid() || !scene.isLoaded)
            {
                return;
            }

            foreach (GameObject root in scene.GetRootGameObjects())
            {
                TMP_Text[] texts = root.GetComponentsInChildren<TMP_Text>(true);
                foreach (TMP_Text text in texts)
                {
                    text.font = fontAsset;
                    EditorUtility.SetDirty(text);
                }

                TMP_InputField[] inputs = root.GetComponentsInChildren<TMP_InputField>(true);
                foreach (TMP_InputField input in inputs)
                {
                    if (input.textComponent != null)
                    {
                        input.textComponent.font = fontAsset;
                        EditorUtility.SetDirty(input.textComponent);
                    }

                    if (input.placeholder is TMP_Text placeholder)
                    {
                        placeholder.font = fontAsset;
                        EditorUtility.SetDirty(placeholder);
                    }

                    EditorUtility.SetDirty(input);
                }
            }

            EditorSceneManager.MarkSceneDirty(scene);
        }

        private static TMP_Settings GetTmpSettingsAsset()
        {
            if (TMP_Settings.instance != null)
            {
                return TMP_Settings.instance;
            }

            string[] guids = AssetDatabase.FindAssets("t:TMP_Settings");
            foreach (string guid in guids)
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                TMP_Settings settings = AssetDatabase.LoadAssetAtPath<TMP_Settings>(path);
                if (settings != null)
                {
                    return settings;
                }
            }

            return null;
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
