using ConveyorCV_frontend.Models;
using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

namespace ConveyorCV_frontend.Services
{
    public class SettingsService
    {
        private readonly HttpClient _httpClient;
        private readonly string _baseUrl;
        private readonly JsonSerializerOptions _jsonOptions;

        public event Action<string>? StatusChanged;
        public event Action<string>? ErrorOccurred;

        public SettingsService(string baseUrl = "localhost:8000")
        {
            _baseUrl = baseUrl;
            _httpClient = new HttpClient()
            {
                Timeout = TimeSpan.FromSeconds(10)
            };
            _jsonOptions = new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true
            };
        }

        public async Task<SettingsDTO?> GetSettingsAsync()
        {
            try
            {
                var response = await _httpClient.GetAsync($"http://{_baseUrl}/settings/");
                response.EnsureSuccessStatusCode();
                
                var json = await response.Content.ReadAsStringAsync();
                Console.WriteLine($"Json: {json}");
                var settings = JsonSerializer.Deserialize<SettingsDTO>(json, _jsonOptions);
                Console.WriteLine($"Settings: {settings}");
                StatusChanged?.Invoke("Настройки успешно загружены");
                return settings;
            }
            catch (Exception ex)
            {
                ErrorOccurred?.Invoke($"Ошибка при загрузке настроек: {ex.Message}");
                return null;
            }
        }

        public async Task<bool> ApplySettingsAsync(SettingsDTO settings)
        {
            try
            {
                var json = JsonSerializer.Serialize(settings, _jsonOptions);
                Console.WriteLine("Json: {0}", json);
                var content = new StringContent(json, Encoding.UTF8, "application/json");
                
                var response = await _httpClient.PostAsync($"http://{_baseUrl}/settings/apply", content);
                response.EnsureSuccessStatusCode();
                
                var result = await response.Content.ReadAsStringAsync();
                var responseObj = JsonSerializer.Deserialize<dynamic>(result, _jsonOptions);
                
                StatusChanged?.Invoke("Настройки успешно применены");
                return true;
            }
            catch (Exception ex)
            {
                ErrorOccurred?.Invoke($"Ошибка при применении настроек: {ex.Message}");
                return false;
            }
        }
    }
}