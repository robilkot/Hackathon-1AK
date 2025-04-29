using System;
using System.Linq;
using System.Net.Http;
using System.Text.Json;
using System.Threading.Tasks;
using ConveyorCV_frontend.Models;

namespace ConveyorCV_frontend.Services
{
    public class ValidationLogService
    {
        private readonly HttpClient _httpClient;
        private readonly string _baseUrl;
        private readonly JsonSerializerOptions _jsonOptions;

        public event Action<string>? StatusChanged;
        public event Action<string>? ErrorOccurred;

        public ValidationLogService(string baseUrl = "localhost:8000")
        {
            _baseUrl = baseUrl;
            _httpClient = new HttpClient();
            _jsonOptions = new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true
            };
        }

        public async Task<ValidationLogResponseDTO?> GetLogsAsync(
            DateTimeOffset? startDate = null,
            DateTimeOffset? endDate = null,
            int page = 1,
            int pageSize = 10)
        {
            try
            {
                StatusChanged?.Invoke("Загрузка журнала...");

                var url = $"http://{_baseUrl}/validation/logs?page={page}&page_size={pageSize}";

                if (startDate.HasValue)
                    url += $"&start_date={startDate.Value:yyyy-MM-ddTHH:mm:ss}";

                if (endDate.HasValue)
                    url += $"&end_date={endDate.Value:yyyy-MM-ddTHH:mm:ss}";

                var response = await _httpClient.GetAsync(url);
                response.EnsureSuccessStatusCode();

                var json = await response.Content.ReadAsStringAsync();
                var logs = JsonSerializer.Deserialize<ValidationLogResponseDTO>(json, _jsonOptions);

                StatusChanged?.Invoke($"Загружено {logs?.Logs?.Count() ?? 0} записей");
                return logs;
            }
            catch (Exception ex)
            {
                var message = $"Ошибка загрузки журнала: {ex.Message}";
                Console.WriteLine(message);
                ErrorOccurred?.Invoke(message);
                return null;
            }
        }
        
        public async Task<bool> DeleteLogAsync(int logId)
        {
            try
            {
                StatusChanged?.Invoke($"Удаление записи #{logId}...");
        
                var response = await _httpClient.DeleteAsync($"http://{_baseUrl}/validation/logs/{logId}");
                response.EnsureSuccessStatusCode();
        
                StatusChanged?.Invoke($"Запись #{logId} успешно удалена");
                return true;
            }
            catch (Exception ex)
            {
                var message = $"Ошибка удаления записи: {ex.Message}";
                Console.WriteLine(message);
                ErrorOccurred?.Invoke(message);
                return false;
            }
        }
    }
}