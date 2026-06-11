using System;
using ProjectSENA.Protocol;
using UnityEngine;
using UnityEngine.UI;

namespace ProjectSENA.UI
{
    public sealed class ApprovalPanelController : MonoBehaviour
    {
        private const string TestFailureAppName = "__project_sena_missing_app__";
        private const int MaxTextPreviewLength = 80;

        [SerializeField] private GameObject root;
        [SerializeField] private Text summaryText;
        [SerializeField] private Text promptText;
        [SerializeField] private Button allowButton;
        [SerializeField] private Button denyButton;
        [SerializeField] private Text allowButtonText;
        [SerializeField] private Text denyButtonText;

        private Action<bool> _onDecision;

        private void Awake()
        {
            if (root == null)
            {
                root = gameObject;
            }

            if (allowButtonText == null && allowButton != null)
            {
                allowButtonText = allowButton.GetComponentInChildren<Text>();
            }

            if (denyButtonText == null && denyButton != null)
            {
                denyButtonText = denyButton.GetComponentInChildren<Text>();
            }

            if (allowButton != null)
            {
                allowButton.onClick.AddListener(() => Decide(true));
            }

            if (denyButton != null)
            {
                denyButton.onClick.AddListener(() => Decide(false));
            }

            if (allowButtonText != null)
            {
                allowButtonText.text = "허용";
            }

            if (denyButtonText != null)
            {
                denyButtonText.text = "거절";
            }
        }

        public void Show(ApprovalRequestPayload payload, Action<bool> onDecision)
        {
            _onDecision = onDecision;

            if (summaryText != null)
            {
                summaryText.text = BuildSummaryText(payload);
            }

            if (promptText != null)
            {
                promptText.text = BuildPromptText(payload);
            }

            if (root != null)
            {
                root.SetActive(true);
            }
        }

        public void Hide()
        {
            _onDecision = null;
            if (root != null)
            {
                root.SetActive(false);
            }
        }

        private void Decide(bool approved)
        {
            Action<bool> callback = _onDecision;
            Hide();
            callback?.Invoke(approved);
        }

        private static string BuildSummaryText(ApprovalRequestPayload payload)
        {
            string toolLabel = payload.tool_name switch
            {
                "open_app" => "앱 실행 요청",
                "get_active_window" => "현재 창 조회 요청",
                "capture_screen" => "화면 캡처 요청",
                "type_text" => "텍스트 입력 요청",
                _ => payload.tool_name
            };

            string riskLabel = payload.risk_level switch
            {
                "low" => "낮음",
                "medium" => "보통",
                "high" => "높음",
                "critical" => "매우 높음",
                _ => payload.risk_level
            };

            return $"{toolLabel} · 위험도 {riskLabel}";
        }

        private static string BuildPromptText(ApprovalRequestPayload payload)
        {
            string actionText = payload.tool_name switch
            {
                "open_app" => BuildOpenAppPrompt(payload),
                "get_active_window" => "현재 활성 창 정보를 확인할게.",
                "capture_screen" => BuildCaptureScreenPrompt(payload),
                "type_text" => BuildTypeTextPrompt(payload),
                _ => payload.prompt
            };

            return $"{actionText}\n\n요청 이유: {BuildReasonText(payload.reason)}";
        }

        private static string BuildOpenAppPrompt(ApprovalRequestPayload payload)
        {
            if (payload.arguments != null &&
                payload.arguments.TryGetValue("app_name", out object value) &&
                value != null)
            {
                string appName = value.ToString();
                if (string.Equals(appName, "notepad", StringComparison.OrdinalIgnoreCase))
                {
                    return "메모장을 실행할까?";
                }

                if (string.Equals(appName, TestFailureAppName, StringComparison.OrdinalIgnoreCase))
                {
                    return "테스트용 앱 실행 실패를 확인할까?";
                }

                return $"{appName} 앱을 실행할까?";
            }

            return "앱을 실행할까?";
        }

        private static string BuildCaptureScreenPrompt(ApprovalRequestPayload payload)
        {
            string captureMode = GetArgumentString(payload, "capture_mode");
            string title = GetArgumentString(payload, "expected_window_title");
            string processName = GetArgumentString(payload, "expected_process_name");
            string modeLabel = captureMode switch
            {
                "active_window" => "현재 활성 창",
                "target_window" => "대상 창",
                "all_screens" => "전체 화면",
                "full_screen" => "전체 화면",
                _ => "화면"
            };

            string target = string.Empty;
            if (!string.IsNullOrEmpty(title))
            {
                target = title;
                if (!string.IsNullOrEmpty(processName))
                {
                    target = $"{title} ({processName})";
                }
            }

            if (string.IsNullOrEmpty(target))
            {
                return $"{modeLabel}을 PNG 파일로 저장할까?";
            }

            return $"{modeLabel}을 PNG 파일로 저장할까?"
                + $"\n\n대상 창: {target}";
        }

        private static string BuildTypeTextPrompt(ApprovalRequestPayload payload)
        {
            string text = GetArgumentString(payload, "text");
            string title = GetArgumentString(payload, "expected_window_title");
            string processName = GetArgumentString(payload, "expected_process_name");

            string target = string.IsNullOrEmpty(title) ? "현재 활성 창" : title;
            if (!string.IsNullOrEmpty(title) && !string.IsNullOrEmpty(processName))
            {
                target = $"{title} ({processName})";
            }

            string preview = TrimTextPreview(text);
            string actionText = string.IsNullOrEmpty(title)
                ? "현재 창에 다음 텍스트를 입력할까?"
                : "대상 창에 다음 텍스트를 입력할까?";
            return actionText
                + $"\n\n대상 창: {target}"
                + $"\n입력 내용: {preview}"
                + "\n\n입력 중에는 다른 창으로 포커스를 옮기지 말아줘.";
        }

        private static string GetArgumentString(ApprovalRequestPayload payload, string key)
        {
            if (payload.arguments == null ||
                !payload.arguments.TryGetValue(key, out object value) ||
                value == null)
            {
                return string.Empty;
            }

            return value.ToString();
        }

        private static string TrimTextPreview(string text)
        {
            if (string.IsNullOrEmpty(text))
            {
                return "(비어 있음)";
            }

            string normalized = text.Replace("\r\n", "\n").Replace("\r", "\n");
            if (normalized.Length <= MaxTextPreviewLength)
            {
                return normalized;
            }

            return normalized.Substring(0, MaxTextPreviewLength) + "...";
        }

        private static string BuildReasonText(string reason)
        {
            return reason switch
            {
                "The user asked to open a plain text editor." => "텍스트 편집기를 열어 달라는 요청을 받았어.",
                "The user asked for current active window context." => "현재 사용 중인 창 정보를 확인해 달라는 요청을 받았어.",
                "The user asked to type text into the active foreground window." => "현재 활성 창에 텍스트를 입력해 달라는 요청을 받았어.",
                "Project-SENA failure injection test requested." => "실패 복구 UX를 확인하기 위한 테스트 요청이야.",
                _ => reason
            };
        }
    }
}
