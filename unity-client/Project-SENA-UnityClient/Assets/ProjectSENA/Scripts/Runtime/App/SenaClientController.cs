using System.Collections;
using ProjectSENA.Networking;
using ProjectSENA.Protocol;
using ProjectSENA.UI;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem;
using UnityEngine.UI;

namespace ProjectSENA.App
{
    public sealed class SenaClientController : MonoBehaviour
    {
        [Header("Server")]
        [SerializeField] private string inferenceServerBaseUrl = "http://127.0.0.1:8000";
        [SerializeField] private string languageCode = "ko";

        [Header("Chat UI")]
        [SerializeField] private TMP_InputField tmpInputField;
        [SerializeField] private Button sendButton;
        [SerializeField] private Text sendButtonText;
        [SerializeField] private TMP_Text sendButtonTmpText;
        [SerializeField] private TMP_Text inputPlaceholderTmpText;
        [SerializeField] private RectTransform composerPanelRect;
        [SerializeField] private Text connectionStatusText;
        [SerializeField] private Text assistantStateText;
        [SerializeField] private ChatPanelController chatPanel;
        [SerializeField] private ApprovalPanelController approvalPanel;
        [SerializeField] private RectTransform approvalPanelRect;

        [Header("Input Composer")]
        [SerializeField] private float minInputFieldHeight = 56f;
        [SerializeField] private float maxInputFieldHeight = 160f;
        [SerializeField] private float inputFieldVerticalPadding = 20f;

        [Header("Responsive Layout")]
        [SerializeField] private float approvalPanelWidthRatio = 0.36f;
        [SerializeField] private float approvalPanelMinWidth = 520f;
        [SerializeField] private float approvalPanelMaxWidth = 760f;
        [SerializeField] private float approvalPanelHeightRatio = 0.5f;
        [SerializeField] private float approvalPanelMinHeight = 260f;
        [SerializeField] private float approvalPanelMaxHeight = 340f;

        private SenaApiClient _apiClient;
        private RectTransform _inputFieldRect;
        private RectTransform _rootCanvasRect;
        private string _sessionId;
        private bool _requestInFlight;
        private bool _approvalPending;
        private bool _reactivateInputNextFrame;
        private bool _inputHeightRefreshPending;
        private bool _submitDeferredUntilCompositionEnds;
        private bool _submitFromEnterPending;
        private float _composerExtraHeight;
        private Vector2 _lastCanvasSize;

        private void Awake()
        {
            _sessionId = $"unity-session-{System.Guid.NewGuid():N}";
            _apiClient = new SenaApiClient(inferenceServerBaseUrl);

            if (sendButton != null)
            {
                sendButton.onClick.AddListener(SendCurrentInput);
            }

            if (sendButtonText == null && sendButton != null)
            {
                sendButtonText = sendButton.GetComponentInChildren<Text>();
            }

            if (sendButtonTmpText == null && sendButton != null)
            {
                sendButtonTmpText = sendButton.GetComponentInChildren<TMP_Text>();
            }

            if (tmpInputField != null)
            {
                _inputFieldRect = tmpInputField.GetComponent<RectTransform>();

                if (inputPlaceholderTmpText == null)
                {
                    inputPlaceholderTmpText = tmpInputField.placeholder as TMP_Text;
                }

                ConfigureTmpInputField();
                tmpInputField.onValueChanged.AddListener(HandleInputFieldValueChanged);
            }

            if (composerPanelRect == null && tmpInputField != null)
            {
                composerPanelRect = tmpInputField.transform.parent as RectTransform;
            }

            if (approvalPanelRect == null && approvalPanel != null)
            {
                approvalPanelRect = approvalPanel.transform as RectTransform;
            }

            RectTransform rootCanvasRect = approvalPanelRect != null ? approvalPanelRect.parent as RectTransform : null;
            if (rootCanvasRect != null)
            {
                _rootCanvasRect = rootCanvasRect;
            }

            if (composerPanelRect != null && _inputFieldRect != null)
            {
                _composerExtraHeight = composerPanelRect.sizeDelta.y - _inputFieldRect.sizeDelta.y;
            }

            ApplyResponsiveLayout(force: true);
            ApplyStaticUiText();
            UpdateInputFieldHeight();
            UpdateConnectionStatus(true);
            UpdateAssistantState("idle", "Waiting for input.");
            UpdateSendInteractivity();
        }

