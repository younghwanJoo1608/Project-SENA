using System;
using UnityEngine;

namespace ProjectSENA.Character
{
    public readonly struct SenaCharacterSnapshot
    {
        public SenaCharacterSnapshot(
            SenaCharacterState state,
            string assistantState,
            string personaState,
            string detail,
            bool shouldSpeak)
        {
            State = state;
            AssistantState = assistantState;
            PersonaState = personaState;
            Detail = detail;
            ShouldSpeak = shouldSpeak;
        }

        public SenaCharacterState State { get; }
        public string AssistantState { get; }
        public string PersonaState { get; }
        public string Detail { get; }
        public bool ShouldSpeak { get; }
    }

    public sealed class CharacterStateController : MonoBehaviour
    {
        [Header("Presentation")]
        [SerializeField] private CharacterPresenterBase presenter;

        public event Action<SenaCharacterSnapshot> StateChanged;
        public event Action<SenaCharacterPresentation> PresentationChanged;

        public SenaCharacterState CurrentState { get; private set; } = SenaCharacterState.Idle;
        public string CurrentAssistantState { get; private set; } = "idle";
        public string CurrentPersonaState { get; private set; } = "neutral";
        public string CurrentDetail { get; private set; } = string.Empty;
        public bool ShouldSpeak { get; private set; }

        private void Awake()
        {
            if (presenter == null)
            {
                presenter = GetComponentInChildren<CharacterPresenterBase>();
            }

            EmitStateChanged();
        }

        private void Start()
        {
            // Run once after every component has completed Awake so Live2D bindings can initialize.
            EmitStateChanged();
        }

        public void ApplyAssistantState(string assistantState, string detail)
        {
            CurrentAssistantState = string.IsNullOrEmpty(assistantState) ? "idle" : assistantState;
            CurrentDetail = detail ?? string.Empty;
            SetState(MapAssistantState(CurrentAssistantState));
        }

        public void BindPresenter(CharacterPresenterBase characterPresenter)
        {
            presenter = characterPresenter;
            EmitStateChanged();
        }

        public void ApplyAssistantText(string personaState, bool shouldSpeak)
        {
            CurrentPersonaState = string.IsNullOrEmpty(personaState) ? "neutral" : personaState;
            ShouldSpeak = shouldSpeak;

            if (shouldSpeak)
            {
                SetState(SenaCharacterState.Speaking);
                return;
            }

            if (CurrentState == SenaCharacterState.Idle ||
                CurrentState == SenaCharacterState.Speaking ||
                CurrentState == SenaCharacterState.Satisfied ||
                CurrentState == SenaCharacterState.Concerned)
            {
                SetState(MapPersonaState(CurrentPersonaState, shouldSpeak));
            }
            else
            {
                EmitStateChanged();
            }
        }

        public void ApplyApprovalRequest()
        {
            CurrentAssistantState = "awaiting_approval";
            SetState(SenaCharacterState.AwaitingApproval);
        }

        public void ApplyToolResult(string status)
        {
            if (string.Equals(status, "success", StringComparison.OrdinalIgnoreCase))
            {
                SetState(SenaCharacterState.Satisfied);
                return;
            }

            if (string.Equals(status, "denied", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(status, "cancelled", StringComparison.OrdinalIgnoreCase))
            {
                SetState(SenaCharacterState.Concerned);
                return;
            }

            SetState(SenaCharacterState.Error);
        }

        public void MarkDisconnected(string detail)
        {
            CurrentAssistantState = "disconnected";
            CurrentDetail = detail ?? string.Empty;
            SetState(SenaCharacterState.Disconnected);
        }

        public void MarkError(string detail)
        {
            CurrentAssistantState = "error";
            CurrentDetail = detail ?? string.Empty;
            SetState(SenaCharacterState.Error);
        }

        private void SetState(SenaCharacterState nextState)
        {
            CurrentState = nextState;
            EmitStateChanged();
        }

        private void EmitStateChanged()
        {
            SenaCharacterSnapshot snapshot = new SenaCharacterSnapshot(
                CurrentState,
                CurrentAssistantState,
                CurrentPersonaState,
                CurrentDetail,
                ShouldSpeak);
            SenaCharacterPresentation presentation = CharacterPresentationMapper.Map(snapshot);
            presenter?.ApplyPresentation(presentation);
            StateChanged?.Invoke(snapshot);
            PresentationChanged?.Invoke(presentation);
        }

        private static SenaCharacterState MapAssistantState(string assistantState)
        {
            return assistantState switch
            {
                "listening" => SenaCharacterState.Listening,
                "thinking" => SenaCharacterState.Thinking,
                "speaking" => SenaCharacterState.Speaking,
                "awaiting_approval" => SenaCharacterState.AwaitingApproval,
                "tool_running" => SenaCharacterState.ToolRunning,
                "error" => SenaCharacterState.Error,
                "disconnected" => SenaCharacterState.Disconnected,
                _ => SenaCharacterState.Idle
            };
        }

        private static SenaCharacterState MapPersonaState(string personaState, bool shouldSpeak)
        {
            if (shouldSpeak)
            {
                return SenaCharacterState.Speaking;
            }

            return personaState switch
            {
                "focused" => SenaCharacterState.Thinking,
                "satisfied" => SenaCharacterState.Satisfied,
                "concerned" => SenaCharacterState.Concerned,
                "playful" => SenaCharacterState.Satisfied,
                "calm" => SenaCharacterState.Idle,
                _ => SenaCharacterState.Idle
            };
        }

    }
}
