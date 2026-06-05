using System;
using ProjectSENA.Protocol;
using UnityEngine;
using UnityEngine.UI;

namespace ProjectSENA.UI
{
    public sealed class ApprovalPanelController : MonoBehaviour
    {
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
                "capture_screen" => "화면을 캡처할게.",
                "type_text" => "지정한 텍스트를 입력할게.",
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

                return $"{appName} 앱을 실행할까?";
            }

            return "앱을 실행할까?";
        }

        private static string BuildReasonText(string reason)
        {
            return reason switch
            {
                "The user asked to open a plain text editor." => "텍스트 편집기를 열어 달라는 요청을 받았어.",
                "The user asked for current active window context." => "현재 사용 중인 창 정보를 확인해 달라는 요청을 받았어.",
                _ => reason
            };
        }
    }
}
