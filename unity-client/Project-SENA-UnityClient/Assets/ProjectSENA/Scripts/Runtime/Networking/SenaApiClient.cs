using System;
using System.Collections;
using System.Text;
using ProjectSENA.Protocol;
using UnityEngine;
using UnityEngine.Networking;

namespace ProjectSENA.Networking
{
    public sealed class SenaApiClient
    {
        private readonly string _baseUrl;
        private readonly int _timeoutSeconds;

        public SenaApiClient(string baseUrl, int timeoutSeconds = 8)
        {
            _baseUrl = baseUrl.TrimEnd('/');
            _timeoutSeconds = timeoutSeconds;
        }

        public IEnumerator PostMessage(
            SenaEnvelope message,
            Action<SenaBatchResponse> onSuccess,
            Action<string> onError)
        {
            string url = $"{_baseUrl}/v1/messages";
            string json = SenaJson.Serialize(message);
            byte[] body = Encoding.UTF8.GetBytes(json);

            using UnityWebRequest request = new UnityWebRequest(url, UnityWebRequest.kHttpVerbPOST);
            request.uploadHandler = new UploadHandlerRaw(body);
            request.downloadHandler = new DownloadHandlerBuffer();
            request.timeout = _timeoutSeconds;
            request.SetRequestHeader("Content-Type", "application/json; charset=utf-8");

            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success)
            {
                onError?.Invoke(BuildErrorMessage(request));
                yield break;
            }

            try
            {
                SenaBatchResponse response = SenaJson.DeserializeBatch(request.downloadHandler.text);
                onSuccess?.Invoke(response);
            }
            catch (Exception ex)
            {
                onError?.Invoke($"Failed to parse server response: {ex.Message}");
            }
        }

        private static string BuildErrorMessage(UnityWebRequest request)
        {
            if (request.result == UnityWebRequest.Result.ConnectionError)
            {
                return $"Connection failed: {request.error}";
            }

            if (request.result == UnityWebRequest.Result.ProtocolError)
            {
                return $"HTTP {(long)request.responseCode}: {request.downloadHandler?.text}";
            }

            if (request.result == UnityWebRequest.Result.DataProcessingError)
            {
                return $"Response processing failed: {request.error}";
            }

            return request.error;
        }
    }
}