        private void OnDestroy()
        {
            if (sendButton != null)
            {
                sendButton.onClick.RemoveListener(SendCurrentInput);
            }

            if (tmpInputField != null)
            {
                tmpInputField.onValueChanged.RemoveListener(HandleInputFieldValueChanged);
            }
        }

        private void Update()
        {
            ApplyResponsiveLayout();
            HandleDeferredTmpSubmit();
            HandleKeyboardSubmitForTmpInput();

            if (_reactivateInputNextFrame)
            {
                ActivateCurrentInputField();
                _reactivateInputNextFrame = false;
            }
        }

        private void HandleDeferredTmpSubmit()
        {
            if (!_submitDeferredUntilCompositionEnds || IsImeCompositionActive())
            {
                return;
            }

            StartCoroutine(SubmitTmpInputAtEndOfFrame());
        }

        private void HandleKeyboardSubmitForTmpInput()
        {
            if (tmpInputField == null || !tmpInputField.isFocused || _requestInFlight || _approvalPending)
            {
                return;
            }

            if (_submitFromEnterPending || _submitDeferredUntilCompositionEnds)
            {
                return;
            }

            Keyboard keyboard = Keyboard.current;
            if (keyboard == null)
            {
                return;
            }

            bool enterPressed = keyboard.enterKey.wasPressedThisFrame || keyboard.numpadEnterKey.wasPressedThisFrame;
            if (!enterPressed)
            {
                return;
            }

            bool shiftPressed = keyboard.leftShiftKey.isPressed || keyboard.rightShiftKey.isPressed;
            if (shiftPressed)
            {
                QueueInputFieldHeightRefresh();
                return;
            }

            if (IsImeCompositionActive())
            {
                _submitDeferredUntilCompositionEnds = true;
                return;
            }

            StartCoroutine(SubmitTmpInputAtEndOfFrame());
        }

        private void ApplyResponsiveLayout(bool force = false)
        {
            if (_rootCanvasRect == null)
            {
                return;
            }

            Vector2 canvasSize = _rootCanvasRect.rect.size;
            if (canvasSize.x <= 0f || canvasSize.y <= 0f)
            {
                return;
            }

            if (!force && (canvasSize - _lastCanvasSize).sqrMagnitude < 0.01f)
            {
                return;
            }

            _lastCanvasSize = canvasSize;

            if (approvalPanelRect != null)
            {
                float approvalWidth = Mathf.Clamp(canvasSize.x * approvalPanelWidthRatio, approvalPanelMinWidth, approvalPanelMaxWidth);
                float approvalHeight = Mathf.Clamp(approvalWidth * approvalPanelHeightRatio, approvalPanelMinHeight, approvalPanelMaxHeight);
                approvalPanelRect.sizeDelta = new Vector2(approvalWidth, approvalHeight);
            }
        }

        public void SendCurrentInput()
        {
            if (_requestInFlight || _approvalPending || tmpInputField == null)
            {
                return;
            }

            if (tmpInputField.isFocused)
            {
                if (IsImeCompositionActive())
                {
                    _submitDeferredUntilCompositionEnds = true;
                }
                else
                {
                    StartCoroutine(SubmitTmpInputAtEndOfFrame());
                }

                return;
            }

            SubmitText(NormalizeSubmittedText(tmpInputField.text));
        }

        private void HandleInputFieldValueChanged(string _)
        {
            QueueInputFieldHeightRefresh();
        }

        private void QueueInputFieldHeightRefresh()
        {
            UpdateInputFieldHeight();

            if (_inputHeightRefreshPending)
            {
                return;
            }

            StartCoroutine(RefreshInputFieldHeightAtEndOfFrame());
        }

