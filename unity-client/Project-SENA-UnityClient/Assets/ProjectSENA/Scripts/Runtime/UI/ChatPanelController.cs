using System.Text;
using UnityEngine;
using UnityEngine.UI;

namespace ProjectSENA.UI
{
    public sealed class ChatPanelController : MonoBehaviour
    {
        [SerializeField] private Text transcriptText;
        [SerializeField] private ScrollRect transcriptScrollRect;

        private readonly StringBuilder _buffer = new StringBuilder();

        public void AppendUserMessage(string text)
        {
            AppendLine($"나: {text}");
        }

        public void AppendAssistantMessage(string text)
        {
            AppendLine($"세나: {text}");
        }

        public void AppendSystemMessage(string text)
        {
            AppendLine($"안내: {text}");
        }

        public void Clear()
        {
            _buffer.Clear();
            ApplyText();
        }

        private void AppendLine(string line)
        {
            if (_buffer.Length > 0)
            {
                _buffer.AppendLine();
            }

            _buffer.Append(line);
            ApplyText();
        }

        private void ApplyText()
        {
            if (transcriptText != null)
            {
                transcriptText.text = _buffer.ToString();
            }

            if (transcriptScrollRect != null)
            {
                Canvas.ForceUpdateCanvases();
                transcriptScrollRect.verticalNormalizedPosition = 0f;
            }
        }
    }
}
