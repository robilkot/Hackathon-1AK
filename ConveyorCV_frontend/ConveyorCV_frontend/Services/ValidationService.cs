using ConveyorCV_frontend.Models;
using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Threading.Tasks;

namespace ConveyorCV_frontend.Services
{
    public class ValidationService
    {
        private readonly WebSocketService _webSocketService;

        public event Action<StickerValidationResult> ValidationResultReceived;

        public ValidationService(WebSocketService webSocketService)
        {
            _webSocketService = webSocketService;
            _webSocketService.EventReceived += OnEventReceived;
        }

        public async Task ConnectAsync()
        {
            Console.WriteLine("Connecting to events WebSocket...");
            await _webSocketService.ConnectAsync("/ws/events", "events");
        }

        public async Task DisconnectAsync()
        {
            await _webSocketService.DisconnectAsync("events");
        }

        private void OnEventReceived(string streamType, object eventData)
        {
            Console.WriteLine($"Event received from {streamType}");

            if (streamType != "events")
                return;

            try
            {
                if (eventData is Dictionary<string, object> data)
                {
                    string eventType = data.GetString("type")!;
                    Console.WriteLine($"Event type: {eventType}");

                    if (eventType == "validation_result")
                    {
                        var result = new StickerValidationResult(
                            Convert.FromBase64String(data.GetString("image")!),
                            DateTimeOffset.Now, //(data, "timestamp"),
                            data.GetInt("seq_number")!.Value,
                            data.GetBool("sticker_present")!.Value,
                            data.GetBool("sticker_matches_design"),
                            new(), // todo
                            new(), // todo
                            data.GetDouble("rotation")
                        );

                        ValidationResultReceived?.Invoke(result);
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error processing event: {ex.Message}");
                // todo handle
            }
        }
    }

    public static class JsonExtensisons
    {
        public static string? GetString(this Dictionary<string, object> data, string key)
        {
            if (data.TryGetValue(key, out var value))
            {
                if (value is string strVal)
                    return strVal;
                else if (value is JsonElement jsonElement && jsonElement.ValueKind == JsonValueKind.String)
                    return jsonElement.GetString();
                else
                    return value?.ToString();
            }

            return null;
        }

        public static int? GetInt(this Dictionary<string, object> data, string key)
        {
            if (data.TryGetValue(key, out var value))
            {
                if (value is int intVal)
                    return intVal;
                else if (value is JsonElement jsonElement && jsonElement.ValueKind == JsonValueKind.Number)
                    return jsonElement.GetInt32();
                else if (value != null)
                    return int.TryParse(value.ToString(), out var result) ? result : 0;
            }

            return null;
        }

        public static double? GetDouble(this Dictionary<string, object> data, string key)
        {
            if (data.TryGetValue(key, out var value))
            {
                if (value is double doubleVal)
                    return doubleVal;
                else if (value is JsonElement jsonElement && jsonElement.ValueKind == JsonValueKind.Number)
                    return jsonElement.GetDouble();
                else if (value != null)
                    return double.TryParse(value.ToString(), out var result) ? result : 0;
            }

            return null;
        }

        public static bool? GetBool(this Dictionary<string, object> data, string key)
        {
            if (data.TryGetValue(key, out var value))
            {
                if (value is bool boolVal)
                    return boolVal;
                else if (value is JsonElement jsonElement)
                {
                    if (jsonElement.ValueKind == JsonValueKind.True)
                        return true;
                    else if (jsonElement.ValueKind == JsonValueKind.False)
                        return false;
                    else if (jsonElement.ValueKind == JsonValueKind.String)
                        return bool.TryParse(jsonElement.GetString(), out var result) && result;
                    else if (jsonElement.ValueKind == JsonValueKind.Number)
                        return jsonElement.GetInt32() != 0;
                }
            }

            return null;
        }
    };
}