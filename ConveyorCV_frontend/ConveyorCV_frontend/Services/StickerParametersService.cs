using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using ConveyorCV_frontend.Models;

namespace ConveyorCV_frontend.Services
{
    public class StickerParametersService
    {
        private readonly HttpClient _httpClient;
        private readonly string _baseUrl;
        private readonly JsonSerializerOptions _jsonOptions;

        public event Action<string> ErrorOccurred;
        public event Action<string> StatusChanged;

        public StickerParametersService(string baseUrl = "localhost:8000")
        {
            _baseUrl = baseUrl;
            _httpClient = new HttpClient();
            _jsonOptions = new JsonSerializerOptions
            {
                PropertyNamingPolicy = JsonNamingPolicy.CamelCase
            };
        }

        public async Task<bool> SetParametersAsync(StickerParametersDTO parameters)
        {
            try
            {
                StatusChanged?.Invoke("Отправка параметров наклейки...");

                var json = JsonSerializer.Serialize(parameters, _jsonOptions);
                Console.WriteLine($"Sending parameters: {json}");
                var content = new StringContent(json, Encoding.UTF8, "application/json");

                var response = await _httpClient.PostAsync($"http://{_baseUrl}/sticker/parameters", content);
                var responseBody = await response.Content.ReadAsStringAsync();
                Console.WriteLine($"Response: {responseBody}");
                
                response.EnsureSuccessStatusCode();
                
                StatusChanged?.Invoke("Параметры наклейки успешно установлены");
                return true;
            }
            catch (Exception ex)
            {
                var message = $"Ошибка отправки параметров: {ex.Message}";
                Console.WriteLine(message);
                ErrorOccurred?.Invoke(message);
                return false;
            }
        }

        // Helper method for converting image to base64
        public static string ImageToBase64(string imagePath)
        {
            try
            {
                byte[] imageBytes = System.IO.File.ReadAllBytes(imagePath);
                return Convert.ToBase64String(imageBytes);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error converting image to base64: {ex.Message}");
                return null;
            }
        }
    }
}