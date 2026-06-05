using System;
using System.Collections.Generic;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace ProjectSENA.Protocol
{
    [Serializable]
    public sealed class SenaEnvelope
    {
        public string protocol_version = "0.1";
        public string type = string.Empty;
        public string message_id = string.Empty;
        public string session_id = string.Empty;
        public string timestamp = string.Empty;
        public string source = string.Empty;
        public JObject payload = new JObject();

        public T ToPayload<T>()
        {
            return payload.ToObject<T>()!;
        }
    }

    [Serializable]
    public sealed class SenaBatchResponse
    {
        public List<SenaEnvelope> messages = new List<SenaEnvelope>();
    }

    [Serializable]
    public sealed class UserTextPayload
    {
        public string text = string.Empty;
        public string language = "ko";
        public string input_mode = "typed";
    }

    [Serializable]
    public sealed class ApprovalResultPayload
    {
        public bool approved;
        public string decision_reason = string.Empty;
    }

    [Serializable]
    public sealed class AssistantTextPayload
    {
        public string text = string.Empty;
        public string display_text = string.Empty;
        public string persona_state = string.Empty;
        public bool should_speak;
    }

    [Serializable]
    public sealed class AssistantStatePayload
    {
        public string state = string.Empty;
        public string detail = string.Empty;
    }

    [Serializable]
    public sealed class ApprovalRequestPayload
    {
        public string tool_name = string.Empty;
        public string reason = string.Empty;
        public string risk_level = string.Empty;
        public string prompt = string.Empty;
        public Dictionary<string, object> arguments = new Dictionary<string, object>();
    }

    [Serializable]
    public sealed class ToolResultPayload
    {
        public string tool_name = string.Empty;
        public string status = string.Empty;
        public Dictionary<string, object> result = new Dictionary<string, object>();
        public string error_message = string.Empty;
    }

    [Serializable]
    public sealed class ErrorPayload
    {
        public string code = string.Empty;
        public string message = string.Empty;
        public bool retryable;
    }

    public static class SenaRequestFactory
    {
        public static SenaEnvelope CreateUserText(
            string sessionId,
            string text,
            string language)
        {
            return CreateEnvelope(
                "user_text",
                sessionId,
                "unity-client",
                JObject.FromObject(new UserTextPayload
                {
                    text = text,
                    language = language,
                    input_mode = "typed"
                }));
        }

        public static SenaEnvelope CreateApprovalResult(
            string sessionId,
            bool approved,
            string decisionReason)
        {
            return CreateEnvelope(
                "approval_result",
                sessionId,
                "unity-client",
                JObject.FromObject(new ApprovalResultPayload
                {
                    approved = approved,
                    decision_reason = decisionReason
                }));
        }

        private static SenaEnvelope CreateEnvelope(
            string type,
            string sessionId,
            string source,
            JObject payload)
        {
            return new SenaEnvelope
            {
                protocol_version = "0.1",
                type = type,
                message_id = $"msg-{Guid.NewGuid():N}",
                session_id = sessionId,
                timestamp = DateTime.UtcNow.ToString("O"),
                source = source,
                payload = payload
            };
        }
    }

    public static class SenaJson
    {
        public static string Serialize(object value)
        {
            return JsonConvert.SerializeObject(value);
        }

        public static SenaBatchResponse DeserializeBatch(string json)
        {
            return JsonConvert.DeserializeObject<SenaBatchResponse>(json) ?? new SenaBatchResponse();
        }
    }
}
