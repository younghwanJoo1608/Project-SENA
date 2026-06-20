#if PROJECT_SENA_LIVE2D
using System;
using Live2D.Cubism.Core;
using Live2D.Cubism.Framework;
using UnityEngine;

namespace ProjectSENA.Character
{
    [DisallowMultipleComponent]
    public sealed class Live2DProceduralIdleDriver : MonoBehaviour, ICubismUpdatable
    {
        [Header("Playback")]
        [SerializeField] private bool playOnStart = true;
        [SerializeField] private float globalWeight = 1f;
        [SerializeField] private IdleParameterBinding[] parameters =
        {
            new IdleParameterBinding("ParamAngleX", 3f, 0.12f, 0f),
            new IdleParameterBinding("ParamAngleY", 2f, 0.10f, 0.25f),
            new IdleParameterBinding("ParamAngleZ", 1.5f, 0.08f, 0.5f),
            new IdleParameterBinding("ParamBodyAngleX", 2f, 0.08f, 0.15f),
            new IdleParameterBinding("ParamBodyAngleY", 1f, 0.06f, 0.35f),
            new IdleParameterBinding("ParamBreath", 0.25f, 0.22f, 0f)
        };

        [Header("Diagnostics")]
        [SerializeField] private bool warnWhenNoParametersFound = true;

        private ResolvedIdleParameter[] resolvedParameters = Array.Empty<ResolvedIdleParameter>();
        private bool isPlaying;
        private bool warnedNoParameters;

        [HideInInspector] public bool HasUpdateController { get; set; }

        public int ExecutionOrder => CubismUpdateExecutionOrder.CubismHarmonicMotionController + 1;
        public bool NeedsUpdateOnEditing => false;

        private void Start()
        {
            Refresh();
            isPlaying = playOnStart;
        }

        private void LateUpdate()
        {
            if (!HasUpdateController)
            {
                OnLateUpdate();
            }
        }

        public void OnLateUpdate()
        {
            if (!enabled || !isPlaying || resolvedParameters.Length == 0)
            {
                return;
            }

            float time = Time.time;
            float weight = Mathf.Clamp01(globalWeight);
            for (int i = 0; i < resolvedParameters.Length; i++)
            {
                ResolvedIdleParameter item = resolvedParameters[i];
                float phase = (time * item.FrequencyHz * Mathf.PI * 2f) + item.PhaseRadians;
                float value = Mathf.Sin(phase) * item.Amplitude;
                item.Parameter.BlendToValue(CubismParameterBlendMode.Additive, value, weight);
            }
        }

        [ContextMenu("SENA/Refresh Procedural Idle Parameters")]
        public void Refresh()
        {
            HasUpdateController = GetComponent<CubismUpdateController>() != null;

            if (parameters == null || parameters.Length == 0)
            {
                resolvedParameters = Array.Empty<ResolvedIdleParameter>();
                return;
            }

            var resolved = new System.Collections.Generic.List<ResolvedIdleParameter>();
            for (int i = 0; i < parameters.Length; i++)
            {
                IdleParameterBinding binding = parameters[i];
                if (string.IsNullOrWhiteSpace(binding.parameterId) ||
                    Mathf.Approximately(binding.amplitude, 0f) ||
                    binding.frequencyHz <= 0f)
                {
                    continue;
                }

                CubismParameter parameter = FindParameter(binding.parameterId);
                if (parameter == null)
                {
                    continue;
                }

                float clampedAmplitude = ClampAmplitude(parameter, Mathf.Abs(binding.amplitude));
                if (Mathf.Approximately(clampedAmplitude, 0f))
                {
                    continue;
                }

                resolved.Add(new ResolvedIdleParameter(
                    parameter,
                    clampedAmplitude,
                    binding.frequencyHz,
                    binding.phaseOffset * Mathf.PI * 2f));
            }

            resolvedParameters = resolved.ToArray();

            if (resolvedParameters.Length == 0)
            {
                WarnNoParametersOnce();
            }
        }

        [ContextMenu("SENA/Start Procedural Idle")]
        public void StartIdle()
        {
            isPlaying = true;
        }

        [ContextMenu("SENA/Stop Procedural Idle")]
        public void StopIdle()
        {
            isPlaying = false;
        }

        private CubismParameter FindParameter(string parameterId)
        {
            Transform parameterTransform = transform.Find($"Parameters/{parameterId}");
            if (parameterTransform != null &&
                parameterTransform.TryGetComponent(out CubismParameter directParameter))
            {
                return directParameter;
            }

            CubismParameter[] allParameters = GetComponentsInChildren<CubismParameter>(includeInactive: true);
            for (int i = 0; i < allParameters.Length; i++)
            {
                CubismParameter candidate = allParameters[i];
                if (candidate != null &&
                    string.Equals(candidate.Id, parameterId, StringComparison.Ordinal))
                {
                    return candidate;
                }
            }

            return null;
        }

        private static float ClampAmplitude(CubismParameter parameter, float amplitude)
        {
            float defaultValue = parameter.DefaultValue;
            float positiveRoom = parameter.MaximumValue - defaultValue;
            float negativeRoom = defaultValue - parameter.MinimumValue;
            float availableRoom = Mathf.Max(0f, Mathf.Max(positiveRoom, negativeRoom));
            return Mathf.Min(amplitude, availableRoom);
        }

        private void WarnNoParametersOnce()
        {
            if (!warnWhenNoParametersFound || warnedNoParameters)
            {
                return;
            }

            warnedNoParameters = true;
            Debug.LogWarning(
                "Live2D procedural idle found no supported parameters. " +
                "Check that this model has ParamAngleX/Y/Z, ParamBodyAngleX/Y, or ParamBreath.",
                this);
        }

        [Serializable]
        public struct IdleParameterBinding
        {
            public string parameterId;
            public float amplitude;
            public float frequencyHz;
            public float phaseOffset;

            public IdleParameterBinding(string parameterId, float amplitude, float frequencyHz, float phaseOffset)
            {
                this.parameterId = parameterId;
                this.amplitude = amplitude;
                this.frequencyHz = frequencyHz;
                this.phaseOffset = phaseOffset;
            }
        }

        private readonly struct ResolvedIdleParameter
        {
            public ResolvedIdleParameter(
                CubismParameter parameter,
                float amplitude,
                float frequencyHz,
                float phaseRadians)
            {
                Parameter = parameter;
                Amplitude = amplitude;
                FrequencyHz = frequencyHz;
                PhaseRadians = phaseRadians;
            }

            public CubismParameter Parameter { get; }
            public float Amplitude { get; }
            public float FrequencyHz { get; }
            public float PhaseRadians { get; }
        }
    }
}
#endif