        private IEnumerator SubmitTmpInputAtEndOfFrame()
        {
            if (_submitFromEnterPending)
            {
                yield break;
            }

            _submitFromEnterPending = true;
            _submitDeferredUntilCompositionEnds = false;
            yield return new WaitForEndOfFrame();
            _submitFromEnterPending = false;

            if (tmpInputField == null)
            {
                yield break;
            }

            string normalized = NormalizeSubmittedText(tmpInputField.text);
            if (string.IsNullOrEmpty(normalized))
            {
                ClearCurrentInputText();
                UpdateInputFieldHeight();
                _reactivateInputNextFrame = true;
                yield break;
            }

            SubmitText(normalized);
        }

        private IEnumerator RefreshInputFieldHeightAtEndOfFrame()
        {
            _inputHeightRefreshPending = true;
            yield return new WaitForEndOfFrame();
            UpdateInputFieldHeight();
            _inputHeightRefreshPending = false;
        }

        private void SubmitText(string text)
        {
            if (string.IsNullOrEmpty(text) || tmpInputField == null)
            {
                return;
            }

            ClearCurrentInputText();
            UpdateInputFieldHeight();

            chatPanel?.AppendUserMessage(text);
            _reactivateInputNextFrame = true;

            SenaEnvelope request = SenaRequestFactory.CreateUserText(_sessionId, text, languageCode);
            StartCoroutine(PostEnvelope(request));
        }

        private IEnumerator PostEnvelope(SenaEnvelope envelope)
        {
            _requestInFlight = true;
            UpdateConnectionStatus(true, "\uC785\uB825\uC744 \uBCF4\uB0B4\uACE0 \uC788\uC5B4.");
            UpdateSendInteractivity();

            yield return _apiClient.PostMessage(
                envelope,
                HandleBatchResponse,
                HandleTransportError);

            _requestInFlight = false;
            UpdateSendInteractivity();
        }

        private void HandleBatchResponse(SenaBatchResponse batch)
        {
            UpdateConnectionStatus(true);
            if (batch == null || batch.messages == null)
            {
                return;
            }

            foreach (SenaEnvelope message in batch.messages)
            {
                switch (message.type)
                {
                    case "assistant_text":
                    {
                        AssistantTextPayload payload = message.ToPayload<AssistantTextPayload>();
                        chatPanel?.AppendAssistantMessage(payload.display_text);
                        break;
                    }
                    case "assistant_state":
                    {
                        AssistantStatePayload payload = message.ToPayload<AssistantStatePayload>();
                        UpdateAssistantState(payload.state, payload.detail);
                        break;
                    }
                    case "approval_request":
                    {
                        ApprovalRequestPayload payload = message.ToPayload<ApprovalRequestPayload>();
                        _approvalPending = true;
                        UpdateSendInteractivity();
                        approvalPanel?.Show(payload, approved => OnApprovalDecision(approved));
                        break;
                    }
                    case "tool_result":
                    {
                        ToolResultPayload payload = message.ToPayload<ToolResultPayload>();
                        chatPanel?.AppendSystemMessage(FormatToolResult(payload));
                        _approvalPending = false;
                        UpdateSendInteractivity();
                        break;
                    }
                    case "error":
                    {
                        ErrorPayload payload = message.ToPayload<ErrorPayload>();
                        chatPanel?.AppendSystemMessage($"\uC624\uB958: {payload.message}");
                        UpdateAssistantState("error", payload.message);
                        _approvalPending = false;
                        UpdateSendInteractivity();
                        break;
                    }
                }
            }
        }

        private void HandleTransportError(string error)
        {
            UpdateConnectionStatus(false);
            chatPanel?.AppendSystemMessage($"\uD1B5\uC2E0 \uC624\uB958: {error}");
            UpdateAssistantState("disconnected", error);
            _approvalPending = false;
            _requestInFlight = false;
            UpdateSendInteractivity();
        }

