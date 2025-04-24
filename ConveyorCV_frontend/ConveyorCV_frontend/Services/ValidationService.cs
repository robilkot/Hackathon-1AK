using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Threading.Tasks;
using Avalonia.Media.Imaging;
using ConveyorCV_frontend.Models;

namespace ConveyorCV_frontend.Services
{
    public class ValidationService
    {
        private readonly WebSocketService _webSocketService;

        public event Action<Bitmap> ImageReceived;
        public event Action<ValidationResultDTO> ValidationResultReceived;
        public event Action<string> ErrorOccurred;

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
                    string eventType = GetJsonString(data, "type");
                    Console.WriteLine($"Event type: {eventType}");

                    if (eventType == "validation_result")
                    {
                        var result = new ValidationResultDTO
                        {
                            Type = eventType,
                            SeqNumber = GetJsonInt(data, "seq_number"),
                            Timestamp = GetJsonDouble(data, "timestamp"),
                            StickerPresent = GetJsonBool(data, "sticker_present"),
                            StickerMatchesDesign = GetJsonBool(data, "sticker_matches_design"),
                            Image = GetJsonString(data, "image")
                        };

                        Console.WriteLine($"Validation result: Present={result.StickerPresent}, " +
                            $"Matches={result.StickerMatchesDesign}, HasImage={!string.IsNullOrEmpty(result.Image)}");
                        
                        // Process image if present
                        if (!string.IsNullOrEmpty(result.Image))
                        {
                            try
                            {
                                var bitmap = ConvertBase64ToBitmap(result.Image);
                                if (bitmap != null)
                                {
                                    Console.WriteLine("Image decoded successfully");
                                    ImageReceived?.Invoke(bitmap);
                                }
                            }
                            catch (Exception ex)
                            {
                                Console.WriteLine($"Image conversion error: {ex.Message}");
                            }
                        }

                        ValidationResultReceived?.Invoke(result);
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error processing event: {ex.Message}");
                ErrorOccurred?.Invoke($"Error processing event: {ex.Message}");
            }
        }

        private bool GetJsonBool(Dictionary<string, object> data, string key)
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
            return false;
        }

        private string GetJsonString(Dictionary<string, object> data, string key)
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

        private int GetJsonInt(Dictionary<string, object> data, string key)
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
            return 0;
        }

        private double GetJsonDouble(Dictionary<string, object> data, string key)
        {
            if (data.TryGetValue(key, out var value))
            {
                if (value is double doubleVal)
                    return doubleVal;
                else if (value is JsonElement jsonElement)
                {
                    if (jsonElement.ValueKind == JsonValueKind.Number)
                        return jsonElement.GetDouble();
                    else if (jsonElement.ValueKind == JsonValueKind.String && 
                             double.TryParse(jsonElement.GetString(), out var parsed))
                        return parsed;
                    return 0;
                }
                else if (value != null && double.TryParse(value.ToString(), out var result))
                    return result;
            }
            return 0;
        }

        private Bitmap ConvertBase64ToBitmap(string base64String)
        {
            try
            {
                byte[] bytes = Convert.FromBase64String(base64String);
                using (var ms = new MemoryStream(bytes))
                {
                    return new Bitmap(ms);
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error converting base64 to bitmap: {ex.Message}");
                return null;
            }
        }
    }
}