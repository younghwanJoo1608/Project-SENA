using TMPro;
using UnityEngine.EventSystems;

namespace ProjectSENA.UI
{
    public sealed class SenaChatInputField : TMP_InputField
    {
        protected override bool IsValidChar(char c)
        {
            // TMP converts Shift+Enter to a vertical tab for soft line breaks.
            // The bundled validator rejects it as a control character, so allow
            // it through and convert it before insertion.
            return c == '\v' || base.IsValidChar(c);
        }

        protected override void Append(char input)
        {
            base.Append(input == '\v' ? '\n' : input);
        }

        public override void OnSubmit(BaseEventData eventData)
        {
            // Chat submit is coordinated by SenaClientController so IME finalization,
            // Enter-to-send, and Shift+Enter newline stay in one policy path.
        }
    }
}