        private void OnApprovalDecision(bool approved)
        {
            string decisionReason = approved
                ? "Unity UI\uC5D0\uC11C \uD5C8\uC6A9\uD588\uC5B4."
                : "Unity UI\uC5D0\uC11C \uAC70\uC808\uD588\uC5B4.";

            _approvalPending = false;
            UpdateSendInteractivity();

            SenaEnvelope request = SenaRequestFactory.CreateApprovalResult(
                _sessionId,
                approved,
                decisionReason);
            StartCoroutine(PostEnvelope(request));
        }

        private void ConfigureTmpInputField()
        {
            tmpInputField.lineType = TMP_InputField.LineType.MultiLineNewline;
            tmpInputField.richText = false;

            ConfigureTmpViewport(tmpInputField.textViewport);

            if (tmpInputField.textComponent != null)
            {
                tmpInputField.textComponent.alignment = TextAlignmentOptions.TopLeft;
                tmpInputField.textComponent.enableWordWrapping = true;
                tmpInputField.textComponent.margin = Vector4.zero;
                ConfigureTmpTextRect(tmpInputField.textComponent.rectTransform);
            }

            if (tmpInputField.placeholder is TMP_Text placeholderText)
            {
                placeholderText.alignment = TextAlignmentOptions.TopLeft;
                placeholderText.enableWordWrapping = true;
                placeholderText.margin = Vector4.zero;
                ConfigureTmpTextRect(placeholderText.rectTransform);
            }
        }

        private static void ConfigureTmpViewport(RectTransform viewport)
        {
            if (viewport == null)
            {
                return;
            }

            viewport.anchorMin = Vector2.zero;
            viewport.anchorMax = Vector2.one;
            viewport.pivot = new Vector2(0.5f, 0.5f);
            viewport.anchoredPosition = Vector2.zero;
            viewport.sizeDelta = new Vector2(-16f, -16f);

            RectMask2D rectMask = viewport.GetComponent<RectMask2D>();
            if (rectMask != null)
            {
                rectMask.padding = Vector4.zero;
            }
        }

        private static void ConfigureTmpTextRect(RectTransform rectTransform)
        {
            if (rectTransform == null)
            {
                return;
            }

            rectTransform.anchorMin = Vector2.zero;
            rectTransform.anchorMax = Vector2.one;
            rectTransform.pivot = new Vector2(0.5f, 0.5f);
            rectTransform.anchoredPosition = Vector2.zero;
            rectTransform.sizeDelta = Vector2.zero;
        }

        private void ApplyStaticUiText()
        {
            if (sendButtonText != null)
            {
                sendButtonText.text = "\uBCF4\uB0B4\uAE30";
            }

            if (sendButtonTmpText != null)
            {
                sendButtonTmpText.text = "\uBCF4\uB0B4\uAE30";
            }

            if (inputPlaceholderTmpText != null)
            {
                inputPlaceholderTmpText.text = "\uBA54\uC2DC\uC9C0\uB97C \uC785\uB825\uD574 \uC918";
            }
        }

        private void UpdateInputFieldHeight()
        {
            if (_inputFieldRect == null || tmpInputField == null)
            {
                return;
            }

            float preferredHeight = GetTmpPreferredHeight();

            float targetHeight = Mathf.Clamp(preferredHeight + inputFieldVerticalPadding, minInputFieldHeight, maxInputFieldHeight);
            float currentHeight = _inputFieldRect.sizeDelta.y;

            if (!Mathf.Approximately(currentHeight, targetHeight))
            {
                Vector2 inputSize = _inputFieldRect.sizeDelta;
                inputSize.y = targetHeight;
                _inputFieldRect.sizeDelta = inputSize;

                if (composerPanelRect != null)
                {
                    Vector2 composerSize = composerPanelRect.sizeDelta;
                    composerSize.y = targetHeight + _composerExtraHeight;
                    composerPanelRect.sizeDelta = composerSize;
                }
            }

            ForceCurrentInputFieldLabelUpdate();
        }

