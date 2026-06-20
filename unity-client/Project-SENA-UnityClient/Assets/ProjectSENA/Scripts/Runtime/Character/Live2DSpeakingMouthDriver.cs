#if PROJECT_SENA_LIVE2D
using Live2D.Cubism.Framework;
using Live2D.Cubism.Framework.MouthMovement;
using UnityEngine;

namespace ProjectSENA.Character
{
    [DisallowMultipleComponent]
    public sealed class Live2DSpeakingMouthDriver : MonoBehaviour
    {
        [Header("Sources")]
        [SerializeField] private CharacterStateController characterState;
        [SerializeField] private CubismMouthController mouthController;

        [Header("Mouth Opening")]
        [SerializeField] private CubismParameterBlendMode mouthBlendMode = CubismParameterBlendMode.Override;
        [SerializeField, Range(0f, 1f)] private float closedOpening;
        [SerializeField, Range(0f, 1f)] private float minimumSpeakingOpening = 0.15f;
        [SerializeField, Range(0f, 1f)] private float maximumSpeakingOpening = 0.75f;
        [SerializeField] private float syllableFrequencyHz = 4.5f;
        [SerializeField] private float smoothingSpeed = 18f;
        [SerializeField] private bool closeMouthWhenNotSpeaking = true;

        [Header("Diagnostics")]
        [SerializeField] private bool warnWhenMouthControllerMissing = true;

        private bool isSpeaking;
        private float currentOpening;
        private bool warnedMissingMouthController;

        private void Awake()
        {
            if (characterState == null)
            {
                characterState = GetComponentInParent<CharacterStateController>();
            }

            if (mouthController == null)
            {
                mouthController = GetComponentInChildren<CubismMouthController>(includeInactive: true);
            }
        }

        private void OnEnable()
        {
            if (characterState != null)
            {
                characterState.PresentationChanged += HandlePresentationChanged;
            }
        }

        private void Start()
        {
            if (mouthController != null)
            {
                mouthController.BlendMode = mouthBlendMode;
                mouthController.Refresh();
                currentOpening = closeMouthWhenNotSpeaking
                    ? closedOpening
                    : mouthController.MouthOpening;
                mouthController.MouthOpening = currentOpening;
            }
            else
            {
                WarnMissingMouthControllerOnce();
            }
        }

        private void OnDisable()
        {
            if (characterState != null)
            {
                characterState.PresentationChanged -= HandlePresentationChanged;
            }
        }

        private void Update()
        {
            if (mouthController == null)
            {
                WarnMissingMouthControllerOnce();
                return;
            }

            float targetOpening = ResolveTargetOpening();
            float smoothing = Mathf.Max(0.01f, smoothingSpeed);
            currentOpening = Mathf.Lerp(
                currentOpening,
                targetOpening,
                1f - Mathf.Exp(-smoothing * Time.deltaTime));
            mouthController.MouthOpening = Mathf.Clamp01(currentOpening);
        }

        private void HandlePresentationChanged(SenaCharacterPresentation presentation)
        {
            isSpeaking = presentation.IsSpeaking;
        }

        private float ResolveTargetOpening()
        {
            if (!isSpeaking)
            {
                return closeMouthWhenNotSpeaking
                    ? closedOpening
                    : mouthController.MouthOpening;
            }

            float frequency = Mathf.Max(0.1f, syllableFrequencyHz);
            float wave = (Mathf.Sin(Time.time * frequency * Mathf.PI * 2f) + 1f) * 0.5f;
            float min = Mathf.Min(minimumSpeakingOpening, maximumSpeakingOpening);
            float max = Mathf.Max(minimumSpeakingOpening, maximumSpeakingOpening);
            return Mathf.Lerp(min, max, wave);
        }

        private void WarnMissingMouthControllerOnce()
        {
            if (!warnWhenMouthControllerMissing || warnedMissingMouthController)
            {
                return;
            }

            warnedMissingMouthController = true;
            Debug.LogWarning(
                "Live2D speaking mouth driver could not find a CubismMouthController. " +
                "Add CubismMouthController to the model root and make sure the model has a CubismMouthParameter.",
                this);
        }
    }
}
#endif
