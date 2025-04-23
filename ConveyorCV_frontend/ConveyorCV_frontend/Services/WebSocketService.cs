using System;
using System.Collections.Generic;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Avalonia.Media.Imaging;
using System.IO;
using System.Net.Http;

namespace ConveyorCV_frontend.Services
{
    public class WebSocketService : IDisposable
    {
        private readonly Dictionary<string, ClientWebSocket> _webSockets = new();
        private readonly Dictionary<string, CancellationTokenSource> _tokenSources = new();
        private readonly string _baseUrl;
        private readonly HttpClient _httpClient;

        public event Action<string, Bitmap> ImageReceived;
        public event Action<string, object> EventReceived;
        public event Action<string, Exception> ErrorOccurred;
        public event Action<string> ConnectionClosed;

        public WebSocketService(string baseUrl = "localhost:8000")
        {
            _baseUrl = baseUrl;
            _httpClient = new HttpClient();
        }

        public async Task ConnectAsync(string path, string streamType)
        {
            // Disconnect if already connected
            await DisconnectAsync(streamType);
            
            // Create new connection
            var webSocket = new ClientWebSocket();
            var tokenSource = new CancellationTokenSource();
            var uri = new Uri($"ws://{_baseUrl}{path}");
            
            try
            {
                await webSocket.ConnectAsync(uri, tokenSource.Token);
                _webSockets[streamType] = webSocket;
                _tokenSources[streamType] = tokenSource;
                
                // Start receiving messages
                _ = ReceiveMessagesAsync(webSocket, tokenSource.Token, streamType);
            }
            catch (Exception ex)
            {
                ErrorOccurred?.Invoke(streamType, ex);
                throw;
            }
        }

        public async Task DisconnectAsync(string streamType)
        {
            if (_webSockets.TryGetValue(streamType, out var webSocket))
            {
                if (webSocket.State == WebSocketState.Open)
                {
                    try
                    {
                        // Send close handshake
                        var closeToken = new CancellationTokenSource(TimeSpan.FromSeconds(2)).Token;
                        await webSocket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Closing", closeToken);
                    }
                    catch { /* Ignore errors during close */ }
                }

                _tokenSources[streamType]?.Cancel();
                _webSockets.Remove(streamType);
                _tokenSources.Remove(streamType);
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
                ErrorOccurred?.Invoke("api", ex);
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
                ErrorOccurred?.Invoke("api", ex);
                throw;
            }
        }

        private async Task ReceiveMessagesAsync(ClientWebSocket webSocket, CancellationToken token, string streamType)
        {
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
                        ConnectionClosed?.Invoke(streamType);
                        break;
                    }

                    if (result.MessageType == WebSocketMessageType.Text)
                    {
                        memoryStream.Position = 0;
                        using var reader = new StreamReader(memoryStream, Encoding.UTF8);
                        string message = await reader.ReadToEndAsync();
                        
                        try
                        {
                            var jsonDoc = JsonDocument.Parse(message);
                            
                            // Handle image messages
                            if (jsonDoc.RootElement.TryGetProperty("image", out var imageProperty))
                            {
                                string base64Image = imageProperty.GetString();
                                if (!string.IsNullOrEmpty(base64Image))
                                {
                                    byte[] imageData = Convert.FromBase64String(base64Image);
                                    using var imageStream = new MemoryStream(imageData);
                                    var bitmap = new Bitmap(imageStream);
                                    ImageReceived?.Invoke(streamType, bitmap);
                                }
                            }
                            // Handle event messages
                            else if (jsonDoc.RootElement.TryGetProperty("type", out _))
                            {
                                var eventData = JsonSerializer.Deserialize<Dictionary<string, object>>(message);
                                EventReceived?.Invoke(streamType, eventData);
                            }
                        }
                        catch (Exception ex)
                        {
                            ErrorOccurred?.Invoke(streamType, 
                                new Exception($"Failed to parse message: {ex.Message}", ex));
                        }
                    }
                }
            }
            catch (OperationCanceledException)
            {
                // Normal cancellation, don't report as error
                ConnectionClosed?.Invoke(streamType);
            }
            catch (Exception ex)
            {
                if (!token.IsCancellationRequested)
                {
                    ErrorOccurred?.Invoke(streamType, ex);
                }
                ConnectionClosed?.Invoke(streamType);
            }
        }

        public void Dispose()
        {
            foreach (var streamType in new List<string>(_webSockets.Keys))
            {
                _tokenSources[streamType]?.Cancel();
                _webSockets[streamType]?.Dispose();
            }
            
            _webSockets.Clear();
            _tokenSources.Clear();
            _httpClient?.Dispose();
        }
    }
}