using System.Collections;
using System.Runtime.InteropServices;
using ProjectSENA.Character;
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
        private const int AllowSetForegroundWindowAnyProcess = -1;

        [Header("Server")]
        [SerializeField] private string inferenceServerBaseUrl = "http://127.0.0.1:8000";
        [SerializeField] private string languageCode = "ko";

        [Header("Chat UI")]
        [SerializeField] private TMP_InputField tmpInputField;
        [SerializeField] private Button sendButton;
        [SerializeField] private Button newSessionButton;
        [SerializeField] private Text sendButtonText;
        [SerializeField] private Text newSessionButtonText;
        [SerializeField] private TMP_Text sendButtonTmpText;
        [SerializeField] private TMP_Text inputPlaceholderTmpText;
        [SerializeField] private RectTransform composerPanelRect;
        [SerializeField] private Text connectionStatusText;
        [SerializeField] private Text assistantStateText;
        [SerializeField] private ChatPanelController chatPanel;
        [SerializeField] private ApprovalPanelController approvalPanel;
        [SerializeField] private RectTransform approvalPanelRect;

        [Header("Character")]
        [SerializeField] private CharacterStateController characterState;
        [SerializeField] private float minimumSpeakingPresentationSeconds = 1.2f;

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
        private bool _characterSpeakingHoldActive;
        private bool _hasDeferredAssistantState;
        private float _composerExtraHeight;
        private Vector2 _lastCanvasSize;
        private Coroutine _speakingHoldCoroutine;
        private string _deferredAssistantState;
        private string _deferredAssistantDetail;

        private void Awake()
        {
            _sessionId = CreateSessionId();
            _apiClient = new SenaApiClient(inferenceServerBaseUrl);

            if (sendButton != null)
            {
                sendButton.onClick.AddListener(SendCurrentInput);
            }

            if (newSessionButton != null)
            {
                newSessionButton.onClick.AddListener(StartNewSession);
            }

            if (sendButtonText == null && sendButton != null)
            {
                sendButtonText = sendButton.GetComponentInChildren<Text>();
            }

            if (newSessionButtonText == null && newSessionButton != null)
            {
                newSessionButtonText = newSessionButton.GetComponentInChildren<Text>();
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

            EnsureCharacterStateController();

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
            CancelCharacterSpeakingHold();

            if (sendButton != null)
            {
                sendButton.onClick.RemoveListener(SendCurrentInput);
            }

            if (newSessionButton != null)
            {
                newSessionButton.onClick.RemoveListener(StartNewSession);
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

        public void StartNewSession()
        {
            if (_requestInFlight)
            {
                chatPanel?.AppendSystemMessage("\uC694\uCCAD\uC744 \uCC98\uB9AC\uD558\uB294 \uC911\uC774\uC57C. \uC751\uB2F5\uC774 \uB3CC\uC544\uC628 \uB4A4 \uC0C8 \uB300\uD654\uB97C \uC2DC\uC791\uD560 \uC218 \uC788\uC5B4.");
                return;
            }

            bool closedPendingApproval = _approvalPending;
            string previousSessionId = _sessionId;
            if (closedPendingApproval)
            {
                StartCoroutine(CancelPendingApprovalForSession(previousSessionId));
            }

            _sessionId = CreateSessionId();
            _approvalPending = false;
            _submitDeferredUntilCompositionEnds = false;
            _submitFromEnterPending = false;
            _inputHeightRefreshPending = false;
            CancelCharacterSpeakingHold();

            approvalPanel?.Hide();
            chatPanel?.Clear();
            chatPanel?.AppendSystemMessage(
                closedPendingApproval
                    ? "\uC0C8 \uB300\uD654\uB97C \uC2DC\uC791\uD558\uBA74\uC11C \uC774\uC804 \uC571 \uC2E4\uD589 \uC694\uCCAD\uC744 \uCDE8\uC18C\uD588\uC5B4."
                    : "\uC0C8 \uB300\uD654\uB97C \uC2DC\uC791\uD588\uC5B4.");

            ClearCurrentInputText();
            UpdateInputFieldHeight();
            UpdateConnectionStatus(true);
            UpdateAssistantState("idle", "Waiting for input.");
            UpdateSendInteractivity();
            _reactivateInputNextFrame = true;
        }

        private IEnumerator CancelPendingApprovalForSession(string sessionId)
        {
            if (_apiClient == null || string.IsNullOrEmpty(sessionId))
            {
                yield break;
            }

            SenaEnvelope cancellation = SenaRequestFactory.CreateApprovalResult(
                sessionId,
                false,
                "Unity UI\uC5D0\uC11C \uC0C8 \uB300\uD654\uB97C \uC2DC\uC791\uD574\uC11C \uC774\uC804 \uC2B9\uC778 \uC694\uCCAD\uC744 \uCDE8\uC18C\uD588\uC5B4.");

            yield return _apiClient.PostMessage(
                cancellation,
                _ => { },
                error => Debug.LogWarning($"Project-SENA approval cancellation failed: {error}"));
        }

        private void EnsureCharacterStateController()
        {
            if (characterState != null)
            {
                return;
            }

            characterState = UnityEngine.Object.FindAnyObjectByType<CharacterStateController>();
            if (characterState != null)
            {
                return;
            }

            RectTransform parent = _rootCanvasRect;
            if (parent == null)
            {
                Canvas canvas = UnityEngine.Object.FindAnyObjectByType<Canvas>();
                parent = canvas != null ? canvas.transform as RectTransform : null;
            }

            if (parent == null)
            {
                return;
            }

            characterState = CharacterPlaceholderFactory.Create(parent);
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
                RecoverFromFailedExchange("서버 응답을 읽지 못했어. 잠시 후 다시 시도해 줘.", "Server returned an empty response.");
                return;
            }

            foreach (SenaEnvelope message in batch.messages)
            {
                switch (message.type)
                {
                    case "assistant_text":
                    {
                        AssistantTextPayload payload = message.ToPayload<AssistantTextPayload>();
                        ApplyAssistantTextToCharacter(payload.persona_state, payload.should_speak);
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
                        CancelCharacterSpeakingHold();
                        characterState?.ApplyApprovalRequest();
                        approvalPanel?.Show(payload, approved => OnApprovalDecision(approved));
                        break;
                    }
                    case "tool_result":
                    {
                        ToolResultPayload payload = message.ToPayload<ToolResultPayload>();
                        CancelCharacterSpeakingHold();
                        characterState?.ApplyToolResult(payload.status);
                        string toolResultText = FormatToolResult(payload);
                        if (ShouldDisplayToolResultAsAssistant(payload))
                        {
                            chatPanel?.AppendAssistantMessage(toolResultText);
                        }
                        else
                        {
                            chatPanel?.AppendSystemMessage(toolResultText);
                        }

                        _approvalPending = false;
                        UpdateSendInteractivity();
                        break;
                    }
                    case "error":
                    {
                        ErrorPayload payload = message.ToPayload<ErrorPayload>();
                        chatPanel?.AppendSystemMessage(FormatServerError(payload));
                        UpdateAssistantState("error", string.IsNullOrEmpty(payload.message) ? "Server returned an error." : payload.message);
                        _approvalPending = false;
                        approvalPanel?.Hide();
                        UpdateSendInteractivity();
                        _reactivateInputNextFrame = true;
                        break;
                    }
                }
            }
        }

        private void HandleTransportError(string error)
        {
            RecoverFromFailedExchange(FormatTransportError(error), error);
        }

        private void OnApprovalDecision(bool approved)
        {
            string decisionReason = approved
                ? "Unity UI\uC5D0\uC11C \uD5C8\uC6A9\uD588\uC5B4."
                : "Unity UI\uC5D0\uC11C \uAC70\uC808\uD588\uC5B4.";

            if (approved)
            {
                AllowDesktopAgentForegroundActivation();
            }

            _approvalPending = false;
            UpdateSendInteractivity();

            SenaEnvelope request = SenaRequestFactory.CreateApprovalResult(
                _sessionId,
                approved,
                decisionReason);
            StartCoroutine(PostEnvelope(request));
        }

        private static void AllowDesktopAgentForegroundActivation()
        {
#if UNITY_STANDALONE_WIN || UNITY_EDITOR_WIN
            AllowSetForegroundWindow(AllowSetForegroundWindowAnyProcess);
#endif
        }

        private void RecoverFromFailedExchange(string userMessage, string technicalDetail)
        {
            UpdateConnectionStatus(false, "\uC7AC\uC2DC\uB3C4\uAC00 \uD544\uC694\uD574.");
            chatPanel?.AppendSystemMessage(userMessage);
            UpdateAssistantState("disconnected", FormatFailureStateDetail(technicalDetail));
            _approvalPending = false;
            _requestInFlight = false;
            approvalPanel?.Hide();
            UpdateSendInteractivity();
            _reactivateInputNextFrame = true;

            if (!string.IsNullOrEmpty(technicalDetail))
            {
                Debug.LogWarning($"Project-SENA request failed: {technicalDetail}");
            }
        }

        private static string FormatTransportError(string error)
        {
            string normalized = error ?? string.Empty;

            if (ContainsIgnoreCase(normalized, "Connection failed") ||
                ContainsIgnoreCase(normalized, "Cannot connect") ||
                ContainsIgnoreCase(normalized, "connection refused") ||
                ContainsIgnoreCase(normalized, "Failed to connect"))
            {
                return "\uCD94\uB860 \uC11C\uBC84\uC5D0 \uC5F0\uACB0\uD558\uC9C0 \uBABB\uD588\uC5B4. inference-server\uAC00 \uC2E4\uD589 \uC911\uC778\uC9C0 \uD655\uC778\uD55C \uB4A4 \uB2E4\uC2DC \uBCF4\uB0B4\uC918.";
            }

            if (ContainsIgnoreCase(normalized, "timed out") || ContainsIgnoreCase(normalized, "timeout"))
            {
                return "\uC11C\uBC84 \uC751\uB2F5\uC744 \uAE30\uB2E4\uB9AC\uB2E4\uAC00 \uC2DC\uAC04\uC774 \uCD08\uACFC\uB410\uC5B4. \uC11C\uBC84 \uC0C1\uD0DC\uB97C \uD655\uC778\uD558\uACE0 \uB2E4\uC2DC \uC2DC\uB3C4\uD574 \uC918.";
            }

            if (normalized.StartsWith("HTTP ", System.StringComparison.Ordinal))
            {
                return "\uC11C\uBC84\uAC00 \uC624\uB958 \uC751\uB2F5\uC744 \uBCF4\uB0C8\uC5B4. \uC11C\uBC84 \uB85C\uADF8\uB97C \uD655\uC778\uD55C \uB4A4 \uB2E4\uC2DC \uC2DC\uB3C4\uD574 \uC918.";
            }

            if (ContainsIgnoreCase(normalized, "parse") || ContainsIgnoreCase(normalized, "processing"))
            {
                return "\uC11C\uBC84 \uC751\uB2F5 \uD615\uC2DD\uC744 \uC77D\uC9C0 \uBABB\uD588\uC5B4. \uD504\uB85C\uD1A0\uCF5C\uC774 \uB9DE\uB294\uC9C0 \uD655\uC778\uD574\uC57C \uD574.";
            }

            return string.IsNullOrEmpty(normalized)
                ? "\uC11C\uBC84\uC640 \uD1B5\uC2E0\uD558\uB294 \uC911 \uC54C \uC218 \uC5C6\uB294 \uC624\uB958\uAC00 \uBC1C\uC0DD\uD588\uC5B4. \uB2E4\uC2DC \uC2DC\uB3C4\uD574 \uC918."
                : $"\uC11C\uBC84\uC640 \uD1B5\uC2E0\uD558\uB294 \uC911 \uC624\uB958\uAC00 \uBC1C\uC0DD\uD588\uC5B4. {normalized}";
        }

        private static string FormatFailureStateDetail(string technicalDetail)
        {
            string normalized = technicalDetail ?? string.Empty;

            if (ContainsIgnoreCase(normalized, "timed out") || ContainsIgnoreCase(normalized, "timeout"))
            {
                return "Server response timed out.";
            }

            if (normalized.StartsWith("HTTP ", System.StringComparison.Ordinal))
            {
                return "Server returned an error.";
            }

            if (ContainsIgnoreCase(normalized, "parse") || ContainsIgnoreCase(normalized, "processing"))
            {
                return "Server response could not be read.";
            }

            return "Connection failed.";
        }

        private static bool ContainsIgnoreCase(string text, string value)
        {
            return text.IndexOf(value, System.StringComparison.OrdinalIgnoreCase) >= 0;
        }

        private static string FormatServerError(ErrorPayload payload)
        {
            if (payload == null)
            {
                return "\uC11C\uBC84\uC5D0\uC11C \uC624\uB958\uAC00 \uB3CC\uC544\uC654\uC5B4.";
            }

            if (payload.code == "desktop_agent_unreachable")
            {
                return "\uB370\uC2A4\uD06C\uD1B1 \uC5D0\uC774\uC804\uD2B8\uC5D0 \uC5F0\uACB0\uD558\uC9C0 \uBABB\uD588\uC5B4. desktop-agent\uAC00 \uC2E4\uD589 \uC911\uC778\uC9C0 \uD655\uC778\uD55C \uB4A4 \uB2E4\uC2DC \uBCF4\uB0B4\uC918.";
            }

            if (payload.code == "tool_execution_error")
            {
                return payload.retryable
                    ? "\uB370\uC2A4\uD06C\uD1B1 \uC791\uC5C5 \uC2E4\uD589 \uC911 \uC624\uB958\uAC00 \uBC1C\uC0DD\uD588\uC5B4. \uC0C1\uD0DC\uB97C \uD655\uC778\uD55C \uB4A4 \uB2E4\uC2DC \uC2DC\uB3C4\uD560 \uC218 \uC788\uC5B4."
                    : "\uB370\uC2A4\uD06C\uD1B1 \uC791\uC5C5 \uC2E4\uD589 \uC911 \uC624\uB958\uAC00 \uBC1C\uC0DD\uD588\uC5B4.";
            }

            if (payload.code == "pending_tool_exists")
            {
                return "\uC774\uBBF8 \uD655\uC778\uC744 \uAE30\uB2E4\uB9AC\uB294 \uC791\uC5C5\uC774 \uC788\uC5B4. \uBA3C\uC800 \uC2B9\uC778 \uCC3D\uC5D0\uC11C \uD5C8\uC6A9\uD558\uAC70\uB098 \uAC70\uC808\uD574\uC918.";
            }

            if (payload.code == "stale_approval_result")
            {
                return "\uC774\uBBF8 \uCC98\uB9AC\uB41C \uC2B9\uC778 \uC751\uB2F5\uC774\uC57C. \uD544\uC694\uD558\uBA74 \uC694\uCCAD\uC744 \uB2E4\uC2DC \uBCF4\uB0B4\uC918.";
            }

            string message = string.IsNullOrEmpty(payload.message)
                ? "\uC11C\uBC84\uC5D0\uC11C \uC624\uB958\uAC00 \uB3CC\uC544\uC654\uC5B4."
                : payload.message;

            return payload.retryable
                ? $"\uC624\uB958: {message} \uC7A0\uC2DC \uD6C4 \uB2E4\uC2DC \uC2DC\uB3C4\uD560 \uC218 \uC788\uC5B4."
                : $"\uC624\uB958: {message}";
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

            if (newSessionButtonText != null)
            {
                newSessionButtonText.text = "\uC0C8 \uB300\uD654";
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
                : (string.IsNullOrEmpty(suffix) ? "\uC5F0\uACB0 \uB04A\uAE40" : $"\uC5F0\uACB0 \uB04A\uAE40 \u00B7 {suffix}");
        }

        private void UpdateAssistantState(string state, string detail)
        {
            ApplyAssistantStateToCharacter(state, detail);

            if (assistantStateText == null)
            {
                return;
            }

            assistantStateText.text = $"{TranslateState(state)}: {TranslateDetail(detail)}";
        }

        private void ApplyAssistantTextToCharacter(string personaState, bool shouldSpeak)
        {
            characterState?.ApplyAssistantText(personaState, shouldSpeak);

            if (shouldSpeak)
            {
                BeginCharacterSpeakingHold();
                return;
            }

            CancelCharacterSpeakingHold();
        }

        private void ApplyAssistantStateToCharacter(string state, string detail)
        {
            if (ShouldDeferAssistantStateForSpeaking(state))
            {
                _hasDeferredAssistantState = true;
                _deferredAssistantState = state;
                _deferredAssistantDetail = detail;
                return;
            }

            if (!IsIdleAssistantState(state))
            {
                CancelCharacterSpeakingHold();
            }

            characterState?.ApplyAssistantState(state, detail);
        }

        private void BeginCharacterSpeakingHold()
        {
            if (characterState == null || minimumSpeakingPresentationSeconds <= 0f)
            {
                return;
            }

            _characterSpeakingHoldActive = true;
            _hasDeferredAssistantState = false;
            _deferredAssistantState = null;
            _deferredAssistantDetail = null;

            if (_speakingHoldCoroutine != null)
            {
                StopCoroutine(_speakingHoldCoroutine);
            }

            _speakingHoldCoroutine = StartCoroutine(CompleteCharacterSpeakingHoldAfterDelay());
        }

        private IEnumerator CompleteCharacterSpeakingHoldAfterDelay()
        {
            yield return new WaitForSeconds(minimumSpeakingPresentationSeconds);

            _speakingHoldCoroutine = null;
            _characterSpeakingHoldActive = false;

            if (!_hasDeferredAssistantState)
            {
                yield break;
            }

            string deferredState = _deferredAssistantState;
            string deferredDetail = _deferredAssistantDetail;
            _hasDeferredAssistantState = false;
            _deferredAssistantState = null;
            _deferredAssistantDetail = null;

            characterState?.ApplyAssistantState(deferredState, deferredDetail);
        }

        private void CancelCharacterSpeakingHold()
        {
            if (_speakingHoldCoroutine != null)
            {
                StopCoroutine(_speakingHoldCoroutine);
                _speakingHoldCoroutine = null;
            }

            _characterSpeakingHoldActive = false;
            _hasDeferredAssistantState = false;
            _deferredAssistantState = null;
            _deferredAssistantDetail = null;
        }

        private bool ShouldDeferAssistantStateForSpeaking(string state)
        {
            return _characterSpeakingHoldActive && IsIdleAssistantState(state);
        }

        private static bool IsIdleAssistantState(string state)
        {
            return string.Equals(state, "idle", System.StringComparison.OrdinalIgnoreCase);
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

            if (newSessionButton != null)
            {
                newSessionButton.interactable = !_requestInFlight;
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

        private static string CreateSessionId()
        {
            return $"unity-session-{System.Guid.NewGuid():N}";
        }

#if UNITY_STANDALONE_WIN || UNITY_EDITOR_WIN
        [DllImport("user32.dll")]
        private static extern bool AllowSetForegroundWindow(int processId);
#endif

        private static string FormatToolResult(ToolResultPayload payload)
        {
            return payload.status switch
            {
                "success" => payload.tool_name switch
                {
                    "open_app" => "\uC571 \uC2E4\uD589\uC774 \uC644\uB8CC\uB410\uC5B4.",
                    "get_active_window" => FormatActiveWindowToolResult(payload),
                    "capture_screen" => "\uD654\uBA74 \uCEA1\uCC98\uB97C \uB9C8\uCCE4\uC5B4.",
                    "type_text" => "\uD14D\uC2A4\uD2B8 \uC785\uB825\uC744 \uB9C8\uCCE4\uC5B4.",
                    _ => $"{GetToolDisplayName(payload.tool_name)} \uC791\uC5C5\uC744 \uB9C8\uCCE4\uC5B4."
                },
                "denied" => payload.tool_name switch
                {
                    "open_app" => "\uC571 \uC2E4\uD589 \uC694\uCCAD\uC744 \uCDE8\uC18C\uD588\uC5B4.",
                    _ => $"{GetToolDisplayName(payload.tool_name)} \uC791\uC5C5\uC744 \uCDE8\uC18C\uD588\uC5B4."
                },
                _ => FormatToolError(payload)
            };
        }

        private static bool ShouldDisplayToolResultAsAssistant(ToolResultPayload payload)
        {
            return payload.status == "success" && payload.tool_name == "get_active_window";
        }

        private static string FormatActiveWindowToolResult(ToolResultPayload payload)
        {
            string title = GetResultString(payload, "window_title");
            string processName = GetResultString(payload, "process_name");

            if (string.IsNullOrEmpty(title) && string.IsNullOrEmpty(processName))
            {
                return "\uD604\uC7AC \uD65C\uC131 \uCC3D \uC815\uBCF4\uB97C \uD655\uC778\uD588\uC5B4.";
            }

            string descriptor = string.IsNullOrEmpty(title) ? processName : title;
            if (!string.IsNullOrEmpty(title) && !string.IsNullOrEmpty(processName))
            {
                descriptor = $"{title} ({processName})";
            }

            return $"\uD604\uC7AC \uCC3D\uC740 {descriptor}\uC774\uC57C.";
        }

        private static string FormatToolError(ToolResultPayload payload)
        {
            if (payload.tool_name == "capture_screen")
            {
                string reason = GetResultString(payload, "reason");
                if (reason == "missing_foreground_window")
                {
                    return "\uCEA1\uCC98\uD560 \uD65C\uC131 \uCC3D\uC744 \uCC3E\uC9C0 \uBABB\uD588\uC5B4. \uBA3C\uC800 \uCEA1\uCC98\uD560 \uCC3D\uC744 \uC120\uD0DD\uD574 \uC918.";
                }

                if (reason == "target_window_not_found" ||
                    reason == "target_app_window_not_found")
                {
                    return "\uCEA1\uCC98\uD560 \uB300\uC0C1 \uCC3D\uC744 \uCC3E\uC9C0 \uBABB\uD588\uC5B4. \uCC3D\uC774 \uC5F4\uB824 \uC788\uB294\uC9C0 \uD655\uC778\uD55C \uB4A4 \uB2E4\uC2DC \uC2DC\uB3C4\uD574 \uC918.";
                }

                if (reason == "window_not_capturable")
                {
                    return "\uB300\uC0C1 \uCC3D\uC744 \uCEA1\uCC98\uD560 \uC218 \uC5C6\uC5B4. \uCC3D\uC774 \uCD5C\uC18C\uD654\uB418\uC5B4 \uC788\uB2E4\uBA74 \uB2E4\uC2DC \uC5F4\uC5B4 \uC900 \uB4A4 \uC2DC\uB3C4\uD574 \uC918.";
                }

                if (reason == "target_window_not_foreground")
                {
                    return "\uCEA1\uCC98\uD560 \uB300\uC0C1 \uCC3D\uC744 \uC55E\uC73C\uB85C \uAC00\uC838\uC624\uC9C0 \uBABB\uD588\uC5B4. \uCC3D\uC744 \uD655\uC778\uD55C \uB4A4 \uB2E4\uC2DC \uC2DC\uB3C4\uD574 \uC918.";
                }

                if (reason == "unsupported_capture_mode" ||
                    reason == "unsupported_capture_format" ||
                    reason == "window_rect_failed")
                {
                    return $"\uD654\uBA74 \uCEA1\uCC98\uB97C \uC644\uB8CC\uD558\uC9C0 \uBABB\uD588\uC5B4. \uC6D0\uC778: {reason}";
                }
            }

            if (payload.tool_name == "type_text")
            {
                string reason = GetResultString(payload, "reason");
                if (reason == "active_window_changed_before_typing" ||
                    reason == "active_window_changed_while_typing")
                {
                    return "\uC785\uB825 \uB300\uC0C1 \uCC3D\uC774 \uBC14\uB00C\uC5B4\uC11C \uD14D\uC2A4\uD2B8\uB97C \uC785\uB825\uD558\uC9C0 \uC54A\uC558\uC5B4. \uB300\uC0C1 \uCC3D\uC744 \uD655\uC778\uD55C \uB4A4 \uB2E4\uC2DC \uC2DC\uB3C4\uD574 \uC918.";
                }

                if (reason == "missing_foreground_window")
                {
                    return "\uC785\uB825\uD560 \uD65C\uC131 \uCC3D\uC744 \uCC3E\uC9C0 \uBABB\uD588\uC5B4. \uBA3C\uC800 \uD14D\uC2A4\uD2B8\uB97C \uC785\uB825\uD560 \uCC3D\uC744 \uC120\uD0DD\uD574 \uC918.";
                }

                if (reason == "target_window_not_found")
                {
                    return "\uC785\uB825\uD560 \uB300\uC0C1 \uCC3D\uC744 \uB2E4\uC2DC \uCC3E\uC9C0 \uBABB\uD588\uC5B4. \uBA54\uBAA8\uC7A5\uC774 \uC5F4\uB824 \uC788\uB294\uC9C0 \uD655\uC778\uD55C \uB4A4 \uB2E4\uC2DC \uC2DC\uB3C4\uD574 \uC918.";
                }

                if (reason == "target_app_window_not_found")
                {
                    return "\uC694\uCCAD\uD55C \uC571 \uCC3D\uC744 \uCC3E\uC9C0 \uBABB\uD588\uC5B4. \uBA54\uBAA8\uC7A5\uC774 \uC5F4\uB824 \uC788\uB294\uC9C0 \uD655\uC778\uD55C \uB4A4 \uB2E4\uC2DC \uC2DC\uB3C4\uD574 \uC918.";
                }

                if (reason == "send_input_failed" ||
                    reason == "clipboard_paste_failed" ||
                    reason == "clipboard_open_failed" ||
                    reason == "clipboard_alloc_failed" ||
                    reason == "clipboard_lock_failed" ||
                    reason == "clipboard_empty_failed" ||
                    reason == "clipboard_set_failed" ||
                    reason == "unexpected_executor_error")
                {
                    string win32Error = GetResultString(payload, "win32_error");
                    string detail = string.IsNullOrEmpty(win32Error)
                        ? reason
                        : $"{reason}, Win32={win32Error}";
                    return $"\uD14D\uC2A4\uD2B8 \uC785\uB825\uC744 \uC644\uB8CC\uD558\uC9C0 \uBABB\uD588\uC5B4. \uC6D0\uC778: {detail}";
                }

                if (!string.IsNullOrEmpty(payload.error_message))
                {
                    return $"\uD14D\uC2A4\uD2B8 \uC785\uB825\uC744 \uC644\uB8CC\uD558\uC9C0 \uBABB\uD588\uC5B4. \uC6D0\uC778: {payload.error_message}";
                }
            }

            if (string.IsNullOrEmpty(payload.error_message))
            {
                return $"{GetToolDisplayName(payload.tool_name)} \uC791\uC5C5 \uC911 \uC624\uB958\uAC00 \uBC1C\uC0DD\uD588\uC5B4.";
            }

            return $"{GetToolDisplayName(payload.tool_name)} \uC791\uC5C5 \uC911 \uC624\uB958\uAC00 \uBC1C\uC0DD\uD588\uC5B4. \uC0C1\uD0DC\uB97C \uD655\uC778\uD55C \uB4A4 \uB2E4\uC2DC \uC2DC\uB3C4\uD574 \uC918.";
        }

        private static string GetResultString(ToolResultPayload payload, string key)
        {
            if (payload.result == null || !payload.result.TryGetValue(key, out object value) || value == null)
            {
                return string.Empty;
            }

            return value.ToString();
        }

        private static string GetToolDisplayName(string toolName)
        {
            return toolName switch
            {
                "open_app" => "\uC571 \uC2E4\uD589",
                "get_active_window" => "\uD604\uC7AC \uCC3D \uD655\uC778",
                "capture_screen" => "\uD654\uBA74 \uCEA1\uCC98",
                "type_text" => "\uD14D\uC2A4\uD2B8 \uC785\uB825",
                _ => toolName
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
                "Observation completed." => "\uD655\uC778\uD588\uC5B4.",
                "Tool execution denied." => "\uC791\uC5C5\uC744 \uCDE8\uC18C\uD588\uC5B4.",
                "Tool execution failed." => "\uC791\uC5C5 \uC2E4\uD589\uC5D0 \uC2E4\uD328\uD588\uC5B4.",
                "Desktop-agent returned an error." => "\uB370\uC2A4\uD06C\uD1B1 \uC5D0\uC774\uC804\uD2B8\uC5D0\uC11C \uC624\uB958\uAC00 \uB3CC\uC544\uC654\uC5B4.",
                "Desktop-agent dispatch failed." => "\uB370\uC2A4\uD06C\uD1B1 \uC5D0\uC774\uC804\uD2B8\uC640 \uD1B5\uC2E0\uD558\uC9C0 \uBABB\uD588\uC5B4.",
                "Connection failed." => "\uC11C\uBC84\uC5D0 \uC5F0\uACB0\uD560 \uC218 \uC5C6\uC5B4.",
                "Server response timed out." => "\uC11C\uBC84 \uC751\uB2F5 \uC2DC\uAC04\uC774 \uCD08\uACFC\uB410\uC5B4.",
                "Server returned an error." => "\uC11C\uBC84\uAC00 \uC624\uB958 \uC751\uB2F5\uC744 \uBCF4\uB0C8\uC5B4.",
                "Server response could not be read." => "\uC11C\uBC84 \uC751\uB2F5\uC744 \uC77D\uC9C0 \uBABB\uD588\uC5B4.",
                "No pending approval exists." => "\uCC98\uB9AC\uD560 \uC2B9\uC778 \uC694\uCCAD\uC774 \uC5C6\uC5B4.",
                _ => detail
            };
        }
    }
}
