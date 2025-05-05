using ConveyorCV_frontend.Models;
using System;
using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

namespace ConveyorCV_frontend.Services
{
    public class WebSocketService : IDisposable
    {
        private readonly string _baseUrl;
        private readonly HttpClient _httpClient;

        private ClientWebSocket? _webSocket = null;
        private CancellationTokenSource? _tokenSource = null;

        public event Action<StreamingMessage>? MessageReceived;
        public event Action<Exception>? ErrorOccurred;
        public event Action? ConnectionClosed;

        public WebSocketService(string baseUrl = "localhost:8000")
        {
            _baseUrl = baseUrl;
            _httpClient = new HttpClient()
            {
                Timeout = TimeSpan.FromSeconds(5)
            };
        }

        public async Task ConnectAsync()
        {
            if (_webSocket is not null && _webSocket.State == WebSocketState.Open)
            {
                throw new InvalidOperationException();
            }

            _webSocket = new ClientWebSocket();
            _tokenSource = new CancellationTokenSource();
            var uri = new Uri($"ws://{_baseUrl}/ws");

            try
            {
                await _webSocket.ConnectAsync(uri, _tokenSource.Token);

                _ = ReceiveMessagesAsync(_webSocket, _tokenSource.Token);
            }
            catch (Exception ex)
            {
                ErrorOccurred?.Invoke(ex);
                throw;
            }
        }

        public async Task DisconnectAsync()
        {
            try
            {
                _tokenSource?.Cancel();

                if (_webSocket is not null && _webSocket.State == WebSocketState.Open)
                {
                    var closeToken = new CancellationTokenSource(TimeSpan.FromSeconds(2)).Token;
                    await _webSocket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Closing", closeToken);
                }

                _tokenSource?.Dispose();
                _tokenSource = null;
                _webSocket?.Dispose();
                _webSocket = null;
            }
            catch
            {
                /* Ignore errors during close */
            }
        }

        public async Task StartStreamAsync()
        {
            try
            {
                var response = await _httpClient.PostAsync($"http://{_baseUrl}/stream/start", null);
                response.EnsureSuccessStatusCode();
            }
            catch (Exception ex)
            {
                ErrorOccurred?.Invoke(ex);
                throw;
            }
        }

        public async Task StopStreamAsync()
        {
            try
            {
                var response = await _httpClient.PostAsync($"http://{_baseUrl}/stream/stop", null);
                response.EnsureSuccessStatusCode();
            }
            catch (Exception ex)
            {
                ErrorOccurred?.Invoke(ex);
                throw;
            }
        }

        private async Task ReceiveMessagesAsync(ClientWebSocket webSocket, CancellationToken token)
        {
            var options = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };

            var buffer = new byte[16384]; // Larger buffer for image data

            try
            {
                while (webSocket.State == WebSocketState.Open && !token.IsCancellationRequested)
                {
                    using var memoryStream = new MemoryStream();
                    WebSocketReceiveResult result;

                    do
                    {
                        result = await webSocket.ReceiveAsync(new ArraySegment<byte>(buffer), token);
                        if (result.Count > 0)
                            await memoryStream.WriteAsync(buffer, 0, result.Count, token);
                    } while (!result.EndOfMessage && !token.IsCancellationRequested);

                    if (token.IsCancellationRequested)
                        break;

                    if (result.MessageType == WebSocketMessageType.Close)
                    {
                        await webSocket.CloseOutputAsync(WebSocketCloseStatus.NormalClosure, "Closing", CancellationToken.None);
                        ConnectionClosed?.Invoke();
                        break;
                    }

                    if (result.MessageType == WebSocketMessageType.Text)
                    {
                        memoryStream.Position = 0;
                        using var reader = new StreamReader(memoryStream, Encoding.UTF8);
                        string json_message = await reader.ReadToEndAsync(token);
                        Debug.WriteLine(
                            $"[WebSocketService] Raw message: {json_message.Substring(0, Math.Min(json_message.Length, 200))}...");

                        try
                        {
                            var message = JsonSerializer.Deserialize<StreamingMessageDto>(json_message, options);
                            Debug.WriteLine($"[WebSocketService] Message envelope type: {message!.type}");

                            StreamingMessageContent content;

                            if (message.type == StreamingMessageType.VALIDATION)
                            {
                                Debug.WriteLine($"[WebSocketService] Processing VALIDATION message");
                                Debug.WriteLine(
                                    $"[WebSocketService] Content to deserialize: {message.content.Substring(0, Math.Min(message.content.Length, 200))}...");

                                var validationContent =
                                    JsonSerializer.Deserialize<ValidationStreamingMessageContent>(message.content,
                                        options);

                                Debug.WriteLine($"[WebSocketService] Validation deserialization result:");
                                Debug.WriteLine(
                                    $"  - Timestamp: {validationContent?.ValidationResult?.Timestamp}");
                                Debug.WriteLine(
                                    $"  - StickerPresent: {validationContent?.ValidationResult?.StickerPresent}");
                                Debug.WriteLine(
                                    $"  - StickerMatchesDesign: {validationContent?.ValidationResult?.StickerMatchesDesign}");
                                Debug.WriteLine(
                                    $"  - StickerPosition: {validationContent?.ValidationResult?.StickerPosition}");
                                Debug.WriteLine($"  - StickerSize: {validationContent?.ValidationResult?.StickerSize}");
                                Debug.WriteLine(
                                    $"  - StickerRotation: {validationContent?.ValidationResult?.StickerRotation}");
                                Debug.WriteLine($"  - SeqNumber: {validationContent?.ValidationResult?.SeqNumber}");
                                Debug.WriteLine(
                                    $"  - Image length: {validationContent?.ValidationResult?.Image?.Length ?? 0} bytes");

                                content = validationContent!;
                            }
                            else if (message.type == StreamingMessageType.RAW ||
                                     message.type == StreamingMessageType.SHAPE ||
                                     message.type == StreamingMessageType.PROCESSED)
                            {
                                Debug.WriteLine($"[WebSocketService] Processing {message.type} message");
                                content = JsonSerializer.Deserialize<ImageStreamingMessageContent>(message.content,
                                    options)!;
                                Debug.WriteLine(
                                    $"[WebSocketService] Image content length: {(content as ImageStreamingMessageContent)?.image?.Length ?? 0} chars");
                            }
                            else
                            {
                                throw new NotImplementedException($"Unsupported message type: {message.type}");
                            }

                            MessageReceived?.Invoke(new StreamingMessage() { Type = message.type, Content = content });
                            Debug.WriteLine($"[WebSocketService] Message processed and event fired");
                        }
                        catch (Exception ex)
                        {
                            Debug.WriteLine($"[WebSocketService] Failed to parse message: {ex.Message}");
                            Debug.WriteLine($"[WebSocketService] Exception details: {ex}");
                            ErrorOccurred?.Invoke(new Exception($"Failed to parse message: {ex.Message}", ex));
                        }
                    }
                }
            }
            catch (OperationCanceledException)
            {
                // Normal cancellation, don't report as error
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"WebSocket error: {ex.Message}");
                if (!token.IsCancellationRequested)
                {
                    ErrorOccurred?.Invoke(ex);
                }

            }
            finally
            {
                ConnectionClosed?.Invoke();
            }
        }

        public void Dispose()
        {
            _tokenSource?.Cancel();
            _tokenSource?.Dispose();
            _webSocket?.Dispose();
            _httpClient?.Dispose();
        }
    }
}