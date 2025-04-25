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
            _httpClient = new HttpClient();
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
            if (_webSocket is not null && _webSocket.State == WebSocketState.Open)
            {
                try
                {
                    var closeToken = new CancellationTokenSource(TimeSpan.FromSeconds(2)).Token;
                    await _webSocket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Closing", closeToken);
                }
                catch { /* Ignore errors during close */ }
            }

            _tokenSource?.Cancel();
            _tokenSource?.Dispose();
            _tokenSource = null;
            _webSocket?.Dispose();
            _webSocket = null;
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

                        try
                        {
                            var message = JsonSerializer.Deserialize<StreamingMessageDto>(json_message, options);

                            StreamingMessageContent content = message!.type switch
                            {
                                StreamingMessageType.VALIDATION => JsonSerializer.Deserialize<ValidationStreamingMessageContent>(message.content, options)!,
                                StreamingMessageType.RAW or StreamingMessageType.SHAPE or StreamingMessageType.PROCESSED
                                    => JsonSerializer.Deserialize<ImageStreamingMessageContent>(message.content, options)!,
                                _ => throw new NotImplementedException()
                            };

                            MessageReceived?.Invoke(new StreamingMessage() { Type = message.type, Content = content });
                        }
                        catch (Exception ex)
                        {
                            Debug.WriteLine($"Failed to parse message: {ex.Message}");
                            ErrorOccurred?.Invoke(new Exception($"Failed to parse message: {ex.Message}", ex));
                        }
                    }
                }
            }
            catch (OperationCanceledException)
            {
                // Normal cancellation, don't report as error
                ConnectionClosed?.Invoke();
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"WebSocket error: {ex.Message}");
                if (!token.IsCancellationRequested)
                {
                    ErrorOccurred?.Invoke(ex);
                }
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