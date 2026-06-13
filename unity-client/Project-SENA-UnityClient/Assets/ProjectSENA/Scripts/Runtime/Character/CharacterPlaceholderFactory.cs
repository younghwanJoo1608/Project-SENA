using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace ProjectSENA.Character
{
    public static class CharacterPlaceholderFactory
    {
        public static CharacterStateController Create(RectTransform parent)
        {
            RectTransform root = CreateRect("SenaCharacterPlaceholder", parent);
            root.anchorMin = new Vector2(1f, 0.5f);
            root.anchorMax = new Vector2(1f, 0.5f);
            root.pivot = new Vector2(1f, 0.5f);
            root.anchoredPosition = new Vector2(-96f, 0f);
            root.sizeDelta = new Vector2(280f, 420f);
            root.SetAsFirstSibling();

            RectTransform body = CreateRect("Body", root);
            body.anchorMin = new Vector2(0.5f, 0.5f);
            body.anchorMax = new Vector2(0.5f, 0.5f);
            body.pivot = new Vector2(0.5f, 0.5f);
            body.anchoredPosition = new Vector2(0f, 28f);
            body.sizeDelta = new Vector2(180f, 280f);

            Image bodyImage = body.gameObject.AddComponent<Image>();
            bodyImage.raycastTarget = false;

            RectTransform label = CreateRect("StateLabel", root);
            label.anchorMin = new Vector2(0f, 0f);
            label.anchorMax = new Vector2(1f, 0f);
            label.pivot = new Vector2(0.5f, 0f);
            label.anchoredPosition = new Vector2(0f, 18f);
            label.sizeDelta = new Vector2(0f, 40f);

            TextMeshProUGUI labelText = label.gameObject.AddComponent<TextMeshProUGUI>();
            labelText.raycastTarget = false;
            labelText.alignment = TextAlignmentOptions.Center;
            labelText.fontSize = 24f;
            labelText.color = new Color(0.12f, 0.14f, 0.16f, 0.9f);
            labelText.text = SenaCharacterState.Idle.ToString();

            PlaceholderCharacterPresenter presenter = root.gameObject.AddComponent<PlaceholderCharacterPresenter>();
            presenter.BindVisuals(bodyImage, labelText, body);

            CharacterStateController controller = root.gameObject.AddComponent<CharacterStateController>();
            controller.BindPresenter(presenter);
            return controller;
        }

        private static RectTransform CreateRect(string name, RectTransform parent)
        {
            GameObject gameObject = new GameObject(name, typeof(RectTransform));
            gameObject.layer = parent.gameObject.layer;
            RectTransform rect = gameObject.GetComponent<RectTransform>();
            rect.SetParent(parent, false);
            rect.localScale = Vector3.one;
            rect.localRotation = Quaternion.identity;
            rect.localPosition = Vector3.zero;
            return rect;
        }
    }
}