        private float GetTmpPreferredHeight()
        {
            TMP_Text textComponent = tmpInputField.textComponent;
            if (textComponent == null)
            {
                return minInputFieldHeight - inputFieldVerticalPadding;
            }

            string content = GetInputMeasurementText(tmpInputField.text);
            if (content.EndsWith("\n") || content.EndsWith("\v"))
            {
                content += " ";
            }

            content = content.Replace('\v', '\n');

            float width = textComponent.rectTransform.rect.width;
            if (width <= 0f)
            {
                width = _inputFieldRect.rect.width;
            }

            Vector2 preferredSize = textComponent.GetPreferredValues(content, width, Mathf.Infinity);
            float explicitLineHeight = GetExplicitLineCount(tmpInputField.text) * GetTmpLineHeight(textComponent);
            return Mathf.Max(preferredSize.y, explicitLineHeight);
        }

        private void UpdateConnectionStatus(bool connected, string suffix = "")
        {
            if (connectionStatusText == null)
            {
                return;
            }

            connectionStatusText.text = connected
                ? (string.IsNullOrEmpty(suffix) ? "\uC5F0\uACB0\uB428" : $"\uC5F0\uACB0\uB428 \u00B7 {suffix}")
                : "\uC5F0\uACB0 \uB04A\uAE40";
        }

        private void UpdateAssistantState(string state, string detail)
        {
            if (assistantStateText == null)
            {
                return;
            }

            assistantStateText.text = $"{TranslateState(state)}: {TranslateDetail(detail)}";
        }

        private void UpdateSendInteractivity()
        {
            bool canSend = !_requestInFlight && !_approvalPending;

            if (sendButton != null)
            {
                sendButton.interactable = canSend;
            }

            if (tmpInputField != null)
            {
                tmpInputField.interactable = canSend;
            }
        }

        private void ActivateCurrentInputField()
        {
            if (tmpInputField != null && tmpInputField.interactable)
            {
                tmpInputField.ActivateInputField();
                tmpInputField.MoveTextEnd(false);
            }
        }

        private void ClearCurrentInputText()
        {
            if (tmpInputField != null)
            {
                tmpInputField.SetTextWithoutNotify(string.Empty);
                tmpInputField.text = string.Empty;
                tmpInputField.ForceLabelUpdate();
            }
        }

        private void ForceCurrentInputFieldLabelUpdate()
        {
            if (tmpInputField != null)
            {
                tmpInputField.ForceLabelUpdate();
            }
        }

        private static string NormalizeSubmittedText(string text)
        {
            if (string.IsNullOrEmpty(text))
            {
                return string.Empty;
            }

            return text.Replace('\v', '\n').TrimEnd('\r', '\n').Trim();
        }

        private static string GetInputMeasurementText(string text)
        {
            return string.IsNullOrEmpty(text) ? " " : text;
        }

        private static int GetExplicitLineCount(string text)
        {
            if (string.IsNullOrEmpty(text))
            {
                return 1;
            }

            int lineCount = 1;
            foreach (char c in text)
            {
                if (c == '\n' || c == '\v')
                {
                    lineCount++;
                }
            }

            return lineCount;
        }

        private static float GetTmpLineHeight(TMP_Text textComponent)
        {
            TMP_FontAsset fontAsset = textComponent.font;
            if (fontAsset == null || fontAsset.faceInfo.pointSize <= 0f)
            {
                return textComponent.fontSize;
            }

            float scale = textComponent.fontSize / fontAsset.faceInfo.pointSize;
            return Mathf.Max(textComponent.fontSize, fontAsset.faceInfo.lineHeight * scale);
        }

        private static bool IsImeCompositionActive()
        {
            BaseInput input = EventSystem.current?.currentInputModule?.input;
            return input != null && !string.IsNullOrEmpty(input.compositionString);
        }

