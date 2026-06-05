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

        public SenaApiClient(string baseUrl)
        {
            _baseUrl = baseUrl.TrimEnd('/');
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
            request.SetRequestHeader("Content-Type", "application/json; charset=utf-8");

            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success)
            {
                onError?.Invoke(request.error);
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
    }
}
