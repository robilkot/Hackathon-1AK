using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

namespace ConveyorCV_frontend.Services
{
    public class ConveyorPhotoService
    {
        private readonly HttpClient _httpClient;
        private readonly string _baseUrl;
        
        public event Action<string>? StatusChanged;
        public event Action<string>? ErrorOccurred;

        public ConveyorPhotoService(string baseUrl = "localhost:8000")
        {
            _baseUrl = baseUrl;
            _httpClient = new HttpClient();
        }
        
        public async Task<bool> SaveEmptyConveyorPhotoAsync(string imageBase64)
        {
            try
            {
                if (string.IsNullOrEmpty(imageBase64))
                {
                    ErrorOccurred?.Invoke("Нет доступного изображения");
                    return false;
                }
                
                var payload = new { image = imageBase64 };
                
                var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");
                var response = await _httpClient.PostAsync($"http://{_baseUrl}/set-empty-conveyor", content);
                
                response.EnsureSuccessStatusCode();
                
                var responseString = await response.Content.ReadAsStringAsync();
                var options = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };
                var result = JsonSerializer.Deserialize<EmptyConveyorResponse>(responseString, options);
                
                if (result?.Success == true)
                {
                    StatusChanged?.Invoke("Фоновое изображение конвейера сохранено");
                    return true;
                }
                else
                {
                    ErrorOccurred?.Invoke(result?.Message ?? "Неизвестная ошибка");
                    return false;
                }
            }
            catch (Exception ex)
            {
                ErrorOccurred?.Invoke($"Ошибка сохранения фона: {ex.Message}");
                return false;
            }
        }
        
        private class EmptyConveyorResponse
        {
            public bool Success { get; set; }
            public string? Message { get; set; }
        }
    }
}