        private static string FormatToolResult(ToolResultPayload payload)
        {
            return payload.status switch
            {
                "success" => payload.tool_name switch
                {
                    "open_app" => "\uC548\uB0B4: \uC571 \uC2E4\uD589\uC774 \uC644\uB8CC\uB410\uC5B4.",
                    "get_active_window" => "\uC548\uB0B4: \uD604\uC7AC \uCC3D \uC815\uBCF4\uB97C \uD655\uC778\uD588\uC5B4.",
                    "capture_screen" => "\uC548\uB0B4: \uD654\uBA74 \uCEA1\uCC98\uB97C \uB9C8\uCCE4\uC5B4.",
                    "type_text" => "\uC548\uB0B4: \uD14D\uC2A4\uD2B8 \uC785\uB825\uC744 \uB9C8\uCCE4\uC5B4.",
                    _ => $"\uC548\uB0B4: {payload.tool_name} \uC791\uC5C5\uC744 \uB9C8\uCCE4\uC5B4."
                },
                "denied" => payload.tool_name switch
                {
                    "open_app" => "\uC548\uB0B4: \uC571 \uC2E4\uD589 \uC694\uCCAD\uC744 \uCDE8\uC18C\uD588\uC5B4.",
                    _ => $"\uC548\uB0B4: {payload.tool_name} \uC791\uC5C5\uC744 \uCDE8\uC18C\uD588\uC5B4."
                },
                _ => string.IsNullOrEmpty(payload.error_message)
                    ? $"\uC548\uB0B4: {payload.tool_name} \uC791\uC5C5 \uC911 \uC624\uB958\uAC00 \uBC1C\uC0DD\uD588\uC5B4."
                    : $"\uC548\uB0B4: {payload.tool_name} \uC791\uC5C5 \uC911 \uC624\uB958\uAC00 \uBC1C\uC0DD\uD588\uC5B4. {payload.error_message}"
            };
        }

        private static string TranslateState(string state)
        {
            return state switch
            {
                "idle" => "\uB300\uAE30 \uC911",
                "listening" => "\uB4E3\uB294 \uC911",
                "thinking" => "\uC0DD\uAC01\uD558\uB294 \uC911",
                "speaking" => "\uB9D0\uD558\uB294 \uC911",
                "awaiting_approval" => "\uC2B9\uC778 \uB300\uAE30 \uC911",
                "tool_running" => "\uC791\uC5C5 \uC2E4\uD589 \uC911",
                "error" => "\uC624\uB958",
                "disconnected" => "\uC5F0\uACB0 \uB04A\uAE40",
                _ => state
            };
        }

        private static string TranslateDetail(string detail)
        {
            return detail switch
            {
                "Waiting for input." => "\uC785\uB825\uC744 \uAE30\uB2E4\uB9AC\uACE0 \uC788\uC5B4.",
                "Interpreting user text." => "\uC785\uB825 \uB0B4\uC6A9\uC744 \uD574\uC11D\uD558\uACE0 \uC788\uC5B4.",
                "Waiting for user approval." => "\uC2B9\uC778\uC744 \uAE30\uB2E4\uB9AC\uACE0 \uC788\uC5B4.",
                "Waiting for desktop tool execution." => "\uB370\uC2A4\uD06C\uD1B1 \uC791\uC5C5 \uACB0\uACFC\uB97C \uAE30\uB2E4\uB9AC\uACE0 \uC788\uC5B4.",
                "Tool execution completed." => "\uC791\uC5C5\uC774 \uC644\uB8CC\uB410\uC5B4.",
                "Tool execution denied." => "\uC791\uC5C5\uC744 \uCDE8\uC18C\uD588\uC5B4.",
                "Tool execution failed." => "\uC791\uC5C5 \uC2E4\uD589\uC5D0 \uC2E4\uD328\uD588\uC5B4.",
                "Desktop-agent returned an error." => "\uB370\uC2A4\uD06C\uD1B1 \uC5D0\uC774\uC804\uD2B8\uC5D0\uC11C \uC624\uB958\uAC00 \uB3CC\uC544\uC654\uC5B4.",
                "Desktop-agent dispatch failed." => "\uB370\uC2A4\uD06C\uD1B1 \uC5D0\uC774\uC804\uD2B8\uC640 \uD1B5\uC2E0\uD558\uC9C0 \uBABB\uD588\uC5B4.",
                _ => detail
            };
        }
    }
}
